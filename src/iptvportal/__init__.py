"""Modern Python client for IPTVPortal JSONSQL API."""

from iptvportal.config.settings import IPTVPortalSettings
from iptvportal.core.async_client import AsyncIPTVPortalClient
from iptvportal.core.client import IPTVPortalClient
from iptvportal.exceptions import (
    APIError,
    AuthenticationError,
    ConnectionError,
    IPTVPortalError,
    TimeoutError,
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
