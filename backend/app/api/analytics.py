"""Analytics API endpoints for volume and sentiment data."""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.analytics.schemas import VolumeResponse, SentimentResponse, PlatformsResponse, TopicsResponse
from app.analytics import service as analytics_service
from app.models.raw_post import RawPost

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
    topic: str | None = Query(default=None, description="Filter by topic name (e.g. 'vivienda')"),
    subtopic: str | None = Query(default=None, description="Filter by subtopic name (e.g. 'alquiler')"),
    target: str | None = Query(default=None, description="Filter by political target (e.g. 'pp', 'sanchez')"),
    platform: str | None = Query(default=None, description="Filter by platform (e.g. 'twitter')"),
    session: AsyncSession = Depends(get_db),
) -> VolumeResponse:
    """Get daily post volume for the specified date range.

    - **start_date**: Start date (YYYY-MM-DD), defaults to 7 days ago
    - **end_date**: End date (YYYY-MM-DD), defaults to today
    - **topic**: Filter by topic name (e.g. 'vivienda')
    - **subtopic**: Filter by subtopic name (e.g. 'alquiler')
    - **target**: Filter by political target (e.g. 'pp', 'sanchez')
    - **platform**: Filter by platform (e.g. 'twitter')
    """
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be less than or equal to end_date")
    logger.debug(f"Fetching volume data from {start_date} to {end_date}")
    return await analytics_service.get_volume(session, start_date, end_date, topic, subtopic, target, platform)


@router.get("/sentiment", response_model=SentimentResponse)
async def get_sentiment(
    start_date: date = Query(default_factory=_default_start),
    end_date: date = Query(default_factory=_default_end),
    topic: str | None = Query(default=None, description="Filter by topic name (e.g. 'vivienda')"),
    subtopic: str | None = Query(default=None, description="Filter by subtopic name (e.g. 'alquiler')"),
    target: str | None = Query(default=None, description="Filter by political target (e.g. 'pp', 'sanchez')"),
    platform: str | None = Query(default=None, description="Filter by platform (e.g. 'twitter')"),
    session: AsyncSession = Depends(get_db),
) -> SentimentResponse:
    """Get daily sentiment breakdown for the specified date range.

    Returns stacked data with positive, neutral, and negative counts per day.

    - **start_date**: Start date (YYYY-MM-DD), defaults to 7 days ago
    - **end_date**: End date (YYYY-MM-DD), defaults to today
    - **topic**: Filter by topic name (e.g. 'vivienda')
    - **subtopic**: Filter by subtopic name (e.g. 'alquiler')
    - **target**: Filter by political target (e.g. 'pp', 'sanchez')
    - **platform**: Filter by platform (e.g. 'twitter')
    """
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be less than or equal to end_date")
    logger.debug(f"Fetching sentiment data from {start_date} to {end_date}")
    return await analytics_service.get_sentiment(session, start_date, end_date, topic, subtopic, target, platform)


@router.get("/platforms", response_model=PlatformsResponse)
async def get_platforms(session: AsyncSession = Depends(get_db)) -> PlatformsResponse:
    """Return distinct platform values from raw_posts."""
    stmt = select(RawPost.platform).distinct().order_by(RawPost.platform)
    result = await session.execute(stmt)
    platforms = [row[0] for row in result.all() if row[0]]
    return PlatformsResponse(platforms=platforms)


@router.get("/topics", response_model=TopicsResponse)
async def get_topics(
    request: Request,
    start_date: date = Query(default_factory=_default_start),
    end_date: date = Query(default_factory=_default_end),
    topic: str | None = Query(default=None, description="Filter by topic name (e.g. 'vivienda')"),
    subtopic: str | None = Query(default=None, description="Filter by subtopic name"),
    target: str | None = Query(default=None, description="Filter by political target"),
    platform: str | None = Query(default=None, description="Filter by platform"),
    session: AsyncSession = Depends(get_db),
) -> TopicsResponse:
    """Get topic distribution ranked by volume with sentiment breakdown."""
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be less than or equal to end_date")
    taxonomy = request.app.state.taxonomy
    return await analytics_service.get_topics(session, taxonomy, start_date, end_date, topic, subtopic, target, platform)
