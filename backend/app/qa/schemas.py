"""Pydantic schemas for Q&A retrieval and aggregation."""

from __future__ import annotations
from datetime import date
from pydantic import BaseModel


class QAFilters(BaseModel):
    """Optional filter parameters for Q&A retrieval."""
    topic: str | None = None
    subtopic: str | None = None
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


class NarrativeCluster(BaseModel):
    """A group of thematically related posts representing a single narrative thread."""
    label: str                                  # subtopic_label, or topic_label if no subtopic
    sentiment: str                              # dominant sentiment: "positive" | "neutral" | "negative"
    post_count: int
    representative_posts: list[QAPostItem]      # up to 2 posts (most similar / top of cluster)


class QAMetrics(BaseModel):
    """Aggregated metrics from the retrieved post set."""
    total_retrieved: int
    positive_count: int
    neutral_count: int
    negative_count: int
    top_subtopics: list[QASubtopicSummary]   # up to 5, ranked by count desc


class QAResponse(BaseModel):
    """Response for POST /qa — retrieval + aggregation + LLM summary."""
    question: str
    filters_applied: QAFilters
    retrieved_posts: list[QAPostItem]
    metrics: QAMetrics
    insufficient_data: bool    # True when no posts matched filters/question
    summary: str | None = None          # LLM-generated narrative (None if skipped or failed)
    answer_error: str | None = None     # Degradation message (None unless LLM failed)
    clusters: list[NarrativeCluster] = []       # 2-4 narrative clusters (empty when insufficient_data)
