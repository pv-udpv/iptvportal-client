"""Synchronous IPTVPortal client with context manager and resource support."""

from pathlib import Path
from typing import Any, TypeVar

import httpx

from iptvportal.config import IPTVPortalSettings
from iptvportal.core.auth import AuthManager
from iptvportal.core.cache import QueryCache
from iptvportal.exceptions import APIError, ConnectionError, IPTVPortalError, TimeoutError
from iptvportal.jsonsql.builder import QueryBuilder
from iptvportal.jsonsql.transpiler import SQLTranspiler
from iptvportal.schema import SchemaLoader, SchemaRegistry

T = TypeVar("T")


class IPTVPortalClient:
    """
    Synchronous IPTVPortal API client.
    Use as context manager for automatic connection management.
    """

    def __init__(self, settings: IPTVPortalSettings | None = None, **kwargs):
        self.settings = settings or IPTVPortalSettings(**kwargs)
        self.auth = AuthManager(self.settings)
        self.query = QueryBuilder()
        self._http_client: httpx.Client | None = None
        self._session_id: str | None = None

        # Initialize schema registry
        self.schema_registry = SchemaRegistry()
        self._transpiler: SQLTranspiler | None = None

        # Initialize query cache
        self._cache: QueryCache | None = None
        if self.settings.enable_query_cache:
            self._cache = QueryCache(
                max_size=self.settings.cache_max_size,
                default_ttl=self.settings.cache_ttl,
            )

        # Auto-load schemas if configured
        if self.settings.auto_load_schemas and self.settings.schema_file:
            self._load_schemas()

    def _load_schemas(self) -> None:
        """Load schemas from configuration file or directory."""
        if not self.settings.schema_file:
            return

        schema_path = Path(self.settings.schema_file)
        
        # If it's a directory, load all schema files in it
        if schema_path.is_dir():
            self._load_schemas_from_directory(schema_path)
        # If it's a file, load single file
        elif schema_path.is_file():
            self._load_schema_file(schema_path)
        # If path doesn't exist, check if parent is config directory with multiple schema files
        elif not schema_path.exists():
            # Try loading from config directory if it exists
            config_dir = schema_path.parent if schema_path.parent.name == "config" else schema_path.parent / "config"
            if config_dir.exists() and config_dir.is_dir():
                self._load_schemas_from_directory(config_dir)
    
    def _load_schema_file(self, file_path: Path) -> None:
        """Load schemas from a single file."""
        try:
            # Load schemas based on format
            if file_path.suffix in [".yaml", ".yml"]:
                loaded_registry = SchemaLoader.from_yaml(str(file_path))
            elif file_path.suffix == ".json":
                loaded_registry = SchemaLoader.from_json(str(file_path))
            else:
                return
            
            # Copy schemas to our registry
            for table_name in loaded_registry.list_tables():
                schema = loaded_registry.get(table_name)
                if schema:
                    self.schema_registry.register(schema)
        except Exception:
            # Silently skip files that can't be loaded as schemas
            pass
    
    def _load_schemas_from_directory(self, directory: Path) -> None:
        """Load all schema files from a directory."""
        # Look for files ending with -schema.yaml, -schema.yml, or -schema.json
        schema_patterns = ["*-schema.yaml", "*-schema.yml", "*-schema.json", "schemas.yaml", "schemas.yml", "schemas.json"]
        
        for pattern in schema_patterns:
            for schema_file in directory.glob(pattern):
                if schema_file.is_file():
                    self._load_schema_file(schema_file)

    def _get_transpiler(self) -> SQLTranspiler:
        """Get or create SQL transpiler with schema registry."""
        if self._transpiler is None:
            self._transpiler = SQLTranspiler(
                schema_registry=self.schema_registry,
                auto_order_by_id=self.settings.auto_order_by_id,
            )
        return self._transpiler

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self):
        self._http_client = httpx.Client(
            timeout=self.settings.timeout,
            verify=self.settings.verify_ssl,
            http2=True,
        )
        self._session_id = self.auth.authenticate(self._http_client)

    def close(self):
        if self._http_client:
            self._http_client.close()
            self._http_client = None
            self._session_id = None

    def execute(self, query: dict[str, Any]) -> Any:
        if not self._http_client or not self._session_id:
            raise IPTVPortalError("Client not connected. Use 'with' statement or call connect().")

        # Check cache for read queries
        if self._cache and self._cache.is_read_query(query):
            query_hash = self._cache.compute_query_hash(query)
            cached_result = self._cache.get(query_hash)
            if cached_result is not None:
                if self.settings.log_requests:
                    print(f"Cache hit for query hash: {query_hash[:16]}...")
                return cached_result

        headers = {
            "Iptvportal-Authorization": f"sessionid={self._session_id}",
            "Content-Type": "application/json",
        }
        import time

        last_error: Exception | None = None
        for attempt in range(self.settings.max_retries + 1):
            try:
                response = self._http_client.post(
                    self.settings.api_url, json=query, headers=headers
                )
                response.raise_for_status()
                data = response.json()
                if "error" in data:
                    raise APIError(
                        data["error"].get("message", "API error"),
                        details=data["error"],
                    )
                result = data.get("result")

                # Cache result for read queries
                if self._cache and self._cache.is_read_query(query):
                    query_hash = self._cache.compute_query_hash(query)
                    self._cache.set(query_hash, result)
                    if self.settings.log_requests:
                        print(f"Cached result for query hash: {query_hash[:16]}...")

                return result
            except httpx.TimeoutException as e:
                last_error = TimeoutError(f"Request timeout: {e}")
            except httpx.ConnectError as e:
                last_error = ConnectionError(f"Connection failed: {e}")
            except httpx.HTTPStatusError as e:
                # Try to get response body for better error messages
                try:
                    error_body = e.response.text
                    error_json = (
                        e.response.json()
                        if e.response.headers.get("content-type", "").startswith("application/json")
                        else None
                    )

                    if error_json and "error" in error_json:
                        error_msg = f"HTTP {e.response.status_code}: {error_json['error'].get('message', str(e))}"
                    elif error_body:
                        error_msg = f"HTTP {e.response.status_code}: {error_body[:500]}"  # Limit body length
                    else:
                        error_msg = f"HTTP {e.response.status_code}: {e}"
                except Exception:
                    error_msg = f"HTTP {e.response.status_code}: {e}"

                if 400 <= e.response.status_code < 500:
                    raise APIError(error_msg)
                last_error = APIError(error_msg)
            except Exception as e:
                last_error = IPTVPortalError(f"Unexpected error: {e}")
            if attempt < self.settings.max_retries:
                delay = self.settings.retry_delay * (2**attempt)
                if self.settings.log_requests:
                    print(
                        f"Retry attempt {attempt + 1}/{self.settings.max_retries}, waiting {delay}s..."
                    )
                time.sleep(delay)

        if last_error:
            raise last_error
        raise IPTVPortalError("Request failed with no error captured")

    def execute_mapped(
        self, query: dict[str, Any], table_name: str | None = None, model: type[T] | None = None
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
        result = self.execute(query)

        # Handle empty results
        if not result or not isinstance(result, list):
            return result

        # Try to determine table name from query if not provided
        if not table_name and isinstance(query.get("query"), str):
            # Simple extraction - try to get table name from query string
            sql = query.get("query", "").upper()
            if "FROM" in sql:
                parts = sql.split("FROM")[1].split()
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
