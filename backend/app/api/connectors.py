"""API endpoints for connector management and execution."""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.config import settings
from app.connectors.interface import BaseConnector
from app.connectors.service import get_checkpoint, run_connector
from app.connectors.schemas import ConnectorRunSummary
from app.connectors.twitter_file import TwitterFileConnector
from app.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectorRunRequest(BaseModel):
    """Request body for triggering a connector run."""

    file_path: str | None = None


class ConnectorRunResponse(BaseModel):
    """Response body for connector run results."""

    connector_id: str
    mode: str
    started_at: str
    finished_at: str | None
    fetched: int
    normalized: int
    rejected: int
    inserted: int
    duplicates: int
    validation_errors: list[dict[str, Any]]

    @classmethod
    def from_summary(cls, summary: ConnectorRunSummary) -> "ConnectorRunResponse":
        """Create response from ConnectorRunSummary."""
        return cls(
            connector_id=summary.connector_id,
            mode=summary.mode,
            started_at=summary.started_at.isoformat(),
            finished_at=summary.finished_at.isoformat() if summary.finished_at else None,
            fetched=summary.fetched,
            normalized=summary.normalized,
            rejected=summary.rejected,
            inserted=summary.inserted,
            duplicates=summary.duplicates,
            validation_errors=[
                {"field": e.field, "message": e.message, "raw_value": e.raw_value}
                for e in summary.validation_errors
            ],
        )


@router.post(
    "/{connector_id}/run",
    response_model=ConnectorRunResponse,
    summary="Run a connector",
    description="Execute a connector to fetch and ingest posts from a platform.",
    response_description="Summary of connector run results including counts and status",
)
async def run_connector_endpoint(
    connector_id: str,
    body: ConnectorRunRequest | None = None,
    session: AsyncSession = Depends(get_db),
) -> ConnectorRunResponse:
    """Trigger a connector run.

    Currently supports only 'twitter-file' connector which reads from a JSONL file.

    Args:
        connector_id: The connector identifier (e.g., 'twitter-file')
        body: Optional request body with file_path override
        session: Async database session

    Returns:
        ConnectorRunResponse with metrics

    Raises:
        HTTPException 400: If connector_id is unsupported or file not found
        HTTPException 500: If unexpected error occurs
    """
    # Validate connector_id - currently only twitter-file is supported
    if connector_id != "twitter-file":
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Unsupported connector_id: {connector_id}",
                "supported_connectors": ["twitter-file"],
            },
        )

    # Resolve file_path
    file_path = body.file_path if body and body.file_path else settings.CONNECTOR_TWITTER_FILE_PATH

    try:
        # Instantiate connector
        connector: BaseConnector = TwitterFileConnector(file_path=file_path)

        # Load checkpoint to inject into connector
        checkpoint_data = await get_checkpoint(session, connector_id)
        if checkpoint_data and checkpoint_data.get("last_seen_at"):
            from datetime import datetime as dt

            last_seen_str = checkpoint_data["last_seen_at"]
            try:
                last_seen = dt.fromisoformat(last_seen_str.replace("Z", "+00:00"))
                connector._after_timestamp = last_seen
            except ValueError as e:
                logger.warning(f"Could not parse checkpoint timestamp: {e}")

        # Run the connector
        summary = await run_connector(session, connector)

        return ConnectorRunResponse.from_summary(summary)

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise HTTPException(
            status_code=400,
            detail={"message": str(e)},
        )

    except Exception:
        logger.exception(f"Connector run failed: {connector_id}")
        raise HTTPException(
            status_code=500,
            detail={"message": "Connector run failed"},
        )
