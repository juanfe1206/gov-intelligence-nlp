"""Twitter file connector - reads posts from a JSONL file for offline-first ingestion."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.connectors.interface import BaseConnector
from app.connectors.schemas import NormalizedPost


class TwitterFileConnector(BaseConnector):
    """Connector that reads Twitter posts from a JSONL file.

    This connector implements "offline-first" fetching by reading from
    a local file instead of making live API calls. It supports incremental
    fetching via checkpointing.

    Twitter JSONL format (one JSON object per line):
    {"id": "1234567890", "full_text": "...", "user": {"screen_name": "..."}, "created_at": "Thu Apr 01 12:00:00 +0000 2021", "lang": "es"}

    Optional ``platform`` on each record (lowercase slug) is copied into
    ``raw_posts.platform`` when it is one of ``ALLOWED_PLATFORMS``;
    otherwise ``twitter`` is used (legacy files omit the field).
    """

    connector_id = "twitter-file"

    #: Slugs allowed on JSONL rows for ``raw_posts.platform`` (DB max 100 chars).
    ALLOWED_PLATFORMS = frozenset({"twitter", "bluesky", "reddit"})

    def __init__(self, file_path: str, after_timestamp: datetime | None = None, max_records: int = 0):
        """Initialize the connector.

        Args:
            file_path: Path to the JSONL file containing Twitter posts
            after_timestamp: Optional cutoff timestamp - records with created_at <= this
                            will be skipped during incremental runs
            max_records: Maximum records to return per fetch(); 0 = no limit.
                        Enforces operational limits to prevent accidental over-collection.
        """
        self._file_path = Path(file_path)
        self._after_timestamp = after_timestamp
        if max_records < 0:
            raise ValueError(f"max_records must be >= 0, got {max_records}")
        self._max_records = max_records
        self._last_seen_at: datetime | None = None

    def fetch(self) -> list[dict[str, Any]]:
        """Read raw posts from the JSONL file.

        Returns:
            List of raw payload dictionaries

        Raises:
            FileNotFoundError: If the file does not exist
        """
        if not self._file_path.exists():
            raise FileNotFoundError(f"JSONL file not found: {self._file_path}")

        records = []

        with open(self._file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip blank lines and comment lines
                if not line or line.startswith("#"):
                    continue

                try:
                    record = json.loads(line)
                    records.append(record)
                except json.JSONDecodeError:
                    # Skip invalid JSON lines
                    continue

        # Filter by timestamp if checkpoint exists (strict > to avoid re-processing checkpoint record)
        if self._after_timestamp is not None:
            records = [
                r for r in records
                if self._parse_twitter_date(r.get("created_at", "")) > self._after_timestamp
            ]

        # Sort by created_at to ensure chronological order before truncation
        # This prevents checkpoint from advancing past unsorted intermediate records.
        # Records with unparseable dates are sorted to the end (epoch=0 fallback).
        def _sort_key(r: dict[str, Any]) -> datetime:
            try:
                return self._parse_twitter_date(r.get("created_at", ""))
            except ValueError:
                return datetime.min.replace(tzinfo=timezone.utc)

        records.sort(key=_sort_key)

        # Enforce operational limit (prevents accidental over-collection)
        if self._max_records > 0:
            records = records[:self._max_records]

        return records

    def normalize(self, raw: dict[str, Any]) -> NormalizedPost | None:
        """Normalize a raw Twitter record to a NormalizedPost.

        Args:
            raw: Raw Twitter API payload dictionary

        Returns:
            NormalizedPost if valid, None if the record should be skipped
        """
        # Extract external_id - try both 'id' and 'id_str'
        external_id = raw.get("id") or raw.get("id_str")
        if not external_id:
            return None

        # Extract text - prefer full_text (untruncated) over text
        text = raw.get("full_text") or raw.get("text", "")
        if not text:
            return None

        # Extract author
        author = raw.get("user", {}).get("screen_name")
        if not author:
            author = raw.get("author")

        # Parse created_at timestamp
        try:
            created_at = self._parse_twitter_date(raw.get("created_at", ""))
        except ValueError:
            return None

        # Track max timestamp for checkpoint
        if self._last_seen_at is None or created_at > self._last_seen_at:
            self._last_seen_at = created_at

        platform = self._platform_from_raw(raw)

        return NormalizedPost(
            source=self.connector_id,
            platform=platform,
            external_id=str(external_id),
            text=text,
            author=author,
            created_at=created_at,
            raw_payload=raw,
        )

    @classmethod
    def _platform_from_raw(cls, raw: dict[str, Any]) -> str:
        """Map JSONL ``platform`` to a DB-safe slug (max 100 chars)."""
        raw_value = raw.get("platform")
        if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
            return "twitter"
        slug = str(raw_value).strip().lower()
        if slug in {"x", "twitter/x"}:
            slug = "twitter"
        if slug in cls.ALLOWED_PLATFORMS:
            return slug[:100]
        return "twitter"

    def checkpoint(self) -> dict[str, Any]:
        """Return the current checkpoint state.

        Returns:
            Dictionary with 'last_seen_at' ISO format timestamp
        """
        return {
            "last_seen_at": self._last_seen_at.isoformat() if self._last_seen_at else None
        }

    @staticmethod
    def _parse_twitter_date(value: str) -> datetime:
        """Parse Twitter API date format to timezone-aware datetime.

        Supports Twitter API format: "Thu Apr 01 12:00:00 +0000 2021"
        Also accepts ISO 8601 format as fallback.

        Args:
            value: Date string to parse

        Returns:
            Timezone-aware datetime in UTC

        Raises:
            ValueError: If the date string cannot be parsed
        """
        if not value or not value.strip():
            raise ValueError("Empty or None date value")

        # Try Twitter API format first: "Thu Apr 01 12:00:00 +0000 2021"
        twitter_format = "%a %b %d %H:%M:%S %z %Y"
        try:
            parsed = datetime.strptime(value, twitter_format)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            pass

        # Fallback: try ISO 8601 formats (existing ingestion logic)
        value_stripped = value.strip()

        # Handle 'Z' suffix
        if value_stripped.endswith("Z"):
            value_stripped = value_stripped[:-1] + "+00:00"

        formats = [
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]

        for fmt in formats:
            try:
                parsed = datetime.strptime(value_stripped, fmt)
                if parsed.tzinfo is None:
                    # Default naive datetimes to UTC (consistent with ingestion service)
                    return parsed.replace(tzinfo=timezone.utc)
                return parsed
            except ValueError:
                continue

        raise ValueError(f"Could not parse date: {value}")
