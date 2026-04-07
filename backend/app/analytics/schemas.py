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
