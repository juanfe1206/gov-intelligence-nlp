"""Connector interface and normalization package for source plugins."""

from app.connectors.schemas import NormalizedPost, ValidationError, ConnectorRunSummary
from app.connectors.interface import BaseConnector
from app.connectors.validator import validate_and_normalize

__all__ = [
    "NormalizedPost",
    "ValidationError",
    "ConnectorRunSummary",
    "BaseConnector",
    "validate_and_normalize",
]
