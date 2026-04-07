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
