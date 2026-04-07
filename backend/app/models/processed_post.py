"""SQLAlchemy model for processed posts with embeddings."""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ProcessedPost(Base):
    """Represents a classified and vectorized post with NLP analysis results."""

    __tablename__ = "processed_posts"
    __table_args__ = (
        UniqueConstraint("raw_post_id", name="uq_processed_posts_raw_post_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    raw_post_id = Column(UUID(as_uuid=True), ForeignKey("raw_posts.id"), nullable=False)
    topic = Column(String(100), nullable=False)
    subtopic = Column(String(100), nullable=True)
    sentiment = Column(String(20), nullable=False)
    target = Column(String(255), nullable=True)
    intensity = Column(Float, nullable=True)
    embedding = Column(Vector(1536), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    model_version = Column(String(50), nullable=True)
    error_status = Column(Boolean, nullable=True, default=False)
    error_message = Column(Text, nullable=True)

    # Relationship to RawPost
    raw_post = relationship("RawPost", backref="processed_posts")
