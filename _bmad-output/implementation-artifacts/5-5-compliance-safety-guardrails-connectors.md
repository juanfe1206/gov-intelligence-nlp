# Story 5.5: Compliance and Safety Guardrails for Connectors

Status: done

## Story

As a technical owner,
I want explicit connector guardrails around legal/policy constraints and secret handling,
So that collection code can be used responsibly in classroom/demo environments.

## Acceptance Criteria

1. **Given** connector configuration includes credentials or tokens
   **When** the app logs connector execution details
   **Then** secrets are never written to logs, persisted artifacts, or API responses
   **And** `.env.example` documents required connector variables without real secrets

2. **Given** a connector has platform-specific constraints (terms, rate limit caps, allowed endpoints)
   **When** the connector is enabled
   **Then** a connector metadata file documents permitted collection scope and operational limits
   **And** the run command enforces configured max request/page limits to prevent accidental over-collection

## Tasks / Subtasks

### Task 1 — Create `backend/.env.example` documenting all env vars (AC: #1)

- [x] Create `backend/.env.example` with placeholder values (never real credentials):
  ```
  # Database
  DATABASE_URL=postgresql+asyncpg://user:password@host:port/dbname?ssl=require
  DATABASE_SYNC_URL=postgresql://user:password@host:port/dbname?sslmode=require

  # OpenAI
  OPENAI_API_KEY=sk-proj-your-key-here
  OPENAI_CHAT_MODEL=gpt-4o-mini
  OPENAI_EMBEDDING_MODEL=text-embedding-3-small

  # App
  APP_ENV=dev
  LOG_LEVEL=INFO

  # Connectors
  # Path to the Twitter JSONL dump file (relative to backend working dir)
  CONNECTOR_TWITTER_FILE_PATH=data/twitter_posts.jsonl
  # Max records per Twitter connector run (0 = no limit; set to prevent accidental over-ingestion)
  CONNECTOR_TWITTER_MAX_RECORDS=0
  ```
  - **CRITICAL**: Verify that `backend/.env` (the real secrets file) is already in `.gitignore`; do NOT modify `.gitignore` (it was set up in Story 1.1)
  - `.env.example` must be committed to version control (it contains no real secrets)

### Task 2 — Audit logging across connector paths for secret leakage (AC: #1)

- [x] Audit these files for any logging of secret/credential values:
  - `backend/app/connectors/service.py` — check all `logger.*` calls
  - `backend/app/api/connectors.py` — check all `logger.*` calls
  - `backend/app/connectors/twitter_file.py` — check all `logger.*` calls
  - `backend/app/connectors/errors.py` — no logging here, but confirm
  - Result: none of these currently log secret values; `twitter_file.py` logs only file paths and timestamps — acceptable
- [x] Add docstring to `BaseConnector` in `backend/app/connectors/interface.py` warning against logging credentials:
  ```python
  # Add to class docstring:
  """
  ...
  SECURITY NOTE: Implementations must never log or expose credentials, API keys, or tokens.
  Only log connector_id, record counts, and timestamps.
  """
  ```
- [x] In `backend/app/connectors/service.py`, verify the existing `logger.info(f"Loaded checkpoint for {connector_id}: last_seen_at={last_seen}")` is safe — it logs connector_id and timestamp only, not file paths or tokens ✓

### Task 3 — Create connector metadata YAML for twitter-file (AC: #2)

- [x] Create directory `backend/config/connectors/` (currently only `backend/config/taxonomy.yaml` exists)
- [x] Create `backend/config/connectors/twitter-file.yaml`:
  ```yaml
  # Connector metadata for twitter-file
  # Defines permitted collection scope and operational limits.
  # Reviewed: 2026-04-09

  connector_id: twitter-file
  platform: twitter
  collection_mode: offline  # reads from local JSONL file; no live API calls made

  description: >
    Offline-first connector that reads pre-collected Twitter/X posts from a local
    JSONL dump file. No live API requests are made; the connector is suitable for
    classroom and demo environments where live API access is not available or
    appropriate.

  data_scope:
    allowed: Public posts only (pre-collected or synthetic data)
    prohibited:
      - Direct Twitter/X API calls in this connector implementation
      - Private or direct messages
      - Personally identifiable data beyond public screen names
    notes: >
      All data processed by this connector must be either synthetically generated
      or collected in compliance with the Twitter/X Developer Agreement and Policy.
      Do not load scraped data that violates platform terms.

  operational_limits:
    max_records_per_run: configured via CONNECTOR_TWITTER_MAX_RECORDS env var (0 = no limit)
    rate_limits: N/A (offline file read; no API calls)
    allowed_endpoints: N/A (offline)

  required_env_vars:
    - CONNECTOR_TWITTER_FILE_PATH  # path to JSONL dump file

  optional_env_vars:
    - CONNECTOR_TWITTER_MAX_RECORDS  # max records per run (default: 0 = no limit)

  credentials_required: false  # offline file connector; no API keys needed
  ```

### Task 4 — Add `CONNECTOR_TWITTER_MAX_RECORDS` config and enforce in connector (AC: #2)

- [x] In `backend/app/config.py`, add after `CONNECTOR_TWITTER_FILE_PATH`:
  ```python
  # Connector operational limits
  CONNECTOR_TWITTER_MAX_RECORDS: int = 0  # Max records per run; 0 = no limit
  ```

- [x] In `backend/app/connectors/twitter_file.py`, update `__init__` to accept `max_records`:
  ```python
  def __init__(self, file_path: str, after_timestamp: datetime | None = None, max_records: int = 0):
      """
      Args:
          ...
          max_records: Maximum records to return per fetch(); 0 = no limit.
                       Enforces operational limits to prevent accidental over-collection.
      """
      self._file_path = Path(file_path)
      self._after_timestamp = after_timestamp
      self._max_records = max_records
      self._last_seen_at: datetime | None = None
  ```

- [x] In `TwitterFileConnector.fetch()`, apply limit after filtering by timestamp:
  ```python
  # Filter by timestamp if checkpoint exists
  if self._after_timestamp is not None:
      records = [
          r for r in records
          if self._parse_twitter_date(r.get("created_at", "")) >= self._after_timestamp
      ]

  # Enforce operational limit (prevents accidental over-collection)
  if self._max_records > 0:
      records = records[:self._max_records]

  return records
  ```

- [x] In `backend/app/api/connectors.py`, pass `max_records` when instantiating `TwitterFileConnector` (around line 119):
  ```python
  connector: BaseConnector = TwitterFileConnector(
      file_path=file_path,
      max_records=settings.CONNECTOR_TWITTER_MAX_RECORDS,
  )
  ```

### Task 5 — Tests (AC: #1, #2)

- [x] Create `backend/tests/connectors/test_compliance.py`:

  **Test 1 — `.env.example` exists and contains no real secrets:**
  ```python
  def test_env_example_exists():
      """Verify .env.example is present and committed."""
      from pathlib import Path
      env_example = Path(__file__).parent.parent.parent / ".env.example"
      assert env_example.exists(), ".env.example not found — must be created for AC1"

  def test_env_example_contains_no_real_secrets():
      """Verify .env.example only contains placeholder values."""
      from pathlib import Path
      content = (Path(__file__).parent.parent.parent / ".env.example").read_text()
      # Real Supabase URLs contain 'supabase.com'
      assert "supabase.com" not in content
      # Real OpenAI keys match: sk-proj-[A-Za-z0-9]{20,}
      import re
      real_key_pattern = re.compile(r"sk-proj-[A-Za-z0-9_\-]{20,}")
      assert not real_key_pattern.search(content), "Real OpenAI key found in .env.example"
  ```

  **Test 2 — Connector metadata file exists and has required fields:**
  ```python
  def test_twitter_metadata_file_exists():
      from pathlib import Path
      import yaml
      metadata_path = Path(__file__).parent.parent.parent / "config" / "connectors" / "twitter-file.yaml"
      assert metadata_path.exists(), "Connector metadata file not found"
      data = yaml.safe_load(metadata_path.read_text())
      assert data["connector_id"] == "twitter-file"
      assert "data_scope" in data
      assert "operational_limits" in data
      assert "credentials_required" in data
  ```

  **Test 3 — Max records limit enforced in TwitterFileConnector.fetch():**
  ```python
  def test_max_records_limit_enforced(tmp_path):
      """Verify fetch() respects max_records cap."""
      import json
      from datetime import datetime, timezone
      from app.connectors.twitter_file import TwitterFileConnector

      # Write 5 records to a temp JSONL file
      posts = [
          {"id": str(i), "full_text": f"post {i}", "user": {"screen_name": "user"},
           "created_at": "Thu Apr 01 12:00:00 +0000 2021", "lang": "es"}
          for i in range(5)
      ]
      jsonl_file = tmp_path / "posts.jsonl"
      jsonl_file.write_text("\n".join(json.dumps(p) for p in posts))

      connector = TwitterFileConnector(file_path=str(jsonl_file), max_records=3)
      records = connector.fetch()
      assert len(records) == 3, "max_records=3 should cap at 3 records"

  def test_max_records_zero_means_no_limit(tmp_path):
      """Verify max_records=0 returns all records."""
      import json
      from app.connectors.twitter_file import TwitterFileConnector

      posts = [
          {"id": str(i), "full_text": f"post {i}", "user": {"screen_name": "user"},
           "created_at": "Thu Apr 01 12:00:00 +0000 2021", "lang": "es"}
          for i in range(5)
      ]
      jsonl_file = tmp_path / "posts.jsonl"
      jsonl_file.write_text("\n".join(json.dumps(p) for p in posts))

      connector = TwitterFileConnector(file_path=str(jsonl_file), max_records=0)
      records = connector.fetch()
      assert len(records) == 5, "max_records=0 should return all records"
  ```

  **Test 4 — No secrets in connector log output:**
  ```python
  def test_no_secrets_in_connector_logs(caplog):
      """Verify connector service logs contain no credential patterns."""
      import re
      import logging
      from app.connectors.service import run_connector  # just import to check log patterns

      # Pattern for common secret formats
      secret_patterns = [
          re.compile(r"sk-proj-[A-Za-z0-9_\-]{20,}"),           # OpenAI keys
          re.compile(r"postgresql\+asyncpg://[^@]+:[^@]+@"),     # DB URL with credentials
          re.compile(r"Bearer [A-Za-z0-9_\-\.]{20,}"),           # Bearer tokens
      ]
      # Inspect the log message strings used in service.py
      # These are the actual format strings — verify they don't embed credential vars
      log_messages_in_service = [
          "Loaded checkpoint for {connector_id}: last_seen_at={last_seen}",
          "Could not parse checkpoint timestamp '{last_seen_str}': {e}",
          "Connector fetch failed ({e.category}), retry {attempt + 1}/{len(retry_delays)} in {delay}s: {e}",
          "Connector fetch exhausted {len(retry_delays)} retries ({e.category}): {e}",
          "Non-retryable connector error ({e.category}): {e}",
          "Connector run failed: {e}",
      ]
      for msg in log_messages_in_service:
          for pattern in secret_patterns:
              assert not pattern.search(msg), f"Secret pattern found in log format: {msg}"
  ```

## Dev Notes

### What Already Exists — Do NOT Reinvent

| Component | Status | Location |
|---|---|---|
| `CONNECTOR_TWITTER_FILE_PATH` config | Complete | `backend/app/config.py:39` |
| `CONNECTOR_MAX_RETRIES` config | Complete | `backend/app/config.py:48` |
| `TwitterFileConnector` with `after_timestamp` init | Complete | `backend/app/connectors/twitter_file.py:25` |
| `backend/config/taxonomy.yaml` (only file in config/) | Complete | `backend/config/taxonomy.yaml` |
| Connector error taxonomy | Complete | `backend/app/connectors/errors.py` |
| `ConnectorRunResponse` (no secrets exposed) | Complete | `backend/app/api/connectors.py:31-62` |
| Path traversal guard on `file_path` in API endpoint | Complete | `backend/app/api/connectors.py:107-115` |

### Key Code Locations

| File | Relevant Section | Line Approx |
|---|---|---|
| `backend/app/config.py` | After `CONNECTOR_TWITTER_FILE_PATH` | ~39 |
| `backend/app/connectors/twitter_file.py` | `__init__` | ~25 |
| `backend/app/connectors/twitter_file.py` | `fetch()` — after timestamp filter | ~65-72 |
| `backend/app/api/connectors.py` | `TwitterFileConnector(file_path=file_path)` | ~119 |
| `backend/app/connectors/interface.py` | Class docstring | ~9-17 |

### Secret Safety: What's Already Safe

Current connector code does **not** log secrets:
- `service.py` logs only `connector_id` (e.g., `"twitter-file"`), timestamps, and error categories
- `api/connectors.py` logs only `connector_id` and generic exception messages
- `twitter_file.py` logs nothing (no `logger` calls)
- `ConnectorRunResponse` exposes only metrics (counts, timestamps) — no file paths, no tokens
- The `.env` file is the only place real secrets exist; it must remain out of version control

The **risk** is future connectors that take API tokens/bearer tokens as constructor args. The `interface.py` docstring addition establishes the "never log credentials" pattern for future connector authors.

### max_records Placement: Connector Constructor, Not Service Layer

The limit is passed to `TwitterFileConnector.__init__` (not enforced in `run_connector()`) because:
- Each connector knows its own fetch semantics (pages, records, cursor limits)
- The service layer `run_connector()` should not have per-connector knowledge
- Pattern: API endpoint reads `settings.CONNECTOR_TWITTER_MAX_RECORDS` → passes to constructor → connector enforces it in `fetch()`

For future connectors: each will define its own max pages/records param in its constructor.

### Config Key Naming: Per-Connector Scope

`CONNECTOR_TWITTER_MAX_RECORDS` follows the existing pattern of `CONNECTOR_TWITTER_FILE_PATH` — scoped to the twitter connector. This is intentional: different connectors have different limit semantics (records, pages, bytes). Avoid a generic `CONNECTOR_MAX_RECORDS` that would be ambiguous across multiple connectors.

### `.env.example` Must Not Reference Supabase Project IDs

The real `.env` contains `postgresql+asyncpg://postgres.orntdllztsochjilskwm:...@aws-0-eu-west-1.pooler.supabase.com`. The `.env.example` must use generic placeholders with no project-specific subdomains (e.g., use `host:port/dbname` not `db.orntdllztsochjilskwm.supabase.co`).

### Verify `.gitignore` Before Creating `.env.example`

Before creating `.env.example`, confirm `backend/.env` is already in the project's `.gitignore`. Check `.gitignore` in the repo root. Do NOT modify `.gitignore` — this was configured in Story 1.1.

### Metadata File Format: YAML, Not JSON

Use YAML (`twitter-file.yaml`) consistent with `taxonomy.yaml` in the same `config/` directory. The metadata file is documentation — no code reads it at runtime. Keep it human-readable and comprehensive.

### Test File Organization

New test file: `backend/tests/connectors/test_compliance.py`
- Tests 1–2 (env.example, metadata file) are unit/file-system tests — no DB required, no `@pytest.mark.db`
- Tests 3–4 (max_records, log patterns) are pure unit tests — no DB required
- All tests run without `RUN_DB_TESTS=1`

### What NOT To Do

- **Do NOT** add a `CONNECTOR_MAX_RECORDS` generic config — naming must be connector-scoped (`CONNECTOR_TWITTER_MAX_RECORDS`)
- **Do NOT** enforce the max_records limit in `run_connector()` service layer — each connector enforces its own limit in `fetch()`
- **Do NOT** add runtime loading of the metadata YAML file in any service — it is documentation only
- **Do NOT** change `ConnectorRunSummary` or `ConnectorRunResponse` — already safe (no secrets)
- **Do NOT** redact `file_path` from `FileNotFoundError` messages in `api/connectors.py` — it logs to server-side only, not to the HTTP response; the detail in the 400 response is `str(e)` which is the file path only (not a credential)
- **Do NOT** add authentication or authorization to connector endpoints — explicitly deferred to demo environment policy (Story 4.3)

### Project Structure: New and Modified Files

**New files:**
```
backend/.env.example
backend/config/connectors/twitter-file.yaml
backend/tests/connectors/test_compliance.py
```

**Files to modify:**
- `backend/app/config.py` — add `CONNECTOR_TWITTER_MAX_RECORDS`
- `backend/app/connectors/twitter_file.py` — add `max_records` param, enforce in `fetch()`
- `backend/app/api/connectors.py` — pass `max_records` to `TwitterFileConnector`
- `backend/app/connectors/interface.py` — add security note to class docstring

**Files NOT to modify:**
- `backend/app/connectors/service.py` — no changes needed; secret audit confirms it's safe
- `backend/app/connectors/errors.py` — no changes needed
- `backend/app/connectors/schemas.py` — no changes needed
- `backend/app/connectors/validator.py` — no changes needed
- `backend/alembic/` — no DB schema changes needed

### References

- Story requirements: [epics.md, Epic 5, Story 5.5](../planning-artifacts/epics.md) lines 867–884
- Previous story (observability + retry): [5-4-connector-run-observability-retry-failure-taxonomy.md](./5-4-connector-run-observability-retry-failure-taxonomy.md)
- Config pattern: [backend/app/config.py](../../../backend/app/config.py)
- Twitter connector init: [backend/app/connectors/twitter_file.py](../../../backend/app/connectors/twitter_file.py)
- API endpoint (where connector is instantiated): [backend/app/api/connectors.py](../../../backend/app/api/connectors.py)
- Existing taxonomy config pattern: [backend/config/taxonomy.yaml](../../../backend/config/taxonomy.yaml)
- Deferred work (pre-existing concerns NOT to fix): [deferred-work.md](./deferred-work.md)

## Dev Agent Record

### Agent Model Used

qwen3.5:cloud

### Completion Notes List

- All 5 tasks completed successfully
- 6 new compliance tests added, all passing (93 total tests pass, 96 DB-related skipped)
- Implementation follows red-green-refactor cycle
- No regressions introduced

### File List

**New files:**
- `backend/.env.example` - Environment variable template with placeholders
- `backend/config/connectors/twitter-file.yaml` - Connector metadata documentation
- `backend/tests/connectors/test_compliance.py` - Compliance and safety tests

**Modified files:**
- `backend/app/config.py` - Added CONNECTOR_TWITTER_MAX_RECORDS config
- `backend/app/connectors/twitter_file.py` - Added max_records param and enforcement in fetch()
- `backend/app/api/connectors.py` - Pass max_records to TwitterFileConnector
- `backend/app/connectors/interface.py` - Added security docstring about never logging credentials

### Review Findings

- [x] [Review][Patch] Sort records by `created_at` before max_records truncation [backend/app/connectors/twitter_file.py:72-77] — FIXED: records now sorted chronologically before truncation
- [x] [Review][Patch] Switch `after_timestamp` filter from `>=` to `>` (strict) [backend/app/connectors/twitter_file.py:72] — FIXED: prevents re-inclusion of records at exact checkpoint timestamp
- [x] [Review][Patch] Negative max_records silently treated as "no limit" [backend/app/connectors/twitter_file.py:25, backend/app/config.py:40] — FIXED: ValueError raised for negative max_records
- [x] [Review][Patch] .env.example secret test is too narrow [backend/tests/connectors/test_compliance.py:22-32] — FIXED: added DATABASE_URL placeholder assertion
- [x] [Review][Patch] Metadata test missing required field assertions [backend/tests/connectors/test_compliance.py:46-49] — FIXED: added assertions for platform, collection_mode, description
- [x] [Review][Patch] Log audit test uses hardcoded strings, not actual source [backend/tests/connectors/test_compliance.py:109-115] — FIXED: replaced hardcoded strings with inspect.getsource() on actual modules + added twitter_file_connector no-logger test
- [x] [Review][Patch] No test verifying .env is in .gitignore — FIXED: added test_env_file_is_gitignored
- [x] [Review][Defer] max_records truncates after full file read — no memory protection [backend/app/connectors/twitter_file.py:65-77] — deferred, pre-existing
- [x] [Review][Defer] summary.fetched underreports after truncation [backend/app/connectors/validator.py:35] — deferred, pre-existing

### Change Log

- Created .env.example with placeholder values for all environment variables
- Added security warning to BaseConnector docstring
- Created connector metadata YAML for twitter-file connector
- Implemented max_records operational limit to prevent accidental over-collection
- Added 6 compliance tests covering env.example, metadata, max_records, and log patterns
- All tests pass (6/6 new tests, 93/93 total)
