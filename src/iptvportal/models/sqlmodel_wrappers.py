"""SQLModel wrappers for metadata models.

This module provides SQLModel versions of the Pydantic models for users who
want to use SQLModel for ORM functionality. These models maintain full
compatibility with the original Pydantic models.
"""

from typing import Any

from pydantic import Field, field_validator
from sqlmodel import SQLModel


class SQLQueryInput(SQLModel):
    """SQLModel version of validated SQL query input.

    Attributes:
        sql: SQL query string to execute
        use_cache: Whether to use query result caching
        use_schema_mapping: Whether to map results using schema definitions
        timeout: Optional timeout in seconds for the query
        dry_run: If True, transpile but don't execute the query
    """

    sql: str = Field(..., min_length=1, max_length=50000)
    use_cache: bool = True
    use_schema_mapping: bool = True
    timeout: int | None = Field(None, ge=1, le=300)
    dry_run: bool = False

    @field_validator("sql")
    @classmethod
    def validate_sql(cls, v: str) -> str:
        """Validate SQL query is not empty."""
        if not v.strip():
            raise ValueError("SQL query cannot be empty")
        return v.strip()


class JSONSQLQueryInput(SQLModel):
    """SQLModel version of validated JSONSQL query input.

    Attributes:
        method: JSONSQL method (select, insert, update, delete)
        params: Query parameters as dictionary
        use_cache: Whether to use query result caching
        timeout: Optional timeout in seconds for the query
    """

    method: str = Field(..., pattern="^(select|insert|update|delete)$")
    params: dict[str, Any]
    use_cache: bool = True
    timeout: int | None = Field(None, ge=1, le=300)

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate params is a non-empty dictionary."""
        if not isinstance(v, dict):
            raise ValueError("params must be a dictionary")
        if not v:
            raise ValueError("params cannot be empty")
        return v


class QueryResult(SQLModel):
    """SQLModel version of query execution result.

    Attributes:
        data: Query result data (list of dicts or single dict)
        sql: Original SQL query (if transpiled)
        jsonsql: JSONSQL representation of the query
        method: JSONSQL method used (select, insert, update, delete)
        table: Table name extracted from query
        execution_time_ms: Execution time in milliseconds
        row_count: Number of rows in result
    """

    data: list[dict[str, Any]] | dict[str, Any]
    sql: str | None = None
    jsonsql: dict[str, Any] | None = None
    method: str
    table: str | None = None
    execution_time_ms: float | None = None
    row_count: int = Field(default=0, ge=0)

    def model_post_init(self, __context: Any) -> None:
        """Calculate row count after initialization."""
        if isinstance(self.data, list):
            self.row_count = len(self.data)
        elif isinstance(self.data, dict):
            self.row_count = 1
        else:
            self.row_count = 0


class ExecutionMetadata(SQLModel):
    """SQLModel version of metadata about query execution.

    Attributes:
        cached: Whether result came from cache
        cache_key: Cache key used (if cached)
        request_id: JSON-RPC request ID
        timestamp: Execution timestamp
    """

    cached: bool = False
    cache_key: str | None = None
    request_id: int | None = None
    timestamp: str | None = None


__all__ = [
    "SQLQueryInput",
    "JSONSQLQueryInput",
    "QueryResult",
    "ExecutionMetadata",
]
