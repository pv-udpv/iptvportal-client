"""Query service for orchestrating query execution with business logic."""

import time
from typing import Any

from iptvportal.core.client import IPTVPortalClient
from iptvportal.jsonsql.transpiler import SQLTranspiler
from iptvportal.models.requests import JSONSQLQueryInput, SQLQueryInput
from iptvportal.models.responses import QueryResult


class QueryService:
    """Service layer for query execution.

    Orchestrates query execution with full business logic including:
    - SQL transpilation
    - Schema mapping
    - Caching
    - Validation

    Example:
        >>> from iptvportal import IPTVPortalClient, IPTVPortalSettings
        >>> from iptvportal.service.query import QueryService
        >>> from iptvportal.models.requests import SQLQueryInput
        >>>
        >>> settings = IPTVPortalSettings()
        >>> client = IPTVPortalClient(settings)
        >>> service = QueryService(client)
        >>>
        >>> with client:
        >>>     input_data = SQLQueryInput(sql="SELECT * FROM subscriber LIMIT 5")
        >>>     result = service.execute_sql(input_data)
        >>>     print(f"Got {result.row_count} rows")
    """

    def __init__(
        self,
        client: IPTVPortalClient,
        transpiler: SQLTranspiler | None = None,
    ):
        """Initialize QueryService.

        Args:
            client: IPTVPortal client for executing queries
            transpiler: Optional SQL transpiler (creates one if not provided)
        """
        self.client = client
        self.transpiler = transpiler or self._get_default_transpiler()

    def _get_default_transpiler(self) -> SQLTranspiler:
        """Get default transpiler with client's schema registry."""
        return SQLTranspiler(
            schema_registry=self.client.schema_registry,
            auto_order_by_id=self.client.settings.auto_order_by_id,
        )

    def execute_sql(self, input_data: SQLQueryInput) -> QueryResult:
        """Execute SQL query with transpilation and schema mapping.

        Args:
            input_data: Validated SQL query input

        Returns:
            QueryResult with data and metadata

        Raises:
            IPTVPortalError: If query execution fails
        """
        start_time = time.time()

        # 1. Transpile SQL → JSONSQL
        jsonsql = self.transpiler.transpile(input_data.sql)

        # 2. Infer method
        method = self._infer_method(jsonsql)

        # 3. Extract table for schema mapping
        table_name = self._extract_table(jsonsql, method)

        # If dry run, return without executing
        if input_data.dry_run:
            return QueryResult(
                data=[],
                sql=input_data.sql,
                jsonsql=jsonsql,
                method=method,
                table=table_name,
                row_count=0,
            )

        # 4. Execute via client
        raw_result = self.client.execute(self._build_request(method, jsonsql))

        # 5. Map with schema if needed
        if input_data.use_schema_mapping and table_name:
            result_data = self._map_with_schema(raw_result, table_name)
        else:
            result_data = raw_result

        execution_time_ms = (time.time() - start_time) * 1000

        return QueryResult(
            data=result_data,
            sql=input_data.sql,
            jsonsql=jsonsql,
            method=method,
            table=table_name,
            execution_time_ms=execution_time_ms,
        )

    def execute_jsonsql(self, input_data: JSONSQLQueryInput) -> QueryResult:
        """Execute JSONSQL query directly.

        Args:
            input_data: Validated JSONSQL query input

        Returns:
            QueryResult with data and metadata

        Raises:
            IPTVPortalError: If query execution fails
        """
        start_time = time.time()

        # Extract table name
        table_name = input_data.params.get("from")

        # Execute via client
        raw_result = self.client.execute(self._build_request(input_data.method, input_data.params))

        execution_time_ms = (time.time() - start_time) * 1000

        return QueryResult(
            data=raw_result,
            jsonsql=input_data.params,
            method=input_data.method,
            table=table_name,
            execution_time_ms=execution_time_ms,
        )

    def _infer_method(self, jsonsql: dict[str, Any]) -> str:
        """Infer JSONSQL method from transpiled query.

        Args:
            jsonsql: Transpiled JSONSQL query

        Returns:
            Method name (select, insert, update, delete)
        """
        # The transpiler already structures the query with the method as key
        if "data" in jsonsql and "from" in jsonsql:
            return "select"
        if "insert_data" in jsonsql:
            return "insert"
        if "update_data" in jsonsql:
            return "update"
        if "from" in jsonsql and "where" in jsonsql and "data" not in jsonsql:
            # JSONSQL with from+where and without data indicates a delete
            return "delete"
        return "select"

    def _extract_table(self, jsonsql: dict[str, Any], method: str) -> str | None:
        """Extract table name from JSONSQL query.

        Args:
            jsonsql: JSONSQL query parameters
            method: Query method

        Returns:
            Table name or None if not found
        """
        # Check for 'from' field (most common)
        if "from" in jsonsql:
            from_value = jsonsql["from"]
            if isinstance(from_value, str):
                return from_value
            if isinstance(from_value, list) and from_value:
                # Handle joins - return first table
                first_table = from_value[0]
                if isinstance(first_table, str):
                    return first_table
                if isinstance(first_table, dict) and "table" in first_table:
                    return first_table["table"]

        # Check for 'into' (insert queries)
        if "into" in jsonsql:
            return jsonsql["into"]

        return None

    def _build_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Build JSON-RPC request structure.

        Args:
            method: JSONSQL method
            params: Query parameters

        Returns:
            JSON-RPC request dictionary
        """
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }

    def _map_with_schema(self, data: Any, table_name: str) -> Any:
        """Map query results using schema definitions.

        Args:
            data: Raw query result
            table_name: Table name for schema lookup

        Returns:
            Schema-mapped data
        """
        # Use client's built-in schema mapping
        if hasattr(self.client, "_map_result_with_schema"):
            return self.client._map_result_with_schema(data, table_name)  # type: ignore[attr-defined]
        return data
