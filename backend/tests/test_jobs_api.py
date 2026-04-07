"""Tests for jobs API endpoints."""

from datetime import datetime, timezone
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi import status

from app.db.session import async_session_maker
from app.models.ingestion_job import IngestionJob


class TestGetJobs:
    """Tests for GET /jobs endpoint."""

    def test_get_jobs_empty_list(self, client):
        """Test GET /jobs returns empty list when no jobs exist."""
        response = client.get("/jobs")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["jobs"] == []
        assert data["total"] == 0

    def test_get_jobs_after_ingest(self, client, monkeypatch, tmp_path):
        """Test GET /jobs shows ingest job after ingestion."""
        import csv

        # Create temp CSV
        csv_file = tmp_path / "test.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["text", "platform", "created_at"])
            writer.writeheader()
            writer.writerow({"text": "Test post", "platform": "twitter", "created_at": "2024-01-15T10:00:00"})

        from app import config
        monkeypatch.setattr(config.settings, "INGESTION_CSV_PATH", str(csv_file))

        # Run ingestion
        ingest_response = client.post("/ingest")
        assert ingest_response.status_code == 200

        # Get jobs
        response = client.get("/jobs")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] >= 1
        assert len(data["jobs"]) >= 1

        # Find the ingest job
        ingest_jobs = [j for j in data["jobs"] if j["job_type"] == "ingest"]
        assert len(ingest_jobs) >= 1

        job = ingest_jobs[0]
        assert job["status"] in ("completed", "failed", "partial", "running")
        assert job["source"] == "csv_local"
        assert "started_at" in job

    def test_get_jobs_after_process(self, client):
        """Test GET /jobs shows process job entries."""
        async def create_process_job():
            async with async_session_maker() as session:
                job = IngestionJob(
                    source="nlp_processing",
                    job_type="process",
                    status="completed",
                    started_at=datetime.now(timezone.utc),
                    finished_at=datetime.now(timezone.utc),
                    row_count=5,
                )
                session.add(job)
                await session.commit()

        import asyncio
        asyncio.run(create_process_job())

        # Get jobs
        response = client.get("/jobs")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        process_jobs = [j for j in data["jobs"] if j["job_type"] == "process"]
        assert len(process_jobs) >= 1

    def test_get_jobs_includes_all_fields(self, client):
        """Test that GET /jobs response includes all expected fields."""
        response = client.get("/jobs")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "jobs" in data
        assert "total" in data

    def test_get_jobs_with_limit(self, client):
        """Test GET /jobs respects limit parameter."""
        response = client.get("/jobs?limit=10")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert len(data["jobs"]) <= 10

    def test_get_jobs_limit_validation(self, client):
        """Test that invalid limit values are rejected."""
        # Limit too high
        response = client.get("/jobs?limit=201")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Limit too low
        response = client.get("/jobs?limit=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Negative limit
        response = client.get("/jobs?limit=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestRunningJobStatus:
    """Tests for AC 3: Running job status."""

    def test_running_job_visible_in_list(self, client):
        """Test that a job with status 'running' appears in GET /jobs."""
        # Insert a running job directly via DB
        async def create_running_job():
            async with async_session_maker() as session:
                job = IngestionJob(
                    source="test_source",
                    job_type="ingest",
                    status="running",
                    started_at=datetime.now(timezone.utc),
                )
                session.add(job)
                await session.commit()
                return str(job.id)

        import asyncio
        job_id = asyncio.run(create_running_job())

        # Get jobs
        response = client.get("/jobs")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        jobs_with_id = [j for j in data["jobs"] if j["id"] == job_id]
        assert len(jobs_with_id) == 1

        job = jobs_with_id[0]
        assert job["status"] == "running"
        assert job["finished_at"] is None

    def test_running_job_has_no_finished_at(self, client):
        """Test that running jobs have null finished_at."""
        # Insert a running job
        async def create_running_job():
            async with async_session_maker() as session:
                job = IngestionJob(
                    source="test_running",
                    job_type="process",
                    status="running",
                    started_at=datetime.now(timezone.utc),
                )
                session.add(job)
                await session.commit()
                return str(job.id)

        import asyncio
        job_id = asyncio.run(create_running_job())

        response = client.get("/jobs")
        data = response.json()

        job = next((j for j in data["jobs"] if j["id"] == job_id), None)
        assert job is not None
        assert job["finished_at"] is None


class TestRetryJob:
    """Tests for POST /jobs/{job_id}/retry endpoint."""

    def test_retry_unknown_job_returns_404(self, client):
        """Test retrying unknown job returns 404."""
        random_uuid = str(uuid4())
        response = client.post(f"/jobs/{random_uuid}/retry")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "message" in data["detail"]

    def test_retry_completed_job_returns_400(self, client):
        """Test retrying completed job returns 400."""
        # Insert a completed job
        async def create_completed_job():
            async with async_session_maker() as session:
                job = IngestionJob(
                    source="test_source",
                    job_type="ingest",
                    status="completed",
                    started_at=datetime.now(timezone.utc),
                    finished_at=datetime.now(timezone.utc),
                    row_count=10,
                )
                session.add(job)
                await session.commit()
                return str(job.id)

        import asyncio
        job_id = asyncio.run(create_completed_job())

        response = client.post(f"/jobs/{job_id}/retry")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "completed" in data["detail"]["message"]

    def test_retry_failed_ingest_job(self, client, monkeypatch, tmp_path):
        """Test retrying a failed ingest job creates new job."""
        import csv

        # Create temp CSV
        csv_file = tmp_path / "test_retry.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["text", "platform", "created_at"])
            writer.writeheader()
            writer.writerow({"text": "Retry test", "platform": "twitter", "created_at": "2024-01-15T10:00:00"})

        from app import config
        monkeypatch.setattr(config.settings, "INGESTION_CSV_PATH", str(csv_file))

        # Insert a failed job
        async def create_failed_job():
            async with async_session_maker() as session:
                job = IngestionJob(
                    source="csv_local",
                    job_type="ingest",
                    status="failed",
                    started_at=datetime.now(timezone.utc),
                    finished_at=datetime.now(timezone.utc),
                    row_count=0,
                    error_summary=["CSV file not found"],
                )
                session.add(job)
                await session.commit()
                return str(job.id)

        import asyncio
        job_id = asyncio.run(create_failed_job())

        response = client.post(f"/jobs/{job_id}/retry")
        assert response.status_code == status.HTTP_200_OK

        payload = response.json()
        assert payload["id"] != job_id
        assert payload["job_type"] == "ingest"
        assert payload["source"] == "csv_local"

    def test_retry_failed_process_job(self, client):
        """Test retrying a failed process job."""
        # Insert a failed process job
        async def create_failed_process_job():
            async with async_session_maker() as session:
                job = IngestionJob(
                    source="nlp_processing",
                    job_type="process",
                    status="failed",
                    started_at=datetime.now(timezone.utc),
                    finished_at=datetime.now(timezone.utc),
                    row_count=5,
                    error_summary=["OpenAI API error"],
                )
                session.add(job)
                await session.commit()
                return str(job.id)

        import asyncio
        job_id = asyncio.run(create_failed_process_job())

        with patch("app.api.jobs.retry_job") as mock_retry:
            from types import SimpleNamespace
            mock_retry.return_value = SimpleNamespace(
                id=uuid4(),
                job_type="process",
                status="running",
                source="nlp_processing",
                started_at=datetime.now(timezone.utc),
                finished_at=None,
                row_count=0,
                inserted_count=0,
                skipped_count=0,
                duplicate_count=0,
                error_summary=None,
            )

            response = client.post(f"/jobs/{job_id}/retry")
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["job_type"] == "process"

    def test_retry_partial_job_allowed(self, client):
        """Test that partial jobs can be retried."""
        # Insert a partial job
        async def create_partial_job():
            async with async_session_maker() as session:
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
                return str(job.id)

        import asyncio
        job_id = asyncio.run(create_partial_job())

        with patch("app.api.jobs.retry_job") as mock_retry:
            from types import SimpleNamespace
            mock_retry.return_value = SimpleNamespace(
                id=uuid4(),
                job_type="process",
                status="running",
                source="nlp_processing",
                started_at=datetime.now(timezone.utc),
                finished_at=None,
                row_count=0,
                inserted_count=0,
                skipped_count=0,
                duplicate_count=0,
                error_summary=None,
            )

            response = client.post(f"/jobs/{job_id}/retry")
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["job_type"] == "process"


class TestJobResponseSchema:
    """Tests for job response schema validation."""

    def test_job_response_includes_all_fields(self, client):
        """Test that job response includes all expected fields."""
        # Insert a job with all fields populated
        async def create_full_job():
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
                    error_summary=["Row 5: missing text"],
                )
                session.add(job)
                await session.commit()
                return str(job.id)

        import asyncio
        job_id = asyncio.run(create_full_job())

        response = client.get("/jobs")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        job = next((j for j in data["jobs"] if j["id"] == job_id), None)
        assert job is not None

        # Verify all expected fields
        expected_fields = [
            "id", "job_type", "status", "source", "started_at",
            "finished_at", "row_count", "inserted_count",
            "skipped_count", "duplicate_count", "error_summary",
        ]
        for field in expected_fields:
            assert field in job, f"Missing field: {field}"

    def test_job_response_field_types(self, client):
        """Test that job response fields have correct types."""
        response = client.get("/jobs")
        data = response.json()

        for job in data["jobs"]:
            assert isinstance(job["id"], str)
            assert isinstance(job["job_type"], str)
            assert isinstance(job["status"], str)
            assert isinstance(job["source"], str)
            assert isinstance(job["row_count"], int)
            assert isinstance(job["inserted_count"], int)
            assert isinstance(job["skipped_count"], int)
            assert isinstance(job["duplicate_count"], int)

            if job["error_summary"] is not None:
                assert isinstance(job["error_summary"], list)


class TestJobOrdering:
    """Tests for job ordering in responses."""

    def test_jobs_ordered_by_started_at_desc(self, client):
        """Test that jobs are ordered by started_at descending (most recent first)."""
        # Insert multiple jobs with different timestamps
        async def create_jobs():
            async with async_session_maker() as session:
                jobs = []
                for i in range(3):
                    job = IngestionJob(
                        source=f"source_{i}",
                        job_type="ingest",
                        status="completed",
                        started_at=datetime(2024, 1, 15 - i, 10, 0, 0, tzinfo=timezone.utc),
                        finished_at=datetime(2024, 1, 15 - i, 10, 1, 0, tzinfo=timezone.utc),
                    )
                    jobs.append(job)
                session.add_all(jobs)
                await session.commit()
                return [str(j.id) for j in jobs]

        import asyncio
        job_ids = asyncio.run(create_jobs())

        response = client.get("/jobs")
        data = response.json()

        # Find our created jobs in response
        response_job_ids = [j["id"] for j in data["jobs"] if j["id"] in job_ids]

        assert len(response_job_ids) == 3
        assert response_job_ids == job_ids


class TestRetryPreservesOriginalJob:
    """Tests that retry preserves original failed job record."""

    def test_retry_creates_new_job_preserves_original(self, client, monkeypatch, tmp_path):
        """Test that retry creates new job while preserving original."""
        import csv

        # Create temp CSV
        csv_file = tmp_path / "test_preserve.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["text", "platform", "created_at"])
            writer.writeheader()
            writer.writerow({"text": "Preserve test", "platform": "twitter", "created_at": "2024-01-15T10:00:00"})

        from app import config
        monkeypatch.setattr(config.settings, "INGESTION_CSV_PATH", str(csv_file))

        # Insert a failed job
        async def create_failed_job():
            async with async_session_maker() as session:
                job = IngestionJob(
                    source="csv_local",
                    job_type="ingest",
                    status="failed",
                    started_at=datetime.now(timezone.utc),
                    finished_at=datetime.now(timezone.utc),
                    error_summary=["Original error"],
                )
                session.add(job)
                await session.commit()
                return str(job.id)

        import asyncio
        original_job_id = asyncio.run(create_failed_job())

        # Retry
        response = client.post(f"/jobs/{original_job_id}/retry")

        # Original job should still exist with failed status
        async def check_original_job():
            async with async_session_maker() as session:
                from sqlalchemy import select
                result = await session.execute(select(IngestionJob).where(IngestionJob.id == UUID(original_job_id)))
                job = result.scalar_one_or_none()
                return job.status if job else None

        original_status = asyncio.run(check_original_job())
        assert original_status == "failed"
