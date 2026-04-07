"""API endpoints for CSV data ingestion."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.ingestion.schemas import IngestionSummary
from app.ingestion.service import ingest_csv

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "",
    response_model=IngestionSummary,
    summary="Ingest CSV data",
    description="Trigger ingestion of configured CSV file into raw_posts table.",
    response_description="Summary of ingestion results including counts and status",
)
async def trigger_ingest(
    session: AsyncSession = Depends(get_db),
) -> IngestionSummary:
    """Trigger CSV ingestion.

    Loads the configured CSV file and inserts valid rows into raw_posts.
    Skips invalid rows, detects duplicates, and creates a job record.

    Returns:
        IngestionSummary with counts of processed, inserted, skipped, and duplicate rows

    Raises:
        HTTPException 500: If ingestion fails unexpectedly
    """
    try:
        summary = await ingest_csv(session)

        if summary.status == "failed":
            # Return 200 with error details in body for partial failures
            # Full failures are still reported via the summary
            logger.warning(f"Ingestion completed with failures: {summary.errors}")

        return summary

    except Exception:
        logger.exception("Unexpected ingestion error")
        raise HTTPException(
            status_code=500,
            detail={"message": "Ingestion failed"},
        )
