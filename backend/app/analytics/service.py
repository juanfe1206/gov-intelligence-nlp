"""Analytics service for volume and sentiment queries."""

from datetime import date, timedelta
from collections import defaultdict

from sqlalchemy import func, cast, Date, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.raw_post import RawPost
from app.models.processed_post import ProcessedPost
from app.analytics.schemas import (
    DailyVolume,
    VolumeResponse,
    DailySentiment,
    SentimentResponse,
    SubtopicDistributionItem,
    TopicDistributionItem,
    TopicsResponse,
    PostItem,
    PostsResponse,
)
from app.taxonomy.schemas import TaxonomyConfig


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


async def get_topics(
    session: AsyncSession,
    taxonomy: TaxonomyConfig,
    start_date: date,
    end_date: date,
    topic: str | None = None,
    subtopic: str | None = None,
    target: str | None = None,
    platform: str | None = None,
) -> TopicsResponse:
    """Get topic distribution with sentiment breakdown.

    Ranks topics by post count (descending). Each topic includes sentiment
    distribution and top subtopics. Applies same filter pattern as get_volume.
    If topic filter is set, returns only that topic with its subtopics.
    """
    date_col = cast(RawPost.created_at, Date)
    base_filters = [
        date_col >= start_date,
        date_col <= end_date,
        or_(
            ProcessedPost.error_status.is_(False),
            ProcessedPost.error_status.is_(None),
        ),
    ]
    if topic is not None:
        base_filters.append(ProcessedPost.topic == topic)
    if subtopic is not None:
        base_filters.append(ProcessedPost.subtopic == subtopic)
    if target is not None:
        base_filters.append(ProcessedPost.target == target)
    if platform is not None:
        base_filters.append(RawPost.platform == platform)

    # Query 1: group by topic + sentiment
    topic_stmt = (
        select(
            ProcessedPost.topic,
            ProcessedPost.sentiment,
            func.count().label("count"),
        )
        .select_from(ProcessedPost)
        .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
        .where(and_(*base_filters))
        .group_by(ProcessedPost.topic, ProcessedPost.sentiment)
    )
    topic_result = await session.execute(topic_stmt)

    # Aggregate topic-level counts
    topic_data: dict[str, dict] = {}
    for row in topic_result.all():
        t = row.topic or "unknown"
        if t not in topic_data:
            topic_data[t] = {"count": 0, "positive": 0, "neutral": 0, "negative": 0}
        sentiment = (row.sentiment or "neutral").lower()
        if sentiment not in ("positive", "neutral", "negative"):
            sentiment = "neutral"
        topic_data[t][sentiment] += row.count
        topic_data[t]["count"] += row.count

    # Query 2: group by topic + subtopic + sentiment
    subtopic_stmt = (
        select(
            ProcessedPost.topic,
            ProcessedPost.subtopic,
            ProcessedPost.sentiment,
            func.count().label("count"),
        )
        .select_from(ProcessedPost)
        .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
        .where(and_(*base_filters))
        .group_by(ProcessedPost.topic, ProcessedPost.subtopic, ProcessedPost.sentiment)
    )
    subtopic_result = await session.execute(subtopic_stmt)

    # Aggregate subtopic-level counts
    subtopic_data: dict[str, dict[str, dict]] = {}
    for row in subtopic_result.all():
        t = row.topic or "unknown"
        s = row.subtopic or ""
        if not s:
            continue
        if t not in subtopic_data:
            subtopic_data[t] = {}
        if s not in subtopic_data[t]:
            subtopic_data[t][s] = {"count": 0, "positive": 0, "neutral": 0, "negative": 0}
        sentiment = (row.sentiment or "neutral").lower()
        if sentiment not in ("positive", "neutral", "negative"):
            sentiment = "neutral"
        subtopic_data[t][s][sentiment] += row.count
        subtopic_data[t][s]["count"] += row.count

    # Build label lookup from taxonomy (topic labels + per-topic subtopic maps)
    topic_label_map: dict[str, str] = {t.name: t.label for t in taxonomy.topics}
    topic_subtopic_labels: dict[str, dict[str, str]] = {
        t.name: {st.name: st.label for st in t.subtopics} for t in taxonomy.topics
    }

    # Build response, sorted by count descending
    result_topics: list[TopicDistributionItem] = []
    for topic_name, counts in sorted(topic_data.items(), key=lambda x: x[1]["count"], reverse=True):
        st_labels = topic_subtopic_labels.get(topic_name, {})
        subtopics_for_topic = []
        for st_name, st_counts in sorted(
            subtopic_data.get(topic_name, {}).items(),
            key=lambda x: x[1]["count"],
            reverse=True,
        ):
            subtopics_for_topic.append(
                SubtopicDistributionItem(
                    name=st_name,
                    label=st_labels.get(st_name, st_name),
                    **st_counts,
                )
            )
        result_topics.append(
            TopicDistributionItem(
                name=topic_name,
                label=topic_label_map.get(topic_name, topic_name),
                subtopics=subtopics_for_topic,
                **{k: counts[k] for k in ("count", "positive", "neutral", "negative")},
            )
        )

    return TopicsResponse(topics=result_topics)


async def get_posts(
    session: AsyncSession,
    taxonomy: TaxonomyConfig,
    start_date: date,
    end_date: date,
    topic: str | None = None,
    subtopic: str | None = None,
    target: str | None = None,
    platform: str | None = None,
    limit: int = 10,
) -> PostsResponse:
    """Get representative posts for the given filters.

    Posts are ranked by intensity DESC (most intense/representative first),
    then by created_at DESC (most recent). Applies same filter pattern as get_volume.
    Returns up to `limit` posts plus the total count matching filters.
    """
    date_col = cast(RawPost.created_at, Date)
    base_filters = [
        date_col >= start_date,
        date_col <= end_date,
        or_(
            ProcessedPost.error_status.is_(False),
            ProcessedPost.error_status.is_(None),
        ),
    ]
    if topic is not None:
        base_filters.append(ProcessedPost.topic == topic)
    if subtopic is not None:
        base_filters.append(ProcessedPost.subtopic == subtopic)
    if target is not None:
        base_filters.append(ProcessedPost.target == target)
    if platform is not None:
        base_filters.append(RawPost.platform == platform)

    # Count query (no LIMIT)
    count_stmt = (
        select(func.count())
        .select_from(ProcessedPost)
        .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
        .where(and_(*base_filters))
    )
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    # Posts query — ranked by intensity DESC NULLS LAST, then created_at DESC
    posts_stmt = (
        select(
            ProcessedPost.id,
            RawPost.original_text,
            RawPost.platform,
            RawPost.created_at,
            RawPost.author,
            RawPost.source,
            ProcessedPost.sentiment,
            ProcessedPost.topic,
            ProcessedPost.subtopic,
            ProcessedPost.intensity,
        )
        .select_from(ProcessedPost)
        .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
        .where(and_(*base_filters))
        .order_by(ProcessedPost.intensity.desc().nulls_last(), RawPost.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(posts_stmt)

    # Build label lookup from taxonomy (per-topic subtopic maps — same as get_topics)
    topic_label_map: dict[str, str] = {t.name: t.label for t in taxonomy.topics}
    topic_subtopic_labels: dict[str, dict[str, str]] = {
        t.name: {st.name: st.label for st in t.subtopics} for t in taxonomy.topics
    }

    posts: list[PostItem] = []
    for row in result.all():
        topic_name = row.topic or "unknown"
        subtopic_name = row.subtopic
        st_labels = topic_subtopic_labels.get(topic_name, {})
        created_date = row.created_at.date() if hasattr(row.created_at, "date") else row.created_at
        posts.append(
            PostItem(
                id=str(row.id),
                original_text=row.original_text,
                platform=row.platform or "",
                created_at=str(created_date),
                sentiment=(row.sentiment or "neutral").lower(),
                topic=topic_name,
                topic_label=topic_label_map.get(topic_name, topic_name),
                subtopic=subtopic_name,
                subtopic_label=st_labels.get(subtopic_name, subtopic_name) if subtopic_name else None,
                author=row.author,
                source=row.source,
            )
        )

    return PostsResponse(posts=posts, total=total)
