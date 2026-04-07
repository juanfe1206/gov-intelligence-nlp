"""Application configuration with environment variable validation."""

import os
from pydantic import ConfigDict, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All required variables must be set. Missing required variables
    will raise a ValidationError at startup.
    """

    # Required
    DATABASE_URL: str
    DATABASE_SYNC_URL: str | None = None
    OPENAI_API_KEY: str

    # Optional with defaults
    APP_ENV: str = "dev"
    LOG_LEVEL: str = "INFO"
    # Backend configuration
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000

    # CORS configuration
    CORS_ALLOW_ORIGINS: str = "http://localhost:3000"

    # Taxonomy configuration
    TAXONOMY_PATH: str = "config/taxonomy.yaml"

    # Ingestion configuration
    INGESTION_CSV_PATH: str = "data/posts.csv"
    INGESTION_SOURCE_NAME: str = "csv_local"
    INGESTION_PLATFORM_DEFAULT: str = ""

    # Processing configuration
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    PROCESSING_BATCH_SIZE: int = 50
    PROCESSING_MAX_RETRIES: int = 3

    @model_validator(mode="after")
    def _ensure_sync_url(self) -> "Settings":
        """Derive DATABASE_SYNC_URL when omitted (useful for CI sqlite)."""
        if self.DATABASE_SYNC_URL:
            return self

        # For sqlite URLs, sync/async can safely use the same URL here.
        if self.DATABASE_URL.startswith("sqlite"):
            self.DATABASE_SYNC_URL = self.DATABASE_URL
            return self

        # Common async driver fallback.
        self.DATABASE_SYNC_URL = self.DATABASE_URL.replace("+asyncpg", "+psycopg2")
        return self

    def get_cors_origins(self) -> list[str]:
        """Parse CORS origins from comma-separated string.

        Validates that '*' is not used when credentials are enabled.
        """
        origins = [o.strip() for o in self.CORS_ALLOW_ORIGINS.split(",") if o.strip()]

        # Security: '*' with credentials is a vulnerability
        if "*" in origins:
            raise ValueError(
                "CORS_ALLOW_ORIGINS cannot contain '*' when allow_credentials is True. "
                "Specify explicit origins instead."
            )

        return origins

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


# Global settings instance - created at import time to fail fast
settings = Settings()
