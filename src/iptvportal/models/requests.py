"""Request models for input validation."""

from pydantic import BaseModel, Field, field_validator


class SQLQueryInput(BaseModel):
    """Validated SQL query input.

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


class JSONSQLQueryInput(BaseModel):
    """Validated JSONSQL query input.

    Attributes:
        method: JSONSQL method (select, insert, update, delete)
        params: Query parameters as dictionary
        use_cache: Whether to use query result caching
        timeout: Optional timeout in seconds for the query
    """

    method: str = Field(..., pattern="^(select|insert|update|delete)$")
    params: dict
    use_cache: bool = True
    timeout: int | None = Field(None, ge=1, le=300)

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: dict) -> dict:
        """Validate params is a non-empty dictionary."""
        if not isinstance(v, dict):
            raise ValueError("params must be a dictionary")
        if not v:
            raise ValueError("params cannot be empty")
        return v
