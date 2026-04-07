"""API endpoints for NLP processing pipeline."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.processing.schemas import ProcessRequest, ProcessResponse
from app.processing.service import process_posts

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "",
    response_model=ProcessResponse,
    summary="Process unclassified posts",
    description="Trigger NLP classification and embedding generation for unprocessed posts in raw_posts table.",
    response_description="Summary of processing results including counts and status",
)
async def trigger_processing(
    request: Request,
    process_request: ProcessRequest | None = None,
    session: AsyncSession = Depends(get_db),
) -> ProcessResponse:
    """Trigger NLP processing on unprocessed posts.

    Loads unprocessed posts from raw_posts table, classifies them using OpenAI,
    generates embeddings, and stores results in processed_posts table.

    Args:
        request: FastAPI request object (for accessing app.state.taxonomy)
        process_request: Optional processing parameters (force, batch_size)
        session: Database session

    Returns:
        ProcessResponse with counts of processed, succeeded, failed, and skipped posts

    Raises:
        HTTPException 500: If processing fails unexpectedly
        HTTPException 503: If taxonomy is not loaded
    """
    process_request = process_request or ProcessRequest()

    try:
        # Get taxonomy from app state
        taxonomy = request.app.state.taxonomy
        if not taxonomy:
            raise HTTPException(
                status_code=503,
                detail="Taxonomy not loaded. Ensure taxonomy configuration is valid.",
            )

        # Run processing
        summary = await process_posts(
            session,
            taxonomy,
            force=process_request.force,
            batch_size=process_request.batch_size,
        )

        if summary.status == "failed" and summary.succeeded == 0:
            # Return 200 with error details in body for complete failures
            logger.error(f"Processing failed: {summary.errors}")

        return ProcessResponse(
            job_id="",  # Will be populated from job record
            status=summary.status,
            processed=summary.processed,
            succeeded=summary.succeeded,
            failed=summary.failed,
            skipped=summary.skipped,
            errors=summary.errors,
            duration_seconds=summary.duration_seconds,
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected processing error")
        raise HTTPException(
            status_code=500,
            detail={"message": "Processing failed"},
        )
