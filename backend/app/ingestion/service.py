"""CSV ingestion service for loading raw posts into the database."""

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.ingestion.schemas import IngestionSummary
from app.ingestion.utils import compute_content_hash
from app.models.ingestion_job import IngestionJob
from app.models.raw_post import RawPost

logger = logging.getLogger(__name__)


async def ingest_csv(
    session: AsyncSession,
    csv_path: str | None = None,
    source_name: str | None = None,
) -> IngestionSummary:
    """Ingest a CSV file into raw_posts table.

    Args:
        session: Database session
        csv_path: Path to CSV file (defaults to settings.INGESTION_CSV_PATH)
        source_name: Source identifier (defaults to settings.INGESTION_SOURCE_NAME)

    Returns:
        IngestionSummary with counts and status
    """
    csv_path = csv_path or settings.INGESTION_CSV_PATH
    source_name = source_name or settings.INGESTION_SOURCE_NAME

    started_at = datetime.now(timezone.utc)
    summary = IngestionSummary(
        status="failed",
        source=source_name,
        started_at=started_at,
    )

    try:
        file_path = Path(csv_path)
        if not file_path.exists():
            error_msg = f"CSV file not found: {csv_path}"
            logger.error(error_msg)
            summary.errors.append(error_msg)
            summary.finished_at = datetime.now(timezone.utc)
            await _persist_job(session, summary)
            return summary

        rows = await _read_csv_rows(file_path, summary)
        await _insert_rows(session, rows, source_name, summary)

        summary.status = "completed"
        summary.finished_at = datetime.now(timezone.utc)

    except Exception as e:
        logger.exception("Ingestion failed")
        summary.status = "failed"
        summary.errors.append(f"Unexpected error: {str(e)}")
        summary.finished_at = datetime.now(timezone.utc)
        await session.rollback()

    await _persist_job(session, summary)
    return summary


async def _read_csv_rows(
    file_path: Path,
    summary: IngestionSummary,
) -> list[dict[str, Any]]:
    """Read and parse CSV file, returning valid rows."""
    rows = []

    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
                summary.processed += 1

                # Basic validation
                text = row.get("text", "").strip()
                if not text:
                    summary.skipped += 1
                    summary.errors.append(f"Row {row_num}: missing or empty text")
                    continue

                platform = row.get("platform", "").strip()
                if not platform:
                    platform = settings.INGESTION_PLATFORM_DEFAULT or "unknown"

                author = row.get("author", "").strip() or None

                # Parse created_at timestamp (required field)
                created_at_str = row.get("created_at", "").strip()
                if not created_at_str:
                    summary.skipped += 1
                    summary.errors.append(f"Row {row_num}: missing created_at")
                    continue
                try:
                    created_at = _parse_timestamp(created_at_str)
                except ValueError as e:
                    summary.skipped += 1
                    summary.errors.append(f"Row {row_num}: invalid timestamp '{created_at_str}' - {e}")
                    continue

                # Build metadata from any extra columns
                metadata = {}
                known_cols = {"text", "platform", "author", "created_at"}
                for key, value in row.items():
                    if key is None:
                        if value:
                            metadata["__extra__"] = value
                        continue
                    if key not in known_cols and value:
                        metadata[key] = value

                rows.append({
                    "text": text,
                    "platform": platform,
                    "author": author,
                    "created_at": created_at,
                    "metadata": metadata,
                    "row_num": row_num,
                })

    except Exception as e:
        logger.error(f"Failed to read CSV: {e}")
        summary.errors.append(f"CSV read error: {str(e)}")
        raise

    return rows


async def _insert_rows(
    session: AsyncSession,
    rows: list[dict[str, Any]],
    source_name: str,
    summary: IngestionSummary,
) -> None:
    """Insert validated rows into raw_posts with deduplication."""
    for row_data in rows:
        text = row_data["text"]
        content_hash = compute_content_hash(text)

        try:
            async with session.begin_nested():
                stmt = (
                    pg_insert(RawPost)
                    .values(
                        source=source_name,
                        platform=row_data["platform"],
                        original_text=text,
                        content_hash=content_hash,
                        author=row_data["author"],
                        created_at=row_data["created_at"],
                        metadata=row_data["metadata"] if row_data["metadata"] else None,
                    )
                    .on_conflict_do_nothing(
                        index_elements=["source", "content_hash"],
                    )
                    .returning(RawPost.id)
                )
                result = await session.execute(stmt)
            if result.scalar_one_or_none():
                summary.inserted += 1
            else:
                summary.duplicates += 1
        except Exception as e:
            summary.skipped += 1
            summary.errors.append(f"Row {row_data['row_num']}: insert error - {str(e)}")
            logger.error(f"Failed to insert row: {e}")

    await session.commit()


async def _persist_job(
    session: AsyncSession,
    summary: IngestionSummary,
) -> None:
    """Persist ingestion job record to database."""
    job = IngestionJob(
        source=summary.source,
        status=summary.status,
        started_at=summary.started_at,
        finished_at=summary.finished_at,
        row_count=summary.processed,
        inserted_count=summary.inserted,
        skipped_count=summary.skipped,
        duplicate_count=summary.duplicates,
        error_summary=summary.errors if summary.errors else None,
    )
    session.add(job)
    await session.commit()


def _parse_timestamp(value: str) -> datetime:
    """Parse various timestamp formats.

    Supports ISO 8601 and common variants.
    """
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    formats = [
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]

    # Try each format
    for fmt in formats:
        try:
            parsed = datetime.strptime(value, fmt)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            continue

    raise ValueError(f"Could not parse timestamp: {value}")
