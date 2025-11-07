"""Exception hierarchy for IPTVPortal client."""

from typing import Any


class IPTVPortalError(Exception):
    """Base exception for all IPTVPortal errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuthenticationError(IPTVPortalError):
    """Authentication failed."""

    pass


class APIError(IPTVPortalError):
    """API returned an error response."""

    pass


class TimeoutError(IPTVPortalError):
    """Request timeout."""

    pass


class ConnectionError(IPTVPortalError):
    """Connection failed."""

    pass


class ValidationError(IPTVPortalError):
    """Data validation error."""

    pass
