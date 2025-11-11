"""Example: Using SQLModel wrappers for metadata models.

This example demonstrates how to use the SQLModel wrapper versions
of the metadata models instead of the Pydantic BaseModel versions.
"""

from iptvportal.models.sqlmodel_wrappers import (
    ExecutionMetadata,
    JSONSQLQueryInput,
    QueryResult,
    SQLQueryInput,
)


def example_sql_query_input():
    """Example of using SQLQueryInput with SQLModel."""
    # Create a SQL query input with validation
    query_input = SQLQueryInput(
        sql="SELECT id, username, email FROM subscriber WHERE disabled = false",
        use_cache=True,
        use_schema_mapping=True,
        timeout=60,
        dry_run=False,
    )

    print(f"SQL Query: {query_input.sql}")
    print(f"Use cache: {query_input.use_cache}")
    print(f"Timeout: {query_input.timeout}s")

    # Serialize to dict
    data = query_input.model_dump()
    print(f"Serialized: {data}")

    return query_input


def example_jsonsql_query_input():
    """Example of using JSONSQLQueryInput with SQLModel."""
    # Create a JSONSQL query input
    jsonsql_input = JSONSQLQueryInput(
        method="select",
        params={
            "from": "subscriber",
            "data": ["id", "username", "email"],
            "where": {"disabled": False},
            "limit": 10,
        },
        use_cache=True,
        timeout=30,
    )

    print(f"Method: {jsonsql_input.method}")
    print(f"Params: {jsonsql_input.params}")

    return jsonsql_input


def example_query_result():
    """Example of using QueryResult with SQLModel."""
    # Create a query result
    result = QueryResult(
        data=[
            {"id": 1, "username": "alice", "email": "alice@example.com"},
            {"id": 2, "username": "bob", "email": "bob@example.com"},
            {"id": 3, "username": "charlie", "email": "charlie@example.com"},
        ],
        sql="SELECT id, username, email FROM subscriber LIMIT 3",
        jsonsql={
            "from": "subscriber",
            "data": ["id", "username", "email"],
            "limit": 3,
        },
        method="select",
        table="subscriber",
        execution_time_ms=42.5,
    )

    # Row count is automatically calculated
    print(f"Rows returned: {result.row_count}")
    print(f"Table: {result.table}")
    print(f"Execution time: {result.execution_time_ms}ms")
    print(f"First row: {result.data[0]}")

    return result


def example_execution_metadata():
    """Example of using ExecutionMetadata with SQLModel."""
    # Create execution metadata
    metadata = ExecutionMetadata(
        cached=True,
        cache_key="query:subscriber:12345",
        request_id=42,
        timestamp="2024-01-15T10:30:00Z",
    )

    print(f"Cached: {metadata.cached}")
    print(f"Cache key: {metadata.cache_key}")
    print(f"Request ID: {metadata.request_id}")
    print(f"Timestamp: {metadata.timestamp}")

    return metadata


def example_with_orm_usage():
    """Example showing potential ORM usage with SQLModel wrappers.

    Note: These models can be used with SQLAlchemy/SQLModel's ORM features
    if you need database persistence.
    """
    # The SQLModel wrappers inherit from SQLModel, so they can be used
    # with SQLAlchemy engines and sessions if needed
    from sqlmodel import create_engine

    # Example: Create an in-memory SQLite database
    _ = create_engine("sqlite:///:memory:")

    # Note: For actual ORM usage with database tables, you would need to
    # add table=True to the model definitions and create the tables.
    # The current implementation is designed for API models, not database tables.

    print("SQLModel wrappers can be extended for ORM usage if needed")


if __name__ == "__main__":
    print("=" * 60)
    print("SQLModel Wrappers Examples")
    print("=" * 60)

    print("\n1. SQLQueryInput Example")
    print("-" * 60)
    example_sql_query_input()

    print("\n2. JSONSQLQueryInput Example")
    print("-" * 60)
    example_jsonsql_query_input()

    print("\n3. QueryResult Example")
    print("-" * 60)
    example_query_result()

    print("\n4. ExecutionMetadata Example")
    print("-" * 60)
    example_execution_metadata()

    print("\n5. ORM Usage Note")
    print("-" * 60)
    example_with_orm_usage()

    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
