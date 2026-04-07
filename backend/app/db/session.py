"""Async SQLAlchemy session factory and engine configuration."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings

# Pooler-friendly test mode: avoid keeping/reusing long-lived pooled connections.
engine_kwargs: dict = {
    "echo": True,  # Log SQL queries (disable in production)
    "future": True,
}
if settings.APP_ENV == "test":
    engine_kwargs["poolclass"] = NullPool
    engine_kwargs["connect_args"] = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
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
