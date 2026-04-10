"""Tests for connector service layer."""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.service import run_connector, get_checkpoint, _upsert_checkpoint
from app.connectors.schemas import ConnectorRunSummary
from app.connectors.twitter_file import TwitterFileConnector
from app.models.connector_checkpoint import ConnectorCheckpoint


class TestGetCheckpoint:
    """Tests for get_checkpoint function."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_checkpoint(self, async_db_session: AsyncSession):
        """Test that None is returned when no checkpoint exists."""
        result = await get_checkpoint(async_db_session, "nonexistent-connector")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_checkpoint_data_when_exists(self, async_db_session: AsyncSession):
        """Test that checkpoint data is returned when it exists."""
        # First insert a checkpoint
        checkpoint = ConnectorCheckpoint(
            connector_id="test-connector",
            checkpoint_data={"last_seen_at": "2024-01-15T10:00:00+00:00"},
            updated_at=datetime.now(timezone.utc),
        )
        async_db_session.add(checkpoint)
        await async_db_session.commit()

        result = await get_checkpoint(async_db_session, "test-connector")
        assert result is not None
        assert result["last_seen_at"] == "2024-01-15T10:00:00+00:00"


class TestUpsertCheckpoint:
    """Tests for _upsert_checkpoint function."""

    @pytest.mark.asyncio
    async def test_inserts_new_checkpoint(self, async_db_session: AsyncSession):
        """Test that a new checkpoint is inserted."""
        await _upsert_checkpoint(
            async_db_session,
            "new-connector",
            {"last_seen_at": "2024-01-15T10:00:00+00:00"},
        )

        # Verify it was inserted
        stmt = select(ConnectorCheckpoint).where(
            ConnectorCheckpoint.connector_id == "new-connector"
        )
        result = await async_db_session.execute(stmt)
        checkpoint = result.scalar_one()
        assert checkpoint.connector_id == "new-connector"
        assert checkpoint.checkpoint_data["last_seen_at"] == "2024-01-15T10:00:00+00:00"

    @pytest.mark.asyncio
    async def test_updates_existing_checkpoint(self, async_db_session: AsyncSession):
        """Test that existing checkpoint is updated."""
        # First insert
        await _upsert_checkpoint(
            async_db_session,
            "update-test-connector",
            {"last_seen_at": "2024-01-15T10:00:00+00:00"},
        )

        # Update with new data
        await _upsert_checkpoint(
            async_db_session,
            "update-test-connector",
            {"last_seen_at": "2024-06-01T12:00:00+00:00"},
        )

        # Verify it was updated
        stmt = select(ConnectorCheckpoint).where(
            ConnectorCheckpoint.connector_id == "update-test-connector"
        )
        result = await async_db_session.execute(stmt)
        checkpoint = result.scalar_one()
        assert checkpoint.checkpoint_data["last_seen_at"] == "2024-06-01T12:00:00+00:00"


class TestRunConnector:
    """Tests for run_connector function."""

    @pytest.mark.asyncio
    async def test_full_run_no_prior_checkpoint(self, async_db_session: AsyncSession, tmp_path):
        """Test full run with no prior checkpoint processes all records."""
        # Create test JSONL file
        test_file = tmp_path / "test.jsonl"
        test_file.write_text(
            '{"id": "1", "full_text": "Post 1", "created_at": "Thu Apr 01 12:00:00 +0000 2021"}\n'
            '{"id": "2", "full_text": "Post 2", "created_at": "Thu Apr 02 12:00:00 +0000 2021"}\n'
        )

        connector = TwitterFileConnector(file_path=str(test_file))

        # Run the connector
        summary = await run_connector(async_db_session, connector)

        assert summary.connector_id == "twitter-file"
        assert summary.mode == "live"
        assert summary.fetched == 2
        assert summary.normalized == 2
        assert summary.inserted == 2

        # Verify checkpoint was saved
        checkpoint = await get_checkpoint(async_db_session, "twitter-file")
        assert checkpoint is not None
        assert checkpoint["last_seen_at"] is not None

    @pytest.mark.asyncio
    async def test_incremental_run_with_prior_checkpoint(self, async_db_session: AsyncSession, tmp_path):
        """Test incremental run with prior checkpoint."""
        # Create test JSONL file with records at different times
        test_file = tmp_path / "test.jsonl"
        test_file.write_text(
            '{"id": "1", "full_text": "Old post", "created_at": "Thu Jan 01 12:00:00 +0000 2021"}\n'
            '{"id": "2", "full_text": "New post", "created_at": "Thu Apr 01 12:00:00 +0000 2021"}\n'
        )

        # Save initial checkpoint with 2021-02-01 cutoff
        await _upsert_checkpoint(
            async_db_session,
            "twitter-file",
            {"last_seen_at": "2021-02-01T00:00:00+00:00"},
        )

        # Run the connector
        connector = TwitterFileConnector(file_path=str(test_file))
        summary = await run_connector(async_db_session, connector)

        # Only the "New post" (April 2021) should be processed
        assert summary.fetched == 1
        assert summary.normalized == 1
        assert summary.inserted == 1

    @pytest.mark.asyncio
    async def test_duplicate_records_are_skipped(self, async_db_session: AsyncSession, tmp_path):
        """Test that duplicate records are detected and not re-inserted."""
        # Create test JSONL file
        test_file = tmp_path / "test.jsonl"
        test_file.write_text(
            '{"id": "1", "full_text": "Unique post", "created_at": "Thu Apr 01 12:00:00 +0000 2021"}\n'
        )

        # First run
        connector = TwitterFileConnector(file_path=str(test_file))
        summary1 = await run_connector(async_db_session, connector)
        assert summary1.inserted == 1
        assert summary1.duplicates == 0

        # Clear checkpoint so second run fetches the same record again
        # This tests DB-level deduplication via content_hash unique constraint
        from sqlalchemy import delete
        from app.models.connector_checkpoint import ConnectorCheckpoint
        await async_db_session.execute(
            delete(ConnectorCheckpoint).where(
                ConnectorCheckpoint.connector_id == "twitter-file"
            )
        )
        await async_db_session.commit()

        # Second run - should fetch same record but detect as duplicate at DB level
        connector = TwitterFileConnector(file_path=str(test_file))
        summary2 = await run_connector(async_db_session, connector)
        assert summary2.inserted == 0
        assert summary2.duplicates == 1
