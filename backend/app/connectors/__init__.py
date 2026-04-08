"""Connector interface and normalization package for source plugins."""

from app.connectors.schemas import ConnectorRunSummary, NormalizedPost, ValidationError
from app.connectors.interface import BaseConnector
from app.connectors.service import get_checkpoint, run_connector
from app.connectors.validator import validate_and_normalize

__all__ = [
    "NormalizedPost",
    "ValidationError",
    "ConnectorRunSummary",
    "BaseConnector",
    "validate_and_normalize",
    "run_connector",
    "get_checkpoint",
]
