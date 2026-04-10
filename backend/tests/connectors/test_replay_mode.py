"""Tests for replay mode functionality."""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.service import run_connector, get_checkpoint, _upsert_checkpoint
from app.connectors.schemas import ConnectorRunSummary
from app.connectors.twitter_file import TwitterFileConnector
from app.models.connector_checkpoint import ConnectorCheckpoint


class TestReplayMode:
    """Tests for replay mode functionality."""

    @pytest.mark.asyncio
    async def test_replay_runs_same_normalization_path(self, async_db_session: AsyncSession, tmp_path):
        """Test that replay mode runs the same normalization path as live mode."""
        # Create test JSONL file
        test_file = tmp_path / "test.jsonl"
        test_file.write_text(
            '{"id": "1", "full_text": "Replay Post 1", "created_at": "Thu Apr 01 12:00:00 +0000 2021"}\n'
            '{"id": "2", "full_text": "Replay Post 2", "created_at": "Thu Apr 02 12:00:00 +0000 2021"}\n'
        )

        connector = TwitterFileConnector(file_path=str(test_file))

        # Run in replay mode
        summary = await run_connector(async_db_session, connector, mode="replay")

        # Verify mode is set correctly in summary
        assert summary.mode == "replay"
        # Verify same counts as live mode would produce
        assert summary.fetched == 2
        assert summary.normalized == 2
        assert summary.inserted == 2

    @pytest.mark.asyncio
    async def test_replay_does_not_update_checkpoint(self, async_db_session: AsyncSession, tmp_path):
        """Test that replay mode does NOT update the checkpoint."""
        # Create initial checkpoint
        initial_checkpoint = {"last_seen_at": "2021-01-15T10:00:00+00:00"}
        await _upsert_checkpoint(
            async_db_session,
            "twitter-file",
            initial_checkpoint,
        )

        # Create test JSONL file with records newer than checkpoint
        test_file = tmp_path / "test.jsonl"
        test_file.write_text(
            '{"id": "1", "full_text": "Post 1", "created_at": "Thu Apr 01 12:00:00 +0000 2021"}\n'
        )

        # Run in replay mode
        connector = TwitterFileConnector(file_path=str(test_file))
        summary = await run_connector(async_db_session, connector, mode="replay")

        # Verify replay completed successfully
        assert summary.mode == "replay"
        assert summary.fetched == 1

        # Verify checkpoint was NOT updated
        checkpoint = await get_checkpoint(async_db_session, "twitter-file")
        assert checkpoint is not None
        assert checkpoint["last_seen_at"] == initial_checkpoint["last_seen_at"]

    @pytest.mark.asyncio
    async def test_live_run_still_works_after_replay(self, async_db_session: AsyncSession, tmp_path):
        """Test that a live run still uses and updates the checkpoint correctly after a replay."""
        # Create initial checkpoint
        initial_checkpoint = {"last_seen_at": "2021-01-15T10:00:00+00:00"}
        await _upsert_checkpoint(
            async_db_session,
            "twitter-file",
            initial_checkpoint,
        )

        # Create test JSONL file with records at different times
        test_file = tmp_path / "test.jsonl"
        test_file.write_text(
            '{"id": "1", "full_text": "Old post", "created_at": "Thu Jan 01 12:00:00 +0000 2021"}\n'
            '{"id": "2", "full_text": "New post", "created_at": "Thu Apr 01 12:00:00 +0000 2021"}\n'
        )

        # First, run in replay mode (should not update checkpoint)
        connector = TwitterFileConnector(file_path=str(test_file))
        replay_summary = await run_connector(async_db_session, connector, mode="replay")
        assert replay_summary.mode == "replay"
        assert replay_summary.fetched == 2  # Replay mode skips checkpoint, fetches all records

        # Verify checkpoint was NOT updated by replay
        checkpoint = await get_checkpoint(async_db_session, "twitter-file")
        assert checkpoint["last_seen_at"] == initial_checkpoint["last_seen_at"]

        # Now run in live mode (should update checkpoint)
        connector = TwitterFileConnector(file_path=str(test_file))
        live_summary = await run_connector(async_db_session, connector, mode="live")
        assert live_summary.mode == "live"

        # Verify checkpoint WAS updated by live run
        checkpoint = await get_checkpoint(async_db_session, "twitter-file")
        assert checkpoint is not None
        assert checkpoint["last_seen_at"] is not None
        # The new checkpoint should be from the live run (newer than initial)
        assert checkpoint["last_seen_at"] >= initial_checkpoint["last_seen_at"]

    @pytest.mark.asyncio
    async def test_replay_deduplication(self, async_db_session: AsyncSession, tmp_path):
        """Test that replay mode properly handles deduplication when replaying same payload twice."""
        # Create test JSONL file
        test_file = tmp_path / "test.jsonl"
        test_file.write_text(
            '{"id": "1", "full_text": "Unique post", "created_at": "Thu Apr 01 12:00:00 +0000 2021"}\n'
        )

        # First replay run
        connector = TwitterFileConnector(file_path=str(test_file))
        summary1 = await run_connector(async_db_session, connector, mode="replay")
        assert summary1.mode == "replay"
        assert summary1.inserted == 1
        assert summary1.duplicates == 0

        # Second replay run - should be duplicate (same content hash)
        connector = TwitterFileConnector(file_path=str(test_file))
        summary2 = await run_connector(async_db_session, connector, mode="replay")
        assert summary2.mode == "replay"
        assert summary2.inserted == 0
        assert summary2.duplicates == 1

    @pytest.mark.asyncio
    async def test_replay_on_empty_file(self, async_db_session: AsyncSession, tmp_path):
        """Test that replay mode handles an empty file correctly."""
        # Create empty JSONL file
        test_file = tmp_path / "empty.jsonl"
        test_file.write_text("")

        connector = TwitterFileConnector(file_path=str(test_file))
        summary = await run_connector(async_db_session, connector, mode="replay")

        assert summary.mode == "replay"
        assert summary.fetched == 0
        assert summary.inserted == 0

    @pytest.mark.asyncio
    async def test_replay_mode_stored_in_job(self, async_db_session: AsyncSession, tmp_path):
        """Test that replay mode is stored in the IngestionJob record."""
        from app.models.ingestion_job import IngestionJob
        from sqlalchemy import select

        # Create test JSONL file
        test_file = tmp_path / "test.jsonl"
        test_file.write_text(
            '{"id": "1", "full_text": "Replay Post", "created_at": "Thu Apr 01 12:00:00 +0000 2021"}\n'
        )

        connector = TwitterFileConnector(file_path=str(test_file))
        summary = await run_connector(async_db_session, connector, mode="replay")

        # Verify job was created with correct mode
        # Expire the session cache so we see committed data from separate sessions
        async_db_session.expire_all()
        # Query the latest job using SQLAlchemy select
        stmt = select(IngestionJob).order_by(IngestionJob.started_at.desc()).limit(1)
        result = await async_db_session.execute(stmt)
        job = result.scalar_one()

        assert job.mode == "replay"
        assert job.source == "twitter-file"
