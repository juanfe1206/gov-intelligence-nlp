"""Core processing orchestration service for NLP pipeline."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, exists, func, not_, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.ingestion_job import IngestionJob
from app.models.processed_post import ProcessedPost
from app.models.raw_post import RawPost
from app.processing.classifier import classify_batch
from app.processing.embeddings import generate_embeddings
from app.processing.schemas import ProcessingSummary

logger = logging.getLogger(__name__)

# Model version for tracking which model processed the data
MODEL_VERSION = f"openai-{settings.OPENAI_CHAT_MODEL}"


async def get_unprocessed_posts(
    session: AsyncSession,
    limit: int | None = None,
    include_failed: bool = False,
) -> list[RawPost]:
    """Query for raw posts that haven't been processed yet.

    Args:
        session: Database session
        limit: Maximum number of posts to return
        include_failed: If True, also include posts that failed previous processing

    Returns:
        List of raw posts needing processing
    """
    # Build subquery for posts that have processed entries
    has_processed = exists().where(ProcessedPost.raw_post_id == RawPost.id)

    # Build conditions
    conditions = [not_(has_processed)]

    if include_failed:
        # Also include posts with error status
        has_failed = exists().where(
            and_(
                ProcessedPost.raw_post_id == RawPost.id,
                ProcessedPost.error_status == True,
            )
        )
        conditions = [not_(has_processed) | has_failed]

    query = select(RawPost).where(*conditions).order_by(RawPost.created_at.asc(), RawPost.id.asc())

    if limit:
        query = query.limit(limit)

    result = await session.execute(query)
    return result.scalars().all()


async def count_skipped_posts(
    session: AsyncSession,
    include_failed: bool = False,
) -> int:
    """Count posts skipped due to prior successful processing."""
    if include_failed:
        skipped_condition = exists().where(
            and_(
                ProcessedPost.raw_post_id == RawPost.id,
                ProcessedPost.error_status.is_(False),
            )
        )
    else:
        skipped_condition = exists().where(ProcessedPost.raw_post_id == RawPost.id)

    result = await session.execute(select(func.count()).select_from(RawPost).where(skipped_condition))
    return int(result.scalar_one() or 0)


async def process_posts(
    session: AsyncSession,
    taxonomy: dict[str, Any],
    force: bool = False,
    batch_size: int | None = None,
) -> ProcessingSummary:
    """Process unclassified posts through NLP pipeline.

    Args:
        session: Database session
        taxonomy: Loaded taxonomy configuration
        force: If True, reprocess failed posts
        batch_size: Override default batch size

    Returns:
        ProcessingSummary with results
    """
    batch_size = batch_size or settings.PROCESSING_BATCH_SIZE
    started_at = datetime.now(timezone.utc)

    # Create running job at start
    job_id = await _create_running_job("nlp_processing", "process")

    summary = ProcessingSummary(
        status="failed",
        started_at=started_at,
        job_id=job_id,
    )

    try:
        summary.skipped = await count_skipped_posts(session, include_failed=force)

        first_batch = await get_unprocessed_posts(
            session,
            limit=1,
            include_failed=force,
        )
        if not first_batch:
            logger.info("No unprocessed posts found")
            summary.status = "completed"
            summary.finished_at = datetime.now(timezone.utc)
            await _persist_job(summary, job_id=job_id)
            return summary

        succeeded = 0
        failed = 0

        while True:
            posts = await get_unprocessed_posts(
                session,
                limit=batch_size,
                include_failed=force,
            )
            if not posts:
                break

            texts = [post.original_text for post in posts]
            summary.processed += len(posts)

            logger.info(f"Classifying {len(posts)} posts")
            classifications = await classify_batch(texts, taxonomy)

            logger.info(f"Generating embeddings for {len(posts)} posts")
            embeddings = await generate_embeddings(texts)

            for i, post in enumerate(posts):
                classification = classifications[i]
                embedding = embeddings[i]

                if classification and embedding:
                    was_saved = await _insert_processed_post(
                        session,
                        post.id,
                        classification,
                        embedding,
                    )
                    if was_saved:
                        succeeded += 1
                    continue

                error_msg = ""
                if not classification:
                    error_msg += "Classification failed. "
                if not embedding:
                    error_msg += "Embedding generation failed."

                await _insert_failed_post(session, post.id, error_msg)
                summary.errors.append(f"Post {post.id}: {error_msg}")
                failed += 1

        await session.commit()

        failure_rate = (failed / summary.processed) if summary.processed else 0.0
        if failed == 0:
            summary.status = "completed"
        elif failure_rate > 0.5:
            summary.status = "failed"
        else:
            summary.status = "partial"

        summary.succeeded = succeeded
        summary.failed = failed
        summary.finished_at = datetime.now(timezone.utc)

        logger.info(
            f"Processing complete: {succeeded} succeeded, {failed} failed, "
            f"{summary.skipped} skipped"
        )

    except Exception as e:
        logger.exception("Processing failed")
        summary.status = "failed"
        summary.errors.append(f"Unexpected error: {str(e)}")
        summary.finished_at = datetime.now(timezone.utc)
        await session.rollback()

    await _persist_job(summary, job_id=job_id)
    return summary


async def _insert_processed_post(
    session: AsyncSession,
    raw_post_id: Any,
    classification: Any,
    embedding: list[float],
) -> bool:
    """Insert a successfully processed post."""
    stmt = (
        pg_insert(ProcessedPost)
        .values(
            raw_post_id=raw_post_id,
            topic=classification.topic,
            subtopic=classification.subtopic,
            sentiment=classification.sentiment,
            target=classification.target,
            intensity=classification.intensity,
            embedding=embedding,
            model_version=MODEL_VERSION,
            error_status=False,
        )
        .on_conflict_do_update(
            index_elements=["raw_post_id"],
            set_={
                "topic": classification.topic,
                "subtopic": classification.subtopic,
                "sentiment": classification.sentiment,
                "target": classification.target,
                "intensity": classification.intensity,
                "embedding": embedding,
                "model_version": MODEL_VERSION,
                "error_status": False,
                "error_message": None,
                "processed_at": func.now(),
            },
        )
        .returning(ProcessedPost.id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def _insert_failed_post(
    session: AsyncSession,
    raw_post_id: Any,
    error_message: str,
) -> None:
    """Insert a failed post with error status."""
    stmt = (
        pg_insert(ProcessedPost)
        .values(
            raw_post_id=raw_post_id,
            topic="error",
            sentiment="neutral",
            error_status=True,
            error_message=error_message,
            model_version=MODEL_VERSION,
        )
        .on_conflict_do_update(
            index_elements=["raw_post_id"],
            set_={
                "topic": "error",
                "sentiment": "neutral",
                "error_status": True,
                "error_message": error_message,
                "model_version": MODEL_VERSION,
                "processed_at": func.now(),
            },
        )
    )
    await session.execute(stmt)


async def _create_running_job(source: str, job_type: str) -> str:
    """Create a job record with status 'running' at the start of processing.

    Args:
        source: Data source identifier
        job_type: Type of job ("ingest" or "process")

    Returns:
        UUID string of the created job
    """
    from app.db.session import async_session_maker

    async with async_session_maker() as session:
        job = IngestionJob(
            source=source,
            job_type=job_type,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        session.add(job)
        await session.commit()
        return str(job.id)


async def _persist_job(summary: ProcessingSummary, job_id: str | None = None) -> str:
    """Persist processing job record to database.

    Args:
        summary: Processing summary with results
        job_id: Optional job ID to update (for running jobs). If not provided, creates new record.

    Returns:
        UUID string of the job
    """
    from app.db.session import async_session_maker
    from sqlalchemy import update

    error_summary = None
    if summary.errors:
        # Limit error summary size
        error_summary = summary.errors[:50]

    async with async_session_maker() as session:
        if job_id:
            # Update existing running job
            job_id_uuid = uuid.UUID(job_id)
            await session.execute(
                update(IngestionJob)
                .where(IngestionJob.id == job_id_uuid)
                .values(
                    status=summary.status,
                    finished_at=summary.finished_at,
                    row_count=summary.processed,
                    inserted_count=summary.succeeded,
                    skipped_count=summary.skipped,
                    duplicate_count=summary.failed,
                    error_summary=error_summary,
                )
            )
            await session.commit()
            return job_id
        else:
            # Create new job record (backward compatibility)
            job = IngestionJob(
                source="nlp_processing",
                job_type="process",
                status=summary.status,
                started_at=summary.started_at,
                finished_at=summary.finished_at,
                row_count=summary.processed,
                inserted_count=summary.succeeded,
                skipped_count=summary.skipped,
                duplicate_count=summary.failed,
                error_summary=error_summary,
            )
            session.add(job)
            try:
                await session.flush()
                await session.commit()
                return str(job.id)
            except ProgrammingError as exc:
                await session.rollback()
                if "job_type" not in str(exc).lower():
                    raise
                result = await session.execute(
                    text(
                        """
                        INSERT INTO ingestion_jobs
                        (source, status, started_at, finished_at, row_count, inserted_count, skipped_count, duplicate_count, error_summary)
                        VALUES
                        (:source, :status, :started_at, :finished_at, :row_count, :inserted_count, :skipped_count, :duplicate_count, :error_summary)
                        RETURNING id
                        """
                    ),
                    {
                        "source": "nlp_processing",
                        "status": summary.status,
                        "started_at": summary.started_at,
                        "finished_at": summary.finished_at,
                        "row_count": summary.processed,
                        "inserted_count": summary.succeeded,
                        "skipped_count": summary.skipped,
                        "duplicate_count": summary.failed,
                        "error_summary": json.dumps(error_summary) if error_summary else None,
                    },
                )
                await session.commit()
                return str(result.scalar_one())
