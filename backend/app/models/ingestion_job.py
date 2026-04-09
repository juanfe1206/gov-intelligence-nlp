"""SQLAlchemy model for ingestion/processing job tracking."""

import uuid

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base


class IngestionJob(Base):
    """Tracks the status and results of ingestion and processing runs."""

    __tablename__ = "ingestion_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String(255), nullable=False)
    job_type = Column(String(50), nullable=True, default="ingest")  # ingest, process
    mode = Column(String(10), nullable=True)  # live, replay
    status = Column(String(50), nullable=False)  # completed, failed, partial
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    row_count = Column(Integer, default=0)
    inserted_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    duplicate_count = Column(Integer, default=0)
    normalized_count = Column(Integer, nullable=True)  # Records passing normalization (connector jobs only)
    failure_category = Column(String(50), nullable=True)  # Machine-readable failure category for failed connector runs
    error_summary = Column(JSONB, nullable=True)  # List of error messages
