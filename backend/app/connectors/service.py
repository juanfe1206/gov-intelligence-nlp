"""Connector service layer for managing connector runs and checkpoints."""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.interface import BaseConnector
from app.connectors.schemas import ConnectorRunSummary, NormalizedPost
from app.connectors.validator import validate_and_normalize
from app.models.connector_checkpoint import ConnectorCheckpoint
from app.models.ingestion_job import IngestionJob
from app.models.raw_post import RawPost

logger = logging.getLogger(__name__)


async def run_connector(
    session: AsyncSession,
    connector: BaseConnector,
) -> ConnectorRunSummary:
    """Execute a connector run with checkpoint-based incremental fetching.

    This function orchestrates the full connector workflow:
    1. Load checkpoint from DB
    2. Instantiate connector with checkpoint cutoff
    3. Fetch and normalize records
    4. Ingest into raw_posts with deduplication
    5. Save new checkpoint

    Args:
        session: Async SQLAlchemy session
        connector: The connector implementation to run

    Returns:
        ConnectorRunSummary with metrics and status
    """
    connector_id = connector.connector_id
    started_at = datetime.now(timezone.utc)

    # Create running job record
    job = IngestionJob(
        source=connector_id,
        job_type="connector",
        status="running",
        started_at=started_at,
    )
    session.add(job)
    await session.commit()
    job_id = str(job.id)

    # Load checkpoint from DB
    checkpoint_data = await get_checkpoint(session, connector_id)

    # Inject checkpoint cutoff into connector for incremental fetching
    if checkpoint_data and checkpoint_data.get("last_seen_at"):
        from datetime import datetime as dt
        last_seen_str = checkpoint_data["last_seen_at"]
        try:
            last_seen = dt.fromisoformat(last_seen_str.replace("Z", "+00:00"))
            connector._after_timestamp = last_seen
            logger.info(f"Loaded checkpoint for {connector_id}: last_seen_at={last_seen}")
        except ValueError as e:
            logger.warning(f"Could not parse checkpoint timestamp '{last_seen_str}': {e}")

    # Initialize summary
    summary = ConnectorRunSummary(
        connector_id=connector_id,
        mode="live",
        started_at=started_at,
    )

    try:
        # Fetch raw records from source
        raw_records = connector.fetch()
        summary.fetched = len(raw_records)

        # Validate and normalize
        posts = validate_and_normalize(connector, raw_records, summary)

        # Ingest with external_id support
        await ingest_normalized_posts_with_external_id(session, posts, summary)

        # Update job with final counts
        await _persist_connector_job(session, job_id, summary, status="completed")

        # Save checkpoint (max timestamp seen in this run)
        checkpoint = connector.checkpoint()
        await _upsert_checkpoint(session, connector_id, checkpoint)

        summary.finished_at = datetime.now(timezone.utc)
        summary.status = "completed"

    except Exception as e:
        logger.exception(f"Connector run failed: {e}")
        await _persist_connector_job(session, job_id, summary, status="failed")
        raise

    return summary


async def get_checkpoint(session: AsyncSession, connector_id: str) -> dict[str, Any] | None:
    """Retrieve checkpoint data for a connector.

    Args:
        session: Async SQLAlchemy session
        connector_id: The connector identifier (e.g., 'twitter-file')

    Returns:
        Checkpoint data dictionary or None if no checkpoint exists
    """
    stmt = select(ConnectorCheckpoint).where(ConnectorCheckpoint.connector_id == connector_id)
    result = await session.execute(stmt)
    checkpoint = result.scalar_one_or_none()

    if checkpoint:
        return checkpoint.checkpoint_data
    return None


async def ingest_normalized_posts_with_external_id(
    session: AsyncSession,
    posts: list[NormalizedPost],
    summary: ConnectorRunSummary,
) -> None:
    """Ingest normalized posts with external_id for platform deduplication.

    Uses the partial unique index (platform, external_id) for secondary deduplication
    alongside the existing content_hash-based primary deduplication.

    Args:
        session: Async SQLAlchemy session
        posts: List of normalized posts to ingest
        summary: ConnectorRunSummary to update with counts
    """
    for post in posts:
        from app.ingestion.utils import compute_content_hash

        content_hash = compute_content_hash(post.text)

        stmt = (
            RawPost.__table__.insert()
            .values(
                source=post.source,
                platform=post.platform,
                original_text=post.text,
                content_hash=content_hash,
                external_id=post.external_id,
                author=post.author,
                created_at=post.created_at,
                metadata_={
                    "external_id": post.external_id,
                    "raw_payload": post.raw_payload,
                },
            )
            .on_conflict_do_nothing(
                index_elements=["source", "content_hash"],
            )
            .returning(RawPost.id)
        )

        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            summary.inserted += 1
        else:
            summary.duplicates += 1

    await session.commit()


async def _persist_connector_job(
    session: AsyncSession,
    job_id: str,
    summary: ConnectorRunSummary,
    status: str,
) -> None:
    """Persist connector job record with final status and counts.

    Args:
        session: Async SQLAlchemy session
        job_id: Job UUID string
        summary: ConnectorRunSummary with final metrics
        status: Final job status ('completed', 'failed', 'partial')
    """
    from sqlalchemy import update
    from sqlalchemy.dialects.postgresql import JSONB

    await session.execute(
        update(IngestionJob)
        .where(IngestionJob.id == job_id)
        .values(
            status=status,
            finished_at=summary.finished_at,
            row_count=summary.fetched,
            inserted_count=summary.inserted,
            skipped_count=summary.rejected,
            duplicate_count=summary.duplicates,
            error_summary=summary.validation_errors if summary.validation_errors else None,
        )
    )
    await session.commit()


async def _upsert_checkpoint(
    session: AsyncSession,
    connector_id: str,
    checkpoint_data: dict[str, Any],
) -> None:
    """Upsert checkpoint data for a connector.

    Args:
        session: Async SQLAlchemy session
        connector_id: The connector identifier
        checkpoint_data: Checkpoint dictionary to store
    """
    from sqlalchemy.dialects.postgresql import insert

    stmt = insert(ConnectorCheckpoint).values(
        connector_id=connector_id,
        checkpoint_data=checkpoint_data,
        updated_at=func.now(),
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["connector_id"],
        set_={
            "checkpoint_data": checkpoint_data,
            "updated_at": func.now(),
        },
    )
    await session.execute(stmt)
    await session.commit()
