"""Analytics service for volume and sentiment queries."""

from datetime import date, timedelta
from collections import defaultdict

from sqlalchemy import func, cast, Date, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.raw_post import RawPost
from app.models.processed_post import ProcessedPost
from app.analytics.schemas import DailyVolume, VolumeResponse, DailySentiment, SentimentResponse


async def get_volume(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    topic: str | None = None,
    subtopic: str | None = None,
    target: str | None = None,
    platform: str | None = None,
) -> VolumeResponse:
    """Get daily post volume for a date range.

    Joins processed_posts with raw_posts to get the created_at date dimension.
    Filters out posts with error_status=True.
    Optional filters: topic, subtopic, target, platform.
    """
    date_col = cast(RawPost.created_at, Date)
    filters = [
        date_col >= start_date,
        date_col <= end_date,
        or_(
            ProcessedPost.error_status.is_(False),
            ProcessedPost.error_status.is_(None),
        ),
    ]
    if topic is not None:
        filters.append(ProcessedPost.topic == topic)
    if subtopic is not None:
        filters.append(ProcessedPost.subtopic == subtopic)
    if target is not None:
        filters.append(ProcessedPost.target == target)
    if platform is not None:
        filters.append(RawPost.platform == platform)

    stmt = (
        select(date_col.label("day"), func.count().label("count"))
        .select_from(ProcessedPost)
        .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
        .where(and_(*filters))
        .group_by(date_col)
        .order_by(date_col)
    )
    result = await session.execute(stmt)
    rows = result.all()
    row_map = {str(row.day): row.count for row in rows}

    # Fill the entire requested date range with explicit zero buckets.
    data: list[DailyVolume] = []
    current = start_date
    while current <= end_date:
        day_str = current.isoformat()
        data.append(DailyVolume(date=day_str, count=row_map.get(day_str, 0)))
        current += timedelta(days=1)

    return VolumeResponse(data=data, total=sum(d.count for d in data))


async def get_sentiment(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    topic: str | None = None,
    subtopic: str | None = None,
    target: str | None = None,
    platform: str | None = None,
) -> SentimentResponse:
    """Get daily sentiment breakdown for a date range.

    Joins processed_posts with raw_posts to get the created_at date dimension.
    Filters out posts with error_status=True.
    Aggregates counts by date and sentiment (positive/neutral/negative).
    Optional filters: topic, subtopic, target, platform.
    """
    date_col = cast(RawPost.created_at, Date)
    filters = [
        date_col >= start_date,
        date_col <= end_date,
        or_(
            ProcessedPost.error_status.is_(False),
            ProcessedPost.error_status.is_(None),
        ),
    ]
    if topic is not None:
        filters.append(ProcessedPost.topic == topic)
    if subtopic is not None:
        filters.append(ProcessedPost.subtopic == subtopic)
    if target is not None:
        filters.append(ProcessedPost.target == target)
    if platform is not None:
        filters.append(RawPost.platform == platform)

    stmt = (
        select(
            date_col.label("day"),
            ProcessedPost.sentiment,
            func.count().label("count"),
        )
        .select_from(ProcessedPost)
        .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
        .where(and_(*filters))
        .group_by(date_col, ProcessedPost.sentiment)
        .order_by(date_col)
    )
    result = await session.execute(stmt)
    rows = result.all()

    # Aggregate by date
    by_date: dict[str, dict[str, int]] = defaultdict(lambda: {"positive": 0, "neutral": 0, "negative": 0})
    for row in rows:
        day_str = str(row.day)
        sentiment = row.sentiment.lower() if row.sentiment else "neutral"
        if sentiment in ("positive", "neutral", "negative"):
            by_date[day_str][sentiment] += row.count
        else:
            by_date[day_str]["neutral"] += row.count  # fallback

    # Fill the entire requested date range with explicit zero buckets.
    data: list[DailySentiment] = []
    current = start_date
    while current <= end_date:
        day_str = current.isoformat()
        counts = by_date.get(day_str, {"positive": 0, "neutral": 0, "negative": 0})
        data.append(DailySentiment(date=day_str, **counts))
        current += timedelta(days=1)

    return SentimentResponse(data=data)
