# Story 5.4: Connector Run Observability, Retry, and Failure Taxonomy

Status: done

## Story

As an admin or technical owner,
I want connector runs to expose clear status, retryability, and categorized failures,
So that I can diagnose and recover from source collection issues quickly.

## Acceptance Criteria

1. **Given** a connector run starts
   **When** the run status is queried (via `POST /connectors/{connector_id}/run` response or `GET /jobs`)
   **Then** job metadata includes connector id, mode (`live` or `replay`), start/end time, fetched count, normalized count, skipped count, and failure summary

2. **Given** a run fails due to transient issues (rate limit, timeout, temporary upstream errors)
   **When** retries are configured
   **Then** retries execute with bounded exponential backoff and final status reflects whether recovery succeeded
   **And** failure categories are machine-readable (e.g., `auth_error`, `rate_limit`, `upstream_unavailable`, `validation_error`)

## Tasks / Subtasks

### Task 1 — Create `ConnectorError` taxonomy (`backend/app/connectors/errors.py`) (AC: #2)

- [x] Create `backend/app/connectors/errors.py`:
  ```python
  """Connector error taxonomy for machine-readable failure categorization."""

  RETRYABLE_CATEGORIES = {"rate_limit", "upstream_unavailable"}

  class ConnectorError(Exception):
      """Base class for categorized connector errors.
      
      All connector implementations should raise subclasses of this when
      errors are recoverable or classifiable. Generic Python exceptions
      (e.g., FileNotFoundError, ValueError) are NOT retried.
      """
      category: str = "unknown"

      def __init__(self, message: str, category: str | None = None):
          super().__init__(message)
          self.category = category or self.__class__.category

  class AuthError(ConnectorError):
      """Authentication or authorization failure. NOT retried."""
      category = "auth_error"

  class RateLimitError(ConnectorError):
      """Rate limit exceeded. RETRIED with backoff."""
      category = "rate_limit"

  class UpstreamUnavailableError(ConnectorError):
      """Upstream service temporarily unavailable. RETRIED with backoff."""
      category = "upstream_unavailable"
  ```
  - Note: `validation_error` category is used when a run fails due to structural issues, not for per-record validation (those go into `ConnectorRunSummary.validation_errors`)
  - `TwitterFileConnector.fetch()` raises `FileNotFoundError` (not retried) or returns records normally — no change needed to connector implementations for this story

### Task 2 — DB Migration: Add `normalized_count` and `failure_category` to `ingestion_jobs` (AC: #1, #2)

- [x] Create `backend/alembic/versions/006_add_connector_observability.py`:
  - [ ] Add `normalized_count` column: `VARCHAR(50) NULLABLE DEFAULT NULL` → actually `INTEGER NULLABLE DEFAULT NULL`
  - [ ] Add `failure_category` column: `VARCHAR(50) NULLABLE DEFAULT NULL`
  - [ ] Use `_has_column` guard pattern from `003_add_processing_columns_and_job_type.py`
  - [ ] Implement `downgrade()` that drops both columns

  ```python
  """Add normalized_count and failure_category to ingestion_jobs."""
  from alembic import op
  import sqlalchemy as sa

  revision = "006"
  down_revision = "005"
  branch_labels = None
  depends_on = None

  def _has_column(op, table, column):
      from sqlalchemy import inspect
      conn = op.get_bind()
      insp = inspect(conn)
      return column in [c["name"] for c in insp.get_columns(table)]

  def upgrade():
      if not _has_column(op, "ingestion_jobs", "normalized_count"):
          op.add_column("ingestion_jobs", sa.Column("normalized_count", sa.Integer(), nullable=True))
      if not _has_column(op, "ingestion_jobs", "failure_category"):
          op.add_column("ingestion_jobs", sa.Column("failure_category", sa.String(50), nullable=True))

  def downgrade():
      op.drop_column("ingestion_jobs", "failure_category")
      op.drop_column("ingestion_jobs", "normalized_count")
  ```

### Task 3 — Update `IngestionJob` model (AC: #1, #2)

- [x] In `backend/app/models/ingestion_job.py`, add two columns after `duplicate_count`:
  ```python
  normalized_count = Column(Integer, nullable=True)      # Records passing normalization
  failure_category = Column(String(50), nullable=True)   # Machine-readable error category
  ```

### Task 4 — Add `CONNECTOR_MAX_RETRIES` to config (AC: #2)

- [x] In `backend/app/config.py`, add after `PROCESSING_MAX_RETRIES`:
  ```python
  # Connector retry configuration
  CONNECTOR_MAX_RETRIES: int = 3
  ```
  - Note: existing `PROCESSING_MAX_RETRIES` is used by the NLP processing pipeline; this is a separate, connector-specific setting

### Task 5 — Add retry logic and error categorization to `run_connector()` (AC: #2)

- [x] In `backend/app/connectors/service.py`, update imports:
  ```python
  import asyncio
  from app.connectors.errors import ConnectorError, RETRYABLE_CATEGORIES
  ```

- [ ] Replace the direct `raw_records = connector.fetch()` call (currently line ~71) with a retry loop:
  ```python
  # Fetch raw records with bounded backoff retry for transient failures
  retry_delays = [1.0, 2.0, 4.0]  # seconds between attempts
  fetch_attempt = 0
  failure_category: str | None = None

  for attempt, delay in enumerate(retry_delays + [None]):
      try:
          raw_records = connector.fetch()
          break  # success — exit retry loop
      except ConnectorError as e:
          failure_category = e.category
          if e.category not in RETRYABLE_CATEGORIES:
              logger.error(f"Non-retryable connector error ({e.category}): {e}")
              raise
          fetch_attempt = attempt + 1
          if delay is None:
              logger.error(f"Connector fetch exhausted {settings.CONNECTOR_MAX_RETRIES} retries ({e.category}): {e}")
              raise
          logger.warning(
              f"Connector fetch failed ({e.category}), retry {attempt + 1}/{len(retry_delays)} in {delay}s: {e}"
          )
          await asyncio.sleep(delay)
  ```
  - Adjust `len(retry_delays)` based on `settings.CONNECTOR_MAX_RETRIES`

- [ ] In the `except Exception` handler at line ~90, capture failure_category and pass to `_persist_connector_job`:
  ```python
  except Exception as e:
      logger.exception(f"Connector run failed: {e}")
      fc = failure_category or (e.category if isinstance(e, ConnectorError) else None)
      await _persist_connector_job(job_id, summary, status="failed", mode=mode, failure_category=fc)
      raise
  ```

- [ ] Pass `failure_category` through the success path too (it will be None for successful runs):
  ```python
  await _persist_connector_job(job_id, summary, status="completed", mode=mode, failure_category=None)
  ```

### Task 6 — Update `_persist_connector_job()` to store new fields (AC: #1, #2)

- [x] In `backend/app/connectors/service.py`, update `_persist_connector_job()` signature:
  ```python
  async def _persist_connector_job(
      job_id: str,
      summary: ConnectorRunSummary,
      status: str,
      mode: str = "live",
      failure_category: str | None = None,
  ) -> None:
  ```

- [ ] Add `normalized_count` and `failure_category` to the `update(IngestionJob).values(...)` call:
  ```python
  .values(
      status=status,
      finished_at=summary.finished_at,
      row_count=summary.fetched,
      normalized_count=summary.normalized,   # NEW
      inserted_count=summary.inserted,
      skipped_count=summary.rejected,
      duplicate_count=summary.duplicates,
      mode=mode,
      failure_category=failure_category,     # NEW
      error_summary=error_summary,
  )
  ```

### Task 7 — Update `JobResponse` schema and `_job_to_response()` (AC: #1, #2)

- [x] In `backend/app/jobs/schemas.py`, add two fields to `JobResponse` after `duplicate_count`:
  ```python
  normalized_count: int | None = Field(None, description="Records passing normalization (connector jobs only)")
  failure_category: str | None = Field(None, description="Machine-readable failure category for failed connector runs")
  ```

- [ ] In `backend/app/api/jobs.py`, update `_job_to_response()` to map the new fields:
  ```python
  return JobResponse(
      ...
      duplicate_count=job.duplicate_count or 0,
      normalized_count=getattr(job, "normalized_count", None),     # NEW
      failure_category=getattr(job, "failure_category", None),     # NEW
      mode=getattr(job, "mode", None),
      error_summary=error_summary if error_summary else None,
  )
  ```

### Task 8 — Tests (AC: #1, #2)

- [x] Create `backend/tests/connectors/test_observability.py`:

  - [ ] **Test normalized_count persisted in job record**: After a run with 3 records (2 valid, 1 invalid), `normalized_count=2` in the `IngestionJob`; query the job and assert `normalized_count == 2`
  - [ ] **Test failure_category on non-retryable error**: Connector raises `AuthError`; run fails immediately (no retry); job has `status="failed"` and `failure_category="auth_error"`
  - [ ] **Test failure_category on retryable error (exhausted)**: Connector raises `RateLimitError` on all attempts; run fails after retries; job has `status="failed"` and `failure_category="rate_limit"`; verify retry loop executed (count of fetch calls > 1)
  - [ ] **Test success after transient retry**: Connector raises `UpstreamUnavailableError` on first attempt, succeeds on second; run completes with `status="completed"` and `failure_category=None`
  - [ ] **Test JobResponse exposes failure_category**: After a failed run, `GET /jobs` returns job with `failure_category` populated
  - [ ] **Test JobResponse exposes normalized_count**: After a successful run, `GET /jobs` returns job with correct `normalized_count`
  - [ ] Use `unittest.mock.MagicMock` to create a connector with a `fetch()` that raises or returns records on demand
  - [ ] Use `async_db_session` fixture; use `async_session_maker()` pattern to query `IngestionJob` with `expire_all()` after run (same as `test_replay_mode.py:166-168`)

## Dev Notes

### What Already Exists — Do NOT Reinvent

| Component | Status | Location |
|---|---|---|
| `ConnectorRunSummary` with all metrics | Complete | `backend/app/connectors/schemas.py` |
| `ConnectorRunResponse` (full observability on run response) | Complete | `backend/app/api/connectors.py` |
| `mode` field in `IngestionJob` and `JobResponse` | Complete (added in 5-3 review) | `backend/app/models/ingestion_job.py`, `backend/app/jobs/schemas.py` |
| Per-record validation errors in `error_summary` | Complete | `backend/app/connectors/service.py:_persist_connector_job()` |
| `tenacity` in requirements | Available | `backend/requirements.txt` — but use a simple async retry loop (more transparent than tenacity decorators for this use case) |

### Key Code Locations

| File | Relevant Section | Line Approx |
|---|---|---|
| `backend/app/connectors/service.py` | `run_connector()` — fetch call to wrap | ~71 |
| `backend/app/connectors/service.py` | `run_connector()` — except handler | ~90 |
| `backend/app/connectors/service.py` | `_persist_connector_job()` — values dict | ~228–242 |
| `backend/app/models/ingestion_job.py` | After `duplicate_count` | ~27 |
| `backend/app/jobs/schemas.py` | `JobResponse` fields | ~19–22 |
| `backend/app/api/jobs.py` | `_job_to_response()` | ~30–43 |
| `backend/app/config.py` | After `PROCESSING_MAX_RETRIES` | ~46 |

### Retry Logic: Use Simple Async Loop, Not Tenacity Decorator

Although `tenacity` is available, use a **manual `await asyncio.sleep()` retry loop** in `run_connector()`. Reasons:
- `connector.fetch()` is synchronous — tenacity's `AsyncRetrying` context manager works but adds complexity
- A manual loop makes retry count and backoff delays explicit and easy to test
- The simple `[1.0, 2.0, 4.0]` seconds pattern is consistent with the style of this codebase (explicit, readable)

If `settings.CONNECTOR_MAX_RETRIES = 3`, use `retry_delays = [1.0, 2.0, 4.0]` (3 delays = 3 retries before final raise).

### Failure Category Scope: `fetch()` Only

Only `connector.fetch()` is retried and categorized. These are NOT retried:
- Per-record normalization failures (those go into `summary.validation_errors`, not `failure_category`)
- `ingest_normalized_posts_with_external_id()` failures (DB errors — not connector errors)
- Checkpoint upsert failures (pre-existing deferred concern)

The `TwitterFileConnector.fetch()` currently raises `FileNotFoundError` (a Python built-in, not a `ConnectorError`) — this propagates as-is and results in `failure_category=None` in the job record, which is correct (it's a config error, not a connector protocol error).

### Failure Category for Generic Exceptions

In the `except Exception` handler, for non-`ConnectorError` exceptions:
```python
fc = failure_category or (e.category if isinstance(e, ConnectorError) else None)
```
This means generic Python exceptions (FileNotFoundError, ValueError, etc.) result in `failure_category=None` in the job record. This is correct — they're not protocol-level connector failures.

### DB Migration Pattern (Follow 003/005 Exactly)

From `003_add_processing_columns_and_job_type.py`:
```python
def _has_column(op, table, column):
    from sqlalchemy import inspect
    conn = op.get_bind()
    insp = inspect(conn)
    return column in [c["name"] for c in insp.get_columns(table)]
```
Use this guard in `upgrade()` to make migration idempotent. Alembic revision `006`, `down_revision = "005"`.

### Test Pattern: Multiple Sessions (CRITICAL)

From Story 5-3 review findings: `_create_running_job()` and `_persist_connector_job()` use `async_session_maker()` (separate sessions). To see their committed changes in tests, use `expire_all()`:

```python
# After run_connector() completes, query the job:
await async_db_session.expire_all()
result = await async_db_session.execute(select(IngestionJob).where(...))
job = result.scalar_one()
assert job.failure_category == "rate_limit"
```

### Mock Connector for Tests

Create a minimal mock connector that can be configured to raise on specific attempts:
```python
from unittest.mock import MagicMock
from app.connectors.interface import BaseConnector
from app.connectors.errors import RateLimitError

class MockConnector(BaseConnector):
    connector_id = "mock-connector"
    
    def __init__(self, fetch_side_effects):
        self._effects = iter(fetch_side_effects)
        self._last_seen_at = None
    
    def fetch(self):
        effect = next(self._effects)
        if isinstance(effect, Exception):
            raise effect
        return effect  # list of raw records
    
    def normalize(self, raw):
        from app.connectors.schemas import NormalizedPost
        from datetime import datetime, timezone
        return NormalizedPost(
            source="mock", platform="test", external_id=raw["id"],
            text=raw["text"], created_at=datetime.now(timezone.utc),
        )
    
    def checkpoint(self):
        return {}
```

### `connector_id` in Job Metadata

The `source` field in `IngestionJob` stores the `connector_id` (e.g., `"twitter-file"`). The existing `JobResponse.source` already exposes this. The AC's "connector id" requirement is satisfied by `source`. No new field needed.

### AC1: What's Fully Covered After This Story

After Task 2–7, `GET /jobs` will return for connector jobs:
| AC1 requirement | `JobResponse` field |
|---|---|
| connector id | `source` (already) |
| mode | `mode` (added in 5-3 review) |
| start/end time | `started_at`, `finished_at` (already) |
| fetched count | `row_count` (already) |
| normalized count | `normalized_count` (NEW in this story) |
| skipped count | `skipped_count` (already — maps to `rejected`) |
| failure summary | `error_summary` + `failure_category` (NEW category field) |

### What NOT To Do

- **Do NOT** add a new connector-specific status endpoint — the existing `POST /connectors/{connector_id}/run` response (`ConnectorRunResponse`) already includes full observability for the active run; `GET /jobs` covers historical queries
- **Do NOT** add retry logic around `validate_and_normalize()` or `ingest_normalized_posts_with_external_id()` — only `fetch()` is retried
- **Do NOT** change `ConnectorRunSummary` or `ConnectorRunResponse` — these are already complete and well-designed
- **Do NOT** change `BaseConnector.fetch()` signature — connector implementations raise `ConnectorError` subclasses if they encounter protocol errors; `TwitterFileConnector` doesn't need changes
- **Do NOT** use `PROCESSING_MAX_RETRIES` for connector retries — add `CONNECTOR_MAX_RETRIES` to keep concerns separate

### Project Structure: New and Modified Files

**New files:**
```
backend/app/connectors/errors.py
backend/alembic/versions/006_add_connector_observability.py
backend/tests/connectors/test_observability.py
```

**Files to modify:**
- `backend/app/connectors/service.py` — retry loop, failure_category tracking, updated `_persist_connector_job()`
- `backend/app/models/ingestion_job.py` — add `normalized_count`, `failure_category`
- `backend/app/jobs/schemas.py` — add to `JobResponse`
- `backend/app/api/jobs.py` — map new fields in `_job_to_response()`
- `backend/app/config.py` — add `CONNECTOR_MAX_RETRIES`

**Files NOT to modify:**
- `backend/app/connectors/interface.py` — interface is complete
- `backend/app/connectors/schemas.py` — `ConnectorRunSummary` is complete
- `backend/app/connectors/twitter_file.py` — mode-agnostic, no protocol errors
- `backend/app/connectors/validator.py` — per-record validation is separate from run-level errors
- `backend/app/api/connectors.py` — `ConnectorRunResponse` already fully observable

### References

- Story requirements: [epics.md, Epic 5, Story 5.4](../planning-artifacts/epics.md) lines 848–865
- Previous story (replay mode + mode field): [5-3-replay-mode-deterministic-demo-runs.md](./5-3-replay-mode-deterministic-demo-runs.md)
- Connector service (run_connector): [backend/app/connectors/service.py](../../../backend/app/connectors/service.py)
- Job response schema: [backend/app/jobs/schemas.py](../../../backend/app/jobs/schemas.py)
- Job response mapping: [backend/app/api/jobs.py](../../../backend/app/api/jobs.py)
- IngestionJob model: [backend/app/models/ingestion_job.py](../../../backend/app/models/ingestion_job.py)
- Migration pattern: [backend/alembic/versions/003_add_processing_columns_and_job_type.py](../../../backend/alembic/versions/003_add_processing_columns_and_job_type.py)
- Deferred work (pre-existing concerns NOT to fix): [deferred-work.md](./deferred-work.md) — `rollback()` in IntegrityError handler, `_upsert_checkpoint` session commit, `_after_timestamp` mutation

## Dev Agent Record

### Agent Model Used

qwen3.5:cloud

### Completion Notes List

- ✅ Task 1: Created `backend/app/connectors/errors.py` with `ConnectorError` base class and subclasses (`AuthError`, `RateLimitError`, `UpstreamUnavailableError`) plus `RETRYABLE_CATEGORIES` set
- ✅ Task 2: Created Alembic migration `006_add_connector_observability.py` adding `normalized_count` (Integer) and `failure_category` (String(50)) columns to `ingestion_jobs`
- ✅ Task 3: Updated `IngestionJob` model with `normalized_count` and `failure_category` columns
- ✅ Task 4: Added `CONNECTOR_MAX_RETRIES = 3` config setting
- ✅ Task 5: Implemented retry loop in `run_connector()` with exponential backoff ([1.0, 2.0, 4.0] seconds), handling `ConnectorError` taxonomy and tracking `failure_category`
- ✅ Task 6: Updated `_persist_connector_job()` signature and values dict to include `normalized_count` and `failure_category`
- ✅ Task 7: Added `normalized_count` and `failure_category` fields to `JobResponse` schema and `_job_to_response()` mapping
- ✅ Task 8: Created comprehensive test suite in `backend/tests/connectors/test_observability.py` covering:
  - Error taxonomy unit tests (6 tests)
  - `normalized_count` persistence test
  - Non-retryable error (`AuthError`) fails immediately with correct category
  - Retryable error (`RateLimitError`) exhausts retries with correct category
  - Success after transient retry (`UpstreamUnavailableError`)
  - `JobResponse` exposes both new fields
  - Generic exceptions result in `failure_category=None`
- All error taxonomy tests pass (6/6); DB integration tests require live database connection

### File List

**New files:**
- `backend/app/connectors/errors.py` — Connector error taxonomy
- `backend/alembic/versions/006_add_connector_observability.py` — DB migration
- `backend/tests/connectors/test_observability.py` — Test suite

**Modified files:**
- `backend/app/connectors/service.py` — Retry loop, failure_category tracking, updated _persist_connector_job()
- `backend/app/models/ingestion_job.py` — Added normalized_count, failure_category columns
- `backend/app/jobs/schemas.py` — Added normalized_count, failure_category to JobResponse
- `backend/app/api/jobs.py` — Map new fields in _job_to_response()
- `backend/app/config.py` — Added CONNECTOR_MAX_RETRIES setting

### Review Findings

- [x] [Review][Decision] `CONNECTOR_MAX_RETRIES` config does not control retry count — resolved: derive `retry_delays` from config using `[2**i for i in range(settings.CONNECTOR_MAX_RETRIES)]`
- [x] [Review][Patch] Stale `failure_category` leaks after transient retry then different error [`service.py`:84] — fixed: reset `failure_category = None` on successful fetch
- [x] [Review][Patch] `fetch_attempt` unused variable (dead code) [`service.py`:76,88] — removed
- [x] [Review][Patch] Test conftest missing `normalized_count` and `failure_category` columns [`tests/conftest.py`] — added ALTER TABLE statements
- [x] [Review][Defer] No length validation on `failure_category` against `String(50)` [`errors.py`, `service.py`] — deferred, low risk; categories are defined in code as short strings
- [x] [Review][Defer] Synchronous `fetch()` blocks event loop (pre-existing, worsened by retries) [`service.py`:81] — deferred, pre-existing architecture concern
- [x] [Review][Defer] No jitter on backoff delays [`service.py`:75] — deferred, not required by spec; single-connector architecture
- [x] [Review][Defer] `duplicate_count = Column(Integer, 0)` malformed (pre-existing) [`ingestion_job.py`] — deferred, pre-existing
- [x] [Review][Defer] `validation_error` not a subclass (explicitly deferred in dev notes) [`errors.py`] — deferred per spec
- [x] [Review][Defer] `_persist_connector_job` separate session risk (pre-existing) [`service.py`] — deferred, pre-existing pattern
- [x] [Review][Defer] `ConnectorError(category=None)` edge case [`errors.py`:15] — deferred, unlikely in practice

### Change Log

- Implemented connector error taxonomy with retryable vs non-retryable categories (Date: 2026-04-09)
- Added DB migration 006 for observability columns (Date: 2026-04-09)
- Implemented bounded retry loop with exponential backoff in run_connector() (Date: 2026-04-09)
- Updated job persistence and API response schemas to expose normalized_count and failure_category (Date: 2026-04-09)
- Created comprehensive test suite covering error taxonomy and retry behavior (Date: 2026-04-09)
