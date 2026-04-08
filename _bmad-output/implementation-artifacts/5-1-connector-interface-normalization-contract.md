# Story 5.1: Connector Interface & Normalization Contract

Status: review

## Story

As a developer,
I want a provider-agnostic connector interface and shared normalized post schema,
So that collection from different platforms can plug into the same ingestion flow without custom downstream logic per source.

## Acceptance Criteria

1. **Given** the backend codebase
   **When** a developer adds a new connector
   **Then** it implements a shared interface (methods: `fetch`, `normalize`, `checkpoint`) and returns `NormalizedPost` records with required fields (`source`, `platform`, `external_id`, `text`, `author`, `created_at`, `raw_payload`)
   **And** normalized records can be ingested by the existing raw ingestion pipeline without special-case per-platform code

2. **Given** malformed or incomplete source payloads
   **When** normalization runs
   **Then** invalid records are rejected with structured validation errors (field name + message) and valid records continue processing
   **And** rejection counts are surfaced in the `ConnectorRunSummary`

## Tasks / Subtasks

### Task 1 — Create `backend/app/connectors/` package (AC: #1, #2)

- [ ] Create `backend/app/connectors/__init__.py` (empty)
- [ ] Create `backend/app/connectors/schemas.py`:
  - [ ] Define `NormalizedPost` Pydantic model with required fields: `source` (str), `platform` (str), `external_id` (str), `text` (str, min_length=1), `author` (str | None), `created_at` (datetime, timezone-aware), `raw_payload` (dict[str, Any])
  - [ ] Define `ValidationError` dataclass/model: `field: str`, `message: str`, `raw_value: Any`
  - [ ] Define `ConnectorRunSummary` Pydantic model: `connector_id` (str), `mode` (Literal["live", "replay"] = "live"), `started_at` (datetime), `finished_at` (datetime | None), `fetched` (int = 0), `normalized` (int = 0), `rejected` (int = 0), `inserted` (int = 0), `duplicates` (int = 0), `validation_errors` (list[ValidationError] = [])
- [ ] Create `backend/app/connectors/interface.py`:
  - [ ] Define `BaseConnector` abstract base class (ABC) with abstract methods:
    - `fetch(self) -> list[dict[str, Any]]` — returns raw platform payloads
    - `normalize(self, raw: dict[str, Any]) -> NormalizedPost | None` — returns NormalizedPost or None on failure; populates `validation_errors` on the summary
    - `checkpoint(self) -> dict[str, Any]` — returns cursor/state for incremental runs
  - [ ] Add class-level `connector_id: str` abstract attribute
- [ ] Create `backend/app/connectors/validator.py`:
  - [ ] Implement `validate_and_normalize(connector: BaseConnector, raw_records: list[dict], summary: ConnectorRunSummary) -> list[NormalizedPost]`
  - [ ] For each raw record: call `connector.normalize(raw)`; on success increment `summary.normalized`; on failure append `ValidationError` to `summary.validation_errors`, increment `summary.rejected`
  - [ ] Increment `summary.fetched` for every raw record attempted

### Task 2 — Create ingestion bridge function (AC: #1)

- [ ] Add `ingest_normalized_posts(session, posts: list[NormalizedPost], summary: ConnectorRunSummary) -> None` in `backend/app/connectors/validator.py` (or a new `backend/app/connectors/ingestion_bridge.py`):
  - [ ] Map each `NormalizedPost` to a `RawPost` row:
    - `source` → `source`
    - `platform` → `platform`
    - `original_text` ← `text`
    - `content_hash` ← `compute_content_hash(text)` (reuse `app.ingestion.utils.compute_content_hash`)
    - `author` → `author`
    - `created_at` → `created_at`
    - `metadata_` ← `{"external_id": post.external_id, "raw_payload": post.raw_payload}`
  - [ ] Use the existing `pg_insert(RawPost).on_conflict_do_nothing(index_elements=["source", "content_hash"])` deduplication pattern (same as `ingestion/service.py:_insert_rows`)
  - [ ] On conflict (duplicate): increment `summary.duplicates`; on insert: increment `summary.inserted`
  - [ ] Commit the session after all rows

### Task 3 — Smoke tests (AC verification)

- [ ] AC1: Write `backend/tests/connectors/test_interface.py`:
  - [ ] Create a minimal concrete `DummyConnector(BaseConnector)` that implements all abstract methods
  - [ ] Assert `DummyConnector` instantiates without error
  - [ ] Assert `connector.fetch()` returns a list
  - [ ] Assert `connector.normalize(raw)` returns a valid `NormalizedPost` given a complete raw dict
  - [ ] Assert `connector.normalize(raw)` returns `None` given an incomplete/malformed raw dict (e.g. missing `text`)
- [ ] AC2: Test `validate_and_normalize`:
  - [ ] Given one valid + one malformed record → `summary.normalized == 1`, `summary.rejected == 1`, `summary.fetched == 2`, `len(summary.validation_errors) == 1`

## Dev Notes

### Package Location — New Module, No New API Router Yet

This story is **purely infrastructure**. Create the `backend/app/connectors/` package — no FastAPI router, no changes to `main.py`. The `POST /connectors/{connector_id}/run` endpoint comes in Story 5.2.

Do NOT add an `api/connectors.py` router or register anything in `main.py` for this story.

### Existing Ingestion Pipeline — Do NOT Modify

The existing ingestion path (`backend/app/ingestion/service.py:ingest_csv`) must not be changed. The connector framework is **additive** — a new package plugging into the same `RawPost` ORM model via the same `pg_insert().on_conflict_do_nothing()` pattern.

Reuse:
- `app.ingestion.utils.compute_content_hash` — existing SHA-256 hash utility
- `app.models.raw_post.RawPost` — existing ORM model, no schema changes
- `sqlalchemy.dialects.postgresql.insert as pg_insert` — existing deduplication pattern
- `app.db.session.get_db` / `async_session_maker` — existing session management

### Deduplication Strategy

The existing unique constraint is `(source, content_hash)` on `raw_posts`. For Story 5.1, keep this — use `compute_content_hash(post.text)` as the content hash. Store `external_id` in `metadata_` alongside `raw_payload`. A dedicated `external_id` column + `(platform, external_id)` unique index may be added in Story 5.2 when the first real connector is built.

### `NormalizedPost` Required Fields (from Epic 5 AC)

```python
class NormalizedPost(BaseModel):
    source: str                    # connector/run identifier (e.g. "twitter-scrape-2026-04")
    platform: str                  # platform name (e.g. "twitter", "reddit")
    external_id: str               # platform-specific record ID, for deduplication
    text: str                      # post content, min_length=1
    author: str | None = None      # author identifier, nullable
    created_at: datetime           # original post timestamp, must be timezone-aware
    raw_payload: dict[str, Any]    # full raw record for replay mode (Story 5.3)
```

`created_at` must always be timezone-aware (UTC). If a connector produces naive datetimes, it should attach `timezone.utc` during `normalize()`.

### `ConnectorRunSummary` — Superset of `IngestionSummary`

`ConnectorRunSummary` is the connector-native equivalent of `IngestionSummary` (`app/ingestion/schemas.py`). Do NOT reuse `IngestionSummary` — the connector summary has connector-specific fields (`connector_id`, `mode`, `validation_errors`). Future stories (5.4) will extend this further.

```python
class ConnectorRunSummary(BaseModel):
    connector_id: str
    mode: Literal["live", "replay"] = "live"
    started_at: datetime
    finished_at: datetime | None = None
    fetched: int = 0       # total raw records attempted
    normalized: int = 0    # passed normalization
    rejected: int = 0      # failed normalization
    inserted: int = 0      # written to raw_posts
    duplicates: int = 0    # dedup conflicts
    validation_errors: list[ValidationError] = []
```

### `BaseConnector` Abstract Interface

```python
from abc import ABC, abstractmethod
from app.connectors.schemas import NormalizedPost, ConnectorRunSummary

class BaseConnector(ABC):
    connector_id: str  # class-level, overridden by subclass

    @abstractmethod
    def fetch(self) -> list[dict[str, Any]]:
        """Fetch raw payloads from the source. Returns list of dicts."""
        ...

    @abstractmethod
    def normalize(self, raw: dict[str, Any]) -> NormalizedPost | None:
        """Convert a raw payload to NormalizedPost. Return None if invalid."""
        ...

    @abstractmethod
    def checkpoint(self) -> dict[str, Any]:
        """Return current cursor/state for incremental fetching (Story 5.2)."""
        ...
```

The `checkpoint()` method is part of the interface contract in Story 5.1 but is only **used** in Story 5.2 (incremental fetching). For the first concrete connector in 5.2, it returns the last timestamp or cursor.

### `validate_and_normalize` Implementation Pattern

```python
def validate_and_normalize(
    connector: BaseConnector,
    raw_records: list[dict],
    summary: ConnectorRunSummary,
) -> list[NormalizedPost]:
    valid = []
    for raw in raw_records:
        summary.fetched += 1
        try:
            result = connector.normalize(raw)
            if result is None:
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationError(field="__record__", message="normalize() returned None", raw_value=raw)
                )
            else:
                summary.normalized += 1
                valid.append(result)
        except Exception as e:
            summary.rejected += 1
            summary.validation_errors.append(
                ValidationError(field="__record__", message=str(e), raw_value=raw)
            )
    return valid
```

### Ingestion Bridge — Exact Pattern to Follow

From `ingestion/service.py:_insert_rows` (line 149–182):

```python
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.models.raw_post import RawPost
from app.ingestion.utils import compute_content_hash

async def ingest_normalized_posts(
    session: AsyncSession,
    posts: list[NormalizedPost],
    summary: ConnectorRunSummary,
) -> None:
    for post in posts:
        content_hash = compute_content_hash(post.text)
        stmt = (
            pg_insert(RawPost)
            .values(
                source=post.source,
                platform=post.platform,
                original_text=post.text,
                content_hash=content_hash,
                author=post.author,
                created_at=post.created_at,
                metadata_={"external_id": post.external_id, "raw_payload": post.raw_payload},
            )
            .on_conflict_do_nothing(index_elements=["source", "content_hash"])
            .returning(RawPost.id)
        )
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            summary.inserted += 1
        else:
            summary.duplicates += 1
    await session.commit()
```

### Project Structure Notes

**New files to create:**
```
backend/app/connectors/__init__.py
backend/app/connectors/interface.py
backend/app/connectors/schemas.py
backend/app/connectors/validator.py   (includes validate_and_normalize + ingest_normalized_posts)
backend/tests/connectors/__init__.py
backend/tests/connectors/test_interface.py
```

**Files NOT modified:**
- `backend/app/main.py` — no router registration for this story
- `backend/app/ingestion/service.py` — not modified; bridge uses same ORM pattern independently
- `backend/app/models/raw_post.py` — no schema changes
- Any existing API or analytics files

**Package pattern:** Follow the existing domain package pattern (e.g., `app/ingestion/`, `app/jobs/`): `__init__.py` + domain-specific modules. For Story 5.1 there is no `service.py` — `validator.py` handles both validation and ingestion bridge since there's no API surface yet.

### Testing Notes

Test file lives in `backend/tests/connectors/` — follow the existing test file location pattern. Use `pytest` + `pytest-asyncio` (already in dev deps). For the ingestion bridge test, you may mock the DB session rather than requiring a live DB — the unit test only needs to verify the ORM insert pattern is called correctly.

Existing test examples to follow:
- `backend/tests/test_health.py` — simple endpoint tests
- Pattern: async test functions with `@pytest.mark.asyncio`

### References

- Story requirements: [epics.md, Epic 5, Story 5.1](../planning-artifacts/epics.md) lines 789–806
- Existing ingestion pipeline (deduplication pattern): [backend/app/ingestion/service.py](../../../backend/app/ingestion/service.py) lines 149–182
- Content hash utility: [backend/app/ingestion/utils.py](../../../backend/app/ingestion/utils.py)
- RawPost model (columns, unique constraint): [backend/app/models/raw_post.py](../../../backend/app/models/raw_post.py)
- IngestionSummary (for schema reference): [backend/app/ingestion/schemas.py](../../../backend/app/ingestion/schemas.py)
- Router registration pattern (for Story 5.2): [backend/app/main.py](../../../backend/app/main.py) lines 87–93
- Previous story learnings (code patterns): [4-4-demo-reset-clean-pipeline-reinitialization.md](./4-4-demo-reset-clean-pipeline-reinitialization.md)

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Debug Log References

### Completion Notes List

- **2026-04-08**: Story implementation completed successfully. All acceptance criteria verified through unit tests.
- Created `backend/app/connectors/` package with `__init__.py`, `schemas.py`, `interface.py`, and `validator.py`
- Implemented `NormalizedPost` Pydantic model with all required fields
- Implemented `ValidationError` dataclass for tracking validation failures
- Implemented `ConnectorRunSummary` Pydantic model for tracking connector run metrics
- Implemented `BaseConnector` ABC with abstract methods for `fetch()`, `normalize()`, and `checkpoint()`
- Implemented `validate_and_normalize()` function that processes raw records and tracks metrics
- Implemented `ingest_normalized_posts()` async function that bridges to existing `RawPost` ORM with deduplication
- Created `backend/tests/connectors/test_interface.py` with 8 passing tests covering AC1 and AC2

### File List

- `backend/app/connectors/__init__.py` — Created (package init, exports)
- `backend/app/connectors/schemas.py` — Created (NormalizedPost, ValidationError, ConnectorRunSummary)
- `backend/app/connectors/interface.py` — Created (BaseConnector ABC)
- `backend/app/connectors/validator.py` — Created (validate_and_normalize, ingest_normalized_posts)
- `backend/tests/connectors/__init__.py` — Created (package init)
- `backend/tests/connectors/test_interface.py` — Created (8 unit tests)
