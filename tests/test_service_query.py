"""Tests for QueryService."""

from unittest.mock import MagicMock, Mock

import pytest

from iptvportal.models.requests import JSONSQLQueryInput, SQLQueryInput
from iptvportal.service.query import QueryService


class TestQueryService:
    """Test QueryService orchestration."""

    def test_init_with_default_transpiler(self):
        """Test QueryService initializes with default transpiler."""
        mock_client = MagicMock()
        mock_client.schema_registry = MagicMock()
        mock_client.settings.auto_order_by_id = True
        
        service = QueryService(mock_client)
        
        assert service.client is mock_client
        assert service.transpiler is not None

    def test_init_with_custom_transpiler(self):
        """Test QueryService accepts custom transpiler."""
        mock_client = MagicMock()
        mock_transpiler = MagicMock()
        
        service = QueryService(mock_client, mock_transpiler)
        
        assert service.client is mock_client
        assert service.transpiler is mock_transpiler

    def test_execute_sql_dry_run(self):
        """Test execute_sql with dry_run returns without executing."""
        mock_client = MagicMock()
        mock_client.schema_registry = MagicMock()
        mock_client.settings.auto_order_by_id = True
        
        service = QueryService(mock_client)
        
        # Mock transpiler
        service.transpiler = MagicMock()
        service.transpiler.transpile.return_value = {
            "data": ["id", "username"],
            "from": "subscriber",
            "limit": 5
        }
        
        input_data = SQLQueryInput(
            sql="SELECT id, username FROM subscriber LIMIT 5",
            dry_run=True
        )
        
        result = service.execute_sql(input_data)
        
        # Should not call client.execute in dry run
        mock_client.execute.assert_not_called()
        
        # Result should contain metadata
        assert result.sql == input_data.sql
        assert result.jsonsql is not None
        assert result.method == "select"
        assert result.table == "subscriber"
        assert result.row_count == 0

    def test_execute_sql_with_schema_mapping(self):
        """Test execute_sql with schema mapping enabled."""
        mock_client = MagicMock()
        mock_client.schema_registry = MagicMock()
        mock_client.settings.auto_order_by_id = True
        
        # Mock execute to return data
        mock_data = [{"id": 1}, {"id": 2}]
        mock_client.execute.return_value = mock_data
        
        # Mock schema mapping method
        mock_client._map_result_with_schema = MagicMock(return_value=mock_data)
        
        service = QueryService(mock_client)
        
        # Mock transpiler
        service.transpiler = MagicMock()
        service.transpiler.transpile.return_value = {
            "data": ["id", "username"],
            "from": "subscriber",
            "limit": 5
        }
        
        input_data = SQLQueryInput(
            sql="SELECT id, username FROM subscriber LIMIT 5",
            use_schema_mapping=True
        )
        
        result = service.execute_sql(input_data)
        
        # Should call client.execute
        mock_client.execute.assert_called_once()
        
        # Result should contain data
        assert result.data == mock_data
        assert result.method == "select"
        assert result.table == "subscriber"
        assert result.row_count == 2

    def test_execute_jsonsql(self):
        """Test execute_jsonsql directly."""
        mock_client = MagicMock()
        mock_client.schema_registry = MagicMock()
        mock_client.settings.auto_order_by_id = True
        mock_client.execute.return_value = [{"id": 1}, {"id": 2}]
        
        service = QueryService(mock_client)
        
        input_data = JSONSQLQueryInput(
            method="select",
            params={
                "data": ["id", "username"],
                "from": "subscriber",
                "limit": 5
            }
        )
        
        result = service.execute_jsonsql(input_data)
        
        # Should call client.execute
        mock_client.execute.assert_called_once()
        
        # Result should contain data
        assert result.data == [{"id": 1}, {"id": 2}]
        assert result.method == "select"
        assert result.table == "subscriber"
        assert result.row_count == 2

    def test_infer_method_select(self):
        """Test _infer_method for SELECT queries."""
        mock_client = MagicMock()
        mock_client.schema_registry = MagicMock()
        mock_client.settings.auto_order_by_id = True
        
        service = QueryService(mock_client)
        
        jsonsql = {"data": ["id"], "from": "subscriber"}
        assert service._infer_method(jsonsql) == "select"

    def test_infer_method_insert(self):
        """Test _infer_method for INSERT queries."""
        mock_client = MagicMock()
        mock_client.schema_registry = MagicMock()
        mock_client.settings.auto_order_by_id = True
        
        service = QueryService(mock_client)
        
        jsonsql = {"insert_data": {"username": "test"}, "into": "subscriber"}
        assert service._infer_method(jsonsql) == "insert"

    def test_extract_table_from_string(self):
        """Test _extract_table from simple 'from' field."""
        mock_client = MagicMock()
        mock_client.schema_registry = MagicMock()
        mock_client.settings.auto_order_by_id = True
        
        service = QueryService(mock_client)
        
        jsonsql = {"from": "subscriber"}
        assert service._extract_table(jsonsql, "select") == "subscriber"

    def test_extract_table_from_into(self):
        """Test _extract_table from 'into' field."""
        mock_client = MagicMock()
        mock_client.schema_registry = MagicMock()
        mock_client.settings.auto_order_by_id = True
        
        service = QueryService(mock_client)
        
        jsonsql = {"into": "subscriber"}
        assert service._extract_table(jsonsql, "insert") == "subscriber"

    def test_build_request(self):
        """Test _build_request creates proper JSON-RPC structure."""
        mock_client = MagicMock()
        mock_client.schema_registry = MagicMock()
        mock_client.settings.auto_order_by_id = True
        
        service = QueryService(mock_client)
        
        params = {"data": ["id"], "from": "subscriber"}
        request = service._build_request("select", params)
        
        assert request["jsonrpc"] == "2.0"
        assert request["method"] == "select"
        assert request["params"] == params
        assert "id" in request
