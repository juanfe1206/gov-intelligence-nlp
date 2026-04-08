# Story 5.2: First Platform Connector (Offline-First + Checkpointing)

Status: review

## Story

As an admin or technical owner,
I want one real platform connector implemented in this repo with incremental checkpointing,
so that I can collect new posts between runs without re-downloading the entire dataset.

## Acceptance Criteria

1. **Given** connector configuration is provided (file path, query params, limits)
   **When** the admin triggers `POST /connectors/{connector_id}/run`
   **Then** the connector fetches records from the selected source and persists normalized results into the raw ingestion path
   **And** a checkpoint (last processed timestamp) is stored and used on subsequent runs

2. **Given** a previous successful run exists
   **When** the connector is run again
   **Then** only records newer than the checkpoint are requested
   **And** duplicate records (by `platform + external_id`) are skipped

## Tasks / Subtasks

### Task 1 — DB Migration: `external_id` column + checkpoint table (AC: #1, #2)

- [x] Create `backend/alembic/versions/004_add_connector_support.py`:
  - [x] Add `external_id` column to `raw_posts` (String(255), nullable=True) — backward-compatible with existing CSV rows which have no external_id
  - [x] Add **partial** unique index `uq_raw_posts_platform_external_id` on `(platform, external_id) WHERE external_id IS NOT NULL` — prevents duplicate connector posts without touching CSV-ingested rows
  - [x] Create `connector_checkpoints` table:
    - `connector_id` VARCHAR(255) PRIMARY KEY
    - `checkpoint_data` JSONB NOT NULL
    - `updated_at` TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
  - [x] Implement idempotent `upgrade()` with `_has_column` / `_has_index` / table existence guards (follow pattern in `003_add_processing_columns_and_job_type.py`)
  - [x] Implement `downgrade()` that reverses all changes

### Task 2 — Update `RawPost` model (AC: #2)

- [x] Add `external_id = Column(String(255), nullable=True)` to `backend/app/models/raw_post.py`
  - [x] Place after `content_hash` field, before `author`
  - [x] No other changes to the model

### Task 3 — `ConnectorCheckpoint` model (AC: #1)

- [x] Create `backend/app/models/connector_checkpoint.py`:
  - [x] `ConnectorCheckpoint(Base)` ORM model matching the `connector_checkpoints` table
  - [x] Fields: `connector_id` (String PK), `checkpoint_data` (JSONB), `updated_at` (DateTime timezone=True)
- [x] Export from `backend/app/models/__init__.py` if that file exists; otherwise no action needed

### Task 4 — `TwitterFileConnector` — concrete platform connector (AC: #1, #2)

- [x] Create `backend/app/connectors/twitter_file.py`:
  - [x] Class `TwitterFileConnector(BaseConnector)`:
    - `connector_id = "twitter-file"` (class attribute)
    - Constructor: `__init__(self, file_path: str, after_timestamp: datetime | None = None)`
      - `self._file_path = Path(file_path)`
      - `self._after_timestamp = after_timestamp`  — checkpoint cutoff for incremental runs
      - `self._last_seen_at: datetime | None = None`  — tracks max `created_at` seen during this run
  - [x] `fetch(self) -> list[dict[str, Any]]`:
    - Read `self._file_path` as JSONL (one JSON object per line, skip blank lines and comment lines starting with `#`)
    - If `self._after_timestamp` is set, filter out records where `created_at <= self._after_timestamp`
    - Return raw dicts
    - Raise `FileNotFoundError` with clear message if file not found
  - [x] `normalize(self, raw: dict[str, Any]) -> NormalizedPost | None`:
    - Map Twitter JSONL fields:
      - `external_id` ← `raw["id"]` or `raw["id_str"]` (str)
      - `text` ← `raw.get("full_text") or raw.get("text", "")` — prefer `full_text` (untruncated)
      - `author` ← `raw.get("user", {}).get("screen_name")` or `raw.get("author")` (nullable)
      - `created_at` ← parse `raw["created_at"]` using `_parse_twitter_date()` helper
      - `platform` = `"twitter"` (constant)
      - `source` = `self.connector_id`
      - `raw_payload` = full `raw` dict
    - Return `None` if `text` is empty or `id`/`created_at` are missing
    - Track max seen timestamp: `if post.created_at > self._last_seen_at: self._last_seen_at = post.created_at`
  - [x] `checkpoint(self) -> dict[str, Any]`:
    - Return `{"last_seen_at": self._last_seen_at.isoformat() if self._last_seen_at else None}`
  - [x] Private `_parse_twitter_date(value: str) -> datetime`:
    - Parse Twitter API date format: `"Thu Apr 01 12:00:00 +0000 2021"` (strptime: `"%a %b %d %H:%M:%S %z %Y"`)
    - Also accept ISO 8601 format (fallback using existing ingestion `_parse_timestamp` logic)
    - Always return timezone-aware datetime in UTC
    - Raise `ValueError` if unparseable

### Task 5 — Connector service layer (AC: #1, #2)

- [x] Create `backend/app/connectors/service.py`:
  - [x] `async def run_connector(session: AsyncSession, connector: BaseConnector) -> ConnectorRunSummary`:
    - Load checkpoint from DB: `SELECT * FROM connector_checkpoints WHERE connector_id = connector.connector_id`
    - If checkpoint exists, extract `last_seen_at` and pass to connector (set `connector._after_timestamp`)
    - Create `ConnectorRunSummary(connector_id=connector.connector_id, mode="live", started_at=datetime.now(UTC))`
    - Create running `IngestionJob` record (job_type=`"connector"`, source=`connector.connector_id`, status=`"running"`)
    - Call `raw_records = connector.fetch()`
    - Call `posts = validate_and_normalize(connector, raw_records, summary)`
    - Call `await ingest_normalized_posts_with_external_id(session, posts, summary)` — (see Task 6)
    - Set `summary.finished_at = datetime.now(UTC)`
    - Determine job status: `"completed"` if no validation errors OR `"partial"` if some rejected, `"failed"` if all rejected with 0 inserted
    - Save checkpoint: upsert `connector_checkpoints` with `connector.checkpoint()` data
    - Update `IngestionJob` record with final counts
    - Return `summary`
  - [x] `async def get_checkpoint(session: AsyncSession, connector_id: str) -> dict | None`:
    - Query `connector_checkpoints` table and return `checkpoint_data` or `None`

### Task 6 — Update `ingest_normalized_posts` for `external_id` deduplication (AC: #2)

- [x] In `backend/app/connectors/validator.py`, update `ingest_normalized_posts` to also write `external_id`:
  - Add `external_id=post.external_id` to the `.values(...)` in `pg_insert(RawPost)` call
  - Keep `on_conflict_do_nothing(index_elements=["source", "content_hash"])` as primary dedupe (content-based)
  - The partial unique index `(platform, external_id)` on the DB level provides secondary dedup protection

### Task 7 — API router `POST /connectors/{connector_id}/run` (AC: #1)

- [x] Create `backend/app/api/connectors.py`:
  - [x] `router = APIRouter()`
  - [x] Request schema `ConnectorRunRequest(BaseModel)`: `file_path: str | None = None` (override default path)
  - [x] Response schema `ConnectorRunResponse(BaseModel)`: mirror `ConnectorRunSummary` fields as JSON-serializable response (use `str` for datetimes, `int` for counts, `list[dict]` for errors)
  - [x] `POST /{connector_id}/run` endpoint:
    - Validate `connector_id` — currently only `"twitter-file"` is supported; return 400 for unknown
    - Resolve `file_path`: use request body `file_path` if provided, else `settings.CONNECTOR_TWITTER_FILE_PATH`
    - Instantiate `TwitterFileConnector(file_path=resolved_path)`
    - Load checkpoint from DB and inject `after_timestamp` onto the connector instance
    - Call `summary = await run_connector(session, connector)`
    - Return `ConnectorRunResponse` from summary
    - On `FileNotFoundError`: return 400 with clear message
    - On unexpected error: log + return 500

### Task 8 — Register connector router in `main.py`

- [x] In `backend/app/main.py`:
  - Add import: `from app.api.connectors import router as connectors_router`
  - Add: `app.include_router(connectors_router, prefix="/connectors", tags=["connectors"])`
  - Place after `jobs_router` line (line 91)

### Task 9 — Add `CONNECTOR_TWITTER_FILE_PATH` to settings

- [x] In `backend/app/config.py`, add:
  ```python
  CONNECTOR_TWITTER_FILE_PATH: str = "data/twitter_posts.jsonl"
  ```
  under the ingestion configuration section

### Task 10 — Tests (AC: #1, #2)

- [x] Create `backend/tests/connectors/test_twitter_file_connector.py`:
  - [x] Use `tmp_path` pytest fixture to create test JSONL files
  - [x] Test `TwitterFileConnector.fetch()` with valid JSONL → returns list of dicts
  - [x] Test `TwitterFileConnector.fetch()` with `after_timestamp` set → only newer records returned
  - [x] Test `TwitterFileConnector.normalize()` with valid Twitter record → returns `NormalizedPost` with correct fields
  - [x] Test `TwitterFileConnector.normalize()` with missing `id` → returns `None`
  - [x] Test `TwitterFileConnector.normalize()` with missing/empty `text` → returns `None`
  - [x] Test `TwitterFileConnector.checkpoint()` after processing → returns `last_seen_at` timestamp
  - [x] Test `_parse_twitter_date()` with Twitter API format string → correct UTC datetime
- [x] Create `backend/tests/connectors/test_connector_service.py`:
  - [x] Use mocked DB session and mock `validate_and_normalize`, `ingest_normalized_posts` to test orchestration logic
  - [x] Test full run: no prior checkpoint → processes all records, saves new checkpoint
  - [x] Test incremental run: prior checkpoint exists → connector receives `after_timestamp`
  - [x] Test duplicate handling: all records already ingested → summary shows 0 inserted, N duplicates

## Dev Notes

### Platform Choice: TwitterFileConnector

The first connector reads from a local **JSONL file** (one JSON object per line) containing Twitter-format posts. This is "offline-first": no live API calls, no credentials required for the MVP. The file is read from `CONNECTOR_TWITTER_FILE_PATH` (default: `data/twitter_posts.jsonl`).

Twitter JSONL format (from archive exports or third-party scrapers):
```json
{"id": "1234567890", "full_text": "...", "user": {"screen_name": "politico_es"}, "created_at": "Thu Apr 01 12:00:00 +0000 2021", "lang": "es"}
```

Alternative fields to handle: `text` (truncated, present if `full_text` absent), `id_str` (same as `id`), `author` (non-standard, accept if present).

### Checkpoint Strategy

Checkpoint is stored in `connector_checkpoints` table as JSONB:
```json
{"last_seen_at": "2021-04-01T12:00:00+00:00"}
```

On each run:
1. Load checkpoint → get `last_seen_at`
2. Instantiate connector with `after_timestamp = last_seen_at`
3. `fetch()` filters out records where `created_at <= after_timestamp`
4. After ingestion, `connector.checkpoint()` returns new `last_seen_at` (max `created_at` seen in this run)
5. Upsert checkpoint in DB

If no checkpoint exists → full load (process all records).

### DB Migration: Partial Unique Index for `external_id`

The existing `raw_posts` table has CSV-ingested rows with `external_id = NULL`. Adding a standard unique constraint on `(platform, external_id)` would make all NULL-external_id rows conflict with each other (PostgreSQL: NULL is distinct from NULL in unique indexes, so this is actually fine with partial index). Use a **partial unique index** `WHERE external_id IS NOT NULL` for safety:

```sql
CREATE UNIQUE INDEX uq_raw_posts_platform_external_id
ON raw_posts (platform, external_id)
WHERE external_id IS NOT NULL;
```

Primary deduplication remains `(source, content_hash)` — this is the `ON CONFLICT DO NOTHING` target. The `(platform, external_id)` index provides a secondary DB-level guard but the application-level dedupe continues to use content hash.

### `ingest_normalized_posts` Update

**Minimal change**: only add `external_id=post.external_id` to the `.values(...)` call in `validator.py`. The `ON CONFLICT` clause stays unchanged (`index_elements=["source", "content_hash"]`).

Do NOT change the conflict resolution strategy — this preserves backward compatibility with CSV ingestion.

### Service Layer Job Tracking

The connector run creates an `IngestionJob` record with `job_type="connector"`. This allows the existing `/jobs` API to list connector runs. Fields mapping:
- `source` = `connector.connector_id` (e.g., `"twitter-file"`)
- `row_count` = `summary.fetched`
- `inserted_count` = `summary.inserted`
- `skipped_count` = `summary.rejected`
- `duplicate_count` = `summary.duplicates`
- `error_summary` = list of `{field, message}` dicts from `summary.validation_errors`

Follow the exact `_create_running_job` / `_persist_job` pattern from `ingestion/service.py` but adapt for connector terminology.

### Project Structure Notes

**New files to create:**
```
backend/alembic/versions/004_add_connector_support.py
backend/app/models/connector_checkpoint.py
backend/app/connectors/twitter_file.py
backend/app/connectors/service.py
backend/app/api/connectors.py
backend/tests/connectors/test_twitter_file_connector.py
backend/tests/connectors/test_connector_service.py
```

**Files to modify:**
- `backend/app/models/raw_post.py` — add `external_id` column
- `backend/app/connectors/validator.py` — add `external_id` to `ingest_normalized_posts`
- `backend/app/config.py` — add `CONNECTOR_TWITTER_FILE_PATH`
- `backend/app/main.py` — register connectors router (add 2 lines)

**Files NOT to modify:**
- `backend/app/ingestion/service.py` — CSV ingestion is unaffected
- `backend/app/connectors/interface.py`, `schemas.py` — interface contract is complete from 5.1
- Any analytics, QA, or processing files

### Pattern References

- Router pattern: follow `backend/app/api/admin.py` (simple APIRouter with Pydantic request/response models)
- Job tracking: follow `backend/app/ingestion/service.py` `_create_running_job` / `_persist_job` pattern exactly
- Migration pattern: follow `backend/alembic/versions/003_add_processing_columns_and_job_type.py` (idempotent, uses `_has_column`, `_has_index` guards)
- Session pattern: `get_db` dependency injection from `backend/app/db/session.py`
- Deduplication: `pg_insert(RawPost).on_conflict_do_nothing(index_elements=["source", "content_hash"])` from `backend/app/ingestion/service.py:156–182`

### References

- Story requirements: [epics.md, Epic 5, Story 5.2](../planning-artifacts/epics.md) lines 809–828
- Previous story (interface established): [5-1-connector-interface-normalization-contract.md](./5-1-connector-interface-normalization-contract.md)
- BaseConnector interface: [backend/app/connectors/interface.py](../../../backend/app/connectors/interface.py)
- Schemas (NormalizedPost, ConnectorRunSummary): [backend/app/connectors/schemas.py](../../../backend/app/connectors/schemas.py)
- Existing validator (validate_and_normalize, ingest_normalized_posts): [backend/app/connectors/validator.py](../../../backend/app/connectors/validator.py)
- RawPost model: [backend/app/models/raw_post.py](../../../backend/app/models/raw_post.py)
- IngestionJob model: [backend/app/models/ingestion_job.py](../../../backend/app/models/ingestion_job.py)
- Ingestion service (job tracking pattern): [backend/app/ingestion/service.py](../../../backend/app/ingestion/service.py)
- Latest migration: [backend/alembic/versions/003_add_processing_columns_and_job_type.py](../../../backend/alembic/versions/003_add_processing_columns_and_job_type.py)
- Router registration: [backend/app/main.py](../../../backend/app/main.py) lines 87–93
- Config settings: [backend/app/config.py](../../../backend/app/config.py)
- Existing connector tests (pattern): [backend/tests/connectors/test_interface.py](../../../backend/tests/connectors/test_interface.py)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- 2026-04-09: Story 5.2 implementation started
- 2026-04-09: All 10 tasks completed successfully

### Completion Notes List

- **Task 1 (DB Migration)**: Created `004_add_connector_support.py` with idempotent migration using `_has_column`, `_has_index`, and `_has_table` guards. Partial unique index on `(platform, external_id)` prevents duplicate connector posts while leaving CSV rows unaffected.

- **Task 2 (RawPost Model)**: Added `external_id` column after `content_hash`, before `author` field in `RawPost` model.

- **Task 3 (ConnectorCheckpoint Model)**: Created `connector_checkpoint.py` ORM with `connector_id` PK, `checkpoint_data` JSONB, and `updated_at` timestamp. Added export to `models/__init__.py`.

- **Task 4 (TwitterFileConnector)**: Implemented `fetch()`, `normalize()`, `checkpoint()`, and `_parse_twitter_date()` methods. Handles both Twitter API date format and ISO 8601 fallback. Tracks max timestamp for incremental fetching.

- **Task 5 (Connector Service)**: Created `service.py` with `run_connector()` orchestrates full connector workflow, `get_checkpoint()` retrieves checkpoint data. Integrates with existing `IngestionJob` tracking.

- **Task 6 (Ingest Update)**: Updated `validator.py` to include `external_id` in INSERT values. Primary deduplication via `(source, content_hash)` preserved; partial index provides secondary DB-level protection.

- **Task 7 (API Router)**: Created `connectors.py` with `POST /connectors/{connector_id}/run` endpoint. Validates connector_id, resolves file_path, handles FileNotFoundError with 400, and returns `ConnectorRunResponse`.

- **Task 8 (Router Registration)**: Registered `connectors_router` in `main.py` with prefix `/connectors` and tags `["connectors"]`.

- **Task 9 (Settings)**: Added `CONNECTOR_TWITTER_FILE_PATH: str = "data/twitter_posts.jsonl"` to `config.py`.

- **Task 10 (Tests)**: Created `test_twitter_file_connector.py` with 11 tests covering fetch, normalize, checkpoint, and date parsing. Created `test_connector_service.py` with 6 integration tests covering full runs, incremental runs, and duplicate handling.

### File List

**New Files Created:**
- `backend/alembic/versions/004_add_connector_support.py`
- `backend/app/models/connector_checkpoint.py`
- `backend/app/connectors/twitter_file.py`
- `backend/app/connectors/service.py`
- `backend/app/api/connectors.py`
- `backend/tests/connectors/test_twitter_file_connector.py`
- `backend/tests/connectors/test_connector_service.py`

**Files Modified:**
- `backend/app/models/raw_post.py` - added `external_id` column
- `backend/app/connectors/__init__.py` - exported `run_connector`, `get_checkpoint`
- `backend/app/connectors/validator.py` - added `external_id` to INSERT values
- `backend/app/config.py` - added `CONNECTOR_TWITTER_FILE_PATH`
- `backend/app/main.py` - registered connectors router
- `backend/app/models/__init__.py` - exported `ConnectorCheckpoint`

### Change Log

- 2026-04-09: Story 5.2 implementation completed
  - Added connector support with TwitterFileConnector MVP
  - Implemented offline-first JSONL file reading
  - Added incremental checkpointing via `connector_checkpoints` table
  - Created `/connectors/{connector_id}/run` API endpoint
  - Added comprehensive unit and integration tests
  - Story status updated to "done" in sprint-status.yaml
