"""Tests for CSV ingestion service."""

import csv
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.schemas import CSVRow, IngestionSummary
from app.ingestion.service import ingest_csv, _read_csv_rows, _parse_timestamp
from app.ingestion.utils import compute_content_hash, normalize_text
from app.models.ingestion_job import IngestionJob
from app.models.raw_post import RawPost


class TestTextNormalization:
    """Tests for text normalization utility."""

    def test_normalize_text_lowercases(self):
        """Test that normalize_text converts to lowercase."""
        assert normalize_text("Hello World") == "hello world"
        assert normalize_text("HELLO") == "hello"

    def test_normalize_text_trims_whitespace(self):
        """Test that normalize_text trims whitespace."""
        assert normalize_text("  hello world  ") == "hello world"
        assert normalize_text("\thello\n") == "hello"

    def test_normalize_text_collapse_whitespace(self):
        """Test that normalize_text collapses multiple whitespace."""
        assert normalize_text("hello    world") == "hello world"
        assert normalize_text("hello\t\t\tworld") == "hello world"
        assert normalize_text("hello\n\nworld") == "hello world"


class TestContentHashing:
    """Tests for content hashing utility."""

    def test_compute_content_hash_returns_hex(self):
        """Test that hash is a valid hex string."""
        hash_value = compute_content_hash("hello world")
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_compute_content_hash_is_deterministic(self):
        """Test that same text produces same hash."""
        hash1 = compute_content_hash("test text")
        hash2 = compute_content_hash("test text")
        assert hash1 == hash2

    def test_compute_content_hash_normalizes_first(self):
        """Test that equivalent texts produce same hash after normalization."""
        hash1 = compute_content_hash("Hello World")
        hash2 = compute_content_hash("  hello world  ")
        hash3 = compute_content_hash("HELLO   WORLD")
        assert hash1 == hash2 == hash3

    def test_compute_content_hash_different_texts_different_hashes(self):
        """Test that different texts produce different hashes."""
        hash1 = compute_content_hash("hello")
        hash2 = compute_content_hash("world")
        assert hash1 != hash2


class TestTimestampParsing:
    """Tests for timestamp parsing."""

    def test_parse_iso8601_with_microseconds(self):
        """Test parsing ISO 8601 with microseconds."""
        dt = _parse_timestamp("2024-01-15T14:30:00.123456")
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15
        assert dt.hour == 14
        assert dt.minute == 30
        assert dt.second == 0
        assert dt.tzinfo == timezone.utc

    def test_parse_iso8601_without_microseconds(self):
        """Test parsing ISO 8601 without microseconds."""
        dt = _parse_timestamp("2024-01-15T14:30:00")
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15
        assert dt.tzinfo == timezone.utc

    def test_parse_date_only(self):
        """Test parsing date only."""
        dt = _parse_timestamp("2024-01-15")
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15
        assert dt.tzinfo == timezone.utc

    def test_parse_iso8601_z_suffix(self):
        """Test parsing ISO 8601 UTC Z suffix."""
        dt = _parse_timestamp("2024-01-15T14:30:00Z")
        assert dt.tzinfo is not None

    def test_parse_invalid_timestamp_raises_error(self):
        """Test that invalid timestamps raise ValueError."""
        with pytest.raises(ValueError):
            _parse_timestamp("not-a-date")
        with pytest.raises(ValueError):
            _parse_timestamp("2024/01/15")


class TestCSVRowValidation:
    """Tests for CSV row validation."""

    def test_valid_row_passes_validation(self):
        """Test that a valid row passes validation."""
        row = CSVRow(text="This is a valid post", platform="twitter", author="user123")
        assert row.text == "This is a valid post"
        assert row.platform == "twitter"

    def test_empty_text_raises_error(self):
        """Test that empty text fails validation."""
        with pytest.raises(ValueError):
            CSVRow(text="", platform="twitter")

    def test_whitespace_only_text_raises_error(self):
        """Test that whitespace-only text fails validation."""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            CSVRow(text="   ", platform="twitter")

    def test_optional_author_can_be_none(self):
        """Test that author is optional."""
        row = CSVRow(text="Valid text", platform="twitter", author=None)
        assert row.author is None


class TestCSVReading:
    """Tests for CSV file reading."""

    def test_read_valid_csv(self):
        """Test reading a valid CSV file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["text", "platform", "author", "created_at"])
            writer.writeheader()
            writer.writerow({
                "text": "Test post",
                "platform": "twitter",
                "author": "user1",
                "created_at": "2024-01-15T10:00:00",
            })
            temp_path = f.name

        from app.ingestion.schemas import IngestionSummary
        summary = IngestionSummary(status="pending", source="test", started_at=datetime.now(timezone.utc))

        # Need to run async function
        import asyncio
        rows = asyncio.run(_read_csv_rows(Path(temp_path), summary))

        assert len(rows) == 1
        assert rows[0]["text"] == "Test post"
        assert rows[0]["platform"] == "twitter"
        assert summary.processed == 1
        assert summary.skipped == 0

        Path(temp_path).unlink()

    def test_skip_empty_text_rows(self):
        """Test that rows with empty text are skipped."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["text", "platform", "created_at"])
            writer.writeheader()
            writer.writerow({"text": "Valid post", "platform": "twitter", "created_at": "2024-01-15T10:00:00"})
            writer.writerow({"text": "", "platform": "twitter", "created_at": "2024-01-15T10:00:00"})
            writer.writerow({"text": "   ", "platform": "twitter", "created_at": "2024-01-15T10:00:00"})
            temp_path = f.name

        from app.ingestion.schemas import IngestionSummary
        summary = IngestionSummary(status="pending", source="test", started_at=datetime.now(timezone.utc))

        import asyncio
        rows = asyncio.run(_read_csv_rows(Path(temp_path), summary))

        assert len(rows) == 1
        assert summary.processed == 3
        assert summary.skipped == 2

        Path(temp_path).unlink()

    def test_handle_missing_platform_default(self, monkeypatch):
        """Test that missing platform uses default."""
        from app import config

        monkeypatch.setattr(config.settings, "INGESTION_PLATFORM_DEFAULT", "facebook")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["text", "platform", "created_at"])
            writer.writeheader()
            writer.writerow({"text": "Post without platform", "platform": "", "created_at": "2024-01-15T10:00:00"})
            temp_path = f.name

        from app.ingestion.schemas import IngestionSummary
        summary = IngestionSummary(status="pending", source="test", started_at=datetime.now(timezone.utc))

        import asyncio
        rows = asyncio.run(_read_csv_rows(Path(temp_path), summary))

        assert len(rows) == 1
        assert rows[0]["platform"] == "facebook"

        Path(temp_path).unlink()


class TestIngestionIntegration:
    """Integration tests for full ingestion flow."""

    @pytest.mark.asyncio
    async def test_ingest_csv_creates_job_record(self, async_db_session: AsyncSession):
        """Test that ingestion creates a job record."""
        # Create temp CSV
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["text", "platform", "created_at"])
            writer.writeheader()
            writer.writerow({"text": "Test post 1", "platform": "twitter", "created_at": "2024-01-15T10:00:00"})
            writer.writerow({"text": "Test post 2", "platform": "facebook", "created_at": "2024-01-15T10:01:00"})
            temp_path = f.name

        # Run ingestion
        summary = await ingest_csv(async_db_session, csv_path=temp_path, source_name="test")

        assert summary.status == "completed"
        assert summary.processed == 2
        assert summary.inserted == 2
        assert summary.source == "test"

        # Cleanup
        Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_ingest_csv_skips_invalid_rows(self, async_db_session: AsyncSession):
        """Test that invalid rows are skipped but valid ones are inserted."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["text", "platform", "created_at"])
            writer.writeheader()
            writer.writerow({"text": "Valid post", "platform": "twitter", "created_at": "2024-01-15T10:00:00"})
            writer.writerow({"text": "", "platform": "twitter", "created_at": "2024-01-15T10:00:00"})  # Invalid
            writer.writerow({"text": "Another valid", "platform": "facebook", "created_at": "2024-01-15T10:01:00"})
            temp_path = f.name

        summary = await ingest_csv(async_db_session, csv_path=temp_path, source_name="test")

        assert summary.status == "completed"
        assert summary.processed == 3
        assert summary.inserted == 2
        assert summary.skipped == 1

        Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_ingest_csv_detects_duplicates(self, async_db_session: AsyncSession):
        """Test that duplicate content is detected and skipped."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["text", "platform", "created_at"])
            writer.writeheader()
            writer.writerow({"text": "Duplicate post", "platform": "twitter", "created_at": "2024-01-15T10:00:00"})
            temp_path = f.name

        # First ingestion
        summary1 = await ingest_csv(async_db_session, csv_path=temp_path, source_name="test")
        assert summary1.inserted == 1
        assert summary1.duplicates == 0

        # Second ingestion of same file
        summary2 = await ingest_csv(async_db_session, csv_path=temp_path, source_name="test")
        assert summary2.inserted == 0
        assert summary2.duplicates == 1

        Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_ingest_csv_file_not_found(self, async_db_session: AsyncSession):
        """Test handling of missing CSV file."""
        summary = await ingest_csv(
            async_db_session,
            csv_path=str(Path(tempfile.gettempdir()) / "missing-ingest-service.csv"),
            source_name="test",
        )

        assert summary.status == "failed"
        assert "not found" in summary.errors[0].lower()

    @pytest.mark.asyncio
    async def test_ingest_creates_raw_posts_with_content_hash(self, async_db_session: AsyncSession):
        """Test that ingested posts have content_hash set."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["text", "platform", "created_at"])
            writer.writeheader()
            writer.writerow({"text": "Test content", "platform": "twitter", "created_at": "2024-01-15T10:00:00"})
            temp_path = f.name

        summary = await ingest_csv(async_db_session, csv_path=temp_path, source_name="test")

        assert summary.inserted == 1

        # Query the database to verify content_hash was set
        from sqlalchemy import select
        result = await async_db_session.execute(
            select(RawPost).where(RawPost.original_text == "Test content")
        )
        post = result.scalar_one()
        assert post.content_hash is not None
        assert len(post.content_hash) == 64

        Path(temp_path).unlink()
