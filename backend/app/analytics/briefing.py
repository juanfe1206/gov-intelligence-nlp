"""Daily briefing generation service with anomaly detection."""

import json
import logging
from datetime import date, timedelta
from typing import Any

from openai import APIError, APITimeoutError
from sqlalchemy import func, cast, Date, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.raw_post import RawPost
from app.models.processed_post import ProcessedPost
from app.processing.embeddings import get_openai_client
from app.taxonomy.schemas import TaxonomyConfig

logger = logging.getLogger(__name__)


class DailyBriefing:
    """Container for daily briefing data."""

    def __init__(
        self,
        date: str,
        summary: str,
        key_metrics: dict[str, Any],
        anomalies: list[dict],
        trending_topics: list[dict],
        sentiment_shift: dict[str, Any] | None,
        recommended_actions: list[str],
    ):
        self.date = date
        self.summary = summary
        self.key_metrics = key_metrics
        self.anomalies = anomalies
        self.trending_topics = trending_topics
        self.sentiment_shift = sentiment_shift
        self.recommended_actions = recommended_actions

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "summary": self.summary,
            "key_metrics": self.key_metrics,
            "anomalies": self.anomalies,
            "trending_topics": self.trending_topics,
            "sentiment_shift": self.sentiment_shift,
            "recommended_actions": self.recommended_actions,
        }


async def generate_daily_briefing(
    session: AsyncSession,
    taxonomy: TaxonomyConfig,
    briefing_date: date | None = None,
) -> DailyBriefing | None:
    """Generate a daily briefing with anomaly detection and insights.

    Args:
        session: Database session
        taxonomy: Taxonomy configuration
        briefing_date: Date for briefing (defaults to yesterday)

    Returns:
        DailyBriefing or None if generation fails
    """
    target_date = briefing_date or (date.today() - timedelta(days=1))
    comparison_date = target_date - timedelta(days=1)
    week_ago = target_date - timedelta(days=7)

    date_col = cast(RawPost.created_at, Date)
    base_filter = or_(
        ProcessedPost.error_status.is_(False),
        ProcessedPost.error_status.is_(None),
    )

    # Get day's metrics
    day_metrics = await _get_day_metrics(session, date_col, target_date, base_filter)
    prev_metrics = await _get_day_metrics(session, date_col, comparison_date, base_filter)
    week_avg = await _get_period_average(session, date_col, week_ago, target_date, base_filter)

    # Detect anomalies
    anomalies = await _detect_anomalies(
        session, date_col, target_date, week_ago, base_filter, taxonomy
    )

    # Get trending topics
    trending = await _get_trending_topics(
        session, date_col, target_date, comparison_date, base_filter, taxonomy
    )

    # Calculate sentiment shift
    sentiment_shift = _calculate_sentiment_shift(day_metrics, prev_metrics, week_avg)

    # Generate LLM summary
    summary = await _generate_briefing_summary(
        target_date,
        day_metrics,
        prev_metrics,
        week_avg,
        anomalies,
        trending,
        sentiment_shift,
    )

    # Generate recommended actions
    actions = _generate_recommended_actions(anomalies, sentiment_shift, day_metrics)

    return DailyBriefing(
        date=target_date.isoformat(),
        summary=summary or "Daily briefing unavailable. Please check the metrics directly.",
        key_metrics={
            "total_posts": day_metrics["total"],
            "change_from_previous": _calc_change(day_metrics["total"], prev_metrics["total"]),
            "change_from_weekly_avg": _calc_change(day_metrics["total"], week_avg["total"]),
            "sentiment": {
                "positive": day_metrics["positive"],
                "neutral": day_metrics["neutral"],
                "negative": day_metrics["negative"],
            },
        },
        anomalies=[a.to_dict() for a in anomalies],
        trending_topics=trending,
        sentiment_shift=sentiment_shift,
        recommended_actions=actions,
    )


async def _get_day_metrics(
    session: AsyncSession,
    date_col: Any,
    target_date: date,
    base_filter: Any,
) -> dict:
    """Get metrics for a specific day."""
    stmt = (
        select(
            func.count().label("total"),
            func.sum(func.case((ProcessedPost.sentiment == "positive", 1), else_=0)).label("positive"),
            func.sum(func.case((ProcessedPost.sentiment == "neutral", 1), else_=0)).label("neutral"),
            func.sum(func.case((ProcessedPost.sentiment == "negative", 1), else_=0)).label("negative"),
        )
        .select_from(ProcessedPost)
        .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
        .where(
            and_(
                date_col == target_date,
                base_filter,
            )
        )
    )
    result = await session.execute(stmt)
    row = result.first()

    return {
        "total": row.total or 0,
        "positive": row.positive or 0,
        "neutral": row.neutral or 0,
        "negative": row.negative or 0,
    }


async def _get_period_average(
    session: AsyncSession,
    date_col: Any,
    start_date: date,
    end_date: date,
    base_filter: Any,
) -> dict:
    """Get average metrics over a period."""
    stmt = (
        select(
            func.count().label("total"),
            func.sum(func.case((ProcessedPost.sentiment == "positive", 1), else_=0)).label("positive"),
            func.sum(func.case((ProcessedPost.sentiment == "neutral", 1), else_=0)).label("neutral"),
            func.sum(func.case((ProcessedPost.sentiment == "negative", 1), else_=0)).label("negative"),
        )
        .select_from(ProcessedPost)
        .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
        .where(
            and_(
                date_col >= start_date,
                date_col <= end_date,
                base_filter,
            )
        )
    )
    result = await session.execute(stmt)
    row = result.first()

    days = (end_date - start_date).days + 1
    return {
        "total": (row.total or 0) / max(days, 1),
        "positive": (row.positive or 0) / max(days, 1),
        "neutral": (row.neutral or 0) / max(days, 1),
        "negative": (row.negative or 0) / max(days, 1),
    }


class Anomaly:
    """Represents an detected anomaly."""

    def __init__(
        self,
        type: str,
        severity: str,
        topic: str,
        topic_label: str,
        description: str,
        metric: str,
        value: float,
        expected_range: tuple[float, float],
    ):
        self.type = type
        self.severity = severity
        self.topic = topic
        self.topic_label = topic_label
        self.description = description
        self.metric = metric
        self.value = value
        self.expected_range = expected_range

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "severity": self.severity,
            "topic": self.topic,
            "topic_label": self.topic_label,
            "description": self.description,
            "metric": self.metric,
            "value": self.value,
            "expected_min": self.expected_range[0],
            "expected_max": self.expected_range[1],
        }


async def _detect_anomalies(
    session: AsyncSession,
    date_col: Any,
    target_date: date,
    week_ago: date,
    base_filter: Any,
    taxonomy: TaxonomyConfig,
) -> list[Anomaly]:
    """Detect anomalies in volume and sentiment."""
    anomalies = []

    topic_label_map = {t.name: t.label for t in taxonomy.topics}

    # Get per-topic metrics for target day and week prior
    stmt = (
        select(
            ProcessedPost.topic,
            date_col.label("day"),
            func.count().label("volume"),
            func.sum(func.case((ProcessedPost.sentiment == "positive", 1), else_=0)).label("positive"),
            func.sum(func.case((ProcessedPost.sentiment == "negative", 1), else_=0)).label("negative"),
        )
        .select_from(ProcessedPost)
        .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
        .where(
            and_(
                date_col >= week_ago,
                date_col <= target_date,
                base_filter,
            )
        )
        .group_by(ProcessedPost.topic, date_col)
    )
    result = await session.execute(stmt)
    rows = result.all()

    # Group by topic
    topic_days: dict[str, list[dict]] = {}
    for row in rows:
        topic = row.topic or "unknown"
        if topic not in topic_days:
            topic_days[topic] = []
        topic_days[topic].append({
            "date": row.day,
            "volume": row.volume,
            "positive": row.positive or 0,
            "negative": row.negative or 0,
        })

    # Detect anomalies per topic
    for topic, days in topic_days.items():
        if len(days) < 3:  # Need minimum data
            continue

        # Separate target day from historical
        target_day = next((d for d in days if d["date"] == target_date), None)
        historical = [d for d in days if d["date"] != target_date]

        if not target_day or not historical:
            continue

        # Calculate historical stats
        volumes = [d["volume"] for d in historical]
        avg_volume = sum(volumes) / len(volumes)
        std_volume = (sum((v - avg_volume) ** 2 for v in volumes) / len(volumes)) ** 0.5

        # Volume spike detection (>2 std dev)
        if target_day["volume"] > avg_volume + 2 * std_volume:
            anomalies.append(Anomaly(
                type="volume_spike",
                severity="high" if target_day["volume"] > avg_volume + 3 * std_volume else "medium",
                topic=topic,
                topic_label=topic_label_map.get(topic, topic),
                description=f"Volume spike detected in {topic_label_map.get(topic, topic)}",
                metric="volume",
                value=target_day["volume"],
                expected_range=(max(0, avg_volume - 2 * std_volume), avg_volume + 2 * std_volume),
            ))

        # Volume drop detection (<-2 std dev)
        elif target_day["volume"] < avg_volume - 2 * std_volume:
            anomalies.append(Anomaly(
                type="volume_drop",
                severity="medium",
                topic=topic,
                topic_label=topic_label_map.get(topic, topic),
                description=f"Unusual volume drop in {topic_label_map.get(topic, topic)}",
                metric="volume",
                value=target_day["volume"],
                expected_range=(max(0, avg_volume - 2 * std_volume), avg_volume + 2 * std_volume),
            ))

        # Sentiment shift detection
        historical_positive_pct = sum(d["positive"] for d in historical) / sum(d["volume"] for d in historical) if historical else 0
        historical_negative_pct = sum(d["negative"] for d in historical) / sum(d["volume"] for d in historical) if historical else 0

        target_total = target_day["volume"]
        if target_total > 10:  # Need minimum sample
            target_positive_pct = target_day["positive"] / target_total
            target_negative_pct = target_day["negative"] / target_total

            # Negative sentiment spike
            if target_negative_pct > historical_negative_pct + 0.2:  # 20pp increase
                anomalies.append(Anomaly(
                    type="negative_sentiment_spike",
                    severity="high" if target_negative_pct > historical_negative_pct + 0.3 else "medium",
                    topic=topic,
                    topic_label=topic_label_map.get(topic, topic),
                    description=f"Negative sentiment surge in {topic_label_map.get(topic, topic)}",
                    metric="negative_sentiment_pct",
                    value=target_negative_pct * 100,
                    expected_range=(0, (historical_negative_pct + 0.2) * 100),
                ))

    # Sort by severity
    severity_order = {"high": 0, "medium": 1, "low": 2}
    anomalies.sort(key=lambda a: severity_order.get(a.severity, 3))

    return anomalies[:5]  # Limit to top 5


async def _get_trending_topics(
    session: AsyncSession,
    date_col: Any,
    target_date: date,
    comparison_date: date,
    base_filter: Any,
    taxonomy: TaxonomyConfig,
) -> list[dict]:
    """Get topics trending up or down."""
    topic_label_map = {t.name: t.label for t in taxonomy.topics}

    # Get topic counts for both days
    stmt = (
        select(
            ProcessedPost.topic,
            date_col.label("day"),
            func.count().label("count"),
        )
        .select_from(ProcessedPost)
        .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
        .where(
            and_(
                date_col.in_([target_date, comparison_date]),
                base_filter,
            )
        )
        .group_by(ProcessedPost.topic, date_col)
    )
    result = await session.execute(stmt)
    rows = result.all()

    # Group by topic
    topic_counts: dict[str, dict] = {}
    for row in rows:
        topic = row.topic or "unknown"
        if topic not in topic_counts:
            topic_counts[topic] = {}
        topic_counts[topic][row.day] = row.count

    # Calculate trends
    trending = []
    for topic, counts in topic_counts.items():
        target_count = counts.get(target_date, 0)
        prev_count = counts.get(comparison_date, 0)

        if prev_count > 0 and target_count > 0:
            change_pct = ((target_count - prev_count) / prev_count) * 100
            if abs(change_pct) > 20:  # Only significant changes
                trending.append({
                    "topic": topic,
                    "topic_label": topic_label_map.get(topic, topic),
                    "direction": "up" if change_pct > 0 else "down",
                    "change_pct": round(change_pct, 1),
                    "current_volume": target_count,
                })

    # Sort by absolute change
    trending.sort(key=lambda t: abs(t["change_pct"]), reverse=True)
    return trending[:5]


def _calculate_sentiment_shift(
    day_metrics: dict,
    prev_metrics: dict,
    week_avg: dict,
) -> dict[str, Any] | None:
    """Calculate sentiment shifts."""
    day_total = day_metrics["total"]
    if day_total < 10:
        return None

    day_positive_pct = (day_metrics["positive"] / day_total) * 100
    day_negative_pct = (day_metrics["negative"] / day_total) * 100
    day_net = day_positive_pct - day_negative_pct

    # Compare to previous day
    prev_total = prev_metrics["total"]
    if prev_total >= 10:
        prev_positive_pct = (prev_metrics["positive"] / prev_total) * 100
        prev_negative_pct = (prev_metrics["negative"] / prev_total) * 100
        prev_net = prev_positive_pct - prev_negative_pct

        net_change = day_net - prev_net

        if abs(net_change) > 10:
            return {
                "direction": "positive" if net_change > 0 else "negative",
                "magnitude": abs(net_change),
                "current_net": round(day_net, 1),
                "previous_net": round(prev_net, 1),
                "comparison": "previous_day",
            }

    # Compare to weekly average
    week_total = week_avg["total"] * 7  # Approximate
    if week_total >= 10:
        week_positive_pct = (week_avg["positive"] / week_avg["total"]) * 100
        week_negative_pct = (week_avg["negative"] / week_avg["total"]) * 100
        week_net = week_positive_pct - week_negative_pct

        net_change = day_net - week_net

        if abs(net_change) > 10:
            return {
                "direction": "positive" if net_change > 0 else "negative",
                "magnitude": abs(net_change),
                "current_net": round(day_net, 1),
                "previous_net": round(week_net, 1),
                "comparison": "weekly_average",
            }

    return None


def _calc_change(current: float, previous: float) -> dict:
    """Calculate percentage change."""
    if previous == 0:
        return {"absolute": current, "percentage": None}
    return {
        "absolute": current - previous,
        "percentage": round(((current - previous) / previous) * 100, 1),
    }


async def _generate_briefing_summary(
    target_date: date,
    day_metrics: dict,
    prev_metrics: dict,
    week_avg: dict,
    anomalies: list[Anomaly],
    trending: list[dict],
    sentiment_shift: dict | None,
) -> str | None:
    """Generate LLM summary of the day's activity."""
    total = day_metrics["total"]
    if total == 0:
        return "No activity recorded for this day."

    # Build prompt
    prompt_parts = [
        f"Date: {target_date.isoformat()}",
        f"Total Posts: {total}",
        f"Sentiment: {day_metrics['positive']} positive, {day_metrics['neutral']} neutral, {day_metrics['negative']} negative",
    ]

    if anomalies:
        prompt_parts.append(f"\nAnomalies Detected ({len(anomalies)}):")
        for a in anomalies[:3]:
            prompt_parts.append(f"- {a.description} ({a.severity} severity)")

    if trending:
        prompt_parts.append(f"\nTrending Topics ({len(trending)}):")
        for t in trending[:3]:
            direction = "up" if t["direction"] == "up" else "down"
            prompt_parts.append(f"- {t['topic_label']}: {t['change_pct']}% {direction}")

    if sentiment_shift:
        prompt_parts.append(f"\nSentiment Shift: {sentiment_shift['direction']} ({sentiment_shift['magnitude']:.1f}pp change)")

    system_prompt = (
        "You are a political intelligence analyst writing a daily briefing. "
        "Write 2-3 concise sentences summarizing the day's political discourse. "
        "Focus on significant events, sentiment shifts, and emerging trends. "
        "Be specific about what changed and why it matters."
    )

    user_prompt = f"""Daily Political Intelligence Briefing

{chr(10).join(prompt_parts)}

Write a concise summary (2-3 sentences) highlighting:
1. The overall volume and sentiment trend
2. Any significant anomalies or spikes
3. What this means for political strategy

Keep it actionable and specific."""

    try:
        client = get_openai_client()
        response = await client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_completion_tokens=200,
            temperature=0.3,
        )
        choices = response.choices or []
        summary = choices[0].message.content if choices else None
        return summary.strip() if summary else None
    except (APIError, APITimeoutError) as exc:
        logger.warning("OpenAI briefing generation failed: %s", exc)
        return None
    except Exception as exc:
        logger.error("Unexpected error during briefing generation: %s", exc)
        return None


def _generate_recommended_actions(
    anomalies: list[Anomaly],
    sentiment_shift: dict | None,
    day_metrics: dict,
) -> list[str]:
    """Generate recommended actions based on detected issues."""
    actions = []

    # High priority actions from anomalies
    for anomaly in anomalies:
        if anomaly.severity == "high":
            if anomaly.type == "negative_sentiment_spike":
                actions.append(f"Address negative sentiment in {anomaly.topic_label}: investigate root causes and prepare response")
            elif anomaly.type == "volume_spike":
                actions.append(f"Capitalize on high engagement in {anomaly.topic_label}: amplify positive messaging")

    # Sentiment-based actions
    if sentiment_shift:
        if sentiment_shift["direction"] == "negative" and sentiment_shift["magnitude"] > 15:
            actions.append("Urgent: Significant negative sentiment shift detected - activate crisis communication protocol")
        elif sentiment_shift["direction"] == "positive" and sentiment_shift["magnitude"] > 15:
            actions.append("Opportunity: Strong positive momentum - schedule proactive media appearances")

    # Volume-based actions
    total = day_metrics["total"]
    if total < 50:
        actions.append("Low engagement day - consider scheduling content to boost visibility")
    elif total > 500:
        actions.append("High engagement window - maximize reach with strategic posts")

    return actions[:3]  # Limit to top 3
