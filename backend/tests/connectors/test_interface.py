"""Tests for connector interface and validation."""

from datetime import datetime, timezone
from typing import Any

import pytest

from app.connectors.interface import BaseConnector
from app.connectors.schemas import ConnectorRunSummary, NormalizedPost, ValidationError
from app.connectors.validator import ingest_normalized_posts, validate_and_normalize


class DummyConnector(BaseConnector):
    """Minimal concrete connector for testing."""

    connector_id = "dummy-connector"

    def __init__(self, posts: list[dict[str, Any]] | None = None):
        """Initialize with sample posts.

        Args:
            posts: Optional list of raw posts to return from fetch()
        """
        self.posts = posts or []

    def fetch(self) -> list[dict[str, Any]]:
        """Return configured posts."""
        return self.posts

    def normalize(self, raw: dict[str, Any]) -> NormalizedPost | None:
        """Normalize a raw post to NormalizedPost.

        Requires 'text' field to be present and non-empty.
        """
        text = raw.get("text", "")
        if not text:
            return None

        return NormalizedPost(
            source=raw.get("source", "dummy"),
            platform=raw.get("platform", "test"),
            external_id=raw.get("external_id", "dummy-id"),
            text=text,
            author=raw.get("author"),
            created_at=raw.get("created_at", datetime.now(timezone.utc)),
            raw_payload=raw,
        )

    def checkpoint(self) -> dict[str, Any]:
        """Return dummy checkpoint state."""
        return {"cursor": "dummy-cursor"}


class TestBaseConnectorInterface:
    """Tests for BaseConnector abstract interface."""

    def test_dummy_connector_instantiates(self):
        """Test that a minimal concrete connector instantiates without error."""
        connector = DummyConnector()
        assert connector is not None

    def test_dummy_connector_has_connector_id(self):
        """Test that connector_id is defined."""
        assert DummyConnector.connector_id == "dummy-connector"

    def test_fetch_returns_list(self):
        """Test that fetch() returns a list."""
        connector = DummyConnector()
        result = connector.fetch()
        assert isinstance(result, list)

    def test_normalize_with_complete_record(self):
        """Test normalize returns ValidNormalizedPost for complete record."""
        connector = DummyConnector()
        raw = {
            "source": "test-source",
            "platform": "test-platform",
            "external_id": "123",
            "text": "Test post content",
            "author": "test-author",
            "created_at": datetime.now(timezone.utc),
        }
        result = connector.normalize(raw)
        assert isinstance(result, NormalizedPost)
        assert result.text == "Test post content"
        assert result.author == "test-author"

    def test_normalize_with_incomplete_record_returns_none(self):
        """Test normalize returns None for missing/empty text."""
        connector = DummyConnector()
        # Missing text
        result = connector.normalize({"platform": "test"})
        assert result is None

        # Empty text
        result = connector.normalize({"text": ""})
        assert result is None


class TestValidateAndNormalize:
    """Tests for validate_and_normalize function."""

    def test_with_valid_records_only(self):
        """Test with all valid records."""
        connector = DummyConnector(
            [
                {
                    "source": "test",
                    "platform": "twitter",
                    "external_id": "1",
                    "text": "Valid post 1",
                },
                {
                    "source": "test",
                    "platform": "twitter",
                    "external_id": "2",
                    "text": "Valid post 2",
                },
            ]
        )
        summary = ConnectorRunSummary(
            connector_id="test-connector",
            started_at=datetime.now(timezone.utc),
        )

        result = validate_and_normalize(connector, connector.fetch(), summary)

        assert len(result) == 2
        assert summary.fetched == 2
        assert summary.normalized == 2
        assert summary.rejected == 0
        assert summary.validation_errors == []

    def test_with_one_valid_one_invalid_record(self):
        """Test AC2: valid + malformed record handling."""
        connector = DummyConnector(
            [
                {
                    "source": "test",
                    "platform": "twitter",
                    "external_id": "1",
                    "text": "Valid post",
                },
                {
                    "source": "test",
                    "platform": "twitter",
                    "external_id": "2",
                    "text": "",  # Invalid - empty
                },
            ]
        )
        summary = ConnectorRunSummary(
            connector_id="test-connector",
            started_at=datetime.now(timezone.utc),
        )

        result = validate_and_normalize(connector, connector.fetch(), summary)

        assert len(result) == 1  # Only valid record returned
        assert summary.normalized == 1
        assert summary.rejected == 1
        assert summary.fetched == 2
        assert len(summary.validation_errors) == 1

    def test_all_invalid_records(self):
        """Test with all invalid records."""
        connector = DummyConnector(
            [
                {"text": ""},
                {"text": "   "},  # Valid per min_length=1
                {"platform": "test"},  # Missing text entirely
            ]
        )
        summary = ConnectorRunSummary(
            connector_id="test-connector",
            started_at=datetime.now(timezone.utc),
        )

        result = validate_and_normalize(connector, connector.fetch(), summary)

        # Only 2 rejected (empty string and missing text), 1 valid (whitespace)
        assert len(result) == 1
        assert summary.fetched == 3
        assert summary.normalized == 1
        assert summary.rejected == 2
        assert len(summary.validation_errors) == 2
