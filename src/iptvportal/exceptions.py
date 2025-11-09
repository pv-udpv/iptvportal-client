"""Core exception hierarchy for IPTVPortal client.

These exceptions cover authentication, connection, timeout, API, and
validation related failures. All custom exceptions inherit from
``IPTVPortalError`` so users may catch that base class for any library
error.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class IPTVPortalError(Exception):
    """Base exception for all client errors."""

    def __init__(self, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: Mapping[str, Any] | None = details

    def __str__(self) -> str:  # pragma: no cover - delegating to message
        return self.message


class AuthenticationError(IPTVPortalError):
    """Raised when authentication fails (invalid credentials, missing session)."""


class ConnectionError(IPTVPortalError):
    """Raised when a network connection error occurs (DNS, refused, etc.)."""


class TimeoutError(IPTVPortalError):
    """Raised when a request exceeds the configured timeout."""


class APIError(IPTVPortalError):
    """Raised for API-level errors returned by the JSON-RPC/JSONSQL endpoints."""


class ValidationError(IPTVPortalError):
    """Raised when request or configuration validation fails."""
