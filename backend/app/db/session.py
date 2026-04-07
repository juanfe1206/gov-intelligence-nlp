"""Async SQLAlchemy session factory and engine configuration."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings

# Pooler-friendly test mode: avoid keeping/reusing long-lived pooled connections.
engine_kwargs: dict = {
    "echo": True,  # Log SQL queries (disable in production)
    "future": True,
}
# In tests/CI, pytest may use different event loops across test cases.
# Reusing pooled asyncpg connections across loops causes
# "Future attached to a different loop" and "another operation is in progress".
if settings.APP_ENV in {"test", "ci"}:
    engine_kwargs["poolclass"] = NullPool
    engine_kwargs["connect_args"] = {
        # Fail fast in tests instead of appearing stuck on DB/network waits.
        "timeout": 10,
        "command_timeout": 30,
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "server_settings": {
            "statement_timeout": "30000",
            "lock_timeout": "5000",
        },
    }

# Create async engine for database connections
engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """Dependency for FastAPI routes to get database session."""
    async with async_session_maker() as session:
        yield session
