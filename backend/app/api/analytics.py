"""Analytics API endpoints for volume and sentiment data."""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.analytics.schemas import VolumeResponse, SentimentResponse, PlatformsResponse, TopicsResponse, PostsResponse, ComparisonResponse, SpikesResponse
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


@router.get("/posts", response_model=PostsResponse)
async def get_posts(
    request: Request,
    start_date: date = Query(default_factory=_default_start),
    end_date: date = Query(default_factory=_default_end),
    topic: str | None = Query(default=None, description="Filter by topic name (e.g. 'vivienda')"),
    subtopic: str | None = Query(default=None, description="Filter by subtopic name"),
    target: str | None = Query(default=None, description="Filter by political target"),
    platform: str | None = Query(default=None, description="Filter by platform"),
    session: AsyncSession = Depends(get_db),
) -> PostsResponse:
    """Get representative posts ranked by intensity and recency."""
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be less than or equal to end_date")
    taxonomy = request.app.state.taxonomy
    return await analytics_service.get_posts(session, taxonomy, start_date, end_date, topic, subtopic, target, platform)


@router.get("/compare", response_model=ComparisonResponse)
async def get_comparison(
    request: Request,
    topic: str = Query(..., description="Topic name (e.g., 'vivienda')"),
    parties: list[str] = Query(default=[], description="List of target/party names to compare (e.g., ?parties=party1&parties=party2)"),
    start_date: date = Query(default_factory=_default_start),
    end_date: date = Query(default_factory=_default_end),
    platform: str | None = Query(default=None, description="Filter by platform"),
    session: AsyncSession = Depends(get_db),
) -> ComparisonResponse:
    """Get per-party sentiment and volume comparison for a topic."""
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be less than or equal to end_date")
    if len(parties) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least two parties must be specified for comparison",
        )
    taxonomy = request.app.state.taxonomy
    return await analytics_service.get_comparison(session, taxonomy, topic, parties, start_date, end_date, platform)


@router.get("/spikes", response_model=SpikesResponse)
async def get_spikes(
    request: Request,
    window_hours: int = Query(default=24, ge=2, le=168, description="Detection window in hours (2–168)"),
    volume_threshold: float = Query(default=2.0, ge=1.0, description="Volume spike ratio threshold (default 2.0 = 2× increase)"),
    sentiment_threshold: float = Query(default=0.20, ge=0.0, le=1.0, description="Sentiment spike delta threshold in percentage points (default 0.20 = +20pp)"),
    platform: str | None = Query(default=None, description="Filter by platform"),
    session: AsyncSession = Depends(get_db),
) -> SpikesResponse:
    """Detect volume and sentiment spikes across all topics."""
    taxonomy = request.app.state.taxonomy
    return await analytics_service.get_spikes(
        session,
        taxonomy,
        window_hours=window_hours,
        volume_threshold=volume_threshold,
        sentiment_threshold=sentiment_threshold,
        platform=platform,
    )
