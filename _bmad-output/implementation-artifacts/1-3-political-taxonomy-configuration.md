# Story 1.3: Political Taxonomy Configuration

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an admin or technical user,
I want to configure the list of political topics, subtopics, and targets from a YAML file,
so that the NLP pipeline tags posts consistently using a stable domain taxonomy without requiring code changes.

## Acceptance Criteria

1. **Given** a valid `taxonomy.yaml` file defining topics, subtopics, and targets (parties, leaders)  
   **When** the backend starts  
   **Then** the taxonomy is loaded into memory and `GET /taxonomy` returns the full taxonomy structure as JSON

2. **Given** an admin updates `taxonomy.yaml` to add or rename a topic  
   **When** the backend is restarted  
   **Then** subsequent processing runs use the updated taxonomy and new posts are tagged with the new labels  
   **And** already-processed posts retain their original labels (no retroactive re-tagging)

3. **Given** the taxonomy config is missing or malformed  
   **When** the backend starts  
   **Then** the app fails fast with a clear error identifying the config problem, rather than starting silently with broken data

## Tasks / Subtasks

- [x] Create `backend/config/taxonomy.yaml` with realistic Spanish political taxonomy sample data (AC: #1, #2)
  - [x] Define at least 3 topics, each with 2–3 subtopics
  - [x] Define at least 3 party targets and 3 leader targets
- [x] Create `backend/app/taxonomy/` package with Pydantic schema and loader (AC: #1, #3)
  - [x] `schemas.py` — Pydantic models: `TaxonomyTarget`, `TaxonomySubtopic`, `TaxonomyTopic`, `TaxonomyConfig`
  - [x] `loader.py` — `load_taxonomy(path)` reads YAML, validates via Pydantic, raises on error
  - [x] `__init__.py` — exports `load_taxonomy` and schema types
- [x] Integrate taxonomy loading at application startup (AC: #1, #3)
  - [x] Add `TAXONOMY_PATH` to `Settings` in `backend/app/config.py` with default `config/taxonomy.yaml`
  - [x] Use FastAPI `lifespan` context manager in `main.py` to load taxonomy once at startup and store in `app.state.taxonomy`
  - [x] If `load_taxonomy` raises, let the exception propagate — uvicorn will exit with a clear traceback
- [x] Implement `GET /taxonomy` endpoint (AC: #1)
  - [x] Create `backend/app/api/taxonomy.py` router
  - [x] Register router in `main.py` with prefix `/taxonomy`
  - [x] Return full taxonomy as JSON (topics → subtopics → targets)
- [x] Write tests (AC: #1, #3)
  - [x] `backend/tests/test_taxonomy_loader.py` — valid YAML loads, missing file raises, malformed YAML raises, extra unknown fields are rejected or ignored per policy
  - [x] `backend/tests/test_taxonomy_api.py` — `GET /taxonomy` returns 200 with correct structure using TestClient + mock app state

## Dev Notes

### What This Story Accomplishes

Adds the **taxonomy configuration layer** that stories 1.4 (CSV Ingestion) and 1.5 (NLP Classification) depend on. The taxonomy determines the allowed labels for `topic`, `subtopic`, and `target` fields in `processed_posts`. It is loaded from a file at startup — not stored in the database — to keep configuration externalized and easy to version-control.

This story does **not** implement NLP classification, ingestion, or re-tagging of existing posts. It only exposes what the taxonomy currently is.

### Taxonomy YAML Structure

Design the YAML schema to be both human-editable and machine-validated. Recommended structure:

```yaml
# backend/config/taxonomy.yaml
topics:
  - name: "vivienda"
    label: "Housing"
    subtopics:
      - name: "alquiler"
        label: "Rental"
      - name: "hipotecas"
        label: "Mortgages"
  - name: "sanidad"
    label: "Healthcare"
    subtopics:
      - name: "atencion_primaria"
        label: "Primary Care"

targets:
  parties:
    - name: "pp"
      label: "Partido Popular"
    - name: "psoe"
      label: "PSOE"
    - name: "vox"
      label: "VOX"
  leaders:
    - name: "sanchez"
      label: "Pedro Sánchez"
    - name: "feijoo"
      label: "Alberto Feijóo"
```

- `name` fields are machine identifiers (lowercase, no spaces) — these are what `processed_posts.topic`, `processed_posts.subtopic`, and `processed_posts.target` will store.
- `label` fields are human-readable display strings for the frontend.
- Pydantic validation should reject duplicate `name` values within the same list.

### Pydantic Schema Design

```python
# backend/app/taxonomy/schemas.py
from pydantic import BaseModel, field_validator

class TaxonomyTarget(BaseModel):
    name: str  # machine identifier
    label: str  # display label

class TaxonomySubtopic(BaseModel):
    name: str
    label: str

class TaxonomyTopic(BaseModel):
    name: str
    label: str
    subtopics: list[TaxonomySubtopic] = []

class TaxonomyTargets(BaseModel):
    parties: list[TaxonomyTarget] = []
    leaders: list[TaxonomyTarget] = []

class TaxonomyConfig(BaseModel):
    topics: list[TaxonomyTopic]
    targets: TaxonomyTargets

    @field_validator("topics")
    @classmethod
    def no_duplicate_topic_names(cls, topics):
        names = [t.name for t in topics]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate topic names found in taxonomy")
        return topics
```

### Taxonomy Loader

```python
# backend/app/taxonomy/loader.py
import yaml
from pathlib import Path
from app.taxonomy.schemas import TaxonomyConfig

def load_taxonomy(path: str | Path) -> TaxonomyConfig:
    """Load and validate taxonomy from YAML file.
    
    Raises:
        FileNotFoundError: if path does not exist
        yaml.YAMLError: if YAML is malformed
        pydantic.ValidationError: if schema is invalid
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Taxonomy file not found: {p.resolve()}")
    with open(p, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return TaxonomyConfig.model_validate(raw)
```

**Do not catch exceptions in `load_taxonomy`** — let them propagate so the startup crash message is maximally informative.

### FastAPI Lifespan Integration

Use the `lifespan` context manager (FastAPI 0.93+) instead of deprecated `@app.on_event("startup")`:

```python
# backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from app.taxonomy.loader import load_taxonomy

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load taxonomy — raises on error, which aborts startup
    app.state.taxonomy = load_taxonomy(settings.TAXONOMY_PATH)
    yield
    # Shutdown: nothing to clean up for taxonomy

app = FastAPI(..., lifespan=lifespan)
```

### API Endpoint

```python
# backend/app/api/taxonomy.py
from fastapi import APIRouter, Request
from app.taxonomy.schemas import TaxonomyConfig

router = APIRouter()

@router.get("", response_model=TaxonomyConfig)
async def get_taxonomy(request: Request) -> TaxonomyConfig:
    """Return the full political taxonomy."""
    return request.app.state.taxonomy
```

Register in `main.py`:
```python
from app.api.taxonomy import router as taxonomy_router
app.include_router(taxonomy_router, prefix="/taxonomy", tags=["taxonomy"])
```

### Settings Update

Add to `backend/app/config.py` Settings class:

```python
TAXONOMY_PATH: str = "config/taxonomy.yaml"
```

The default path is relative to the working directory where uvicorn is launched (i.e., `backend/`). No changes to `.env.example` needed unless the operator wants to override.

### Project Structure Notes

**Files to create:**
```
backend/
├── config/
│   └── taxonomy.yaml          # Taxonomy configuration (NEW)
├── app/
│   ├── api/
│   │   └── taxonomy.py        # GET /taxonomy endpoint (NEW)
│   └── taxonomy/
│       ├── __init__.py        # Package init (NEW)
│       ├── schemas.py         # Pydantic models (NEW)
│       └── loader.py          # YAML loader (NEW)
```

**Files to modify:**
- `backend/app/config.py` — add `TAXONOMY_PATH: str = "config/taxonomy.yaml"`
- `backend/app/main.py` — add lifespan context manager and register taxonomy router

**Do not modify:** any files under `backend/app/db/` or `backend/app/models/` — this story has no DB changes.

### Key Constraints (Architecture Compliance)

- Taxonomy is loaded from file, **not** stored in the database for the MVP. The `processed_posts` table stores the resolved `topic`/`subtopic`/`target` string values — validation against the taxonomy happens at classification time (Story 1.5), not enforced by a DB foreign key.
- Use **Pydantic v2** (`model_validate`, `field_validator` with `@classmethod`) — the project already uses Pydantic v2 (see `config.py` using `pydantic_settings`).
- Use `yaml.safe_load` (not `yaml.load`) to prevent arbitrary code execution via YAML.
- The `GET /taxonomy` response must be pure JSON (no YAML). Use Pydantic's `.model_dump()` / FastAPI's `response_model` for serialization.
- `TAXONOMY_PATH` in Settings must NOT be marked as required — it has a sensible default. This prevents CI from failing due to a missing env var.
- Do **not** add `pyyaml` to `requirements-dev.txt` — it belongs in `requirements.txt` since it runs in production.

### Previous Story Intelligence (Story 1.2)

**Patterns established:**
- Pydantic v2 `BaseSettings` used in `config.py` with `class Config: env_file = ".env"; case_sensitive = True`
- FastAPI app defined in `backend/app/main.py` — include new routers there using `app.include_router(...)`
- Tests live in `backend/tests/`; conftest loads `.env` — use `TestClient` from `starlette.testclient` for API tests
- `pytest-asyncio` is installed (dev dep) — use for any async tests

**Review findings from Story 1.2 to avoid repeating:**
- Do NOT interpolate user-controlled strings into SQL without parameterization
- Test conftest loads root `.env`; if taxonomy tests need a custom path, use a `tmp_path` fixture rather than pointing at the real config
- Do not add test/dev-only packages to `requirements.txt` (runtime)

**Files from Story 1.2 you can import from:**
- `app.config.settings` — the global Settings instance
- `app.db.session` — async session factory (NOT needed by this story)
- `app.models` — `RawPost`, `ProcessedPost` (NOT needed by this story)

### Git Intelligence

Recent commits show:
- Story 1.2 complete: `backend/app/config.py` has `DATABASE_SYNC_URL`, `DATABASE_URL`, `OPENAI_API_KEY` as required fields
- CI workflow uses `requirements-dev.txt` for test deps and `requirements.txt` for runtime
- Backend runs from `backend/` directory — paths in config should be relative to that working directory

### References

- [Epics](_bmad-output/planning-artifacts/epics.md#Story-1.3) — Story 1.3 requirements
- [Architecture](_bmad-output/planning-artifacts/architecture.md#Configuration-Management) — Taxonomy externalization rationale
- [Story 1.2](1-2-database-schema-migration-setup.md) — Established patterns and review learnings
- [backend/app/config.py](backend/app/config.py) — Settings class to extend
- [backend/app/main.py](backend/app/main.py) — FastAPI app where lifespan and router are registered

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- ✅ Created `backend/config/taxonomy.yaml` with 4 topics (vivienda, sanidad, economia, educacion), each with 3 subtopics, 6 parties, and 6 leaders
- ✅ Created `backend/app/taxonomy/schemas.py` with Pydantic models (TaxonomyTarget, TaxonomySubtopic, TaxonomyTopic, TaxonomyTargets, TaxonomyConfig) including duplicate name validators and extra="forbid" strict validation
- ✅ Created `backend/app/taxonomy/loader.py` with `load_taxonomy(path)` function that reads YAML, validates via Pydantic, and raises on errors (FileNotFoundError, yaml.YAMLError, ValidationError)
- ✅ Created `backend/app/taxonomy/__init__.py` exporting all public types and load_taxonomy function
- ✅ Updated `backend/app/config.py` with TAXONOMY_PATH setting (default: "config/taxonomy.yaml")
- ✅ Updated `backend/app/main.py` with FastAPI lifespan context manager to load taxonomy at startup and store in app.state.taxonomy
- ✅ Created `backend/app/api/taxonomy.py` with GET /taxonomy endpoint returning full TaxonomyConfig as JSON
- ✅ Registered taxonomy router in main.py with prefix /taxonomy
- ✅ Created `backend/tests/test_taxonomy_loader.py` with 12 comprehensive tests covering valid load, missing file, malformed YAML, invalid schema, empty list handling, unknown fields rejection, duplicate name validators, and model serialization
- ✅ Created `backend/tests/test_taxonomy_api.py` with 9 tests covering response structure, expected topics/targets, schema validation, UTF-8 labels, and content validation
- ✅ All 21 new tests pass (33 total tests pass, 6 skipped due to missing test database)

### File List

- `backend/config/taxonomy.yaml` (NEW)
- `backend/app/taxonomy/__init__.py` (NEW)
- `backend/app/taxonomy/schemas.py` (NEW)
- `backend/app/taxonomy/loader.py` (NEW)
- `backend/app/api/taxonomy.py` (NEW)
- `backend/tests/test_taxonomy_loader.py` (NEW)
- `backend/tests/test_taxonomy_api.py` (NEW)
- `backend/tests/conftest.py` (MODIFIED - added OPENAI_API_KEY default, sample_taxonomy fixture, updated client fixture for lifespan)
- `backend/app/config.py` (MODIFIED - added TAXONOMY_PATH setting)
- `backend/app/main.py` (MODIFIED - added lifespan context manager, taxonomy router registration)

### Review Findings

- [x] [Review][Patch] `sample_taxonomy` fixture uses hardcoded relative path — breaks when pytest run from repo root [backend/tests/conftest.py:53]
- [x] [Review][Patch] Router import placed mid-module after route definitions [backend/app/main.py]
- [x] [Review][Patch] `DATABASE_SYNC_URL` added as required field with no default — already documented in .env.example; dismissed as handled [backend/app/config.py]
- [x] [Review][Patch] `yaml.safe_load()` returns `None` for empty/comment-only YAML — causes confusing Pydantic error instead of clear failure [backend/app/taxonomy/loader.py]
- [x] [Review][Patch] Malformed YAML test uses bare `try/except` — passes even if no exception raised, AC3 not enforced [backend/tests/test_taxonomy_loader.py]
- [x] [Review][Defer] No schema-level validation that `name` fields are lowercase with no spaces [backend/app/taxonomy/schemas.py] — deferred, pre-existing gap; Story 1.5 is the right enforcement point
- [x] [Review][Defer] `tardà` uses non-ASCII character as a machine identifier [backend/config/taxonomy.yaml] — deferred, valid for now; address before any URL routing or DB key usage
- [x] [Review][Defer] API tests assert specific taxonomy YAML content, not just structure [backend/tests/test_taxonomy_api.py] — deferred, low-risk brittleness
- [x] [Review][Defer] `request.app.state.taxonomy` AttributeError if lifespan is bypassed in tests [backend/app/api/taxonomy.py] — deferred, current TestClient context manager guards against this
