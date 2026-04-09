"""Connector service layer for managing connector runs and checkpoints."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
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
    mode: str = "live",
) -> ConnectorRunSummary:
    """Execute a connector run with checkpoint-based incremental fetching.

    This function orchestrates the full connector workflow:
    1. Load checkpoint from DB
    2. Inject checkpoint cutoff into connector via constructor param
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

    # Create running job record (separate session so audit trail survives rollback)
    job_id = await _create_running_job(connector_id, mode=mode)

    # Load checkpoint from DB and inject into connector
    checkpoint_data = await get_checkpoint(session, connector_id)
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
        mode=mode,
        started_at=started_at,
    )

    try:
        # Fetch raw records from source
        raw_records = connector.fetch()

        # Validate and normalize (increments summary.fetched per record)
        posts = validate_and_normalize(connector, raw_records, summary)

        # Ingest with external_id support
        await ingest_normalized_posts_with_external_id(session, posts, summary)

        # Set finished_at before persisting so the job record is complete
        summary.finished_at = datetime.now(timezone.utc)

        # Update job with final counts
        await _persist_connector_job(job_id, summary, status="completed", mode=mode)

        # Save checkpoint only if we saw records and mode is live (prevent erasing valid checkpoint on empty run)
        checkpoint = connector.checkpoint()
        if mode == "live" and checkpoint.get("last_seen_at") is not None:
            await _upsert_checkpoint(session, connector_id, checkpoint)

    except Exception as e:
        logger.exception(f"Connector run failed: {e}")
        await _persist_connector_job(job_id, summary, status="failed", mode=mode)
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

    Uses content_hash-based primary deduplication via on_conflict_do_nothing.
    The partial unique index (platform, external_id) provides secondary DB-level
    protection — IntegrityError from it is caught and treated as a duplicate.

    Args:
        session: Async SQLAlchemy session
        posts: List of normalized posts to ingest
        summary: ConnectorRunSummary to update with counts
    """
    for post in posts:
        from app.ingestion.utils import compute_content_hash

        content_hash = compute_content_hash(post.text)

        stmt = (
            pg_insert(RawPost)
            .values(
                source=post.source,
                platform=post.platform,
                original_text=post.text,
                content_hash=content_hash,
                external_id=post.external_id,
                author=post.author,
                created_at=post.created_at,
                metadata_={
                    "raw_payload": post.raw_payload,
                },
            )
            .on_conflict_do_nothing(
                index_elements=["source", "content_hash"],
            )
            .returning(RawPost.id)
        )

        try:
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                summary.inserted += 1
            else:
                summary.duplicates += 1
        except IntegrityError:
            # Secondary dedup: partial unique index (platform, external_id) violation
            await session.rollback()
            summary.duplicates += 1

    await session.commit()


async def _create_running_job(connector_id: str, mode: str = "live") -> str:
    """Create a job record with status 'running' using a separate session.

    Uses a separate session so the job audit trail survives even if the
    main transaction rolls back.

    Args:
        connector_id: The connector identifier
        mode: Execution mode ('live' or 'replay')

    Returns:
        UUID string of the created job
    """
    from app.db.session import async_session_maker

    async with async_session_maker() as session:
        job = IngestionJob(
            source=connector_id,
            job_type="connector",
            status="running",
            mode=mode,
            started_at=datetime.now(timezone.utc),
        )
        session.add(job)
        await session.commit()
        return str(job.id)


async def _persist_connector_job(
    job_id: str,
    summary: ConnectorRunSummary,
    status: str,
    mode: str = "live",
) -> None:
    """Persist connector job record with final status and counts.

    Uses a separate session so the job record update is independent
    of the main connector transaction.

    Args:
        job_id: Job UUID string
        summary: ConnectorRunSummary with final metrics
        status: Final job status ('completed', 'failed', 'partial')
        mode: Execution mode ('live' or 'replay')
    """
    from app.db.session import async_session_maker

    # Serialize ValidationError dataclasses to dicts for JSONB storage
    error_summary = None
    if summary.validation_errors:
        error_summary = [
            {"field": e.field, "message": e.message, "raw_value": e.raw_value}
            for e in summary.validation_errors
        ]

    async with async_session_maker() as session:
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
                mode=mode,
                error_summary=error_summary,
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
