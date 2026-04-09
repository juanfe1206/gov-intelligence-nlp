"""Tests for connector run observability, retry, and failure taxonomy."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.service import run_connector
from app.connectors.interface import BaseConnector
from app.connectors.errors import (
    ConnectorError,
    AuthError,
    RateLimitError,
    UpstreamUnavailableError,
    RETRYABLE_CATEGORIES,
)
from app.connectors.schemas import NormalizedPost
from app.models.ingestion_job import IngestionJob


class MockConnector(BaseConnector):
    """Mock connector for testing that can be configured with side effects."""

    connector_id = "mock-connector"

    def __init__(self, fetch_side_effects: list, checkpoint_data: dict | None = None):
        """Initialize mock connector.

        Args:
            fetch_side_effects: List of values/exceptions to return/raise on each fetch() call
            checkpoint_data: Optional checkpoint data to return from checkpoint()
        """
        self._effects = iter(fetch_side_effects)
        self._checkpoint_data = checkpoint_data or {}
        self._after_timestamp = None
        self.fetch_call_count = 0

    def fetch(self):
        """Fetch with configured side effects."""
        self.fetch_call_count += 1
        effect = next(self._effects)
        if isinstance(effect, Exception):
            raise effect
        return effect

    def normalize(self, raw: dict) -> NormalizedPost:
        """Normalize a raw record."""
        return NormalizedPost(
            source="mock-connector",
            platform="test",
            external_id=raw["id"],
            text=raw["text"],
            created_at=datetime.now(timezone.utc),
        )

    def checkpoint(self) -> dict:
        """Return checkpoint data."""
        return self._checkpoint_data


class TestConnectorErrorTaxonomy:
    """Tests for the connector error taxonomy."""

    def test_retryable_categories(self):
        """Test that RETRYABLE_CATEGORIES contains expected values."""
        assert "rate_limit" in RETRYABLE_CATEGORIES
        assert "upstream_unavailable" in RETRYABLE_CATEGORIES
        assert "auth_error" not in RETRYABLE_CATEGORIES

    def test_connector_error_default_category(self):
        """Test that base ConnectorError has 'unknown' category."""
        error = ConnectorError("test message")
        assert error.category == "unknown"

    def test_connector_error_explicit_category(self):
        """Test that ConnectorError can override category."""
        error = ConnectorError("test message", category="custom_error")
        assert error.category == "custom_error"

    def test_auth_error_category(self):
        """Test that AuthError has auth_error category."""
        error = AuthError("invalid credentials")
        assert error.category == "auth_error"
        assert error.category not in RETRYABLE_CATEGORIES

    def test_rate_limit_error_category(self):
        """Test that RateLimitError has rate_limit category."""
        error = RateLimitError("rate limit exceeded")
        assert error.category == "rate_limit"
        assert error.category in RETRYABLE_CATEGORIES

    def test_upstream_unavailable_error_category(self):
        """Test that UpstreamUnavailableError has upstream_unavailable category."""
        error = UpstreamUnavailableError("service unavailable")
        assert error.category == "upstream_unavailable"
        assert error.category in RETRYABLE_CATEGORIES


class TestConnectorObservability:
    """Tests for connector run observability features."""

    @pytest.mark.asyncio
    async def test_normalized_count_persisted(self, async_db_session: AsyncSession):
        """Test that normalized_count is persisted in job record."""
        # Create mock records: 3 raw, 2 valid (normalized), 1 invalid (rejected)
        raw_records = [
            {"id": "1", "text": "Valid post 1"},
            {"id": "2", "text": "Valid post 2"},
            {"id": "3", "text": ""},  # Will be rejected by validator (empty text)
        ]

        connector = MockConnector([raw_records])
        summary = await run_connector(async_db_session, connector, mode="live")

        # Verify summary counts
        assert summary.fetched == 3
        assert summary.normalized == 2  # Only 2 valid records

        # Query job record
        async_db_session.expire_all()
        stmt = select(IngestionJob).order_by(IngestionJob.started_at.desc()).limit(1)
        result = await async_db_session.execute(stmt)
        job = result.scalar_one()

        assert job.normalized_count == 2
        assert job.row_count == 3

    @pytest.mark.asyncio
    async def test_failure_category_on_non_retryable_error(self, async_db_session: AsyncSession):
        """Test that non-retryable errors (AuthError) fail immediately with correct category."""
        connector = MockConnector([AuthError("invalid token")])

        with pytest.raises(AuthError):
            await run_connector(async_db_session, connector, mode="live")

        # Verify job was created with correct failure category
        async_db_session.expire_all()
        stmt = select(IngestionJob).order_by(IngestionJob.started_at.desc()).limit(1)
        result = await async_db_session.execute(stmt)
        job = result.scalar_one()

        assert job.status == "failed"
        assert job.failure_category == "auth_error"
        # Verify only one fetch attempt (no retry)
        assert connector.fetch_call_count == 1

    @pytest.mark.asyncio
    async def test_failure_category_on_retryable_error_exhausted(self, async_db_session: AsyncSession):
        """Test that retryable errors (RateLimitError) retry and fail with correct category."""
        # Raise RateLimitError on all attempts (exhaust retries)
        connector = MockConnector([
            RateLimitError("rate limit 1"),
            RateLimitError("rate limit 2"),
            RateLimitError("rate limit 3"),
            RateLimitError("rate limit 4"),  # This should trigger final failure
        ])

        with pytest.raises(RateLimitError):
            await run_connector(async_db_session, connector, mode="live")

        # Verify job was created with correct failure category
        async_db_session.expire_all()
        stmt = select(IngestionJob).order_by(IngestionJob.started_at.desc()).limit(1)
        result = await async_db_session.execute(stmt)
        job = result.scalar_one()

        assert job.status == "failed"
        assert job.failure_category == "rate_limit"
        # Verify multiple fetch attempts (retry loop executed)
        assert connector.fetch_call_count == 4

    @pytest.mark.asyncio
    async def test_success_after_transient_retry(self, async_db_session: AsyncSession):
        """Test that transient errors (UpstreamUnavailableError) can recover and succeed."""
        # Fail first attempt, succeed on second
        raw_records = [{"id": "1", "text": "Success after retry"}]
        connector = MockConnector([
            UpstreamUnavailableError("temporary outage"),
            raw_records,
        ])

        summary = await run_connector(async_db_session, connector, mode="live")

        # Verify run completed successfully
        assert summary.fetched == 1
        assert summary.normalized == 1

        # Query job record
        async_db_session.expire_all()
        stmt = select(IngestionJob).order_by(IngestionJob.started_at.desc()).limit(1)
        result = await async_db_session.execute(stmt)
        job = result.scalar_one()

        assert job.status == "completed"
        assert job.failure_category is None
        # Verify retry occurred
        assert connector.fetch_call_count == 2

    @pytest.mark.asyncio
    async def test_job_response_exposes_failure_category(self, async_db_session: AsyncSession):
        """Test that GET /jobs returns job with failure_category populated."""
        from app.api.jobs import _job_to_response

        connector = MockConnector([AuthError("access denied")])

        with pytest.raises(AuthError):
            await run_connector(async_db_session, connector, mode="live")

        # Query job and convert to response
        async_db_session.expire_all()
        stmt = select(IngestionJob).order_by(IngestionJob.started_at.desc()).limit(1)
        result = await async_db_session.execute(stmt)
        job = result.scalar_one()

        response = _job_to_response(job)
        assert response.failure_category == "auth_error"

    @pytest.mark.asyncio
    async def test_job_response_exposes_normalized_count(self, async_db_session: AsyncSession):
        """Test that GET /jobs returns job with normalized_count populated."""
        from app.api.jobs import _job_to_response

        raw_records = [
            {"id": "1", "text": "Valid post"},
            {"id": "2", "text": "Another valid post"},
        ]
        connector = MockConnector([raw_records])

        await run_connector(async_db_session, connector, mode="live")

        # Query job and convert to response
        async_db_session.expire_all()
        stmt = select(IngestionJob).order_by(IngestionJob.started_at.desc()).limit(1)
        result = await async_db_session.execute(stmt)
        job = result.scalar_one()

        response = _job_to_response(job)
        assert response.normalized_count == 2
        assert response.row_count == 2

    @pytest.mark.asyncio
    async def test_generic_exception_results_in_none_failure_category(self, async_db_session: AsyncSession):
        """Test that generic Python exceptions result in failure_category=None."""
        # Use a generic Python exception (not a ConnectorError)
        connector = MockConnector([FileNotFoundError("config file missing")])

        with pytest.raises(FileNotFoundError):
            await run_connector(async_db_session, connector, mode="live")

        # Verify job was created but failure_category is None
        async_db_session.expire_all()
        stmt = select(IngestionJob).order_by(IngestionJob.started_at.desc()).limit(1)
        result = await async_db_session.execute(stmt)
        job = result.scalar_one()

        assert job.status == "failed"
        assert job.failure_category is None
