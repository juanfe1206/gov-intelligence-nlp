"""Pydantic schemas for job tracking API."""

from datetime import datetime

from pydantic import BaseModel, Field


class JobResponse(BaseModel):
    """Response schema for a single job."""

    id: str = Field(..., description="Job UUID")
    job_type: str = Field(..., description="Job type: ingest or process")
    status: str = Field(..., description="Job status: running, completed, failed, or partial")
    source: str = Field(..., description="Data source identifier")
    started_at: datetime = Field(..., description="Job start time")
    finished_at: datetime | None = Field(None, description="Job finish time (null if running)")
    row_count: int = Field(0, ge=0, description="Total rows/posts processed")
    inserted_count: int = Field(0, ge=0, description="Rows/posts successfully inserted")
    skipped_count: int = Field(0, ge=0, description="Rows/posts skipped")
    duplicate_count: int = Field(0, ge=0, description="Duplicate rows or failed posts")
    mode: str | None = Field(None, description="Execution mode: 'live' or 'replay', null for CSV ingestion")
    error_summary: list[str] | None = Field(None, description="List of error messages")

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Response schema for listing jobs."""

    jobs: list[JobResponse] = Field(default_factory=list, description="List of jobs")
    total: int = Field(0, ge=0, description="Total number of jobs")
