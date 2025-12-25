"""Modern Python client for IPTVPortal JSONSQL API."""

from contextlib import suppress

from iptvportal import project_conf  # backward compatibility import
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
from iptvportal.jsonsql import Field, Q, QueryBuilder, SQLTranspiler
from iptvportal.models import QueryResult, SQLQueryInput
from iptvportal.schema import SchemaRegistry, TableSchema
from iptvportal.service import QueryService

# NOTE: Logging is NOT auto-initialized on import to avoid duplicate warnings.
# For CLI usage, logging is configured via cli/__main__.py global callback.
# For library usage, call setup_logging() explicitly:
#
#   from iptvportal.config import setup_logging
#   setup_logging()
#
# This is safe to call multiple times (idempotent).

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Clients
    "IPTVPortalClient",
    "AsyncIPTVPortalClient",
    # Configuration
    "IPTVPortalSettings",
    # Services
    "QueryService",
    # Models
    "SQLQueryInput",
    "QueryResult",
    # Schema
    "TableSchema",
    "SchemaRegistry",
    # JSONSQL
    "QueryBuilder",
    "SQLTranspiler",
    "Field",
    "Q",
    # Exceptions
    "IPTVPortalError",
    "AuthenticationError",
    "APIError",
    "TimeoutError",
    "ConnectionError",
    # Legacy project configuration module
    "project_conf",
]
