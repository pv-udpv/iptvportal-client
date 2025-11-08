"""Asynchronous IPTVPortal client with async context management."""

import asyncio
from typing import Any, TypeVar

import httpx

from iptvportal.auth import AsyncAuthManager
from iptvportal.config import IPTVPortalSettings
from iptvportal.exceptions import APIError, ConnectionError, IPTVPortalError, TimeoutError
from iptvportal.query.builder import QueryBuilder
from iptvportal.schema import SchemaLoader, SchemaRegistry
from iptvportal.transpiler.transpiler import SQLTranspiler

T = TypeVar('T')


class AsyncIPTVPortalClient:
    """
    Asynchronous IPTVPortal API client, supports 'async with' and parallel execution.
    """

    def __init__(self, settings: IPTVPortalSettings | None = None, **kwargs):
        self.settings = settings or IPTVPortalSettings(**kwargs)
        self.auth = AsyncAuthManager(self.settings)
        self.query = QueryBuilder()
        self._http_client: httpx.AsyncClient | None = None
        self._session_id: str | None = None

        # Initialize schema registry
        self.schema_registry = SchemaRegistry()
        self._transpiler: SQLTranspiler | None = None

        # Auto-load schemas if configured
        if self.settings.auto_load_schemas and self.settings.schema_file:
            self._load_schemas()

    def _load_schemas(self) -> None:
        """Load schemas from configuration file."""
        if not self.settings.schema_file:
            return

        # Load schemas based on format
        if self.settings.schema_format.lower() == 'yaml':
            loaded_registry = SchemaLoader.from_yaml(self.settings.schema_file)
        elif self.settings.schema_format.lower() == 'json':
            loaded_registry = SchemaLoader.from_json(self.settings.schema_file)
        else:
            raise ValueError(f"Unsupported schema format: {self.settings.schema_format}")

        # Copy schemas to our registry
        for table_name in loaded_registry.list_tables():
            schema = loaded_registry.get(table_name)
            if schema:
                self.schema_registry.register(schema)

    def _get_transpiler(self) -> SQLTranspiler:
        """Get or create SQL transpiler with schema registry."""
        if self._transpiler is None:
            self._transpiler = SQLTranspiler(schema_registry=self.schema_registry)
        return self._transpiler

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self):
        self._http_client = httpx.AsyncClient(
            timeout=self.settings.timeout,
            verify=self.settings.verify_ssl,
            http2=True,
        )
        self._session_id = await self.auth.authenticate(self._http_client)

    async def close(self):
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
            self._session_id = None

    async def execute(self, query: dict[str, Any]) -> Any:
        if not self._http_client or not self._session_id:
            raise IPTVPortalError(
                "Async client not connected. Use 'async with' statement or call connect()."
            )
        headers = {
            "Iptvportal-Authorization": f"sessionid={self._session_id}",
            "Content-Type": "application/json",
        }
        last_error = None
        for attempt in range(self.settings.max_retries + 1):
            try:
                response = await self._http_client.post(
                    self.settings.api_url, json=query, headers=headers
                )
                response.raise_for_status()

                # Try to parse JSON response
                try:
                    data = response.json()
                except Exception as json_error:
                    raise APIError(
                        f"Failed to parse JSON response: {json_error}. "
                        f"Response text: {response.text[:500]}"
                    )

                # Debug: log response structure if log_requests is enabled
                if self.settings.log_requests:
                    print(f"Response data type: {type(data)}")
                    print(f"Response data keys: {data.keys() if isinstance(data, dict) else 'N/A'}")

                if "error" in data:
                    error_data = data["error"]
                    # Handle both string and dict error formats
                    if isinstance(error_data, str):
                        raise APIError(error_data)
                    if isinstance(error_data, dict):
                        raise APIError(
                            error_data.get("message", "API error"),
                            details=error_data,
                        )
                    raise APIError(f"API error: {error_data}")

                # Check if result key exists
                if "result" not in data:
                    raise APIError(
                        f"Invalid response format: missing 'result' key. Response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}"
                    )

                return data.get("result")
            except APIError:
                # Re-raise API errors without wrapping
                raise
            except httpx.TimeoutException as e:
                last_error = TimeoutError(f"Request timeout: {e}")
            except httpx.ConnectError as e:
                last_error = ConnectionError(f"Connection failed: {e}")
            except httpx.HTTPStatusError as e:
                # Try to get response body for better error messages
                try:
                    error_body = e.response.text
                    content_type = e.response.headers.get("content-type", "")
                    error_json = (
                        e.response.json() if content_type.startswith("application/json") else None
                    )

                    if error_json and "error" in error_json:
                        error_msg = (
                            f"HTTP {e.response.status_code}: "
                            f"{error_json['error'].get('message', str(e))}"
                        )
                    elif error_body:
                        # Limit body length
                        error_msg = f"HTTP {e.response.status_code}: {error_body[:500]}"
                    else:
                        error_msg = f"HTTP {e.response.status_code}: {e}"
                except Exception:
                    error_msg = f"HTTP {e.response.status_code}: {e}"

                if 400 <= e.response.status_code < 500:
                    raise APIError(error_msg) from e
                last_error = APIError(error_msg)
            except Exception as e:
                last_error = IPTVPortalError(f"Unexpected error: {e}")
            if attempt < self.settings.max_retries:
                delay = self.settings.retry_delay * (2**attempt)
                if self.settings.log_requests:
                    print(
                        f"Async retry {attempt + 1}/{self.settings.max_retries}, waiting {delay}s ..."
                    )
                await asyncio.sleep(delay)

        # If we get here, all retries failed
        if last_error:
            raise last_error
        raise IPTVPortalError("Request failed with unknown error")

    async def execute_many(self, queries: list[dict[str, Any]]) -> list[Any]:
        tasks = [self.execute(query) for query in queries]
        return await asyncio.gather(*tasks)

    async def execute_mapped(
        self,
        query: dict[str, Any],
        table_name: str | None = None,
        model: type[T] | None = None
    ) -> list[dict[str, Any]] | list[T]:
        """
        Execute query and automatically map results using schema.
        
        Args:
            query: Query dictionary to execute
            table_name: Table name for schema lookup (if not in query)
            model: Optional Pydantic/SQLModel model class for result mapping
            
        Returns:
            List of dictionaries or model instances (if model provided)
        """
        result = await self.execute(query)

        # Handle empty results
        if not result or not isinstance(result, list):
            return result

        # Try to determine table name from query if not provided
        if not table_name and isinstance(query.get('query'), str):
            # Simple extraction - try to get table name from query string
            sql = query.get('query', '').upper()
            if 'FROM' in sql:
                parts = sql.split('FROM')[1].split()
                if parts:
                    table_name = parts[0].strip().lower()

        # If we have table_name and schema, map the results
        if table_name and self.schema_registry.has(table_name):
            schema = self.schema_registry.get(table_name)
            if schema:
                if model:
                    # Map to model instances
                    return schema.map_rows_to_model(result)
                # Map to dictionaries
                return [schema.map_row_to_dict(row) for row in result]

        # No schema available, return raw results
        return result
