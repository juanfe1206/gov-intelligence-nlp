"""Analytics API endpoints for volume and sentiment data."""

import json
import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.analytics.schemas import (
    VolumeResponse,
    SentimentResponse,
    PlatformsResponse,
    TopicsResponse,
    PostsResponse,
    ComparisonResponse,
    SpikesResponse,
    DailyBriefingResponse,
)
from app.analytics.briefing import generate_daily_briefing
from app.analytics import service as analytics_service
from app.models.raw_post import RawPost

logger = logging.getLogger(__name__)
router = APIRouter()


def _default_start() -> date:
    """Default start date (10 years ago to cover all historical data)."""
    return date.today() - timedelta(days=3650)


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
    taxonomy = request.app.state.taxonomy_config
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
    limit: int = Query(default=20, ge=1, le=200, description="Number of posts to return"),
    session: AsyncSession = Depends(get_db),
) -> PostsResponse:
    """Get representative posts ranked by intensity and recency."""
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be less than or equal to end_date")
    taxonomy = request.app.state.taxonomy_config
    return await analytics_service.get_posts(session, taxonomy, start_date, end_date, topic, subtopic, target, platform, limit=limit)


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
    taxonomy = request.app.state.taxonomy_config
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
    taxonomy = request.app.state.taxonomy_config
    return await analytics_service.get_spikes(
        session,
        taxonomy,
        window_hours=window_hours,
        volume_threshold=volume_threshold,
        sentiment_threshold=sentiment_threshold,
        platform=platform,
    )


@router.get("/briefing", response_model=DailyBriefingResponse)
async def get_daily_briefing(
    request: Request,
    briefing_date: date | None = Query(default=None, description="Date for briefing (YYYY-MM-DD), defaults to yesterday"),
    session: AsyncSession = Depends(get_db),
) -> DailyBriefingResponse:
    """Generate a daily briefing with anomaly detection and key insights.

    Returns a summary of the day's political discourse including:
    - Key metrics and trends
    - Detected anomalies (volume spikes, sentiment shifts)
    - Trending topics
    - Recommended actions
    """
    from datetime import timedelta
    from app.analytics.schemas import KeyMetrics, SentimentShift

    target_date = briefing_date or (date.today() - timedelta(days=1))
    taxonomy = request.app.state.taxonomy_config
    briefing = await generate_daily_briefing(session, taxonomy, briefing_date)

    if not briefing:
        # Return empty briefing instead of error
        return DailyBriefingResponse(
            date=target_date.isoformat(),
            summary="No data available for this date. Try selecting a different date.",
            key_metrics=KeyMetrics(
                total_posts=0,
                change_from_previous={"absolute": 0, "percentage": None},
                change_from_weekly_avg={"absolute": 0, "percentage": None},
                sentiment={"positive": 0, "neutral": 0, "negative": 0},
            ),
            anomalies=[],
            trending_topics=[],
            sentiment_shift=None,
            recommended_actions=["No data available for analysis."],
        )

    return DailyBriefingResponse(**briefing.to_dict())


@router.get("/export")
async def export_snapshot(
    request: Request,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    topic: str | None = Query(default=None),
    subtopic: str | None = Query(default=None),
    target: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    parties: list[str] = Query(default=[]),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Export a structured snapshot of analytics data as a downloadable JSON file."""
    s = start_date or _default_start()
    e = end_date or _default_end()
    if s > e:
        raise HTTPException(status_code=422, detail="start_date must be before end_date")
    taxonomy = request.app.state.taxonomy_config
    snapshot = await analytics_service.get_export(
        session,
        taxonomy,
        s,
        e,
        topic,
        subtopic,
        target,
        platform,
        parties=parties if parties else None,
    )
    json_bytes = json.dumps(snapshot.model_dump(), ensure_ascii=False, indent=2).encode("utf-8")
    return Response(
        content=json_bytes,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="gov-intelligence-export.json"'},
    )
