"""Tests for database connection and pgvector extension."""

import pytest
from sqlalchemy import text

from app.db.session import async_session_maker


@pytest.mark.asyncio
async def test_database_connection():
    """Test that we can connect to the database."""
    async with async_session_maker() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_pgvector_extension():
    """Test that pgvector extension is available."""
    async with async_session_maker() as session:
        result = await session.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )
        )
        assert result.scalar() is True
