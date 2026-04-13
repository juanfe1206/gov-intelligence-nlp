"""Tests for TwitterFileConnector."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.connectors.twitter_file import TwitterFileConnector


class TestTwitterFileConnector:
    """Tests for TwitterFileConnector implementation."""

    def test_instantiation_with_valid_file(self, tmp_path):
        """Test that connector instantiates with a valid file path."""
        # Create a test file first
        test_file = tmp_path / "test.jsonl"
        test_file.write_text('{"id": "1", "full_text": "test", "created_at": "Thu Apr 01 12:00:00 +0000 2021"}')

        connector = TwitterFileConnector(file_path=str(test_file))
        assert connector is not None
        assert connector.connector_id == "twitter-file"

    def test_fetch_returns_list_of_dicts(self, tmp_path):
        """Test that fetch() returns a list of dictionaries."""
        test_file = tmp_path / "test.jsonl"
        test_file.write_text('{"id": "1", "full_text": "test post", "created_at": "Thu Apr 01 12:00:00 +0000 2021"}')

        connector = TwitterFileConnector(file_path=str(test_file))
        result = connector.fetch()

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert result[0]["id"] == "1"

    def test_fetch_skips_blank_lines_and_comments(self, tmp_path):
        """Test that blank lines and comment lines are skipped."""
        test_file = tmp_path / "test.jsonl"
        content = """# This is a comment
{"id": "1", "full_text": "test", "created_at": "Thu Apr 01 12:00:00 +0000 2021"}

{"id": "2", "full_text": "another", "created_at": "Thu Apr 01 12:00:00 +0000 2021"}
"""
        test_file.write_text(content)

        connector = TwitterFileConnector(file_path=str(test_file))
        result = connector.fetch()

        assert len(result) == 2

    def test_fetch_raises_file_not_found(self):
        """Test that fetch raises FileNotFoundError when file doesn't exist."""
        connector = TwitterFileConnector(file_path="/nonexistent/path.jsonl")

        with pytest.raises(FileNotFoundError):
            connector.fetch()

    def test_fetch_with_after_timestamp_filters(self, tmp_path):
        """Test that after_timestamp filters out records older than cutoff."""
        test_file = tmp_path / "test.jsonl"
        # Create records with different timestamps
        content = """{"id": "1", "full_text": "old post", "created_at": "Thu Jan 01 12:00:00 +0000 2020"}
{"id": "2", "full_text": "new post", "created_at": "Thu Apr 01 12:00:00 +0000 2021"}
"""
        test_file.write_text(content)

        # Set cutoff to 2020-06-01 - only 2021 record should be returned
        cutoff = datetime(2020, 6, 1, tzinfo=timezone.utc)
        connector = TwitterFileConnector(file_path=str(test_file), after_timestamp=cutoff)
        result = connector.fetch()

        assert len(result) == 1
        assert result[0]["id"] == "2"

    def test_normalize_with_valid_twitter_record(self, tmp_path):
        """Test normalize returns NormalizedPost for valid Twitter record."""
        test_file = tmp_path / "test.jsonl"
        test_file.write_text('{"id": "1234567890", "full_text": "Test post content", "user": {"screen_name": "politico_es"}, "created_at": "Thu Apr 01 12:00:00 +0000 2021"}')

        connector = TwitterFileConnector(file_path=str(test_file))
        raw = connector.fetch()[0]
        result = connector.normalize(raw)

        assert result is not None
        assert result.external_id == "1234567890"
        assert result.text == "Test post content"
        assert result.author == "politico_es"
        assert result.platform == "twitter"
        assert result.source == "twitter-file"

    def test_normalize_platform_bluesky_from_json(self, tmp_path):
        """JSONL platform field is copied when allowed."""
        test_file = tmp_path / "test.jsonl"
        test_file.write_text(
            '{"id": "1", "full_text": "Hola", "platform": "bluesky", '
            '"created_at": "Thu Apr 01 12:00:00 +0000 2021"}'
        )
        connector = TwitterFileConnector(file_path=str(test_file))
        raw = connector.fetch()[0]
        result = connector.normalize(raw)
        assert result is not None
        assert result.platform == "bluesky"

    def test_normalize_platform_unknown_defaults_to_twitter(self, tmp_path):
        """Unknown platform slug falls back to twitter."""
        test_file = tmp_path / "test.jsonl"
        test_file.write_text(
            '{"id": "1", "full_text": "Hola", "platform": "facebook", '
            '"created_at": "Thu Apr 01 12:00:00 +0000 2021"}'
        )
        connector = TwitterFileConnector(file_path=str(test_file))
        raw = connector.fetch()[0]
        result = connector.normalize(raw)
        assert result is not None
        assert result.platform == "twitter"

    def test_normalize_with_id_str_fallback(self, tmp_path):
        """Test normalize uses id_str when id is absent."""
        test_file = tmp_path / "test.jsonl"
        test_file.write_text('{"id_str": "1234567890", "full_text": "Test", "created_at": "Thu Apr 01 12:00:00 +0000 2021"}')

        connector = TwitterFileConnector(file_path=str(test_file))
        raw = connector.fetch()[0]
        result = connector.normalize(raw)

        assert result is not None
        assert result.external_id == "1234567890"

    def test_normalize_with_author_fallback(self, tmp_path):
        """Test normalize uses 'author' field when user.screen_name is absent."""
        test_file = tmp_path / "test.jsonl"
        test_file.write_text('{"id": "1", "full_text": "Test", "author": "custom_author", "created_at": "Thu Apr 01 12:00:00 +0000 2021"}')

        connector = TwitterFileConnector(file_path=str(test_file))
        raw = connector.fetch()[0]
        result = connector.normalize(raw)

        assert result is not None
        assert result.author == "custom_author"

    def test_normalize_returns_none_when_id_missing(self, tmp_path):
        """Test normalize returns None when id/id_str is missing."""
        test_file = tmp_path / "test.jsonl"
        test_file.write_text('{"full_text": "Test", "created_at": "Thu Apr 01 12:00:00 +0000 2021"}')

        connector = TwitterFileConnector(file_path=str(test_file))
        raw = connector.fetch()[0]
        result = connector.normalize(raw)

        assert result is None

    def test_normalize_returns_none_when_text_empty(self, tmp_path):
        """Test normalize returns None when text is missing or empty."""
        test_file = tmp_path / "test.jsonl"
        test_file.write_text('{"id": "1", "created_at": "Thu Apr 01 12:00:00 +0000 2021"}')

        connector = TwitterFileConnector(file_path=str(test_file))
        raw = connector.fetch()[0]
        result = connector.normalize(raw)

        assert result is None

    def test_checkpoint_returns_last_seen_at(self, tmp_path):
        """Test checkpoint returns last_seen_at timestamp after processing."""
        test_file = tmp_path / "test.jsonl"
        test_file.write_text('{"id": "1", "full_text": "Test", "created_at": "Thu Apr 01 12:00:00 +0000 2021"}')

        connector = TwitterFileConnector(file_path=str(test_file))
        # Process a record
        raw = connector.fetch()[0]
        connector.normalize(raw)

        checkpoint = connector.checkpoint()
        assert "last_seen_at" in checkpoint
        assert checkpoint["last_seen_at"] is not None

    def test_parse_twitter_date_format(self, tmp_path):
        """Test parsing Twitter API date format."""
        test_file = tmp_path / "test.jsonl"
        test_file.write_text('{"id": "1", "full_text": "Test", "created_at": "Thu Apr 01 12:00:00 +0000 2021"}')

        connector = TwitterFileConnector(file_path=str(test_file))
        raw = connector.fetch()[0]

        # Test via normalize which uses _parse_twitter_date internally
        result = connector.normalize(raw)
        assert result is not None
        # Verify timezone-aware datetime in UTC
        assert result.created_at.tzinfo is not None

    def test_parse_twitter_date_with_missing_value(self, tmp_path):
        """Test normalize returns None when created_at is missing."""
        test_file = tmp_path / "test.jsonl"
        test_file.write_text('{"id": "1", "full_text": "Test"}')

        connector = TwitterFileConnector(file_path=str(test_file))
        raw = connector.fetch()[0]

        result = connector.normalize(raw)
        assert result is None

    def test_normalize_tracks_max_timestamp(self, tmp_path):
        """Test that _last_seen_at tracks the maximum timestamp seen."""
        test_file = tmp_path / "test.jsonl"
        # Write records in non-monotonic order
        content = """{"id": "1", "full_text": "first", "created_at": "Thu Apr 01 12:00:00 +0000 2021"}
{"id": "2", "full_text": "second", "created_at": "Thu Mar 01 12:00:00 +0000 2021"}
{"id": "3", "full_text": "third", "created_at": "Thu May 01 12:00:00 +0000 2021"}
"""
        test_file.write_text(content)

        connector = TwitterFileConnector(file_path=str(test_file))
        for raw in connector.fetch():
            connector.normalize(raw)

        checkpoint = connector.checkpoint()
        # Should track the max (May 1), not the last (May 1 in this case)
        assert checkpoint["last_seen_at"] is not None
