"""Q&A retrieval and aggregation service."""

import logging
from collections import defaultdict
from datetime import date

from sqlalchemy import and_, cast, Date, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.processed_post import ProcessedPost
from app.models.raw_post import RawPost
from app.processing.embeddings import generate_single_embedding
from app.qa.schemas import (
    QAFilters,
    QAMetrics,
    QAPostItem,
    QAResponse,
    QASubtopicSummary,
)
from app.taxonomy.schemas import TaxonomyConfig

logger = logging.getLogger(__name__)

TOP_SUBTOPICS_LIMIT = 5


async def retrieve_and_aggregate(
    session: AsyncSession,
    taxonomy: TaxonomyConfig,
    question: str,
    topic: str | None = None,
    party: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    platform: str | None = None,
    top_n: int = 20,
) -> QAResponse:
    """Retrieve top-N relevant posts via vector similarity, then aggregate metrics."""
    filters_applied = QAFilters(
        topic=topic,
        party=party,
        start_date=start_date,
        end_date=end_date,
        platform=platform,
    )

    # Step 1: embed the question
    query_vector = await generate_single_embedding(question)
    if query_vector is None:
        logger.warning("Embedding generation failed for question; returning insufficient_data")
        return QAResponse(
            question=question,
            filters_applied=filters_applied,
            retrieved_posts=[],
            metrics=_empty_metrics(),
            insufficient_data=True,
        )

    # Step 2: build SQL filters
    sql_filters = [
        or_(
            ProcessedPost.error_status.is_(False),
            ProcessedPost.error_status.is_(None),
        ),
        ProcessedPost.embedding.isnot(None),
    ]
    if topic is not None:
        sql_filters.append(ProcessedPost.topic == topic)
    if party is not None:
        sql_filters.append(ProcessedPost.target == party)
    if start_date is not None:
        sql_filters.append(cast(RawPost.created_at, Date) >= start_date)
    if end_date is not None:
        sql_filters.append(cast(RawPost.created_at, Date) <= end_date)
    if platform is not None:
        sql_filters.append(RawPost.platform == platform)

    # Step 3: vector similarity search
    distance_expr = ProcessedPost.embedding.cosine_distance(query_vector).label("distance")
    stmt = (
        select(ProcessedPost, RawPost, distance_expr)
        .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
        .where(and_(*sql_filters))
        .order_by(distance_expr)
        .limit(top_n)
    )
    result = await session.execute(stmt)
    rows = result.all()

    if not rows:
        return QAResponse(
            question=question,
            filters_applied=filters_applied,
            retrieved_posts=[],
            metrics=_empty_metrics(),
            insufficient_data=True,
        )

    # Step 4: build label lookups from taxonomy
    topic_label_map = {t.name: t.label for t in taxonomy.topics}
    subtopic_label_map: dict[str, dict[str, str]] = {
        t.name: {st.name: st.label for st in t.subtopics}
        for t in taxonomy.topics
    }

    # Step 5: build retrieved posts and aggregate metrics
    retrieved_posts: list[QAPostItem] = []
    sentiment_counts: dict[str, int] = {"positive": 0, "neutral": 0, "negative": 0}
    subtopic_counts: dict[str, int] = defaultdict(int)

    for pp, rp, distance in rows:
        sentiment = (pp.sentiment or "neutral").lower()
        if sentiment not in ("positive", "neutral", "negative"):
            sentiment = "neutral"
        sentiment_counts[sentiment] += 1

        if pp.subtopic:
            subtopic_counts[pp.subtopic] += 1

        similarity_score = max(0.0, min(1.0, 1.0 - float(distance or 1.0)))
        t_labels = subtopic_label_map.get(pp.topic or "", {})
        retrieved_posts.append(
            QAPostItem(
                id=str(pp.id),
                original_text=rp.original_text,
                platform=rp.platform,
                created_at=rp.created_at.strftime("%Y-%m-%d"),
                sentiment=sentiment,
                topic=pp.topic or "",
                topic_label=topic_label_map.get(pp.topic or "", pp.topic or ""),
                subtopic=pp.subtopic,
                subtopic_label=t_labels.get(pp.subtopic, pp.subtopic) if pp.subtopic else None,
                author=rp.author,
                target=pp.target,
                intensity=pp.intensity,
                similarity_score=similarity_score,
            )
        )

    # Step 6: build top subtopics
    top_subtopics = []
    all_topic_subtopic_labels: dict[str, str] = {}
    for t in taxonomy.topics:
        for st in t.subtopics:
            all_topic_subtopic_labels[st.name] = st.label

    for st_name, count in sorted(subtopic_counts.items(), key=lambda x: x[1], reverse=True)[:TOP_SUBTOPICS_LIMIT]:
        top_subtopics.append(QASubtopicSummary(
            subtopic=st_name,
            subtopic_label=all_topic_subtopic_labels.get(st_name, st_name),
            count=count,
        ))

    metrics = QAMetrics(
        total_retrieved=len(retrieved_posts),
        positive_count=sentiment_counts["positive"],
        neutral_count=sentiment_counts["neutral"],
        negative_count=sentiment_counts["negative"],
        top_subtopics=top_subtopics,
    )

    return QAResponse(
        question=question,
        filters_applied=filters_applied,
        retrieved_posts=retrieved_posts,
        metrics=metrics,
        insufficient_data=False,
    )


def _empty_metrics() -> QAMetrics:
    return QAMetrics(
        total_retrieved=0,
        positive_count=0,
        neutral_count=0,
        negative_count=0,
        top_subtopics=[],
    )
