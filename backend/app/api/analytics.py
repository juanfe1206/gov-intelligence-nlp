"""Analytics API endpoints for volume and sentiment data."""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.analytics.schemas import VolumeResponse, SentimentResponse
from app.analytics import service as analytics_service

logger = logging.getLogger(__name__)
router = APIRouter()


def _default_start() -> date:
    """Default start date (7 days ago)."""
    return date.today() - timedelta(days=6)


def _default_end() -> date:
    """Default end date (today)."""
    return date.today()


@router.get("/volume", response_model=VolumeResponse)
async def get_volume(
    start_date: date = Query(default_factory=_default_start),
    end_date: date = Query(default_factory=_default_end),
    session: AsyncSession = Depends(get_db),
) -> VolumeResponse:
    """Get daily post volume for the specified date range.

    - **start_date**: Start date (YYYY-MM-DD), defaults to 7 days ago
    - **end_date**: End date (YYYY-MM-DD), defaults to today
    """
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be less than or equal to end_date")
    logger.debug(f"Fetching volume data from {start_date} to {end_date}")
    return await analytics_service.get_volume(session, start_date, end_date)


@router.get("/sentiment", response_model=SentimentResponse)
async def get_sentiment(
    start_date: date = Query(default_factory=_default_start),
    end_date: date = Query(default_factory=_default_end),
    session: AsyncSession = Depends(get_db),
) -> SentimentResponse:
    """Get daily sentiment breakdown for the specified date range.

    Returns stacked data with positive, neutral, and negative counts per day.

    - **start_date**: Start date (YYYY-MM-DD), defaults to 7 days ago
    - **end_date**: End date (YYYY-MM-DD), defaults to today
    """
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be less than or equal to end_date")
    logger.debug(f"Fetching sentiment data from {start_date} to {end_date}")
    return await analytics_service.get_sentiment(session, start_date, end_date)
