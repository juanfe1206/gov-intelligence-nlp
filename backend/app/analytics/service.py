"""Analytics service for volume and sentiment queries."""

import asyncio
from datetime import date, timedelta
from collections import defaultdict

from sqlalchemy import func, cast, Date, and_, or_, select, desc, case
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
    SubtopicSentiment,
    PartyComparison,
    ComparisonResponse,
    SpikeAlert,
    SpikesResponse,
    ExportFilters,
    ExportSnapshot,
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


async def get_comparison(
    session: AsyncSession,
    taxonomy: TaxonomyConfig,
    topic: str,
    parties: list[str],
    start_date: date,
    end_date: date,
    platform: str | None = None,
) -> ComparisonResponse:
    """Get per-party sentiment and volume breakdown for a given topic and time range.

    Returns post counts, sentiment distributions (positive/neutral/negative),
    and top 3–5 subtopics ranked by negative sentiment for each party.
    """
    if len(parties) < 2:
        raise ValueError("get_comparison requires at least two parties")

    date_col = cast(RawPost.created_at, Date)
    topic_label_map = {t.name: t.label for t in taxonomy.topics}

    # Build per-topic subtopic label map for accurate label lookup
    topic_subtopic_labels: dict[str, dict[str, str]] = {}
    for t in taxonomy.topics:
        topic_subtopic_labels[t.name] = {st.name: st.label for st in t.subtopics}

    # Target label map
    target_label_map: dict[str, str] = {t.name: t.label for t in taxonomy.targets}

    results: list[PartyComparison] = []

    # Query each party separately for clarity
    for party in parties:
        base_filters = [
            date_col >= start_date,
            date_col <= end_date,
            ProcessedPost.topic == topic,
            or_(
                ProcessedPost.error_status.is_(False),
                ProcessedPost.error_status.is_(None),
            ),
        ]
        base_filters.append(ProcessedPost.target == party)
        if platform is not None:
            base_filters.append(RawPost.platform == platform)

        # Main query: post counts and sentiment distribution
        stmt = (
            select(
                func.count().label("total"),
                func.sum(
                    case(
                        (ProcessedPost.sentiment == "positive", 1),
                        else_=0,
                    )
                ).label("positive_count"),
                func.sum(
                    case(
                        (ProcessedPost.sentiment == "neutral", 1),
                        else_=0,
                    )
                ).label("neutral_count"),
                func.sum(
                    case(
                        (ProcessedPost.sentiment == "negative", 1),
                        else_=0,
                    )
                ).label("negative_count"),
            )
            .select_from(ProcessedPost)
            .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
            .where(and_(*base_filters))
        )
        result = await session.execute(stmt)
        row = result.first()

        post_count = row.total or 0
        positive_count = row.positive_count or 0
        neutral_count = row.neutral_count or 0
        negative_count = row.negative_count or 0

        sentiment_pct = {
            "positive": round(positive_count / post_count, 3) if post_count > 0 else 0.0,
            "neutral": round(neutral_count / post_count, 3) if post_count > 0 else 0.0,
            "negative": round(negative_count / post_count, 3) if post_count > 0 else 0.0,
        }

        # Query top subtopics ranked by negative sentiment count
        subtopic_stmt = (
            select(
                ProcessedPost.subtopic,
                func.sum(
                    case(
                        (ProcessedPost.sentiment == "positive", 1),
                        else_=0,
                    )
                ).label("positive_count"),
                func.sum(
                    case(
                        (ProcessedPost.sentiment == "neutral", 1),
                        else_=0,
                    )
                ).label("neutral_count"),
                func.sum(
                    case(
                        (ProcessedPost.sentiment == "negative", 1),
                        else_=0,
                    )
                ).label("negative_count"),
                func.count().label("total"),
            )
            .select_from(ProcessedPost)
            .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
            .where(and_(*base_filters))
            .group_by(ProcessedPost.subtopic)
            .order_by(desc("negative_count"))
            .limit(5)
        )
        subtopic_result = await session.execute(subtopic_stmt)

        top_subtopics: list[SubtopicSentiment] = []
        for st_row in subtopic_result.all():
            st_name = st_row.subtopic or "unknown"
            st_positive = st_row.positive_count or 0
            st_neutral = st_row.neutral_count or 0
            st_negative = st_row.negative_count or 0
            st_total = st_row.total or 0

            st_label = topic_subtopic_labels.get(topic, {}).get(st_name, st_name)
            st_pct = {
                "positive": round(st_positive / st_total, 3) if st_total > 0 else 0.0,
                "neutral": round(st_neutral / st_total, 3) if st_total > 0 else 0.0,
                "negative": round(st_negative / st_total, 3) if st_total > 0 else 0.0,
            }

            top_subtopics.append(SubtopicSentiment(
                subtopic=st_name,
                subtopic_label=st_label,
                positive_count=st_positive,
                neutral_count=st_neutral,
                negative_count=st_negative,
                total=st_total,
                sentiment_percentage=st_pct,
            ))

        party_label = target_label_map.get(party, party)
        results.append(PartyComparison(
            party=party,
            party_label=party_label,
            post_count=post_count,
            positive_count=positive_count,
            neutral_count=neutral_count,
            negative_count=negative_count,
            sentiment_percentage=sentiment_pct,
            top_subtopics=top_subtopics,
        ))

    return ComparisonResponse(
        topic=topic,
        topic_label=topic_label_map.get(topic, topic),
        parties=results,
        total_posts=sum(p.post_count for p in results),
        date_range={"start_date": str(start_date), "end_date": str(end_date)},
    )


async def get_spikes(
    session: AsyncSession,
    taxonomy: TaxonomyConfig,
    window_hours: int = 24,
    volume_threshold: float = 2.0,  # spike if recent > baseline * threshold
    sentiment_threshold: float = 0.20,  # spike if recent negative% > baseline negative% + threshold
    platform: str | None = None,
) -> SpikesResponse:
    """Detect volume and sentiment spikes across all topics.

    Compares the recent window (last `window_hours`) against the prior
    equal-length baseline window. Returns spikes sorted by magnitude desc.

    Posts are bucketed by calendar day (`Date`); `window_hours` is mapped to
    whole days so windows stay disjoint. (`date - timedelta(hours=n)` only
    uses whole days, so hours must not be applied directly to `date`.)
    """
    now = date.today()
    span_days = max(1, (window_hours + 23) // 24)
    recent_end = now
    recent_start = recent_end - timedelta(days=span_days - 1)
    baseline_end = recent_start - timedelta(days=1)
    baseline_start = baseline_end - timedelta(days=span_days - 1)

    topic_label_map = {t.name: t.label for t in taxonomy.topics}

    base_error_filter = or_(
        ProcessedPost.error_status.is_(False),
        ProcessedPost.error_status.is_(None),
    )

    date_col = cast(RawPost.created_at, Date)

    def _platform_filter() -> list:
        return [RawPost.platform == platform] if platform else []

    # Query volume per topic for recent and baseline windows in one pass each
    async def _topic_counts(start: date, end: date) -> dict[str, int]:
        stmt = (
            select(ProcessedPost.topic, func.count().label("cnt"))
            .select_from(ProcessedPost)
            .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
            .where(
                and_(
                    date_col >= start,
                    date_col <= end,
                    base_error_filter,
                    *_platform_filter(),
                )
            )
            .group_by(ProcessedPost.topic)
        )
        result = await session.execute(stmt)
        return {row.topic: row.cnt for row in result.all() if row.topic}

    async def _topic_sentiment_counts(start: date, end: date) -> dict[str, dict[str, int]]:
        """Returns {topic: {positive: N, neutral: N, negative: N, total: N}}"""
        stmt = (
            select(
                ProcessedPost.topic,
                ProcessedPost.sentiment,
                func.count().label("cnt"),
            )
            .select_from(ProcessedPost)
            .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
            .where(
                and_(
                    date_col >= start,
                    date_col <= end,
                    base_error_filter,
                    *_platform_filter(),
                )
            )
            .group_by(ProcessedPost.topic, ProcessedPost.sentiment)
        )
        result = await session.execute(stmt)
        out: dict[str, dict[str, int]] = {}
        for row in result.all():
            if not row.topic:
                continue
            t = out.setdefault(
                row.topic, {"positive": 0, "neutral": 0, "negative": 0, "total": 0}
            )
            sentiment = (row.sentiment or "neutral").lower()
            if sentiment in t:
                t[sentiment] += row.cnt
            t["total"] += row.cnt
        return out

    recent_vol, baseline_vol, recent_sent, baseline_sent = await asyncio.gather(
        _topic_counts(recent_start, recent_end),
        _topic_counts(baseline_start, baseline_end),
        _topic_sentiment_counts(recent_start, recent_end),
        _topic_sentiment_counts(baseline_start, baseline_end),
    )

    spikes: list[SpikeAlert] = []

    for topic_name in set(list(recent_vol.keys()) + list(recent_sent.keys())):
        label = topic_label_map.get(topic_name, topic_name)
        suggested_q = f"What are people saying about {label} right now?"

        r_cnt = recent_vol.get(topic_name, 0)
        b_cnt = baseline_vol.get(topic_name, 0)

        # Volume spike detection
        if r_cnt > 0 and (b_cnt == 0 or r_cnt / max(b_cnt, 1) >= volume_threshold):
            magnitude = r_cnt / max(b_cnt, 1)
            spikes.append(
                SpikeAlert(
                    topic=topic_name,
                    topic_label=label,
                    spike_type="volume",
                    magnitude=round(magnitude, 2),
                    recent_count=r_cnt,
                    baseline_count=b_cnt,
                    window_hours=window_hours,
                    suggested_question=suggested_q,
                )
            )

        # Sentiment spike detection
        r_sent = recent_sent.get(topic_name, {})
        b_sent = baseline_sent.get(topic_name, {})
        r_total = r_sent.get("total", 0)
        b_total = b_sent.get("total", 0)
        if r_total > 0:
            r_neg_pct = r_sent.get("negative", 0) / r_total
            b_neg_pct = b_sent.get("negative", 0) / b_total if b_total > 0 else 0.0
            delta = r_neg_pct - b_neg_pct
            if delta >= sentiment_threshold:
                spikes.append(
                    SpikeAlert(
                        topic=topic_name,
                        topic_label=label,
                        spike_type="sentiment",
                        magnitude=round(delta, 3),
                        recent_count=r_sent.get("negative", 0),
                        baseline_count=b_sent.get("negative", 0),
                        window_hours=window_hours,
                        suggested_question=suggested_q,
                    )
                )

    # Sort by magnitude descending; limit to top 5 most significant spikes
    spikes.sort(key=lambda s: s.magnitude, reverse=True)
    spikes = spikes[:5]

    return SpikesResponse(
        spikes=spikes,
        window_hours=window_hours,
        detected_at=str(date.today()),
    )


async def get_export(
    session: AsyncSession,
    taxonomy: TaxonomyConfig,
    start_date: date,
    end_date: date,
    topic: str | None = None,
    subtopic: str | None = None,
    target: str | None = None,
    platform: str | None = None,
    parties: list[str] | None = None,
) -> ExportSnapshot:
    """Bundle all analytics data for export."""
    volume, sentiment, topics, posts = await asyncio.gather(
        get_volume(session, start_date, end_date, topic, subtopic, target, platform),
        get_sentiment(session, start_date, end_date, topic, subtopic, target, platform),
        get_topics(session, taxonomy, start_date, end_date, topic, subtopic, target, platform),
        get_posts(session, taxonomy, start_date, end_date, topic, subtopic, target, platform, limit=50),
    )
    return ExportSnapshot(
        exported_at=str(date.today()),
        filters=ExportFilters(
            start_date=str(start_date),
            end_date=str(end_date),
            topic=topic,
            subtopic=subtopic,
            target=target,
            platform=platform,
            parties=parties,
        ),
        volume=volume,
        sentiment=sentiment,
        topics=topics,
        posts=posts,
    )
