"""Pydantic schemas for analytics endpoints."""

from datetime import date
from pydantic import BaseModel


class DailyVolume(BaseModel):
    """Daily post volume data point."""

    date: str  # "YYYY-MM-DD"
    count: int


class VolumeResponse(BaseModel):
    """Response for volume analytics endpoint."""

    data: list[DailyVolume]
    total: int


class DailySentiment(BaseModel):
    """Daily sentiment breakdown data point."""

    date: str  # "YYYY-MM-DD"
    positive: int
    neutral: int
    negative: int


class SentimentResponse(BaseModel):
    """Response for sentiment analytics endpoint."""

    data: list[DailySentiment]


class PlatformsResponse(BaseModel):
    """Response for available platforms endpoint."""

    platforms: list[str]


class SubtopicDistributionItem(BaseModel):
    """Subtopic-level breakdown within a topic."""

    name: str
    label: str
    count: int
    positive: int
    neutral: int
    negative: int


class TopicDistributionItem(BaseModel):
    """Topic distribution with sentiment breakdown and top subtopics."""

    name: str
    label: str
    count: int
    positive: int
    neutral: int
    negative: int
    subtopics: list[SubtopicDistributionItem]


class TopicsResponse(BaseModel):
    """Response for topics distribution endpoint."""

    topics: list[TopicDistributionItem]


class PostItem(BaseModel):
    """A single representative post with metadata for display as an Evidence Post Card."""

    id: str
    original_text: str
    platform: str
    created_at: str  # ISO date string "YYYY-MM-DD"
    sentiment: str  # "positive", "neutral", or "negative"
    topic: str
    topic_label: str
    subtopic: str | None
    subtopic_label: str | None
    author: str | None
    source: str | None


class PostsResponse(BaseModel):
    """Response for representative posts endpoint."""

    posts: list[PostItem]
    total: int


class SubtopicSentiment(BaseModel):
    """Subtopic with sentiment breakdown for a party."""

    subtopic: str
    subtopic_label: str
    positive_count: int
    neutral_count: int
    negative_count: int
    total: int
    sentiment_percentage: dict[str, float]  # {"positive": 0.45, "neutral": 0.30, "negative": 0.25}


class PartyComparison(BaseModel):
    """Per-party sentiment and volume breakdown for comparison view."""

    party: str  # target name (e.g. "partido-socialista")
    party_label: str  # display label
    post_count: int
    positive_count: int
    neutral_count: int
    negative_count: int
    sentiment_percentage: dict[str, float]  # {"positive": 0.X, "neutral": 0.Y, "negative": 0.Z}
    top_subtopics: list[SubtopicSentiment]  # up to 3–5 subtopics ranked by negative sentiment


class ComparisonResponse(BaseModel):
    """Response for cross-party sentiment comparison."""

    topic: str
    topic_label: str
    parties: list[PartyComparison]
    total_posts: int
    date_range: dict[str, str]  # {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}


class SpikeAlert(BaseModel):
    """A detected spike in volume or negative sentiment for a topic."""

    topic: str  # topic name (e.g., "vivienda")
    topic_label: str  # display label (e.g., "Vivienda")
    spike_type: str  # "volume" or "sentiment"
    magnitude: float  # ratio for volume (e.g., 2.5 = 2.5× increase); percentage points for sentiment (e.g., 0.25 = +25pp)
    recent_count: int  # posts in recent window
    baseline_count: int  # posts in baseline window (0 if baseline is empty)
    window_hours: int  # time window used for detection
    suggested_question: str  # pre-filled Q&A question, e.g., "What are people saying about Vivienda right now?"


class SpikesResponse(BaseModel):
    """Response for spike detection endpoint."""

    spikes: list[SpikeAlert]
    window_hours: int
    detected_at: str  # ISO date string "YYYY-MM-DD"


class ExportFilters(BaseModel):
    """Filter parameters included in the export for reproducibility."""

    start_date: str
    end_date: str
    topic: str | None = None
    subtopic: str | None = None
    target: str | None = None
    platform: str | None = None
    parties: list[str] | None = None


class ExportSnapshot(BaseModel):
    """Structured snapshot for analyst export."""

    exported_at: str  # ISO date string "YYYY-MM-DD"
    filters: ExportFilters
    volume: VolumeResponse
    sentiment: SentimentResponse
    topics: TopicsResponse
    posts: PostsResponse  # up to 50 posts
