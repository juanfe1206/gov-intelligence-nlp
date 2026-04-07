"""Core processing orchestration service for NLP pipeline."""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, and_, not_, exists, text
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

    query = select(RawPost).where(*conditions)

    if limit:
        query = query.limit(limit)

    result = await session.execute(query)
    return result.scalars().all()


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

    summary = ProcessingSummary(
        status="failed",
        started_at=started_at,
    )

    try:
        # Get unprocessed posts
        posts = await get_unprocessed_posts(
            session,
            limit=batch_size,
            include_failed=force,
        )

        if not posts:
            logger.info("No unprocessed posts found")
            summary.status = "completed"
            summary.finished_at = datetime.now(timezone.utc)
            await _persist_job(summary)
            return summary

        # Extract texts for batch processing
        texts = [post.original_text for post in posts]
        summary.processed = len(posts)

        # Step 1: Classify all posts
        logger.info(f"Classifying {len(posts)} posts")
        classifications = await classify_batch(texts, taxonomy)

        # Step 2: Generate embeddings for all posts
        logger.info(f"Generating embeddings for {len(posts)} posts")
        embeddings = await generate_embeddings(texts)

        # Step 3: Insert results
        succeeded = 0
        failed = 0

        for i, post in enumerate(posts):
            classification = classifications[i]
            embedding = embeddings[i]

            if classification and embedding:
                # Success - insert processed post
                await _insert_processed_post(
                    session,
                    post.id,
                    classification,
                    embedding,
                )
                succeeded += 1
            else:
                # Failure - mark as error
                error_msg = ""
                if not classification:
                    error_msg += "Classification failed. "
                if not embedding:
                    error_msg += "Embedding generation failed."

                await _insert_failed_post(session, post.id, error_msg)
                summary.errors.append(f"Post {post.id}: {error_msg}")
                failed += 1

        await session.commit()

        # Determine final status
        if failed == 0:
            summary.status = "completed"
        elif succeeded == 0:
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

    await _persist_job(summary)
    return summary


async def _insert_processed_post(
    session: AsyncSession,
    raw_post_id: Any,
    classification: Any,
    embedding: list[float],
) -> None:
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
        .on_conflict_do_nothing(
            index_elements=["raw_post_id"],
        )
    )
    await session.execute(stmt)


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
        .on_conflict_do_nothing(
            index_elements=["raw_post_id"],
        )
    )
    await session.execute(stmt)


async def _persist_job(summary: ProcessingSummary) -> None:
    """Persist processing job record to database."""
    from app.db.session import async_session_maker

    error_summary = None
    if summary.errors:
        # Limit error summary size
        error_summary = summary.errors[:50]

    async with async_session_maker() as session:
        job = IngestionJob(
            source="nlp_processing",
            job_type="process",
            status=summary.status,
            started_at=summary.started_at,
            finished_at=summary.finished_at,
            row_count=summary.processed,
            inserted_count=summary.succeeded,
            skipped_count=summary.skipped,
            duplicate_count=summary.failed,  # Use duplicate for failed count
            error_summary=error_summary,
        )
        session.add(job)
        try:
            await session.commit()
        except ProgrammingError as exc:
            await session.rollback()
            if "job_type" not in str(exc).lower():
                raise
            await session.execute(
                text(
                    """
                    INSERT INTO ingestion_jobs
                    (source, status, started_at, finished_at, row_count, inserted_count, skipped_count, duplicate_count, error_summary)
                    VALUES
                    (:source, :status, :started_at, :finished_at, :row_count, :inserted_count, :skipped_count, :duplicate_count, :error_summary)
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
