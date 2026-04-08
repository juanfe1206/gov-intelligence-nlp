"""Admin API endpoints for demo reset and management."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.ingestion_job import IngestionJob
from app.models.processed_post import ProcessedPost
from app.models.raw_post import RawPost

logger = logging.getLogger(__name__)
router = APIRouter()


class ResetRequest(BaseModel):
    preserve_raw: bool = True


class ResetResponse(BaseModel):
    deleted_processed_posts: int
    deleted_jobs: int
    deleted_raw_posts: int
    message: str


def _safe_rowcount(count: int) -> int:
    """Return 0 if the driver reports -1 (unknown rowcount)."""
    return max(count, 0)


@router.post(
    "/reset",
    response_model=ResetResponse,
    summary="Reset demo data",
    description="Clear processed posts and job records for a clean demo run. Optionally clears raw posts.",
)
async def reset_demo(
    body: Optional[ResetRequest] = None,
    session: AsyncSession = Depends(get_db),
) -> ResetResponse:
    """Delete pipeline data from the database for demo reset.

    Deletes in FK-safe order: processed_posts first (FK child of raw_posts),
    then ingestion_jobs, then optionally raw_posts.

    Args:
        body: ResetRequest with preserve_raw flag (default: True)

    Returns:
        ResetResponse with row counts and message
    """
    if body is None:
        body = ResetRequest()

    try:
        result_pp = await session.execute(delete(ProcessedPost))
        deleted_pp = _safe_rowcount(result_pp.rowcount)

        result_ij = await session.execute(delete(IngestionJob))
        deleted_ij = _safe_rowcount(result_ij.rowcount)

        deleted_rp = 0
        if not body.preserve_raw:
            result_rp = await session.execute(delete(RawPost))
            deleted_rp = _safe_rowcount(result_rp.rowcount)

        await session.commit()
    except Exception:
        await session.rollback()
        logger.exception("Demo reset failed — database rolled back")
        raise

    logger.info(
        "Demo reset: deleted %d processed_posts, %d jobs, %d raw_posts",
        deleted_pp, deleted_ij, deleted_rp,
    )

    scope = "processed posts and job records" if body.preserve_raw else "all pipeline data"
    return ResetResponse(
        deleted_processed_posts=deleted_pp,
        deleted_jobs=deleted_ij,
        deleted_raw_posts=deleted_rp,
        message=f"Reset complete. Cleared {scope}.",
    )
