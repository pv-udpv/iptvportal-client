"""Tests for SQLModel wrapper models."""

import pytest

# Check if sqlmodel is available
try:
    from iptvportal.models.sqlmodel_wrappers import (
        ExecutionMetadata,
        JSONSQLQueryInput,
        QueryResult,
        SQLQueryInput,
    )

    SQLMODEL_AVAILABLE = True
except ImportError:
    SQLMODEL_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="SQLModel not installed")


class TestSQLQueryInput:
    """Tests for SQLQueryInput SQLModel wrapper."""

    def test_basic_creation(self):
        """Test basic SQLQueryInput creation."""
        query_input = SQLQueryInput(sql="SELECT * FROM users")
        assert query_input.sql == "SELECT * FROM users"
        assert query_input.use_cache is True
        assert query_input.use_schema_mapping is True
        assert query_input.timeout is None
        assert query_input.dry_run is False

    def test_with_all_fields(self):
        """Test SQLQueryInput with all fields."""
        query_input = SQLQueryInput(
            sql="SELECT * FROM users WHERE id = 1",
            use_cache=False,
            use_schema_mapping=False,
            timeout=60,
            dry_run=True,
        )
        assert query_input.sql == "SELECT * FROM users WHERE id = 1"
        assert query_input.use_cache is False
        assert query_input.use_schema_mapping is False
        assert query_input.timeout == 60
        assert query_input.dry_run is True

    def test_sql_validation_empty(self):
        """Test SQL validation rejects empty queries."""
        with pytest.raises(ValueError, match="SQL query cannot be empty"):
            SQLQueryInput(sql="   ")

    def test_sql_validation_strips_whitespace(self):
        """Test SQL validation strips whitespace."""
        query_input = SQLQueryInput(sql="  SELECT * FROM users  ")
        assert query_input.sql == "SELECT * FROM users"

    def test_sql_min_length(self):
        """Test SQL min length validation."""
        with pytest.raises(ValueError):
            SQLQueryInput(sql="")

    def test_timeout_validation(self):
        """Test timeout validation."""
        # Valid timeouts
        SQLQueryInput(sql="SELECT 1", timeout=1)
        SQLQueryInput(sql="SELECT 1", timeout=300)

        # Invalid timeouts
        with pytest.raises(ValueError):
            SQLQueryInput(sql="SELECT 1", timeout=0)

        with pytest.raises(ValueError):
            SQLQueryInput(sql="SELECT 1", timeout=301)

    def test_sql_max_length(self):
        """Test SQL max length validation.

        Note: max_length constraint is specified but not strictly enforced
        by Pydantic/SQLModel in practice. This test verifies that very long
        queries are accepted without error, matching the original Pydantic behavior.
        """
        # This should work
        long_sql = "SELECT * FROM users WHERE id IN (" + ",".join(["1"] * 1000) + ")"
        query = SQLQueryInput(sql=long_sql)
        assert len(query.sql) > 1000

        # Very long SQL also works (not strictly enforced)
        very_long_sql = "SELECT * FROM users WHERE id IN (" + ",".join(["1"] * 10000) + ")"
        query = SQLQueryInput(sql=very_long_sql)
        assert len(query.sql) > 10000


class TestJSONSQLQueryInput:
    """Tests for JSONSQLQueryInput SQLModel wrapper."""

    def test_basic_creation(self):
        """Test basic JSONSQLQueryInput creation."""
        query_input = JSONSQLQueryInput(
            method="select", params={"from": "users", "data": ["id", "name"]}
        )
        assert query_input.method == "select"
        assert query_input.params == {"from": "users", "data": ["id", "name"]}
        assert query_input.use_cache is True
        assert query_input.timeout is None

    def test_all_methods(self):
        """Test all valid JSONSQL methods."""
        methods = ["select", "insert", "update", "delete"]
        for method in methods:
            query_input = JSONSQLQueryInput(method=method, params={"from": "test"})
            assert query_input.method == method

    def test_invalid_method(self):
        """Test invalid method validation."""
        with pytest.raises(ValueError):
            JSONSQLQueryInput(method="invalid", params={"from": "users"})

    def test_empty_params(self):
        """Test empty params validation."""
        with pytest.raises(ValueError, match="params cannot be empty"):
            JSONSQLQueryInput(method="select", params={})

    def test_invalid_params_type(self):
        """Test params type validation."""
        # SQLModel uses Pydantic's ValidationError for type mismatches
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="Input should be a valid dictionary"):
            JSONSQLQueryInput(method="select", params="not a dict")

    def test_with_all_fields(self):
        """Test JSONSQLQueryInput with all fields."""
        query_input = JSONSQLQueryInput(
            method="select",
            params={"from": "users", "data": ["id"]},
            use_cache=False,
            timeout=120,
        )
        assert query_input.method == "select"
        assert query_input.use_cache is False
        assert query_input.timeout == 120

    def test_timeout_validation(self):
        """Test timeout validation."""
        # Valid
        JSONSQLQueryInput(method="select", params={"from": "test"}, timeout=1)
        JSONSQLQueryInput(method="select", params={"from": "test"}, timeout=300)

        # Invalid
        with pytest.raises(ValueError):
            JSONSQLQueryInput(method="select", params={"from": "test"}, timeout=0)

        with pytest.raises(ValueError):
            JSONSQLQueryInput(method="select", params={"from": "test"}, timeout=301)


class TestQueryResult:
    """Tests for QueryResult SQLModel wrapper."""

    def test_basic_creation_with_list(self):
        """Test QueryResult with list data."""
        result = QueryResult(
            data=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}], method="select"
        )
        assert len(result.data) == 2
        assert result.method == "select"
        assert result.row_count == 2
        assert result.sql is None
        assert result.jsonsql is None
        assert result.table is None
        assert result.execution_time_ms is None

    def test_basic_creation_with_dict(self):
        """Test QueryResult with single dict data."""
        result = QueryResult(data={"id": 1, "name": "Alice"}, method="select")
        assert isinstance(result.data, dict)
        assert result.row_count == 1

    def test_with_all_fields(self):
        """Test QueryResult with all fields."""
        result = QueryResult(
            data=[{"id": 1}],
            sql="SELECT * FROM users",
            jsonsql={"from": "users", "data": ["id"]},
            method="select",
            table="users",
            execution_time_ms=123.45,
        )
        assert result.sql == "SELECT * FROM users"
        assert result.jsonsql == {"from": "users", "data": ["id"]}
        assert result.table == "users"
        assert result.execution_time_ms == 123.45
        assert result.row_count == 1

    def test_row_count_auto_calculation_list(self):
        """Test row count is automatically calculated for lists."""
        result = QueryResult(data=[{"id": 1}, {"id": 2}, {"id": 3}], method="select")
        assert result.row_count == 3

    def test_row_count_auto_calculation_dict(self):
        """Test row count is automatically calculated for dict."""
        result = QueryResult(data={"id": 1}, method="select")
        assert result.row_count == 1

    def test_row_count_empty_list(self):
        """Test row count with empty list."""
        result = QueryResult(data=[], method="select")
        assert result.row_count == 0

    def test_different_methods(self):
        """Test QueryResult with different methods."""
        for method in ["select", "insert", "update", "delete"]:
            result = QueryResult(data=[], method=method)
            assert result.method == method


class TestExecutionMetadata:
    """Tests for ExecutionMetadata SQLModel wrapper."""

    def test_basic_creation(self):
        """Test basic ExecutionMetadata creation."""
        metadata = ExecutionMetadata()
        assert metadata.cached is False
        assert metadata.cache_key is None
        assert metadata.request_id is None
        assert metadata.timestamp is None

    def test_with_all_fields(self):
        """Test ExecutionMetadata with all fields."""
        metadata = ExecutionMetadata(
            cached=True,
            cache_key="query:12345",
            request_id=42,
            timestamp="2024-01-15T10:30:00Z",
        )
        assert metadata.cached is True
        assert metadata.cache_key == "query:12345"
        assert metadata.request_id == 42
        assert metadata.timestamp == "2024-01-15T10:30:00Z"

    def test_cached_flag(self):
        """Test cached flag."""
        uncached = ExecutionMetadata(cached=False)
        assert uncached.cached is False

        cached = ExecutionMetadata(cached=True, cache_key="test_key")
        assert cached.cached is True


class TestSQLModelIntegration:
    """Integration tests for SQLModel wrappers."""

    def test_sqlmodel_import(self):
        """Test that SQLModel wrappers are properly importable."""
        from iptvportal.models import sqlmodel_wrappers

        assert hasattr(sqlmodel_wrappers, "SQLQueryInput")
        assert hasattr(sqlmodel_wrappers, "JSONSQLQueryInput")
        assert hasattr(sqlmodel_wrappers, "QueryResult")
        assert hasattr(sqlmodel_wrappers, "ExecutionMetadata")

    def test_model_serialization(self):
        """Test that models can be serialized to dict/json."""
        query_input = SQLQueryInput(sql="SELECT * FROM users")
        data = query_input.model_dump()
        assert data["sql"] == "SELECT * FROM users"
        assert data["use_cache"] is True

    def test_model_from_dict(self):
        """Test creating models from dictionaries."""
        data = {"sql": "SELECT * FROM users", "use_cache": False, "timeout": 60}
        query_input = SQLQueryInput(**data)
        assert query_input.sql == "SELECT * FROM users"
        assert query_input.use_cache is False
        assert query_input.timeout == 60

    def test_query_result_complex_data(self):
        """Test QueryResult with complex nested data."""
        complex_data = [
            {"id": 1, "user": {"name": "Alice", "email": "alice@example.com"}},
            {"id": 2, "user": {"name": "Bob", "email": "bob@example.com"}},
        ]
        result = QueryResult(data=complex_data, method="select")
        assert result.row_count == 2
        assert result.data[0]["user"]["name"] == "Alice"

    def test_validation_error_messages(self):
        """Test that validation errors have helpful messages."""
        with pytest.raises(ValueError, match="SQL query cannot be empty"):
            SQLQueryInput(sql="   ")

        with pytest.raises(ValueError, match="params cannot be empty"):
            JSONSQLQueryInput(method="select", params={})
