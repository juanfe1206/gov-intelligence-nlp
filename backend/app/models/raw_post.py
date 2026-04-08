"""SQLAlchemy model for raw posts from various sources."""

import uuid

from sqlalchemy import Column, DateTime, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.db.base import Base


class RawPost(Base):
    """Represents a raw post from a data source (Twitter, Reddit, etc.)."""

    __tablename__ = "raw_posts"
    __table_args__ = (
        UniqueConstraint("source", "content_hash", name="uq_raw_posts_source_hash"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String(255), nullable=False)
    platform = Column(String(100), nullable=False)
    original_text = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=True)  # SHA-256 hash for deduplication
    external_id = Column(String(255), nullable=True)  # Platform-specific record ID for deduplication
    author = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    metadata_ = Column("metadata", JSONB, nullable=True)  # metadata is reserved
    ingested_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
