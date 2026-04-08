"""SQLAlchemy model for connector checkpoints to track incremental fetching."""

from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


class ConnectorCheckpoint(Base):
    """Tracks checkpoint state for incremental connector runs.

    Each connector (e.g., 'twitter-file') stores its last seen timestamp
    to enable incremental fetching on subsequent runs.
    """

    __tablename__ = "connector_checkpoints"

    connector_id = Column(String(255), primary_key=True)
    checkpoint_data = Column(JSONB, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
