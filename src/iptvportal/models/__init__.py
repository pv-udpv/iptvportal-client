"""Pydantic models for requests and responses."""

from iptvportal.models.requests import JSONSQLQueryInput, SQLQueryInput
from iptvportal.models.responses import ExecutionMetadata, QueryResult

# SQLModel wrappers (optional, requires sqlmodel package)
try:
    from iptvportal.models import sqlmodel_wrappers

    __all__ = [
        "SQLQueryInput",
        "JSONSQLQueryInput",
        "QueryResult",
        "ExecutionMetadata",
        "sqlmodel_wrappers",
    ]
except ImportError:
    # SQLModel not installed, only export Pydantic models
    __all__ = [
        "SQLQueryInput",
        "JSONSQLQueryInput",
        "QueryResult",
        "ExecutionMetadata",
    ]
