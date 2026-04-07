"""Application configuration with environment variable validation."""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All required variables must be set. Missing required variables
    will raise a ValidationError at startup.
    """

    # Required
    DATABASE_URL: str
    DATABASE_SYNC_URL: str
    OPENAI_API_KEY: str

    # Optional with defaults
    APP_ENV: str = "dev"
    LOG_LEVEL: str = "INFO"
    OPENAI_CHAT_MODEL: str = ""
    OPENAI_EMBEDDING_MODEL: str = ""

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

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance - created at import time to fail fast
settings = Settings()
