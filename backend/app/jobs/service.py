"""Service layer for job tracking and retry operations."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.service import ingest_csv
from app.models.ingestion_job import IngestionJob
from app.processing.service import process_posts


async def list_jobs(session: AsyncSession, limit: int = 50) -> tuple[list[IngestionJob], int]:
    """List recent ingestion/processing jobs.

    Args:
        session: Database session
        limit: Maximum number of jobs to return

    Returns:
        Tuple of (jobs list, total count)
    """
    # Get total count without loading all rows.
    count_result = await session.execute(
        select(func.count()).select_from(IngestionJob)
    )
    total = int(count_result.scalar_one())

    # Get jobs ordered by started_at DESC
    result = await session.execute(
        select(IngestionJob)
        .order_by(IngestionJob.started_at.desc())
        .limit(limit)
    )
    jobs = result.scalars().all()

    return list(jobs), total


async def get_job_by_id(session: AsyncSession, job_id: str) -> IngestionJob | None:
    """Get a job by its ID.

    Args:
        session: Database session
        job_id: Job UUID string

    Returns:
        IngestionJob or None if not found
    """
    import uuid

    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        return None

    result = await session.execute(
        select(IngestionJob).where(IngestionJob.id == job_uuid)
    )
    return result.scalar_one_or_none()


async def retry_job(
    session: AsyncSession,
    job_id: str,
    taxonomy: dict[str, Any],
) -> IngestionJob | None:
    """Retry a failed or partial job.

    Args:
        session: Database session
        job_id: Job UUID string of the job to retry
        taxonomy: Loaded taxonomy configuration (for process jobs)

    Returns:
        New IngestionJob created for the retry, or None if job not found

    Raises:
        ValueError: If job is not in failed/partial status
    """
    import uuid

    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        return None

    # Fetch the job
    result = await session.execute(
        select(IngestionJob).where(IngestionJob.id == job_uuid)
    )
    job = result.scalar_one_or_none()

    if job is None:
        return None

    # Validate status is retryable
    if job.status not in ("failed", "partial"):
        raise ValueError(f"Cannot retry job with status '{job.status}'. Only 'failed' or 'partial' jobs can be retried.")

    # Dispatch based on job type
    if job.job_type == "ingest":
        # For ingest jobs, retry with the same source
        # Note: ingest_csv creates its own running job and returns IngestionSummary
        summary = await ingest_csv(session, source_name=job.source)
        if not summary.job_id:
            return None
        return await get_job_by_id(session, summary.job_id)

    elif job.job_type == "process":
        # For process jobs, retry with force=True to reprocess failed posts
        summary = await process_posts(session, taxonomy, force=True)
        if not summary.job_id:
            return None
        return await get_job_by_id(session, summary.job_id)

    else:
        raise ValueError(f"Unknown job type: {job.job_type}")


async def retry_ingest_job(session: AsyncSession, source: str) -> IngestionJob:
    """Retry an ingestion job for a specific source.

    Args:
        session: Database session
        source: Data source to re-ingest

    Returns:
        The new IngestionJob created for the retry
    """
    await ingest_csv(session, source_name=source)
    # Get the newly created job
    result = await session.execute(
        select(IngestionJob)
        .where(IngestionJob.source == source)
        .order_by(IngestionJob.started_at.desc())
        .limit(1)
    )
    return result.scalar_one()


async def retry_process_job(
    session: AsyncSession,
    taxonomy: dict[str, Any],
) -> IngestionJob:
    """Retry a processing job with force=True.

    Args:
        session: Database session
        taxonomy: Loaded taxonomy configuration

    Returns:
        The new IngestionJob created for the retry
    """
    await process_posts(session, taxonomy, force=True)
    # Get the newly created job
    result = await session.execute(
        select(IngestionJob)
        .where(IngestionJob.job_type == "process")
        .order_by(IngestionJob.started_at.desc())
        .limit(1)
    )
    return result.scalar_one()
