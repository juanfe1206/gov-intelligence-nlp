"""FastAPI application for gov-intelligence-nlp platform."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ingestion import router as ingestion_router
from app.api.taxonomy import router as taxonomy_router
from app.config import settings
from app.taxonomy.loader import load_taxonomy


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager.

    Handles startup and shutdown events:
    - Startup: Loads taxonomy configuration from YAML file
    - Shutdown: Cleanup (if needed)

    The taxonomy is loaded once at startup and stored in app.state.
    If loading fails, the exception propagates and prevents startup.
    """
    # Startup: load taxonomy — raises on error, which aborts startup
    app.state.taxonomy = load_taxonomy(settings.TAXONOMY_PATH)
    yield
    # Shutdown: nothing to clean up for taxonomy


app = FastAPI(
    title="gov-intelligence-nlp API",
    description="Political intelligence platform API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware - origins validated by config
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return {"status": "ok"}


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "gov-intelligence-nlp API",
        "version": "0.1.0",
        "docs": "/docs",
    }


app.include_router(taxonomy_router, prefix="/taxonomy", tags=["taxonomy"])
app.include_router(ingestion_router, prefix="/ingest", tags=["ingestion"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.BACKEND_HOST, port=settings.BACKEND_PORT)
