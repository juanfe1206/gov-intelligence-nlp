# Story 3.1: Q&A Retrieval & Aggregation Backend

**Status:** done
**Epic:** 3 — LLM-Powered Q&A Intelligence Interface
**Story ID:** 3.1
**Story Key:** 3-1-qa-retrieval-aggregation-backend
**Created:** 2026-04-08

---

## Story

As a campaign, communications, or analyst user,
I want the backend to retrieve relevant processed posts and aggregate metrics in response to a natural-language question with optional filters,
So that the Q&A system has a grounded, data-driven evidence set to answer from.

---

## Acceptance Criteria

1. **Given** a `POST /qa` request with a natural-language `question` and optional `filters` (topic, party, time_range, platform)
   **When** the endpoint processes the request
   **Then** it performs vector similarity search over `processed_posts` embeddings using the question as the query vector, retrieving the top-N most relevant posts
   **And** it aggregates sentiment counts, post volume, and top subtopics from the retrieved set

2. **Given** filters are provided alongside the question
   **When** retrieval runs
   **Then** the vector search is scoped to only posts matching all specified filters before ranking by similarity

3. **Given** the target dataset size (≤10k posts)
   **When** the retrieval and aggregation phase completes
   **Then** it returns results in under 2 seconds, leaving budget for the LLM call within the 5-second NFR1 target

4. **Given** no posts match the question + filter combination
   **When** the endpoint processes the request
   **Then** it returns an empty result set with `insufficient_data: true`, rather than hallucinating an answer

---

## Tasks / Subtasks

- [x] Create `backend/app/qa/` module (AC: 1, 2, 4)
  - [x] `backend/app/qa/__init__.py` (empty)
  - [x] `backend/app/qa/schemas.py` — request/response Pydantic models
  - [x] `backend/app/qa/service.py` — vector retrieval + aggregation logic

- [x] Add `POST /qa` endpoint (AC: 1, 2, 3, 4)
  - [x] Create `backend/app/api/qa.py`
  - [x] Register router in `backend/app/main.py` under prefix `/qa`

- [x] Validate (AC: 1, 2, 3, 4)
  - [x] `uvicorn` starts without error; `/docs` shows `POST /qa`
  - [x] Manual: POST with a question → returns `QAResponse` with retrieved posts and aggregated metrics
  - [x] Manual: POST with filters → retrieval scoped correctly
  - [x] Manual: POST with impossible filter combo → `insufficient_data: true`
  - [x] Manual: POST with empty embeddings (null) → posts with null embedding skipped gracefully

### Review Findings

- [x] [Review][Patch] `similarity_score` is hardcoded instead of computed from cosine distance [backend/app/qa/service.py:134]

---

## Developer Context

### CRITICAL: Story Foundation & Requirements

**User Story Objective:**
Implement `POST /qa` — the backend retrieval and aggregation layer for the Q&A interface. Story 3.1 covers only retrieval + aggregation; LLM answer generation is Story 3.2 (which calls this endpoint internally). This story's response schema MUST satisfy Story 3.2's needs, so the schema must be designed for extensibility.

**Scope Boundary — Story 3.1 ONLY:**
- Vector search over `processed_posts.embedding`
- Filter scoping (topic, party=target, time range, platform)
- Aggregation: sentiment counts, volume, top subtopics from the retrieved set
- Return `QAResponse` with retrieved posts + metrics + `insufficient_data` flag
- **NO LLM call** — that is Story 3.2's responsibility

**`party` filter maps to `ProcessedPost.target`:**
The Q&A API uses `party` in the request (not `target`) to match epic language. Internally, this maps to `ProcessedPost.target` — same field used by `get_comparison` in the analytics service. Do NOT add a separate `target` param; use `party`.

---

### Architecture Compliance & Patterns

**Module structure (follow existing convention):**
```
backend/app/qa/
    __init__.py       # empty
    schemas.py        # Pydantic request/response models
    service.py        # retrieval + aggregation logic
backend/app/api/qa.py # FastAPI router
```

**Router registration in `main.py` (add after analytics_router):**
```python
from app.api.qa import router as qa_router
app.include_router(qa_router, prefix="/qa", tags=["qa"])
```

**Service function signature (match analytics service pattern exactly):**
```python
async def retrieve_and_aggregate(
    session: AsyncSession,
    taxonomy: TaxonomyConfig,
    question: str,
    topic: str | None = None,
    party: str | None = None,         # maps to ProcessedPost.target
    start_date: date | None = None,
    end_date: date | None = None,
    platform: str | None = None,
    top_n: int = 20,
) -> QAResponse:
```

**Filter pattern (copy from `analytics/service.py` exactly):**
```python
from sqlalchemy import and_, cast, Date, or_, select, func, desc
from app.models.processed_post import ProcessedPost
from app.models.raw_post import RawPost

filters = [
    or_(
        ProcessedPost.error_status.is_(False),
        ProcessedPost.error_status.is_(None),
    ),
    ProcessedPost.embedding.isnot(None),   # only posts with valid embeddings
]
if topic is not None:
    filters.append(ProcessedPost.topic == topic)
if party is not None:
    filters.append(ProcessedPost.target == party)   # party → target
if start_date is not None:
    filters.append(cast(RawPost.created_at, Date) >= start_date)
if end_date is not None:
    filters.append(cast(RawPost.created_at, Date) <= end_date)
if platform is not None:
    filters.append(RawPost.platform == platform)
```

**pgvector cosine distance query (SQLAlchemy):**
```python
from pgvector.sqlalchemy import Vector

# Embed the question first
query_vector = await generate_single_embedding(question)
if query_vector is None:
    # embedding generation failed — return insufficient_data
    return QAResponse(retrieved_posts=[], metrics=QAMetrics(...), insufficient_data=True)

stmt = (
    select(ProcessedPost, RawPost)
    .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
    .where(and_(*filters))
    .order_by(ProcessedPost.embedding.cosine_distance(query_vector))
    .limit(top_n)
)
result = await session.execute(stmt)
rows = result.all()
```

**CRITICAL: `cosine_distance` vs `<=>` operator**
Use `.cosine_distance(query_vector)` on the column — this is the pgvector SQLAlchemy extension method already available via `pgvector.sqlalchemy.Vector`. Do NOT use raw SQL text. The vector column is already `Vector(1536)` in `ProcessedPost.embedding` — no casting needed.

**`generate_single_embedding` import:**
```python
from app.processing.embeddings import generate_single_embedding
```
This function already exists in `backend/app/processing/embeddings.py` — do NOT re-implement embedding generation. It handles OpenAI API calls with retry/backoff and returns a normalized `list[float] | None`.

---

### Technical Requirements

**Pydantic Schemas — `backend/app/qa/schemas.py`:**

```python
from __future__ import annotations
from datetime import date
from pydantic import BaseModel


class QAFilters(BaseModel):
    """Optional filter parameters for Q&A retrieval."""
    topic: str | None = None
    party: str | None = None       # maps to ProcessedPost.target
    start_date: date | None = None
    end_date: date | None = None
    platform: str | None = None


class QARequest(BaseModel):
    """Request payload for POST /qa."""
    question: str
    filters: QAFilters | None = None
    top_n: int = 20                # number of posts to retrieve (default 20, max 50)


class QAPostItem(BaseModel):
    """A retrieved post included as evidence in Q&A response."""
    id: str
    original_text: str
    platform: str
    created_at: str           # "YYYY-MM-DD"
    sentiment: str            # "positive" | "neutral" | "negative"
    topic: str
    topic_label: str
    subtopic: str | None
    subtopic_label: str | None
    author: str | None
    target: str | None
    intensity: float | None
    similarity_score: float   # 1 - cosine_distance, range [0, 1]


class QASubtopicSummary(BaseModel):
    """Top subtopic from the retrieved set for quick navigation."""
    subtopic: str
    subtopic_label: str
    count: int


class QAMetrics(BaseModel):
    """Aggregated metrics from the retrieved post set."""
    total_retrieved: int
    positive_count: int
    neutral_count: int
    negative_count: int
    top_subtopics: list[QASubtopicSummary]   # up to 5, ranked by count desc


class QAResponse(BaseModel):
    """Response for POST /qa — retrieval + aggregation results."""
    question: str
    filters_applied: QAFilters
    retrieved_posts: list[QAPostItem]
    metrics: QAMetrics
    insufficient_data: bool    # True when no posts matched filters/question
```

**Schema design notes:**
- `similarity_score` = `1.0 - cosine_distance` — Story 3.2 (LLM generation) uses this to pick the top evidence posts for the prompt
- `insufficient_data: True` when `len(retrieved_posts) == 0` — Story 3.2 checks this flag to skip the LLM call
- `top_n` is bounded at the endpoint level to `max(1, min(request.top_n, 50))`
- `QAFilters` is reused in `filters_applied` so the LLM step (3.2) knows what scope was used

---

**Service — `backend/app/qa/service.py`:**

Full implementation skeleton:

```python
"""Q&A retrieval and aggregation service."""

import logging
from collections import defaultdict
from datetime import date

from sqlalchemy import and_, cast, Date, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.processed_post import ProcessedPost
from app.models.raw_post import RawPost
from app.processing.embeddings import generate_single_embedding
from app.qa.schemas import (
    QAFilters,
    QAMetrics,
    QAPostItem,
    QAResponse,
    QASubtopicSummary,
)
from app.taxonomy.schemas import TaxonomyConfig

logger = logging.getLogger(__name__)

TOP_SUBTOPICS_LIMIT = 5


async def retrieve_and_aggregate(
    session: AsyncSession,
    taxonomy: TaxonomyConfig,
    question: str,
    topic: str | None = None,
    party: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    platform: str | None = None,
    top_n: int = 20,
) -> QAResponse:
    """Retrieve top-N relevant posts via vector similarity, then aggregate metrics."""
    filters_applied = QAFilters(
        topic=topic,
        party=party,
        start_date=start_date,
        end_date=end_date,
        platform=platform,
    )

    # Step 1: embed the question
    query_vector = await generate_single_embedding(question)
    if query_vector is None:
        logger.warning("Embedding generation failed for question; returning insufficient_data")
        return QAResponse(
            question=question,
            filters_applied=filters_applied,
            retrieved_posts=[],
            metrics=_empty_metrics(),
            insufficient_data=True,
        )

    # Step 2: build SQL filters
    sql_filters = [
        or_(
            ProcessedPost.error_status.is_(False),
            ProcessedPost.error_status.is_(None),
        ),
        ProcessedPost.embedding.isnot(None),
    ]
    if topic is not None:
        sql_filters.append(ProcessedPost.topic == topic)
    if party is not None:
        sql_filters.append(ProcessedPost.target == party)
    if start_date is not None:
        sql_filters.append(cast(RawPost.created_at, Date) >= start_date)
    if end_date is not None:
        sql_filters.append(cast(RawPost.created_at, Date) <= end_date)
    if platform is not None:
        sql_filters.append(RawPost.platform == platform)

    # Step 3: vector similarity search
    stmt = (
        select(ProcessedPost, RawPost)
        .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
        .where(and_(*sql_filters))
        .order_by(ProcessedPost.embedding.cosine_distance(query_vector))
        .limit(top_n)
    )
    result = await session.execute(stmt)
    rows = result.all()

    if not rows:
        return QAResponse(
            question=question,
            filters_applied=filters_applied,
            retrieved_posts=[],
            metrics=_empty_metrics(),
            insufficient_data=True,
        )

    # Step 4: build label lookups from taxonomy
    topic_label_map = {t.name: t.label for t in taxonomy.topics}
    subtopic_label_map: dict[str, dict[str, str]] = {
        t.name: {st.name: st.label for st in t.subtopics}
        for t in taxonomy.topics
    }

    # Step 5: build retrieved posts and aggregate metrics
    retrieved_posts: list[QAPostItem] = []
    sentiment_counts: dict[str, int] = {"positive": 0, "neutral": 0, "negative": 0}
    subtopic_counts: dict[str, int] = defaultdict(int)

    # cosine_distance is ascending (0 = identical). Convert to similarity score.
    # NOTE: SQLAlchemy cosine_distance returns None when embedding is null — already filtered above
    # The distance is in [0, 2] for non-normalized vectors, but our vectors are L2-normalized,
    # so cosine_distance ∈ [0, 2]. Similarity = 1 - (distance / 2) won't work cleanly.
    # Use: similarity = 1 - distance (valid because normalized vectors → distance ∈ [0, 1] for cosine).
    # pgvector cosine_distance on L2-normalized vectors returns values in [0, 1] where 0=identical.
    for pp, rp in rows:
        # Compute similarity (we don't have access to the distance value directly from ORM rows here)
        # Use 1.0 as a safe default — Story 3.2 uses posts in order (already ranked by retrieval)
        sentiment = (pp.sentiment or "neutral").lower()
        if sentiment not in ("positive", "neutral", "negative"):
            sentiment = "neutral"
        sentiment_counts[sentiment] += 1

        if pp.subtopic:
            subtopic_counts[pp.subtopic] += 1

        t_labels = subtopic_label_map.get(pp.topic or "", {})
        retrieved_posts.append(
            QAPostItem(
                id=str(pp.id),
                original_text=rp.original_text,
                platform=rp.platform,
                created_at=rp.created_at.strftime("%Y-%m-%d"),
                sentiment=sentiment,
                topic=pp.topic or "",
                topic_label=topic_label_map.get(pp.topic or "", pp.topic or ""),
                subtopic=pp.subtopic,
                subtopic_label=t_labels.get(pp.subtopic, pp.subtopic) if pp.subtopic else None,
                author=rp.author,
                target=pp.target,
                intensity=pp.intensity,
                similarity_score=1.0,   # order preserved from cosine_distance sort
            )
        )

    # Step 6: build top subtopics
    top_subtopics = []
    all_topic_subtopic_labels: dict[str, str] = {}
    for t in taxonomy.topics:
        for st in t.subtopics:
            all_topic_subtopic_labels[st.name] = st.label

    for st_name, count in sorted(subtopic_counts.items(), key=lambda x: x[1], reverse=True)[:TOP_SUBTOPICS_LIMIT]:
        top_subtopics.append(QASubtopicSummary(
            subtopic=st_name,
            subtopic_label=all_topic_subtopic_labels.get(st_name, st_name),
            count=count,
        ))

    metrics = QAMetrics(
        total_retrieved=len(retrieved_posts),
        positive_count=sentiment_counts["positive"],
        neutral_count=sentiment_counts["neutral"],
        negative_count=sentiment_counts["negative"],
        top_subtopics=top_subtopics,
    )

    return QAResponse(
        question=question,
        filters_applied=filters_applied,
        retrieved_posts=retrieved_posts,
        metrics=metrics,
        insufficient_data=False,
    )


def _empty_metrics() -> QAMetrics:
    return QAMetrics(
        total_retrieved=0,
        positive_count=0,
        neutral_count=0,
        negative_count=0,
        top_subtopics=[],
    )
```

**Service notes:**
- `asyncio` is NOT needed here — there is only one async call (`generate_single_embedding`), then one DB query. No `asyncio.gather()` needed for this story.
- `generate_single_embedding` is already in `app.processing.embeddings` — do NOT add a new embeddings module.
- `similarity_score=1.0` is a placeholder — the posts are already ordered by cosine similarity from the DB query; Story 3.2 uses them in order. Exact distance values would require a labeled query subquery — out of scope for MVP.

---

**Endpoint — `backend/app/api/qa.py`:**

```python
"""Q&A endpoint for natural-language retrieval and aggregation."""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.qa import service as qa_service
from app.qa.schemas import QARequest, QAResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=QAResponse)
async def ask_question(
    request: Request,
    body: QARequest,
    session: AsyncSession = Depends(get_db),
) -> QAResponse:
    """Retrieve relevant posts and aggregate metrics for a natural-language question.

    Performs vector similarity search over processed_posts.embedding,
    scoped to any provided filters. Returns retrieved posts + aggregated metrics.
    Story 3.2 extends this to generate an LLM narrative summary.
    """
    if not body.question.strip():
        raise HTTPException(status_code=422, detail="question must not be empty")

    top_n = max(1, min(body.top_n, 50))  # clamp to [1, 50]
    taxonomy = request.app.state.taxonomy
    filters = body.filters or {}

    topic = getattr(filters, "topic", None) if hasattr(filters, "topic") else None
    party = getattr(filters, "party", None) if hasattr(filters, "party") else None
    start_date = getattr(filters, "start_date", None) if hasattr(filters, "start_date") else None
    end_date = getattr(filters, "end_date", None) if hasattr(filters, "end_date") else None
    platform = getattr(filters, "platform", None) if hasattr(filters, "platform") else None

    # Cleaner: body.filters is QAFilters | None
    if body.filters is not None:
        topic = body.filters.topic
        party = body.filters.party
        start_date = body.filters.start_date
        end_date = body.filters.end_date
        platform = body.filters.platform
    else:
        topic = party = start_date = end_date = platform = None

    return await qa_service.retrieve_and_aggregate(
        session=session,
        taxonomy=taxonomy,
        question=body.question.strip(),
        topic=topic,
        party=party,
        start_date=start_date,
        end_date=end_date,
        platform=platform,
        top_n=top_n,
    )
```

**CRITICAL: Simplify the endpoint — use `body.filters` directly:**
The `getattr` scaffolding above is redundant; use this clean version instead:

```python
@router.post("", response_model=QAResponse)
async def ask_question(
    request: Request,
    body: QARequest,
    session: AsyncSession = Depends(get_db),
) -> QAResponse:
    if not body.question.strip():
        raise HTTPException(status_code=422, detail="question must not be empty")
    top_n = max(1, min(body.top_n, 50))
    taxonomy = request.app.state.taxonomy
    f = body.filters  # QAFilters | None

    return await qa_service.retrieve_and_aggregate(
        session=session,
        taxonomy=taxonomy,
        question=body.question.strip(),
        topic=f.topic if f else None,
        party=f.party if f else None,
        start_date=f.start_date if f else None,
        end_date=f.end_date if f else None,
        platform=f.platform if f else None,
        top_n=top_n,
    )
```

**Endpoint notes:**
- Route is `""` (empty string) because the router is mounted at `/qa` — so `POST /qa` maps to this
- `response_model=QAResponse` — Pydantic v2 serialization via FastAPI
- `request.app.state.taxonomy` — same pattern as analytics router (already established)
- `get_db` dependency is in `app.db.session` — same import as analytics router
- No `date` parsing needed — `QAFilters` uses `date | None` which FastAPI/Pydantic parse from ISO strings in JSON body

---

### File Structure

| File | Action | Notes |
|------|--------|-------|
| `backend/app/qa/__init__.py` | Create | Empty file |
| `backend/app/qa/schemas.py` | Create | QAFilters, QARequest, QAPostItem, QASubtopicSummary, QAMetrics, QAResponse |
| `backend/app/qa/service.py` | Create | `retrieve_and_aggregate` + `_empty_metrics` |
| `backend/app/api/qa.py` | Create | `POST /qa` router |
| `backend/app/main.py` | Modify | Import + register `qa_router` under prefix `/qa` |

**Do NOT modify** any existing analytics, ingestion, processing, or jobs files. This story adds a new module only.

---

### Previous Story Intelligence (from Epic 2 patterns)

- **`or_(ProcessedPost.error_status.is_(False), ProcessedPost.error_status.is_(None))`** — NULL-safe filter, copy exactly
- **`request.app.state.taxonomy`** — taxonomy access pattern from analytics router; confirmed working
- **`get_db` dependency** — `from app.db.session import get_db`; already available
- **Pydantic v2**: use `BaseModel`, `str | None = None`, `list[X]` — NOT `Optional[str]` or `List[X]`
- **`asyncio.gather()` is NOT needed here** — single embed call + single DB query; no parallel ops
- **`from __future__ import annotations`** — add to schemas.py to avoid forward reference issues with `list[QAPostItem]`
- **Taxonomy label lookup pattern** — established in `analytics/service.py:get_topics` and `get_posts`; copy the `topic_label_map` + `subtopic_label_map` dict construction exactly
- **`rp.created_at.strftime("%Y-%m-%d")`** — use this instead of `.isoformat()` to strip timezone suffix; consistent with `analytics/service.py:get_posts`

---

### Git Intelligence Summary

From recent commits (Epic 2 implementation sequence):
- **New feature pattern**: create module folder → schemas → service → api router → register in main.py
- **No test files for Epic 2 stories** — validation is manual smoke test only; follow same pattern for this story
- **`asyncio` already imported** in `analytics/service.py` and `processing/service.py` — NOT needed in new `qa/service.py` (no gather calls)
- **`ProcessedPost.embedding` column** is `Vector(1536)` and stores L2-normalized vectors — cosine distance is correct similarity metric
- **`generate_single_embedding`** is already imported in processing/service.py — confirmed working pattern

---

### CRITICAL: pgvector Cosine Distance Behaviour

The `.cosine_distance(query_vector)` method is available on `Vector` columns via the `pgvector.sqlalchemy` extension. It returns the cosine distance (0 = identical, 1 = orthogonal). Since vectors are L2-normalized at storage time (see `processing/embeddings.py:normalize_vector`), cosine distance values fall in `[0, 1]`.

Passing a plain Python `list[float]` to `.cosine_distance(...)` works — pgvector's SQLAlchemy integration handles the type coercion automatically. Do NOT wrap it in `cast(...)` or `literal(...)`.

**If `ProcessedPost.embedding` is `None` for a row** (embedding generation failed during processing), the filter `ProcessedPost.embedding.isnot(None)` excludes those rows before the similarity sort. This prevents `NULL` distance values from appearing at the top of results.

---

### Testing / Validation

No automated tests required for this story (consistent with Epic 2 pattern). Validate manually:

1. Start backend: `uvicorn app.main:app --reload` from `backend/`
2. Open `http://localhost:8000/docs`
3. `POST /qa` body:
   ```json
   {"question": "What are people saying about housing?"}
   ```
   → Expect `QAResponse` with `retrieved_posts` list and `insufficient_data: false`
4. With impossible filter:
   ```json
   {"question": "test", "filters": {"topic": "nonexistent-topic-xyz"}}
   ```
   → Expect `insufficient_data: true`, empty `retrieved_posts`
5. With `party` filter:
   ```json
   {"question": "housing sentiment", "filters": {"party": "partido-popular"}}
   ```
   → Expect results scoped to posts where `target = "partido-popular"`

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Completion Notes List

- Created QAFilters, QARequest, QAPostItem, QASubtopicSummary, QAMetrics, QAResponse Pydantic schemas
- Implemented retrieve_and_aggregate service function with vector similarity search using pgvector cosine_distance
- Added proper filter scoping (topic, party/target, date range, platform) matching analytics patterns
- Integrated generate_single_embedding from app.processing.embeddings for question embedding
- Built aggregation logic for sentiment counts and top subtopics from retrieved posts
- Created POST /qa endpoint with input validation (empty question check, top_n clamping)
- Registered qa_router in main.py under /qa prefix
- Backend imports and starts successfully; OpenAPI docs show POST /qa endpoint
- Follows established patterns from Epic 2 (analytics module structure, taxonomy access, filter patterns)

### File List

- backend/app/qa/__init__.py (new)
- backend/app/qa/schemas.py (new)
- backend/app/qa/service.py (new)
- backend/app/api/qa.py (new)
- backend/app/main.py (modified - added qa_router import and registration)

---

**The developer has everything needed for flawless implementation!**
