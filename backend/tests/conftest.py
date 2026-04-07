"""Pytest configuration and fixtures for backend tests."""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend package is importable when running tests from any directory
sys.path.insert(0, str(Path(__file__).parent.parent))

# Prefer backend/.env.test for isolated test runs.
backend_root = Path(__file__).parent.parent
test_env_path = backend_root / ".env.test"
if test_env_path.exists():
    load_dotenv(test_env_path, override=True)
else:
    # Safe local defaults to avoid accidental cloud DB usage from root .env.
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/gov_intelligence_nlp_test",
    )
    os.environ.setdefault(
        "DATABASE_SYNC_URL",
        "postgresql://postgres:postgres@localhost:5432/gov_intelligence_nlp_test",
    )
    os.environ.setdefault(
        "OPENAI_API_KEY",
        "test-key-for-ci",
    )

# Ensure startup taxonomy file resolves from repo root test runs.
os.environ.setdefault("TAXONOMY_PATH", str(backend_root / "config" / "taxonomy.yaml"))

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.taxonomy.loader import load_taxonomy
from app.taxonomy.schemas import TaxonomyConfig


@pytest.fixture
def client():
    """Create a test client for making HTTP requests.

    This fixture uses TestClient with lifespan to properly handle
    startup/shutdown events including taxonomy loading.
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_taxonomy() -> TaxonomyConfig:
    """Create a sample taxonomy configuration for testing."""
    return load_taxonomy(Path(__file__).parent.parent / "config/taxonomy.yaml")


@pytest_asyncio.fixture(scope="session", autouse=True, loop_scope="session")
async def ensure_test_schema_current():
    """Recreate test tables from current ORM models once per test session."""
    from app.db.base import Base
    from app.db.session import engine
    from app import models  # noqa: F401 - ensure model metadata is registered

    async with engine.begin() as conn:
        # Enable pgvector extension before creating tables
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def isolate_test_tables():
    """Ensure core tables are clean before and after every test."""
    from app.db.session import async_session_maker

    async with async_session_maker() as session:
        await session.execute(text("TRUNCATE TABLE ingestion_jobs, raw_posts, processed_posts RESTART IDENTITY CASCADE"))
        await session.commit()

    yield

    async with async_session_maker() as session:
        await session.execute(text("TRUNCATE TABLE ingestion_jobs, raw_posts, processed_posts RESTART IDENTITY CASCADE"))
        await session.commit()


@pytest_asyncio.fixture(loop_scope="session")
async def async_db_session():
    """Create an async database session for tests.

    This fixture provides a fresh async session for each test,
    ensuring test isolation.
    """
    from app.db.session import async_session_maker

    async with async_session_maker() as session:
        yield session
        await session.rollback()
        # Clean up committed test data to avoid cross-test contamination.
        await session.execute(text("TRUNCATE TABLE ingestion_jobs, raw_posts, processed_posts RESTART IDENTITY CASCADE"))
        await session.commit()
