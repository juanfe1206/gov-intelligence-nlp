"""FastAPI application for gov-intelligence-nlp platform."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.admin import router as admin_router
from app.api.analytics import router as analytics_router
from app.api.connectors import router as connectors_router
from app.api.ingestion import router as ingestion_router
from app.api.jobs import router as jobs_router
from app.api.processing import router as processing_router
from app.api.qa import router as qa_router
from app.api.taxonomy import router as taxonomy_router
from app.config import settings
from app.db.session import engine
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
    taxonomy_config = load_taxonomy(settings.TAXONOMY_PATH)

    # Convert Pydantic model to flat dictionary for classifier compatibility
    # Extract topic names from nested structure
    topic_names = [t.name for t in taxonomy_config.topics]

    # Collect all subtopic names across all topics
    subtopic_names = []
    for topic in taxonomy_config.topics:
        for subtopic in topic.subtopics:
            subtopic_names.append(subtopic.name)

    # Collect all target names (parties + leaders)
    target_names = []
    for party in taxonomy_config.targets.parties:
        target_names.append(party.name)
    for leader in taxonomy_config.targets.leaders:
        target_names.append(leader.name)

    app.state.taxonomy = {
        "topics": topic_names,
        "subtopics": subtopic_names,
        "targets": target_names,
    }
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
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/health/db")
async def health_check_db():
    """Database connectivity check. Returns 503 if DB is unreachable."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": "disconnected"},
        )


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "gov-intelligence-nlp API",
        "version": "0.1.0",
        "docs": "/docs",
    }


app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(taxonomy_router, prefix="/taxonomy", tags=["taxonomy"])
app.include_router(ingestion_router, prefix="/ingest", tags=["ingestion"])
app.include_router(connectors_router, prefix="/connectors", tags=["connectors"])
app.include_router(processing_router, prefix="/process", tags=["processing"])
app.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
app.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
app.include_router(qa_router, prefix="/qa", tags=["qa"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.BACKEND_HOST, port=settings.BACKEND_PORT)
