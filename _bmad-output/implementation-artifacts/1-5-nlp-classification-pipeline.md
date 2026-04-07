# Story 1.5: NLP Classification Pipeline

Status: done

## Story

As an admin or technical owner,  
I want to trigger the NLP processing pipeline on ingested posts,  
so that each raw post is classified by topic, subtopic, sentiment, target, and intensity, and an embedding is generated and stored for Q&A retrieval.

## Acceptance Criteria

1. **Given** unprocessed rows exist in `raw_posts`  
   **When** the admin calls `POST /process`  
   **Then** each post is classified and a corresponding row is inserted into `processed_posts` with topic, subtopic, sentiment, target, intensity, and a vector embedding  
   **And** a job record is created with status `completed`, count of posts processed, and timestamp

2. **Given** the NLP model or OpenAI API call fails for a specific post  
   **When** processing runs  
   **Then** that post is marked with an error status and skipped while remaining posts continue processing  
   **And** the job record captures the count and nature of failures

3. **Given** posts have already been processed (existing rows in `processed_posts`)  
   **When** processing runs again  
   **Then** already-processed posts are skipped to avoid duplicate entries

## Tasks / Subtasks

- [x] Add processing configuration in `backend/app/config.py` (AC: 1, 2)
  - [x] Add `OPENAI_CHAT_MODEL` default (`gpt-4o-mini`)
  - [x] Add `OPENAI_EMBEDDING_MODEL` default (`text-embedding-3-small`)
  - [x] Add `PROCESSING_BATCH_SIZE` for chunking large datasets
  - [x] Add `PROCESSING_MAX_RETRIES` for transient OpenAI failures
- [x] Create processing module in `backend/app/processing/` (AC: 1, 2, 3)
  - [x] `schemas.py`: Pydantic schemas for classification results, processing summary
  - [x] `classifier.py`: OpenAI-based classification logic (topic, subtopic, sentiment, target, intensity)
  - [x] `embeddings.py`: OpenAI embedding generation with vector normalization
  - [x] `service.py`: Orchestration, batch processing, error handling, job tracking
- [x] Create `processed_post` model enhancements (AC: 1, 2)
  - [x] Add `error_status` and `error_message` columns to track failed classifications
  - [x] Add partial index for unprocessed posts query performance
- [x] Implement `POST /process` endpoint (AC: 1, 2, 3)
  - [x] Add router file `backend/app/api/processing.py`
  - [x] Register router in `backend/app/main.py`
  - [x] Return processing summary payload (processed, succeeded, failed, skipped counts)
- [x] Add job tracking for processing jobs (AC: 1, 2)
  - [x] Extend `ingestion_jobs` table or create `processing_jobs` table
  - [x] Job type field to distinguish ingest vs process jobs
  - [x] Track per-post success/failure statistics
- [x] Add idempotency for reprocessing prevention (AC: 3)
  - [x] Query to find unprocessed posts (not in `processed_posts`)
  - [x] Skip posts already successfully processed
  - [x] Allow reprocessing of failed posts only (with `force=true` option)
- [x] Add tests (AC: 1, 2, 3)
  - [x] `backend/tests/test_processing_service.py`
  - [x] `backend/tests/test_processing_api.py`
  - [x] Mock OpenAI API calls for deterministic testing
  - [x] Include batch processing, error handling, and idempotency cases

### Review Findings

- [x] [Review][Patch] Force reprocessing path cannot recover failed rows because inserts use `ON CONFLICT DO NOTHING` for existing `raw_post_id` records [backend/app/processing/service.py:120]
- [x] [Review][Patch] Processing only handles a single `batch_size` slice and does not iterate until all unprocessed posts are handled [backend/app/processing/service.py:122]
- [x] [Review][Patch] API returns placeholder `job_id=""`, breaking response contract and job traceability [backend/app/api/processing.py:517]
- [x] [Review][Patch] Retry/backoff requirement for transient OpenAI failures is not implemented in classifier and embeddings flows [backend/app/processing/classifier.py:899]
- [x] [Review][Patch] Taxonomy compliance is prompt-only; code does not validate topic/subtopic/target membership before persistence [backend/app/processing/classifier.py:922]
- [x] [Review][Patch] `skipped` metric is never incremented, so idempotency/skipping stats are inaccurate [backend/app/processing/service.py:1241]
- [x] [Review][Patch] Migration and downgrade cast vectors across dimensions (`vector(768)`/`vector(1536)`) in a way that can fail on existing data [backend/alembic/versions/003_add_processing_columns_and_job_type.py:396]
- [x] [Review][Patch] API tests are weak for critical behavior (no real `force` assertion, always-true call-count checks, no `job_id` verification) [backend/tests/test_processing_api.py:1656]

## Developer Context

### Epic Context and Dependencies

- This story is in Epic 1 and depends directly on completed Stories 1.2, 1.3, and 1.4:
  - Story 1.2 provides DB schema with `processed_posts` table and pgvector extension.
  - Story 1.3 provides taxonomy loaded at startup; classifier must use valid topic/subtopic/target values.
  - Story 1.4 provides ingestion job tracking pattern to extend for processing jobs.
- Downstream dependency: Story 1.6 (`/jobs` API) displays both ingestion and processing jobs.
- Downstream dependency: Epic 2 analytics dashboard requires classified data to display.
- Downstream dependency: Epic 3 Q&A requires embeddings for RAG retrieval.

### Implementation Guardrails

- **Idempotency is critical**: Never duplicate processed post entries. Query for existing `raw_post_id` before processing.
- **Error isolation**: One post failure must not abort the entire batch. Catch and log per-post errors.
- **OpenAI API reliability**: Implement retries with exponential backoff for transient failures (rate limits, timeouts).
- **Batch processing**: Process posts in chunks to avoid memory issues and allow progress tracking.
- **Taxonomy compliance**: Classification must only emit values defined in loaded taxonomy. Validate outputs against taxonomy.
- **Vector dimensions**: `text-embedding-3-small` produces 1536-dimensional vectors. Ensure database column matches (currently 768 - may need migration).

### Technical Requirements

**Classification via OpenAI:**
- Use chat completions API with structured output (JSON mode or function calling)
- Prompt must include taxonomy context (available topics, subtopics, targets)
- Output format: `{ "topic": "string", "subtopic": "string|null", "sentiment": "positive|neutral|negative", "target": "string|null", "intensity": number|null }`
- Intensity: numeric scale 1-10 representing strength of sentiment/target relevance
- Sentiment must be one of: `positive`, `neutral`, `negative`

**Embeddings via OpenAI:**
- Use `text-embedding-3-small` for cost-effective 1536-dimensional embeddings
- Normalize vectors before storage for cosine similarity compatibility
- Batch embedding requests (up to 2048 texts per call per OpenAI limits)

**Data Flow:**
1. Query `raw_posts` for posts without corresponding `processed_posts` entries
2. For each batch:
   a. Call OpenAI to classify each post text
   b. Call OpenAI to generate embeddings for each post text
   c. Insert `processed_posts` rows with classification results + embedding
   d. Track successes and failures
3. Persist job record with statistics

**Error Handling:**
- Transient errors (timeout, rate limit): retry with exponential backoff
- Permanent errors (invalid content, API auth failure): mark post as failed, continue
- Total job failure: if >50% posts fail, mark job as `failed` rather than `completed`

**Performance Targets:**
- Process 100 posts in <30 seconds (including API calls)
- Support datasets up to 10k posts (MVP scope)
- Batch size default: 50 posts (configurable via `PROCESSING_BATCH_SIZE`)

### Architecture Compliance

- Follow existing code layout:
  - `backend/app/api/` for FastAPI routers
  - `backend/app/models/` for SQLAlchemy ORM models
  - `backend/app/<domain>/` package for processing business logic
  - `backend/alembic/versions/` for schema changes
- Use async SQLAlchemy patterns from `app.db.session`
- Use Pydantic v2 schemas for all API boundaries
- Keep OpenAI client initialization in module scope with lazy loading
- Store configuration in env-backed settings; no hardcoded API keys
- Maintain PostgreSQL + pgvector as sole datastore

### Library and Framework Requirements

- **OpenAI SDK**: Use `openai>=1.0.0` async client (`AsyncOpenAI`)
- **Vector operations**: Use `pgvector` SQLAlchemy extension (already configured)
- **Retry logic**: Use `tenacity` or implement simple exponential backoff
- **Pydantic**: v2 models for classification output validation

**Web Research Notes (Current Best Practices):**
- OpenAI structured outputs: Use `response_format={"type": "json_object"}` for reliable JSON
- Embeddings: `text-embedding-3-small` is cost-effective for MVP; upgrade to `text-embedding-3-large` for production
- Batch processing: Keep batches <100 for latency; use 50 for stability
- Rate limits: Default tier allows 3K RPM for embeddings, 500 RPM for GPT-4o-mini

### File Structure Plan

**Create:**
- `backend/app/processing/__init__.py` - Processing module init
- `backend/app/processing/schemas.py` - Pydantic schemas (ClassificationResult, ProcessingSummary)
- `backend/app/processing/classifier.py` - OpenAI classification logic
- `backend/app/processing/embeddings.py` - OpenAI embedding generation
- `backend/app/processing/service.py` - Core processing orchestration
- `backend/app/api/processing.py` - FastAPI router for POST /process
- `backend/alembic/versions/003_add_processing_job_type_and_error_columns.py` - Migration
- `backend/tests/test_processing_service.py` - Service unit tests
- `backend/tests/test_processing_api.py` - API integration tests

**Modify:**
- `backend/app/config.py` - Add processing configuration
- `backend/app/models/processed_post.py` - Add error tracking columns
- `backend/app/models/ingestion_job.py` - Extend for processing jobs (or create new model)
- `backend/app/main.py` - Register processing router
- `backend/app/models/__init__.py` - Export updated models
- `backend/requirements.txt` - Add `openai` and `tenacity` dependencies

### Testing Requirements

**Unit Tests:**
- Classification prompt construction with taxonomy context
- Embedding vector normalization
- Batch chunking logic
- Retry behavior with simulated failures

**Integration Tests:**
- `POST /process` happy path processes unprocessed posts
- Failed OpenAI calls handled gracefully, job continues
- Duplicate processing request skips already-processed posts
- Job record created with accurate statistics
- Mock OpenAI responses for deterministic tests

**Regression:**
- Existing taxonomy and health endpoints continue to work
- Database migrations apply cleanly
- No breaking changes to previously passing tests

### Previous Story Intelligence

**From Story 1.4 (CSV Data Ingestion):**
- Pattern established: domain package with `schemas.py`, `service.py`, utils module
- Job tracking pattern: create job record at start, update at completion with counts
- Error handling: per-row validation with error summary in job record
- Idempotency: defensive checks + database constraints prevent duplicates
- Test pattern: async session fixture for integration tests, mocking external calls

**From Review Feedback on Story 1.4:**
- Ensure rollback on job persistence failures
- Atomic operations where possible
- Proper timezone handling for timestamps
- Don't leak internal exceptions to API responses

### Git Intelligence Summary

Recent commits show active development in:
- Ingestion configuration and service implementation
- Database session management and testing infrastructure
- Taxonomy loading patterns

This story should:
- Reuse existing configuration patterns from `config.py`
- Follow the async session management pattern in `app.db.session`
- Use Pydantic v2 consistently with existing schemas
- Align with ingestion's job tracking approach

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.5] - Story requirements and acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture] - Database and ORM patterns
- [Source: _bmad-output/planning-artifacts/architecture.md#Cross-Cutting Concerns] - Error handling, observability
- [Source: backend/app/models/processed_post.py] - Current processed_posts schema
- [Source: backend/app/ingestion/service.py] - Job tracking and batch processing patterns
- [Source: backend/app/config.py] - Configuration pattern
- [Source: _bmad-output/implementation-artifacts/1-4-csv-data-ingestion.md] - Previous story implementation patterns

## Dev Notes for Questions

- Should we use the existing `ingestion_jobs` table with a `job_type` column, or create a separate `processing_jobs` table?
- Should failed posts be stored in `processed_posts` with an error flag, or kept in a separate error tracking table?
- Should we support partial reprocessing (force reprocess certain post IDs) or only full unprocessed batches?

### Open Questions

- **Vector dimension mismatch**: Current schema has `Vector(768)` but `text-embedding-3-small` produces 1536 dimensions. Need migration to update column?
- **Classification model**: Use GPT-4o-mini for cost/speed balance, or upgrade to GPT-4o for better accuracy on Spanish political context?
- **Taxonomy validation**: Strict validation (error if model returns invalid topic) or permissive (map to "Other")?

## Completion Notes

Ultimate context engine analysis completed - comprehensive developer guide created.
- Story includes NLP classification, embedding generation, job tracking, error handling, and idempotency requirements
- Architecture compliance requirements documented
- Previous story patterns and learnings incorporated
- File structure and testing plan aligned with Epic 1 continuity

### Dev Agent Record

**Implementation Plan:**
1. Extended configuration with OpenAI model settings and processing parameters
2. Created Alembic migration for database schema updates (error columns, job_type, vector dimension)
3. Built processing module with clean separation of concerns:
   - `schemas.py`: Pydantic models for type safety
   - `classifier.py`: OpenAI chat completions with structured JSON output
   - `embeddings.py`: Vector normalization for cosine similarity
   - `service.py`: Orchestration with batching and error isolation
4. Implemented POST /process endpoint with taxonomy validation
5. Added comprehensive test suite with mocked OpenAI calls

**Completion Notes:**
- All ACs satisfied: Classification pipeline, error handling, idempotency
- Vector dimension updated from 768 to 1536 for text-embedding-3-small compatibility
- Error isolation: Per-post failures don't abort batch
- Idempotency: Skips already-processed posts; force flag reprocesses failures
- Job tracking: Extends ingestion_jobs with job_type='process'
- Tests cover: Normalization, classification, embeddings, batch processing, error handling

## File List

**Created:**
- [x] `backend/app/processing/__init__.py` - Processing module init
- [x] `backend/app/processing/schemas.py` - Pydantic schemas
- [x] `backend/app/processing/classifier.py` - OpenAI classification logic
- [x] `backend/app/processing/embeddings.py` - OpenAI embedding generation
- [x] `backend/app/processing/service.py` - Core processing service
- [x] `backend/app/api/processing.py` - FastAPI router for POST /process
- [x] `backend/alembic/versions/003_add_processing_columns_and_job_type.py` - Database migration
- [x] `backend/tests/test_processing_service.py` - Service tests
- [x] `backend/tests/test_processing_api.py` - API tests

**Modified:**
- [x] `backend/app/config.py` - Add OpenAI model and processing config
- [x] `backend/app/models/processed_post.py` - Add error tracking columns, updated vector dimension to 1536
- [x] `backend/app/models/ingestion_job.py` - Add job_type for processing jobs
- [x] `backend/app/main.py` - Register processing router
- [x] `backend/app/models/__init__.py` - No changes needed (models already exported)
- [x] `backend/requirements.txt` - Add openai, tenacity, numpy dependencies
- [x] `backend/tests/conftest.py` - Add processed_posts to test cleanup

## Change Log

- **2026-04-07**: Story created - NLP Classification Pipeline with OpenAI integration
- **2026-04-07**: Defined processing architecture with batching and error isolation
- **2026-04-07**: Identified vector dimension mismatch (768 vs 1536) requiring migration
- **2026-04-07**: Implementation complete - Added processing configuration, models, service, API, and tests
