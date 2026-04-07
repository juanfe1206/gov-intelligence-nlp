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
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.session import get_db, async_session_maker
from app.taxonomy.loader import load_taxonomy
from app.taxonomy.schemas import TaxonomyConfig


def pytest_configure(config):
    """Register custom markers used by this test suite."""
    config.addinivalue_line(
        "markers",
        "db: marks tests that require a live database connection",
    )


def pytest_collection_modifyitems(config, items):
    """Auto-mark DB tests and skip them unless explicitly enabled."""
    run_db_tests = os.environ.get("RUN_DB_TESTS") == "1"
    skip_db = pytest.mark.skip(reason="DB tests disabled. Set RUN_DB_TESTS=1 to enable.")

    for item in items:
        needs_db = "async_db_session" in item.fixturenames or "client" in item.fixturenames
        if needs_db:
            item.add_marker(pytest.mark.db)
            if not run_db_tests:
                item.add_marker(skip_db)


@pytest.fixture
def client():
    """Create a test client for making HTTP requests.

    This fixture uses TestClient with lifespan to properly handle
    startup/shutdown events including taxonomy loading.
    """
    async def _override_get_db():
        async with async_session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


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

    # Ensure required extensions for schema defaults and vector support.
    cur.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    cur.execute('CREATE EXTENSION IF NOT EXISTS "vector"')

    # Create test tables aligned with application schema.
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
            embedding VECTOR(1536),
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


def _truncate_test_tables():
    """Synchronously truncate test tables with short lock/statement timeouts."""
    import psycopg2

    sync_url = os.environ.get(
        "DATABASE_SYNC_URL",
        "postgresql://postgres:postgres@localhost:5432/gov_intelligence_nlp_test",
    )
    conn = psycopg2.connect(
        sync_url,
        connect_timeout=10,
        application_name="pytest_table_truncate",
        options="-c statement_timeout=30000 -c lock_timeout=5000",
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(
        "TRUNCATE TABLE ingestion_jobs, raw_posts, processed_posts RESTART IDENTITY CASCADE"
    )
    cur.close()
    conn.close()


@pytest.fixture(autouse=True)
def isolate_test_tables(request):
    """Ensure core tables are clean before and after every test.

    Uses synchronous TRUNCATE to avoid async event-loop fixture conflicts.
    """
    needs_db = "async_db_session" in request.fixturenames or "client" in request.fixturenames
    if not needs_db:
        yield
        return

    _setup_database_schema()
    _truncate_test_tables()

    yield

    _truncate_test_tables()


@pytest_asyncio.fixture(loop_scope="function")
async def async_db_session():
    """Create an async database session for tests.

    This fixture provides a fresh async session for each test function.
    The session is properly closed after use, with cleanup handled by isolate_test_tables.
    """
    from app.db.session import async_session_maker

    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest_asyncio.fixture(scope="session", autouse=True, loop_scope="session")
async def dispose_async_engine():
    """Dispose global async engine at session end."""
    yield
    from app.db.session import engine

    await engine.dispose()
