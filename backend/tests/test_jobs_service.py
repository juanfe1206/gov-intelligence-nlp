"""Tests for jobs service layer."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.session import async_session_maker
from app.jobs.service import get_job_by_id, list_jobs, retry_job
from app.models.ingestion_job import IngestionJob


class TestListJobs:
    """Tests for list_jobs service function."""

    @pytest.mark.asyncio
    async def test_list_jobs_returns_empty_when_no_jobs(self):
        """Test list_jobs returns empty list when no jobs exist."""
        async with async_session_maker() as session:
            jobs, total = await list_jobs(session, limit=50)
            assert jobs == []
            assert total == 0

    @pytest.mark.asyncio
    async def test_list_jobs_returns_jobs_with_total_count(self):
        """Test list_jobs returns jobs and total count."""
        async with async_session_maker() as session:
            # Create a job
            job = IngestionJob(
                source="test_source",
                job_type="ingest",
                status="completed",
                started_at=datetime.now(timezone.utc),
            )
            session.add(job)
            await session.commit()

            # List jobs
            jobs, total = await list_jobs(session, limit=50)
            assert len(jobs) >= 1
            assert total >= 1

    @pytest.mark.asyncio
    async def test_list_jobs_respects_limit(self):
        """Test list_jobs respects the limit parameter."""
        async with async_session_maker() as session:
            # Create multiple jobs
            for i in range(5):
                job = IngestionJob(
                    source=f"source_{i}",
                    job_type="ingest",
                    status="completed",
                    started_at=datetime.now(timezone.utc),
                )
                session.add(job)
            await session.commit()

            # List with limit
            jobs, total = await list_jobs(session, limit=3)
            assert len(jobs) <= 3
            assert total >= 5

    @pytest.mark.asyncio
    async def test_list_jobs_ordered_by_started_at_desc(self):
        """Test list_jobs orders by started_at descending."""
        async with async_session_maker() as session:
            # Create jobs with specific timestamps
            job1 = IngestionJob(
                source="source_1",
                job_type="ingest",
                status="completed",
                started_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            )
            job2 = IngestionJob(
                source="source_2",
                job_type="ingest",
                status="completed",
                started_at=datetime(2024, 1, 16, 10, 0, 0, tzinfo=timezone.utc),
            )
            session.add_all([job1, job2])
            await session.commit()

            # List jobs
            jobs, _ = await list_jobs(session, limit=50)

            # Find our jobs in the list
            job1_idx = next((i for i, j in enumerate(jobs) if j.source == "source_1"), None)
            job2_idx = next((i for i, j in enumerate(jobs) if j.source == "source_2"), None)

            if job1_idx is not None and job2_idx is not None:
                # job2 (Jan 16) should come before job1 (Jan 15) in desc order
                assert job2_idx < job1_idx


class TestGetJobById:
    """Tests for get_job_by_id service function."""

    @pytest.mark.asyncio
    async def test_get_job_by_id_returns_job(self):
        """Test get_job_by_id returns job when found."""
        async with async_session_maker() as session:
            # Create a job
            job = IngestionJob(
                source="test_source",
                job_type="ingest",
                status="completed",
                started_at=datetime.now(timezone.utc),
            )
            session.add(job)
            await session.commit()

            job_id = str(job.id)

            # Get job by ID
            found_job = await get_job_by_id(session, job_id)
            assert found_job is not None
            assert str(found_job.id) == job_id
            assert found_job.source == "test_source"

    @pytest.mark.asyncio
    async def test_get_job_by_id_returns_none_for_unknown(self):
        """Test get_job_by_id returns None for unknown job."""
        async with async_session_maker() as session:
            random_id = str(uuid4())
            found_job = await get_job_by_id(session, random_id)
            assert found_job is None

    @pytest.mark.asyncio
    async def test_get_job_by_id_returns_none_for_invalid_uuid(self):
        """Test get_job_by_id returns None for invalid UUID."""
        async with async_session_maker() as session:
            found_job = await get_job_by_id(session, "not-a-uuid")
            assert found_job is None


class TestRetryJob:
    """Tests for retry_job service function."""

    @pytest.mark.asyncio
    async def test_retry_job_returns_none_for_unknown_job(self):
        """Test retry_job returns None for unknown job."""
        async with async_session_maker() as session:
            random_id = str(uuid4())
            result = await retry_job(session, random_id, {})
            assert result is None

    @pytest.mark.asyncio
    async def test_retry_job_raises_for_non_retryable_status(self):
        """Test retry_job raises ValueError for non-retryable status."""
        async with async_session_maker() as session:
            # Create a completed job
            job = IngestionJob(
                source="test_source",
                job_type="ingest",
                status="completed",
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
            )
            session.add(job)
            await session.commit()

            job_id = str(job.id)

            # Attempt retry
            with pytest.raises(ValueError) as exc_info:
                await retry_job(session, job_id, {})

            assert "completed" in str(exc_info.value)
            assert "cannot retry" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_retry_job_accepts_failed_status(self):
        """Test retry_job accepts failed status."""
        async with async_session_maker() as session:
            # Create a failed job
            job = IngestionJob(
                source="test_source",
                job_type="ingest",
                status="failed",
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
                error_summary=["Original error"],
            )
            session.add(job)
            await session.commit()

            job_id = str(job.id)

            # Should not raise ValueError
            # Note: Actual retry may fail due to missing CSV, but should not get ValueError for status
            try:
                await retry_job(session, job_id, {})
            except ValueError as e:
                assert "cannot retry" not in str(e).lower()

    @pytest.mark.asyncio
    async def test_retry_job_accepts_partial_status(self):
        """Test retry_job accepts partial status."""
        async with async_session_maker() as session:
            # Create a partial job
            job = IngestionJob(
                source="nlp_processing",
                job_type="process",
                status="partial",
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
                row_count=10,
                inserted_count=5,
                duplicate_count=5,
            )
            session.add(job)
            await session.commit()

            job_id = str(job.id)

            # Should not raise ValueError about status
            try:
                await retry_job(session, job_id, {})
            except ValueError as e:
                assert "cannot retry" not in str(e).lower()


class TestJobModel:
    """Tests for IngestionJob model."""

    @pytest.mark.asyncio
    async def test_job_model_has_all_fields(self):
        """Test IngestionJob model has expected fields."""
        async with async_session_maker() as session:
            job = IngestionJob(
                source="test_source",
                job_type="ingest",
                status="completed",
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
                row_count=100,
                inserted_count=95,
                skipped_count=3,
                duplicate_count=2,
                error_summary=["Error 1", "Error 2"],
            )
            session.add(job)
            await session.commit()

            # Retrieve and verify
            result = await session.execute(select(IngestionJob).where(IngestionJob.id == job.id))
            retrieved = result.scalar_one()

            assert retrieved.source == "test_source"
            assert retrieved.job_type == "ingest"
            assert retrieved.status == "completed"
            assert retrieved.row_count == 100
            assert retrieved.inserted_count == 95
            assert retrieved.skipped_count == 3
            assert retrieved.duplicate_count == 2
            assert retrieved.error_summary == ["Error 1", "Error 2"]

    @pytest.mark.asyncio
    async def test_job_model_default_values(self):
        """Test IngestionJob model default values."""
        async with async_session_maker() as session:
            job = IngestionJob(
                source="test_source",
                status="running",
                started_at=datetime.now(timezone.utc),
            )
            session.add(job)
            await session.commit()

            # Retrieve and verify defaults
            result = await session.execute(select(IngestionJob).where(IngestionJob.id == job.id))
            retrieved = result.scalar_one()

            assert retrieved.job_type == "ingest"  # default
            assert retrieved.row_count == 0  # default
            assert retrieved.inserted_count == 0  # default
            assert retrieved.skipped_count == 0  # default
            assert retrieved.duplicate_count == 0  # default
