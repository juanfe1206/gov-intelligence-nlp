"""Pydantic schemas for normalized posts and connector runs."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class NormalizedPost(BaseModel):
    """A normalized post from any source platform.

    This schema is provider-agnostic and allows ingesting posts from
    different platforms into the same raw_posts table without special-case
    per-platform logic.
    """

    source: str = Field(..., description="Connector/run identifier (e.g., 'twitter-scrape-2026-04')")
    platform: str = Field(..., description="Platform name (e.g., 'twitter', 'reddit')")
    external_id: str = Field(..., description="Platform-specific record ID for deduplication")
    text: str = Field(..., min_length=1, description="Post content")
    author: str | None = Field(None, description="Author identifier, nullable")
    created_at: datetime = Field(..., description="Original post timestamp (must be timezone-aware)")
    raw_payload: dict[str, Any] = Field(default_factory=dict, description="Full raw record for replay mode")


@dataclass
class ValidationError:
    """Validation error for a failed normalization.

    Captures which field failed validation, the error message, and the
    raw value that caused the failure.
    """

    field: str
    message: str
    raw_value: Any


class ConnectorRunSummary(BaseModel):
    """Summary of a connector run.

    Tracks metrics for a single execution, including fetched, normalized,
    rejected, and inserted counts, plus validation errors.
    """

    connector_id: str = Field(..., description="Identifier for the connector")
    mode: str = Field(default="live", description="Execution mode: 'live' or 'replay'")
    started_at: datetime = Field(..., description="Run start time")
    finished_at: datetime | None = Field(None, description="Run finish time")
    fetched: int = Field(default=0, ge=0, description="Total raw records attempted")
    normalized: int = Field(default=0, ge=0, description="Records that passed normalization")
    rejected: int = Field(default=0, ge=0, description="Records that failed normalization")
    inserted: int = Field(default=0, ge=0, description="Records inserted into raw_posts")
    duplicates: int = Field(default=0, ge=0, description="Duplicate records skipped")
    validation_errors: list[ValidationError] = Field(
        default_factory=list,
        description="Validation errors for rejected records",
    )
