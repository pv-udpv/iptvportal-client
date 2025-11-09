"""Modern Python client for IPTVPortal JSONSQL API."""

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
from iptvportal.jsonsql import QueryBuilder, SQLTranspiler
from iptvportal.models import QueryResult, SQLQueryInput
from iptvportal.schema import SchemaRegistry, TableSchema
from iptvportal.service import QueryService

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
    # Exceptions
    "IPTVPortalError",
    "AuthenticationError",
    "APIError",
    "TimeoutError",
    "ConnectionError",
    # Legacy project configuration module
    "project_conf",
]
