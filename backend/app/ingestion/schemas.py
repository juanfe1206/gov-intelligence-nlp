"""Pydantic schemas for CSV ingestion."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CSVRow(BaseModel):
    """Schema for a single CSV row before database insertion."""

    text: str = Field(..., min_length=1, description="The post content")
    platform: str | None = Field(None, description="Platform source (e.g., twitter, facebook)")
    author: str | None = Field(None, description="Post author identifier")
    created_at: datetime | None = Field(None, description="Original post timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional row metadata")

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        """Ensure text is not just whitespace."""
        if not v.strip():
            raise ValueError("Text cannot be empty or whitespace only")
        return v.strip()


class IngestionSummary(BaseModel):
    """Summary of an ingestion run."""

    status: str = Field(..., description="completed or failed")
    source: str = Field(..., description="Data source identifier")
    processed: int = Field(0, ge=0, description="Total rows processed")
    inserted: int = Field(0, ge=0, description="Rows successfully inserted")
    skipped: int = Field(0, ge=0, description="Rows skipped due to validation/errors")
    duplicates: int = Field(0, ge=0, description="Duplicate rows detected and skipped")
    errors: list[str] = Field(default_factory=list, description="Error messages for skipped rows")
    started_at: datetime = Field(..., description="Ingestion start time")
    finished_at: datetime | None = Field(None, description="Ingestion finish time")
    job_id: str | None = Field(None, description="Job ID for tracking the ingestion run")

    @property
    def duration_seconds(self) -> float | None:
        """Calculate duration in seconds if finished."""
        if self.finished_at and self.started_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None
