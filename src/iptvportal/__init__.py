"""Modern Python client for IPTVPortal JSONSQL API."""

from iptvportal.client import IPTVPortalClient
from iptvportal.async_client import AsyncIPTVPortalClient
from iptvportal.config import IPTVPortalSettings
from iptvportal.exceptions import (
    IPTVPortalError,
    AuthenticationError,
    APIError,
    TimeoutError,
    ConnectionError,
)

__version__ = "0.1.0"

__all__ = [
    "IPTVPortalClient",
    "AsyncIPTVPortalClient",
    "IPTVPortalSettings",
    "IPTVPortalError",
    "AuthenticationError",
    "APIError",
    "TimeoutError",
    "ConnectionError",
]
