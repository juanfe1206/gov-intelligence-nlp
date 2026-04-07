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
is_github_ci = os.environ.get("GITHUB_ACTIONS") == "true" or os.environ.get("CI") == "true"
if test_env_path.exists() and not is_github_ci:
    # Local/dev: force .env.test so test runs are isolated and reproducible.
    load_dotenv(test_env_path, override=True)
elif test_env_path.exists() and is_github_ci:
    # CI: rely on workflow-provided env vars and PostgreSQL service config.
    load_dotenv(test_env_path, override=False)
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
    from psycopg2 import OperationalError
    from urllib.parse import urlparse

    sync_url = os.environ.get(
        "DATABASE_SYNC_URL",
        "postgresql://postgres:postgres@localhost:5432/gov_intelligence_nlp_test",
    )
    parsed = urlparse(sync_url)
    db_host = (parsed.hostname or "").lower()
    is_local_db = db_host in {"localhost", "127.0.0.1", "::1"}
    allow_remote_db = os.environ.get("PYTEST_ALLOW_REMOTE_DB") == "1"
    if not is_local_db and not allow_remote_db:
        raise RuntimeError(
            "Refusing to run DB tests against non-local DATABASE_SYNC_URL by default. "
            "Set PYTEST_ALLOW_REMOTE_DB=1 to allow remote DB targets."
        )

    try:
        conn = psycopg2.connect(
            sync_url,
            connect_timeout=10,
            application_name="pytest_schema_setup",
            options="-c statement_timeout=30000 -c lock_timeout=5000",
        )
    except OperationalError as exc:
        raise RuntimeError(
            f"Test database connection failed for DATABASE_SYNC_URL={sync_url!r}. "
            "Check backend/.env.test and ensure the database is reachable."
        ) from exc
    conn.autocommit = True
    cur = conn.cursor()

    # Avoid setup flakiness from managed DB statement timeouts on DROP ... CASCADE.
    # We only need idempotent schema creation plus data cleanup for tests.
    cur.execute("SET statement_timeout = 0")
    cur.execute("SET lock_timeout = 0")

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

    # Ensure a clean test slate without destructive DDL.
    cur.execute(
        "TRUNCATE TABLE ingestion_jobs, raw_posts, processed_posts RESTART IDENTITY CASCADE"
    )

    cur.close()
    conn.close()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def async_engine():
    """Provide the async engine for DB-backed test fixtures."""
    # Initialize schema only when DB-backed fixtures are requested.
    # This prevents non-DB unit tests from hanging on database connectivity.
    _setup_database_schema()
    from app.db.session import engine

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True, loop_scope="function")
async def isolate_test_tables(request):
    """Ensure core tables are clean before and after every test.

    Uses TRUNCATE with engine-level connections for proper isolation.
    """
    needs_db = "async_db_session" in request.fixturenames or "client" in request.fixturenames
    if not needs_db:
        yield
        return

    async_engine = request.getfixturevalue("async_engine")

    # Truncate before test
    async with async_engine.begin() as conn:
        await conn.execute(text("SET LOCAL statement_timeout = '30s'"))
        await conn.execute(text("SET LOCAL lock_timeout = '5s'"))
        await conn.execute(
            text(
                "TRUNCATE TABLE ingestion_jobs, raw_posts, processed_posts RESTART IDENTITY CASCADE"
            )
        )

    yield

    # Truncate after test
    async with async_engine.begin() as conn:
        await conn.execute(text("SET LOCAL statement_timeout = '30s'"))
        await conn.execute(text("SET LOCAL lock_timeout = '5s'"))
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
