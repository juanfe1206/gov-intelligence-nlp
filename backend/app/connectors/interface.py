"""Base connector interface for platform-specific providers."""

from abc import ABC, abstractmethod
from typing import Any

from app.connectors.schemas import NormalizedPost


class BaseConnector(ABC):
    """Abstract base class for all connector implementations.

    Defines the contract that all platform connectors must implement:
    - fetch(): Retrieve raw payloads from the source
    - normalize(): Convert a raw payload to NormalizedPost
    - checkpoint(): Return cursor/state for incremental fetching

    SECURITY NOTE: Implementations must never log or expose credentials, API keys, or tokens.
    Only log connector_id, record counts, and timestamps.
    """

    connector_id: str  # Class-level attribute, overridden by subclasses

    @abstractmethod
    def fetch(self) -> list[dict[str, Any]]:
        """Fetch raw payloads from the source.

        Returns:
            List of raw platform payloads as dictionaries.
        """
        ...

    @abstractmethod
    def normalize(self, raw: dict[str, Any]) -> NormalizedPost | None:
        """Normalize a raw payload to a StandardizedPost.

        Args:
            raw: Raw platform payload dictionary

        Returns:
            NormalizedPost if valid, None if the record should be skipped.
            On failure, implementations should return None rather than raising.
        """
        ...

    @abstractmethod
    def checkpoint(self) -> dict[str, Any]:
        """Return current cursor/state for incremental fetching.

        Returns:
            Dictionary containing cursor or state for tracking progress.
            Used for incremental fetching in Story 5.2.
        """
        ...
