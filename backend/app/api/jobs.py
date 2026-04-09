"""API endpoints for job tracking and retry operations."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.jobs.schemas import JobListResponse, JobResponse
from app.jobs.service import get_job_by_id, list_jobs, retry_job

logger = logging.getLogger(__name__)
router = APIRouter()


def _job_to_response(job: Any) -> JobResponse:
    """Convert IngestionJob model to JobResponse schema."""
    error_summary = job.error_summary
    if error_summary is None:
        error_summary = []
    elif isinstance(error_summary, str):
        # Handle case where error_summary might be a JSON string
        import json
        try:
            error_summary = json.loads(error_summary)
        except json.JSONDecodeError:
            error_summary = [error_summary]

    return JobResponse(
        id=str(job.id),
        job_type=job.job_type or "ingest",
        status=job.status,
        source=job.source,
        started_at=job.started_at,
        finished_at=job.finished_at,
        row_count=job.row_count or 0,
        inserted_count=job.inserted_count or 0,
        skipped_count=job.skipped_count or 0,
        duplicate_count=job.duplicate_count or 0,
        normalized_count=getattr(job, "normalized_count", None),
        failure_category=getattr(job, "failure_category", None),
        mode=getattr(job, "mode", None),
        error_summary=error_summary if error_summary else None,
    )


@router.get(
    "",
    response_model=JobListResponse,
    summary="List recent jobs",
    description="Get a list of recent ingestion and processing jobs with their status.",
    response_description="List of jobs with status and metadata",
)
async def get_jobs(
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number of jobs to return"),
    session: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """List recent ingestion/processing jobs.

    Args:
        limit: Maximum number of jobs to return (default 50, max 200)
        session: Database session

    Returns:
        JobListResponse with list of jobs and total count
    """
    jobs, total = await list_jobs(session, limit=limit)
    return JobListResponse(
        jobs=[_job_to_response(job) for job in jobs],
        total=total,
    )


@router.post(
    "/{job_id}/retry",
    response_model=JobResponse,
    summary="Retry a failed or partial job",
    description="Re-run a failed or partial ingestion/processing job. Creates a new job record for the retry.",
    response_description="The new job created for the retry",
    responses={
        404: {"description": "Job not found"},
        400: {"description": "Job cannot be retried (not in failed/partial status)"},
        500: {"description": "Retry failed unexpectedly"},
    },
)
async def retry_job_endpoint(
    request: Request,
    job_id: str,
    session: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Retry a failed or partial job.

    Args:
        request: FastAPI request object (for accessing app.state.taxonomy)
        job_id: Job UUID to retry
        session: Database session

    Returns:
        JobResponse for the new job created by the retry

    Raises:
        HTTPException 404: If job not found
        HTTPException 400: If job is not in failed/partial status
        HTTPException 500: If retry fails unexpectedly
    """
    # First check if job exists and is retryable
    job = await get_job_by_id(session, job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"Job {job_id} not found"},
        )

    if job.status not in ("failed", "partial"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": f"Cannot retry job with status '{job.status}'. Only 'failed' or 'partial' jobs can be retried."
            },
        )

    taxonomy: dict[str, Any] | None = None
    if (job.job_type or "ingest") == "process":
        taxonomy = request.app.state.taxonomy
        if not taxonomy:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"message": "Taxonomy not loaded. Ensure taxonomy configuration is valid."},
            )

    try:
        # Retry the job
        new_job = await retry_job(session, job_id, taxonomy or {})

        if new_job is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Retry failed to create new job"},
            )

        return _job_to_response(new_job)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e)},
        )
    except Exception:
        logger.exception(f"Unexpected error retrying job {job_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Retry failed unexpectedly"},
        )
