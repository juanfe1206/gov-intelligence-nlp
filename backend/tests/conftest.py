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
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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


# Use raw SQL for schema setup to avoid SQLAlchemy drop_all hanging issues
def _setup_database_schema():
    """Set up the test database schema using raw SQL and sync connection."""
    import psycopg2

    sync_url = os.environ.get(
        "DATABASE_SYNC_URL",
        "postgresql://postgres:postgres@localhost:5432/gov_intelligence_nlp_test",
    )

    conn = psycopg2.connect(sync_url)
    conn.autocommit = True
    cur = conn.cursor()

    # Drop tables in reverse dependency order
    cur.execute("DROP TABLE IF EXISTS processed_posts CASCADE")
    cur.execute("DROP TABLE IF EXISTS raw_posts CASCADE")
    cur.execute("DROP TABLE IF EXISTS ingestion_jobs CASCADE")

    # Create tables with TEXT type instead of VECTOR for testing
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ingestion_jobs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source VARCHAR(255) NOT NULL,
            job_type VARCHAR(50),
            status VARCHAR(50) NOT NULL,
            started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            finished_at TIMESTAMP WITH TIME ZONE,
            row_count INTEGER,
            inserted_count INTEGER,
            skipped_count INTEGER,
            duplicate_count INTEGER,
            error_summary JSONB
        )
    """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS raw_posts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source VARCHAR(255) NOT NULL,
            platform VARCHAR(100) NOT NULL,
            original_text TEXT NOT NULL,
            content_hash VARCHAR(64),
            author VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            metadata JSONB,
            ingested_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            UNIQUE(source, content_hash)
        )
    """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS processed_posts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            raw_post_id UUID NOT NULL REFERENCES raw_posts(id),
            topic VARCHAR(100) NOT NULL,
            subtopic VARCHAR(100),
            sentiment VARCHAR(20) NOT NULL,
            target VARCHAR(255),
            intensity FLOAT,
            embedding TEXT,
            processed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            model_version VARCHAR(50),
            error_status BOOLEAN DEFAULT FALSE,
            error_message TEXT,
            UNIQUE(raw_post_id)
        )
    """
    )

    cur.close()
    conn.close()


@pytest.fixture(scope="session", autouse=True)
def test_database_setup():
    """Set up test database schema once per test session."""
    _setup_database_schema()
    yield


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def async_engine():
    """Provide the async engine for test fixtures."""
    from app.db.session import engine

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True, loop_scope="function")
async def isolate_test_tables(async_engine):
    """Ensure core tables are clean before and after every test.

    Uses TRUNCATE with engine-level connections for proper isolation.
    """
    # Truncate before test
    async with async_engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE ingestion_jobs, raw_posts, processed_posts RESTART IDENTITY CASCADE"
            )
        )

    yield

    # Truncate after test
    async with async_engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE ingestion_jobs, raw_posts, processed_posts RESTART IDENTITY CASCADE"
            )
        )


@pytest_asyncio.fixture(loop_scope="function")
async def async_db_session(async_engine):
    """Create an async database session for tests.

    This fixture provides a fresh async session for each test function.
    The session is properly closed after use, with cleanup handled by isolate_test_tables.
    """
    session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
