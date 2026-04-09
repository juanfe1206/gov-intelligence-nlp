# Story 5.3: Replay Mode for Deterministic Demo Runs

Status: ready-for-dev

## Story

As a demo operator,
I want to replay previously captured raw source payloads through the same connector-normalization code path,
So that demos and tests are reproducible even when live collection is unavailable or unstable.

## Acceptance Criteria

1. **Given** one or more captured source payload files exist locally
   **When** the operator triggers replay mode via `POST /connectors/{connector_id}/run` with `mode: "replay"`
   **Then** the system runs the exact same normalization + ingestion path used by live connector runs
   **And** replay output (rows inserted, rows skipped, validation failures) is reported in the same `ConnectorRunResponse` format as live mode with `mode: "replay"` in the response

2. **Given** a replay payload previously processed successfully
   **When** replay runs again on the same payload
   **Then** deduplication prevents duplicate raw post inserts
   **And** the run summary reports skipped duplicates via `duplicates` count

3. **Given** a replay run completes
   **When** the run finishes
   **Then** the connector checkpoint is NOT updated (replay does not advance the incremental cursor)
   **And** the next live run still uses the previous checkpoint

## Tasks / Subtasks

### Task 1 — DB Migration: Add `mode` column to `ingestion_jobs` (AC: #1, #3)

- [ ] Create `backend/alembic/versions/005_add_connector_mode.py`:
  - [ ] Add `mode` column to `ingestion_jobs`: `VARCHAR(10) NULLABLE DEFAULT NULL`
  - [ ] Use idempotent `_has_column` guard pattern from `003_add_processing_columns_and_job_type.py`
  - [ ] Implement `downgrade()` that drops the column
  - Column purpose: stores `"live"` or `"replay"` for connector jobs; NULL for CSV ingestion jobs

### Task 2 — Update `IngestionJob` model (AC: #1)

- [ ] In `backend/app/models/ingestion_job.py`, add:
  ```python
  mode = Column(String(10), nullable=True)
  ```
  after the `job_type` column

### Task 3 — Update `run_connector()` service to accept mode (AC: #1, #3)

- [ ] In `backend/app/connectors/service.py`, update `run_connector()` signature:
  ```python
  async def run_connector(
      session: AsyncSession,
      connector: BaseConnector,
      mode: str = "live",
  ) -> ConnectorRunSummary:
  ```
- [ ] Set `summary = ConnectorRunSummary(connector_id=connector_id, mode=mode, started_at=started_at)`
  - Replace the hardcoded `mode="live"` at line ~62
- [ ] Gate checkpoint upsert on mode: only call `_upsert_checkpoint(...)` when `mode == "live"`
  - Existing guard: `if checkpoint.get("last_seen_at") is not None:` — add `and mode == "live"` to this condition
- [ ] Pass `mode` to `_persist_connector_job()` call and store in `IngestionJob.mode` column

### Task 4 — Update `_persist_connector_job()` to store mode (AC: #1)

- [ ] In `backend/app/connectors/service.py`, update `_persist_connector_job()` signature:
  ```python
  async def _persist_connector_job(
      job_id: str,
      summary: ConnectorRunSummary,
      status: str,
      mode: str = "live",
  ) -> None:
  ```
- [ ] Add `mode=mode` to the `update(IngestionJob).values(...)` call

### Task 5 — Update `_create_running_job()` to store mode (AC: #1)

- [ ] Update `_create_running_job()` signature:
  ```python
  async def _create_running_job(connector_id: str, mode: str = "live") -> str:
  ```
- [ ] Add `mode=mode` to `IngestionJob(...)` constructor

### Task 6 — Update API endpoint to accept `mode` in request body (AC: #1, #3)

- [ ] In `backend/app/api/connectors.py`, update `ConnectorRunRequest`:
  ```python
  from typing import Literal
  
  class ConnectorRunRequest(BaseModel):
      file_path: str | None = None
      mode: Literal["live", "replay"] = "live"
  ```
- [ ] Pass mode to `run_connector()`:
  ```python
  mode = body.mode if body else "live"
  summary = await run_connector(session, connector, mode=mode)
  ```

### Task 7 — Tests (AC: #1, #2, #3)

- [ ] Create `backend/tests/connectors/test_replay_mode.py`:
  - [ ] **Test replay runs same normalization path**: POST with `mode="replay"`, verify summary has `mode="replay"` and inserted/normalized counts match live equivalent
  - [ ] **Test replay does NOT update checkpoint**: After a replay run, assert `get_checkpoint()` returns the same checkpoint as before
  - [ ] **Test live run still works after replay**: After a replay run, a live run still uses and updates the checkpoint correctly
  - [ ] **Test replay deduplication**: Replay the same payload twice; second replay shows `duplicates > 0` and `inserted == 0`
  - [ ] **Test replay on empty file**: Replay with JSONL with 0 records → summary shows `fetched=0, inserted=0, mode="replay"`
  - [ ] Use `tmp_path` fixture for test JSONL files; mock DB session following pattern in `test_connector_service.py`

## Dev Notes

### Replay Mode: Minimal Change Philosophy

Replay mode is **nearly identical** to live mode. The only behavioral differences are:
1. `ConnectorRunSummary.mode` is set to `"replay"` instead of `"live"`
2. Checkpoint is **NOT upserted** after a replay run
3. The `mode` field is stored in the `IngestionJob` record

Everything else — `fetch()`, `normalize()`, `validate_and_normalize()`, `ingest_normalized_posts_with_external_id()` — runs **identically**. Do NOT create separate code paths.

### Key Code Locations to Modify

| File | Change | Location |
|------|--------|----------|
| `backend/app/connectors/service.py` | Add `mode` param to `run_connector()`, gate checkpoint on `mode == "live"` | Lines ~22–94 |
| `backend/app/connectors/service.py` | Add `mode` param to `_create_running_job()`, `_persist_connector_job()` | Lines ~171–236 |
| `backend/app/api/connectors.py` | Add `mode` field to `ConnectorRunRequest`, pass to `run_connector()` | Lines ~23–27, ~102 |
| `backend/app/models/ingestion_job.py` | Add `mode` column | Line ~26 |
| `backend/alembic/versions/005_add_connector_mode.py` | New migration | N/A |

### Checkpoint Guard: Exact Change Required

In `service.py`, the current checkpoint guard (line ~85–87):
```python
checkpoint = connector.checkpoint()
if checkpoint.get("last_seen_at") is not None:
    await _upsert_checkpoint(session, connector_id, checkpoint)
```

Replace with:
```python
checkpoint = connector.checkpoint()
if mode == "live" and checkpoint.get("last_seen_at") is not None:
    await _upsert_checkpoint(session, connector_id, checkpoint)
```

This is the single most critical change — without it, replay would corrupt the checkpoint.

### API Endpoint: Mode Passthrough

In `api/connectors.py`, the endpoint currently calls:
```python
summary = await run_connector(session, connector)
```

Update to:
```python
mode = body.mode if body else "live"
summary = await run_connector(session, connector, mode=mode)
```

The `ConnectorRunResponse.from_summary()` already includes `mode` from `ConnectorRunSummary`, so the response automatically reflects replay mode — no changes needed to `ConnectorRunResponse`.

### DB Migration Pattern

Follow `backend/alembic/versions/003_add_processing_columns_and_job_type.py` exactly:
- Use `_has_column(op, "ingestion_jobs", "mode")` guard in `upgrade()`
- Column definition: `sa.Column("mode", sa.String(10), nullable=True)`
- `downgrade()`: `op.drop_column("ingestion_jobs", "mode")`

### What NOT To Do

- **Do NOT** add a separate replay endpoint — use the existing `POST /{connector_id}/run` with `mode` in the body
- **Do NOT** create a `ReplayConnector` class or replay-specific subclass of `BaseConnector` — the same `TwitterFileConnector` handles both modes
- **Do NOT** modify `TwitterFileConnector`, `validate_and_normalize()`, or `ingest_normalized_posts_with_external_id()` — these are mode-agnostic
- **Do NOT** skip checkpoint loading for replay — loading the existing checkpoint during a replay run is harmless and keeps the code path clean; just don't *save* a new one

### `raw_payload` Field: Replay Infrastructure Already Exists

`NormalizedPost.raw_payload` (defined in `schemas.py`) already stores the full raw record with the note "for replay mode". `TwitterFileConnector.normalize()` already populates this field. Story 5-3 does not need to change any of this — the field was designed for this story.

### No Checkpoint Injection Change for Replay

The current `run_connector()` loads the checkpoint and injects `_after_timestamp` into the connector regardless of mode. For replay mode, this means:
- If a checkpoint exists, replay will **filter records by timestamp** (only replay records newer than the last checkpoint)
- This is **correct behavior** — replay should behave identically to a live run in terms of which records are processed

If the operator wants to replay ALL records (ignore checkpoint), they should pass the file directly without any checkpoint. This is a design decision — document it clearly, but do NOT add a `ignore_checkpoint` flag (out of scope).

### Previous Story Patterns to Follow

From Story 5-2 review learnings:
- **Multiple session commits**: `_create_running_job` and `_persist_connector_job` use `async_session_maker()` (separate sessions), NOT the main session. Keep this pattern.
- **Path traversal protection**: Already implemented in the endpoint — no changes needed.
- **`finished_at` before persist**: `summary.finished_at = datetime.now(timezone.utc)` must be set BEFORE calling `_persist_connector_job()`.

### Project Structure Notes

**New files to create:**
```
backend/alembic/versions/005_add_connector_mode.py
backend/tests/connectors/test_replay_mode.py
```

**Files to modify:**
- `backend/app/connectors/service.py` — add `mode` param, gate checkpoint on `mode == "live"`
- `backend/app/api/connectors.py` — add `mode` to `ConnectorRunRequest`, pass to `run_connector()`
- `backend/app/models/ingestion_job.py` — add `mode` column

**Files NOT to modify:**
- `backend/app/connectors/interface.py` — interface is complete
- `backend/app/connectors/twitter_file.py` — connector is mode-agnostic
- `backend/app/connectors/validator.py` — validation is mode-agnostic
- `backend/app/connectors/schemas.py` — `ConnectorRunSummary.mode` already exists
- `backend/app/api/connectors.py` `ConnectorRunResponse` — already has `mode` field

### References

- Story requirements: [epics.md, Epic 5, Story 5.3](../planning-artifacts/epics.md) lines 829–845
- Previous story (checkpointing established): [5-2-first-platform-connector-offline-first-checkpointing.md](./5-2-first-platform-connector-offline-first-checkpointing.md)
- Connector service (run_connector): [backend/app/connectors/service.py](../../../backend/app/connectors/service.py)
- Connector API endpoint: [backend/app/api/connectors.py](../../../backend/app/api/connectors.py)
- ConnectorRunSummary schema (mode field): [backend/app/connectors/schemas.py](../../../backend/app/connectors/schemas.py)
- IngestionJob model: [backend/app/models/ingestion_job.py](../../../backend/app/models/ingestion_job.py)
- Migration pattern: [backend/alembic/versions/003_add_processing_columns_and_job_type.py](../../../backend/alembic/versions/003_add_processing_columns_and_job_type.py)
- Existing connector service tests: [backend/tests/connectors/test_connector_service.py](../../../backend/tests/connectors/test_connector_service.py)

## Dev Agent Record

### Agent Model Used

_to be filled by dev agent_

### Debug Log References

_to be filled by dev agent_

### Completion Notes List

_to be filled by dev agent_

### File List

_to be filled by dev agent_

### Change Log

_to be filled by dev agent_
