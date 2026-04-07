# Story 1.4: CSV Data Ingestion

Status: done

## Story

As an admin or technical owner,  
I want to configure a CSV file as a data source and trigger an ingestion run,  
so that raw Spanish political posts are loaded into the system's raw data store ready for processing.

## Acceptance Criteria

1. **Given** a CSV file with columns (`text`, `platform`, `author`, `created_at`) and its path configured  
   **When** the admin calls `POST /ingest`  
   **Then** all valid rows are inserted into `raw_posts` with source metadata captured  
   **And** a job record is created with status `completed`, row count, and timestamp

2. **Given** some rows in the CSV have missing required fields (for example empty `text`)  
   **When** ingestion runs  
   **Then** invalid rows are skipped and logged, while valid rows are still imported  
   **And** the job record captures the count and reason for skipped rows

3. **Given** the same CSV is ingested twice  
   **When** ingestion runs a second time  
   **Then** duplicate posts are detected (by content hash or source id strategy) and skipped rather than inserted again

## Tasks / Subtasks

- [x] Add ingestion configuration in `backend/app/config.py` (AC: 1, 2, 3)
  - [x] Add `INGESTION_CSV_PATH` with a safe default (`data/posts.csv`)
  - [x] Add `INGESTION_SOURCE_NAME` default (`csv_local`)
  - [x] Add optional `INGESTION_PLATFORM_DEFAULT` fallback for rows that omit platform
- [x] Implement ingestion module in `backend/app/ingestion/` (AC: 1, 2, 3)
  - [x] `schemas.py`: row schema + ingestion summary schema using Pydantic v2
  - [x] `service.py`: CSV parsing, row validation, dedupe checks, DB insert orchestration
  - [x] `utils.py`: content hashing helper (normalized text hash)
- [x] Implement `POST /ingest` endpoint (AC: 1, 2, 3)
  - [x] Add router file `backend/app/api/ingestion.py`
  - [x] Register router in `backend/app/main.py`
  - [x] Return ingestion summary payload (processed, inserted, skipped, duplicate counts, errors)
- [x] Add job tracking persistence (AC: 1, 2)
  - [x] Create migration for `ingestion_jobs` table (id, source, status, started_at, finished_at, row_count, inserted_count, skipped_count, duplicate_count, error_summary)
  - [x] Add SQLAlchemy model in `backend/app/models/ingestion_job.py`
  - [x] Write one completed job row per ingestion execution
- [x] Enforce duplicate prevention at DB level (AC: 3)
  - [x] Add `content_hash` column to `raw_posts`
  - [x] Add unique index for dedupe key (`source`, `content_hash`) or (`source`, `platform`, `external_id`) if external id exists
  - [x] Keep ingestion idempotent under retries
- [x] Add tests (AC: 1, 2, 3)
  - [x] `backend/tests/test_ingestion_service.py`
  - [x] `backend/tests/test_ingestion_api.py`
  - [x] Include malformed CSV, empty rows, duplicate rerun, and mixed valid/invalid rows cases

## Developer Context

### Epic Context and Dependencies

- This story is in Epic 1 and depends directly on completed Stories 1.2 and 1.3:
  - Story 1.2 provides DB schema + async SQLAlchemy + Alembic patterns.
  - Story 1.3 provides taxonomy loading; ingestion should not classify, only load raw rows.
- Downstream dependency: Story 1.5 (`POST /process`) consumes `raw_posts`, so ingestion output must be stable and predictable.

### Implementation Guardrails

- Do not add business classification logic in this story; ingestion only writes raw data.
- Use async SQLAlchemy session pattern already used by project (`app.db.session`).
- Use Alembic for all schema changes; no manual SQL-only schema drift.
- Keep endpoint synchronous from client perspective (single non-streaming JSON response), aligned with architecture.
- Preserve existing FastAPI error envelope behavior: clear JSON messages, no opaque tracebacks in API responses.

### Technical Requirements

- CSV parsing:
  - Use Python stdlib `csv` module for low dependency footprint.
  - Validate required fields: `text`, `platform`, `created_at`; `author` may be nullable.
  - Parse timestamps robustly; if parse fails, skip row and record reason.
- Data mapping:
  - Map CSV `text` -> `raw_posts.original_text`
  - Set `raw_posts.source` from configured source name
  - Set `raw_posts.platform` from row value or configured default
  - Store row-level extras in `raw_posts.metadata` (for traceability)
- Deduplication:
  - Normalize text before hashing (trim, collapse whitespace, lowercase) to reduce trivial duplicate variance.
  - Perform defensive duplicate check both in app logic and DB uniqueness constraint.
- Job recording:
  - Always create a job record, even if all rows are skipped.
  - Status values: `completed` or `failed`; include summary counts and compact error summary.

### Architecture Compliance

- Follow existing code layout:
  - `backend/app/api/` for routers
  - `backend/app/models/` for ORM models
  - `backend/app/<domain>/` package for ingestion business logic
  - `backend/alembic/versions/` for schema changes
- Keep secrets/config in env-backed settings; no hardcoded absolute file paths.
- Maintain PostgreSQL-first approach; no Redis/cache additions for this story.

### Library and Framework Requirements

- FastAPI lifespan/event model remains unchanged; only add ingestion router.
- SQLAlchemy 2.x async patterns only (`AsyncSession`, `async_sessionmaker`).
- PostgreSQL + pgvector remains core datastore; this story does not change embedding behavior.
- Web research notes for current practice:
  - FastAPI lifespan pattern remains recommended over deprecated startup events.
  - SQLAlchemy bulk inserts should prefer `session.execute(insert(...), rows)` for performance and clearer batching.

### File Structure Plan

- Create:
  - `backend/app/api/ingestion.py`
  - `backend/app/ingestion/__init__.py`
  - `backend/app/ingestion/schemas.py`
  - `backend/app/ingestion/service.py`
  - `backend/app/ingestion/utils.py`
  - `backend/app/models/ingestion_job.py`
  - `backend/tests/test_ingestion_service.py`
  - `backend/tests/test_ingestion_api.py`
  - New Alembic revision in `backend/alembic/versions/`
- Modify:
  - `backend/app/main.py` (router registration)
  - `backend/app/models/__init__.py` (export model)
  - `backend/app/config.py` (ingestion settings)
  - `backend/app/models/raw_post.py` (dedupe key field if needed)

### Testing Requirements

- Unit:
  - CSV row validation (required/missing/invalid timestamp)
  - Hash normalization and duplicate detection behavior
- Integration:
  - `POST /ingest` happy path inserts expected row count
  - Mixed file imports valid rows while skipping invalid rows
  - Re-running same file yields duplicate skips and no double inserts
  - Job record is persisted with accurate counts and status
- Regression:
  - Existing taxonomy and health endpoints continue to work
  - No breaking changes to previously passing tests

### Previous Story Intelligence

- From Story 1.3:
  - Pattern already used: dedicated domain package + schema loader + API router.
  - FastAPI startup state usage exists; avoid bypassing startup assumptions in tests.
  - Review flagged robust error handling and fixture portability; mirror that rigor here.
- From Story 1.2:
  - Keep Alembic env and migration practices consistent.
  - Avoid unsafe SQL string interpolation and weak URL parsing patterns.

### Git Intelligence Summary

Recent commits indicate active hardening of backend configuration and CI, so this story should:
- keep environment-variable driven config,
- avoid introducing test/runtime dependency confusion,
- and preserve current backend conventions rather than inventing new patterns.

### Completion Notes

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story includes implementation boundaries, schema expectations, API contract, dedupe strategy, and test plan aligned with Epic 1 continuity.

## File List

**Created:**
- `backend/app/ingestion/__init__.py` - Ingestion module init
- `backend/app/ingestion/schemas.py` - Pydantic schemas (CSVRow, IngestionSummary)
- `backend/app/ingestion/utils.py` - Content hashing utility functions
- `backend/app/ingestion/service.py` - Core ingestion service logic
- `backend/app/api/ingestion.py` - FastAPI router for POST /ingest
- `backend/app/models/ingestion_job.py` - SQLAlchemy model for job tracking
- `backend/alembic/versions/002_add_ingestion_jobs_and_content_hash.py` - Database migration
- `backend/tests/test_ingestion_service.py` - Unit and integration tests for service
- `backend/tests/test_ingestion_api.py` - API endpoint tests

**Modified:**
- `backend/app/config.py` - Added ingestion configuration settings
- `backend/app/models/__init__.py` - Exported IngestionJob model
- `backend/app/models/raw_post.py` - Added content_hash column
- `backend/app/main.py` - Registered ingestion router
- `backend/tests/conftest.py` - Added async_db_session fixture

## Change Log

- **2026-04-07**: Story implementation complete - CSV data ingestion with validation, deduplication, and job tracking
- **2026-04-07**: Added ingestion configuration to config.py (INGESTION_CSV_PATH, INGESTION_SOURCE_NAME, INGESTION_PLATFORM_DEFAULT)
- **2026-04-07**: Created ingestion module with schemas, service, and utils
- **2026-04-07**: Implemented POST /ingest endpoint with summary response
- **2026-04-07**: Added ingestion_jobs table and content_hash column with unique index
- **2026-04-07**: Added comprehensive tests for service and API

## Dev Notes for Questions

- Should dedupe key be strictly (`source`, `content_hash`) for CSV MVP, or also include optional source row id if a future connector provides it?
- Should `created_at` parse accept multiple timestamp formats, or fail fast to strict ISO-8601 only?

### Review Findings

- [x] [Review][Patch] Missing rollback before persisting failed ingestion jobs [backend/app/ingestion/service.py:ingest_csv,_persist_job]
- [x] [Review][Patch] Non-atomic dedupe check can fail under concurrent ingests [backend/app/ingestion/service.py:_insert_rows]
- [x] [Review][Patch] `created_at` required-field constraint not enforced during CSV validation [backend/app/ingestion/service.py:_read_csv_rows]
- [x] [Review][Patch] Naive datetimes written to timezone-aware columns [backend/app/ingestion/service.py:ingest_csv,_parse_timestamp]
- [x] [Review][Patch] Extra-column CSV rows may produce non-JSON-serializable metadata keys [backend/app/ingestion/service.py:_read_csv_rows]
- [x] [Review][Patch] API error payload leaks internal exception details to clients [backend/app/api/ingestion.py:trigger_ingest]
- [x] [Review][Patch] Test DB session fixture does not isolate committed writes across tests [backend/tests/conftest.py:async_db_session]
