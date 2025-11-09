"""Response models for query results."""

from typing import Any

from pydantic import BaseModel, Field


class QueryResult(BaseModel):
    """Query execution result.
    
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
    jsonsql: dict | None = None
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


class ExecutionMetadata(BaseModel):
    """Metadata about query execution.
    
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
