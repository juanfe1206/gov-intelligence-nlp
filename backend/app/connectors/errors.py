"""Connector error taxonomy for machine-readable failure categorization."""

RETRYABLE_CATEGORIES = {"rate_limit", "upstream_unavailable"}


class ConnectorError(Exception):
    """Base class for categorized connector errors.

    All connector implementations should raise subclasses of this when
    errors are recoverable or classifiable. Generic Python exceptions
    (e.g., FileNotFoundError, ValueError) are NOT retried.
    """
    category: str = "unknown"

    def __init__(self, message: str, category: str | None = None):
        super().__init__(message)
        self.category = category or self.__class__.category


class AuthError(ConnectorError):
    """Authentication or authorization failure. NOT retried."""
    category = "auth_error"


class RateLimitError(ConnectorError):
    """Rate limit exceeded. RETRIED with backoff."""
    category = "rate_limit"


class UpstreamUnavailableError(ConnectorError):
    """Upstream service temporarily unavailable. RETRIED with backoff."""
    category = "upstream_unavailable"
