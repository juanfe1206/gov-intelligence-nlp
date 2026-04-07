"""Pydantic schemas for NLP processing pipeline."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ClassificationResult(BaseModel):
    """Result of classifying a single post."""

    topic: str = Field(..., description="Primary topic from taxonomy")
    subtopic: str | None = Field(None, description="Subtopic from taxonomy")
    sentiment: str = Field(..., description="Sentiment: positive, neutral, or negative")
    target: str | None = Field(None, description="Political target of the sentiment")
    intensity: float | None = Field(None, ge=1, le=10, description="Intensity score 1-10")

    @field_validator("sentiment")
    @classmethod
    def validate_sentiment(cls, v: str) -> str:
        """Ensure sentiment is one of the allowed values."""
        allowed = {"positive", "neutral", "negative"}
        if v.lower() not in allowed:
            raise ValueError(f"sentiment must be one of {allowed}")
        return v.lower()


class ProcessingSummary(BaseModel):
    """Summary of a processing run."""

    status: str = Field(..., description="completed, failed, or partial")
    processed: int = Field(0, ge=0, description="Total posts processed")
    succeeded: int = Field(0, ge=0, description="Posts successfully classified")
    failed: int = Field(0, ge=0, description="Posts that failed classification")
    skipped: int = Field(0, ge=0, description="Posts already processed (skipped)")
    errors: list[str] = Field(default_factory=list, description="Error messages for failed posts")
    started_at: datetime = Field(..., description="Processing start time")
    finished_at: datetime | None = Field(None, description="Processing finish time")

    @property
    def duration_seconds(self) -> float | None:
        """Calculate duration in seconds if finished."""
        if self.finished_at and self.started_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


class ProcessRequest(BaseModel):
    """Request body for triggering processing."""

    force: bool = Field(
        default=False,
        description="If true, reprocess failed posts; otherwise skip all existing processed posts",
    )
    batch_size: int | None = Field(
        default=None,
        ge=1,
        le=500,
        description="Override default batch size for this run",
    )


class ProcessResponse(BaseModel):
    """Response from processing endpoint."""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status: completed, failed, or partial")
    processed: int = Field(..., ge=0, description="Total posts processed")
    succeeded: int = Field(..., ge=0, description="Posts successfully classified")
    failed: int = Field(..., ge=0, description="Posts that failed classification")
    skipped: int = Field(..., ge=0, description="Posts already processed (skipped)")
    errors: list[str] = Field(default_factory=list, description="Error messages")
    duration_seconds: float | None = Field(None, description="Processing duration in seconds")
