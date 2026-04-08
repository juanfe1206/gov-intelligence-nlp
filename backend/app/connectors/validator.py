"""Validation and ingestion bridge for normalized posts."""

from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.interface import BaseConnector
from app.connectors.schemas import ConnectorRunSummary, NormalizedPost, ValidationError
from app.ingestion.utils import compute_content_hash
from app.models.raw_post import RawPost


def validate_and_normalize(
    connector: BaseConnector,
    raw_records: list[dict[str, Any]],
    summary: ConnectorRunSummary,
) -> list[NormalizedPost]:
    """Validate and normalize a batch of raw records.

    Iterates through raw records, calling the connector's normalize() method
    for each. Tracks metrics in the summary and collects validation errors.

    Args:
        connector: The connector implementation to use for normalization
        raw_records: List of raw platform payloads
        summary: ConnectorRunSummary to update with metrics

    Returns:
        List of successfully normalized NormalizedPost records
    """
    valid: list[NormalizedPost] = []

    for raw in raw_records:
        summary.fetched += 1
        try:
            result = connector.normalize(raw)
            if result is None:
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationError(
                        field="__record__",
                        message="normalize() returned None",
                        raw_value=raw,
                    )
                )
            else:
                summary.normalized += 1
                valid.append(result)
        except Exception as e:
            summary.rejected += 1
            summary.validation_errors.append(
                ValidationError(
                    field="__record__",
                    message=str(e),
                    raw_value=raw,
                )
            )

    return valid


async def ingest_normalized_posts(
    session: AsyncSession,
    posts: list[NormalizedPost],
    summary: ConnectorRunSummary,
) -> None:
    """Ingest normalized posts into the raw_posts table.

    Maps NormalizedPost records to RawPost rows and inserts them using
    the same deduplication pattern as the CSV ingestion pipeline.

    Args:
        session: Async SQLAlchemy session
        posts: List of normalized posts to ingest
        summary: ConnectorRunSummary to update with inserted/duplicate counts
    """
    for post in posts:
        content_hash = compute_content_hash(post.text)

        stmt = (
            pg_insert(RawPost)
            .values(
                source=post.source,
                platform=post.platform,
                original_text=post.text,
                content_hash=content_hash,
                author=post.author,
                created_at=post.created_at,
                metadata_={
                    "external_id": post.external_id,
                    "raw_payload": post.raw_payload,
                },
            )
            .on_conflict_do_nothing(index_elements=["source", "content_hash"])
            .returning(RawPost.id)
        )

        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            summary.inserted += 1
        else:
            summary.duplicates += 1

    await session.commit()
