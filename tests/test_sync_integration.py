"""Integration tests for sync functionality end-to-end.

Run with:
    uv run pytest tests/test_sync_integration.py
    uv run pytest tests/test_sync_integration.py -v -s
"""

import asyncio
import os
import tempfile
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr

from iptvportal.async_client import AsyncIPTVPortalClient
from iptvportal.config import IPTVPortalSettings
from iptvportal.introspector import SchemaIntrospector
from iptvportal.schema import (
    FieldDefinition,
    FieldType,
    SchemaRegistry,
    SyncConfig,
    TableMetadata,
    TableSchema,
)
from iptvportal.sync.database import SyncDatabase
from iptvportal.sync.manager import SyncManager


class TestSyncIntegration:
    """End-to-end sync integration tests."""

    @staticmethod
    def create_user_schema(where_clause: Optional[str] = None, chunk_size: int = 50) -> TableSchema:
        """Factory for creating user table schema."""
        return TableSchema(
            table_name="users",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="email", position=1, field_type=FieldType.STRING),
                2: FieldDefinition(name="name", position=2, field_type=FieldType.STRING),
                3: FieldDefinition(name="created_at", position=3, field_type=FieldType.DATETIME),
                4: FieldDefinition(name="active", position=4, field_type=FieldType.BOOLEAN),
            },
            total_fields=5,
            sync_config=SyncConfig(where=where_clause, cache_strategy="full", chunk_size=chunk_size),
            metadata=TableMetadata(row_count=3),
        )

    @staticmethod
    def create_sample_user_data(count: int = 3) -> List[List[Any]]:
        """Factory for generating sample user data."""
        users = [
            [1, "alice@example.com", "Alice Johnson", "2023-01-01T10:00:00", True],
            [2, "bob@example.com", "Bob Smith", "2023-01-02T11:00:00", False],
            [3, "charlie@example.com", "Charlie Brown", "2023-01-03T12:00:00", True],
            [4, "diana@example.com", "Diana Prince", "2023-01-04T13:00:00", True],
            [5, "eve@example.com", "Eve Wilson", "2023-01-05T14:00:00", False],
        ]
        return users[:count]

    @staticmethod
    def create_product_schema(chunk_size: int = 50) -> TableSchema:
        """Factory for creating product table schema."""
        return TableSchema(
            table_name="products",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="title", position=1, field_type=FieldType.STRING),
                2: FieldDefinition(name="price", position=2, field_type=FieldType.FLOAT),
            },
            total_fields=3,
            sync_config=SyncConfig(cache_strategy="full", chunk_size=chunk_size),
        )

    @staticmethod
    def create_sample_product_data(count: int = 1) -> List[List[Any]]:
        """Factory for generating sample product data."""
        products = [
            [1, "Widget", 19.99],
            [2, "Gadget", 29.99],
            [3, "Tool", 39.99],
        ]
        return products[:count]

    @staticmethod
    def create_large_table_schema(total_rows: int, chunk_size: int) -> TableSchema:
        """Factory for creating large table schema."""
        return TableSchema(
            table_name="large_table",
            fields={0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER)},
            total_fields=1,
            sync_config=SyncConfig(cache_strategy="full", chunk_size=chunk_size),
            metadata=TableMetadata(row_count=total_rows),
        )

    @staticmethod
    def create_large_table_data(total_rows: int) -> List[List[Any]]:
        """Factory for generating large table data."""
        return [[i + 1] for i in range(total_rows)]

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        settings = IPTVPortalSettings(
            domain="test.example.com", username="test_user", password=SecretStr("test_password")
        )
        settings.cache_db_journal_mode = "MEMORY"  # Faster for tests
        settings.cache_db_cache_size = -1000  # 1MB for tests
        settings.default_sync_strategy = "full"
        settings.default_chunk_size = 50  # Small chunks for testing
        settings.default_sync_ttl = 3600
        return settings

    @pytest.fixture
    def mock_client(self):
        """Mock AsyncIPTVPortalClient with realistic responses."""
        client = AsyncMock(spec=AsyncIPTVPortalClient)

        # Mock sample data for user table
        user_sample_data = [
            [1, "alice@example.com", "Alice Johnson", "2023-01-01T10:00:00", True],
            [2, "bob@example.com", "Bob Smith", "2023-01-02T11:00:00", False],
            [3, "charlie@example.com", "Charlie Brown", "2023-01-03T12:00:00", True],
        ]

        # Mock COUNT query
        client.execute.side_effect = lambda query: self._mock_execute(query, user_sample_data)

        return client

    def _mock_execute(self, query, sample_data):
        """Mock execute method with realistic responses."""
        if isinstance(query, dict) and "method" in query:
            method = query["method"]
            params = query.get("params", {})

            if method == "select":
                data = params.get("data", [])
                from_table = params.get("from", "")
                limit = params.get("limit", 1000)
                offset = params.get("offset", 0)

                if data == ["*"] and from_table == "users":
                    # Return sample data for introspection
                    if limit == 1 and offset == 0:
                        return [sample_data[0]]  # First row for schema detection
                    if limit == 1 and offset == 0 and "COUNT(*)" in str(data):
                        return [[len(sample_data)]]
                    # Return chunked data
                    start_idx = offset
                    end_idx = min(offset + limit, len(sample_data))
                    return sample_data[start_idx:end_idx] if start_idx < len(sample_data) else []

                if "COUNT(*)" in str(data):
                    # COUNT query
                    return [[len(sample_data)]]

                if "MAX(id)" in str(data) and "MIN(id)" in str(data):
                    # ID stats query
                    ids = [row[0] for row in sample_data]
                    return [[max(ids), min(ids)]]

                if "MIN(" in str(data) and "MAX(" in str(data) and "created_at" in str(data):
                    # Timestamp range query
                    timestamps = [row[3] for row in sample_data]
                    return [[min(timestamps), max(timestamps)]]

        return []

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_schema_introspection_and_registration(self, temp_db_path: str, settings: IPTVPortalSettings, mock_client: AsyncMock) -> None:
        """Test schema introspection and database registration."""
        # Setup components
        database = SyncDatabase(temp_db_path, settings)
        database.initialize()

        introspector = SchemaIntrospector(mock_client)
        schema_registry = SchemaRegistry()

        # Introspect table schema
        schema = await introspector.introspect_table("users", gather_metadata=True)
        assert schema.table_name == "users"
        assert len(schema.fields) == 5  # id, email, name, timestamp, boolean
        assert schema.total_fields == 5

        # Register schema and create table
        schema_registry.register(schema)
        database.create_data_table(schema)
        database.register_table(schema)

        # Verify schema registration
        registered_schema = schema_registry.get("users")
        assert registered_schema is not None
        assert registered_schema.table_name == "users"

        # Verify table creation
        metadata = database.get_metadata("users")
        assert metadata is not None
        assert "schema_hash" in metadata

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_full_sync_execution(self, temp_db_path: str, settings: IPTVPortalSettings, mock_client: AsyncMock) -> None:
        """Test full sync execution with proper setup."""
        # Setup with pre-registered schema using factory
        database = SyncDatabase(temp_db_path, settings)
        database.initialize()

        schema = self.create_user_schema()
        schema_registry = SchemaRegistry()
        schema_registry.register(schema)
        database.create_data_table(schema)
        database.register_table(schema)

        sync_manager = SyncManager(database, mock_client, schema_registry, settings)

        # Execute full sync
        result = await sync_manager.sync_table("users")

        # Verify sync results
        assert result.status == "success", f"Sync failed: {result.error_message}"
        assert result.strategy == "full"
        assert result.rows_fetched == 3
        assert result.rows_inserted == 3
        assert result.chunks_processed >= 1

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_sync_data_integrity(self, temp_db_path: str, settings: IPTVPortalSettings, mock_client: AsyncMock) -> None:
        """Test data integrity after sync completion."""
        # Setup and perform sync
        database = SyncDatabase(temp_db_path, settings)
        database.initialize()

        schema = TableSchema(
            table_name="users",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="email", position=1, field_type=FieldType.STRING),
                2: FieldDefinition(name="name", position=2, field_type=FieldType.STRING),
                3: FieldDefinition(name="created_at", position=3, field_type=FieldType.DATETIME),
                4: FieldDefinition(name="active", position=4, field_type=FieldType.BOOLEAN),
            },
            total_fields=5,
            sync_config=SyncConfig(cache_strategy="full", chunk_size=50),
            metadata=TableMetadata(row_count=3),
        )

        schema_registry = SchemaRegistry()
        schema_registry.register(schema)
        database.create_data_table(schema)
        database.register_table(schema)

        sync_manager = SyncManager(database, mock_client, schema_registry, settings)
        await sync_manager.sync_table("users")

        # Verify data integrity
        users_data = database.execute_query("users", "SELECT * FROM users ORDER BY id")
        assert len(users_data) == 3, f"Expected 3 rows, got {len(users_data)}"

        # Check first row
        row1 = users_data[0]
        assert row1["id"] == 1, f"Expected id=1, got {row1['id']}"
        assert row1["email"] == "alice@example.com"
        assert row1["name"] == "Alice Johnson"
        assert row1["created_at"] == "2023-01-01T10:00:00"
        assert row1["active"] == 1  # boolean True becomes 1 in SQLite

        # Check second row
        row2 = users_data[1]
        assert row2["id"] == 2
        assert row2["email"] == "bob@example.com"
        assert row2["name"] == "Bob Smith"
        assert row2["active"] == 0  # boolean False becomes 0 in SQLite

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_sync_metadata_tracking(self, temp_db_path: str, settings: IPTVPortalSettings, mock_client: AsyncMock) -> None:
        """Test metadata tracking after sync operations."""
        # Setup and perform sync
        database = SyncDatabase(temp_db_path, settings)
        database.initialize()

        schema = TableSchema(
            table_name="users",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="email", position=1, field_type=FieldType.STRING),
                2: FieldDefinition(name="name", position=2, field_type=FieldType.STRING),
                3: FieldDefinition(name="created_at", position=3, field_type=FieldType.DATETIME),
                4: FieldDefinition(name="active", position=4, field_type=FieldType.BOOLEAN),
            },
            total_fields=5,
            sync_config=SyncConfig(cache_strategy="full", chunk_size=50),
            metadata=TableMetadata(row_count=3),
        )

        schema_registry = SchemaRegistry()
        schema_registry.register(schema)
        database.create_data_table(schema)
        database.register_table(schema)

        sync_manager = SyncManager(database, mock_client, schema_registry, settings)
        await sync_manager.sync_table("users")

        # Verify metadata tracking
        metadata = database.get_metadata("users")
        assert metadata is not None, "Metadata should exist after sync"
        assert metadata["row_count"] == 3
        assert metadata["local_row_count"] == 3
        assert metadata["total_syncs"] == 1
        assert metadata["strategy"] == "full"
        assert "created_at" in metadata  # Sync creates metadata with timestamp

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_incremental_sync_workflow(self, temp_db_path, settings, mock_client):
        """Test incremental sync workflow."""
        # 1. Setup initial full sync
        database = SyncDatabase(temp_db_path, settings)
        database.initialize()

        SchemaIntrospector(mock_client)
        schema_registry = SchemaRegistry()

        # Create schema with incremental config
        schema = TableSchema(
            table_name="users",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="email", position=1, field_type=FieldType.STRING),
                2: FieldDefinition(name="name", position=2, field_type=FieldType.STRING),
                3: FieldDefinition(name="updated_at", position=3, field_type=FieldType.DATETIME),
                4: FieldDefinition(name="active", position=4, field_type=FieldType.BOOLEAN),
            },
            total_fields=5,
            sync_config=SyncConfig(
                cache_strategy="incremental",
                incremental_mode=True,
                incremental_field="updated_at",
                chunk_size=50,
            ),
            metadata=TableMetadata(row_count=100),
        )
        schema_registry.register(schema)

        # Create table in database
        database.create_data_table(schema)
        database.register_table(schema)

        sync_manager = SyncManager(database, mock_client, schema_registry, settings)

        # Set up mock for initial full sync
        class FullSyncMock:
            def __init__(self):
                self.full_data = [
                    [1, "alice@example.com", "Alice Johnson", "2023-01-01T10:00:00", True],
                    [2, "bob@example.com", "Bob Smith", "2023-01-02T11:00:00", False],
                    [3, "charlie@example.com", "Charlie Brown", "2023-01-03T12:00:00", True],
                ]

            def __call__(self, query):
                if isinstance(query, dict) and "method" in query:
                    params = query.get("params", {})
                    data = params.get("data", [])
                    limit = params.get("limit", 1000)
                    offset = params.get("offset", 0)

                    if data == ["*"] and params.get("from") == "users":
                        # Handle chunking queries for full sync
                        start_idx = offset
                        end_idx = min(offset + limit, len(self.full_data))
                        return (
                            self.full_data[start_idx:end_idx]
                            if start_idx < len(self.full_data)
                            else []
                        )
                    if "COUNT(*)" in str(data) and params.get("from") == "users":
                        # Count query
                        return [[len(self.full_data)]]
                    if limit == 1 and offset == 0 and params.get("from") == "users":
                        # Sample query for schema detection
                        return [self.full_data[0]]
                return []

        mock_client.execute.side_effect = FullSyncMock()

        # Initial full sync
        result1 = await sync_manager.sync_table("users", strategy="full")
        assert result1.status == "success"

        # Check metadata after full sync
        metadata = database.get_metadata("users")
        assert metadata is not None
        assert "last_sync_checkpoint" in metadata

        # 2. Setup incremental sync with new data
        class IncrementalSyncMock:
            def __init__(self):
                self.full_data = [
                    [1, "alice@example.com", "Alice Johnson", "2023-01-01T10:00:00", True],
                    [2, "bob@example.com", "Bob Smith", "2023-01-02T11:00:00", False],
                    [3, "charlie@example.com", "Charlie Brown", "2023-01-03T12:00:00", True],
                ]
                self.incremental_data = [
                    [4, "diana@example.com", "Diana Prince", "2023-01-04T13:00:00", True],
                    [5, "eve@example.com", "Eve Wilson", "2023-01-05T14:00:00", False],
                ]

            def __call__(self, query):
                if isinstance(query, dict) and "method" in query:
                    params = query.get("params", {})
                    where = params.get("where", {})
                    data = params.get("data", [])
                    limit = params.get("limit", 1000)
                    offset = params.get("offset", 0)

                    if data == ["*"] and params.get("from") == "users":
                        if not where:
                            start_idx = offset
                            end_idx = min(offset + limit, len(self.full_data))
                            return (
                                self.full_data[start_idx:end_idx]
                                if start_idx < len(self.full_data)
                                else []
                            )
                        if "gt" in where and where["gt"][0] == "updated_at":
                            start_idx = offset
                            end_idx = min(offset + limit, len(self.incremental_data))
                            return (
                                self.incremental_data[start_idx:end_idx]
                                if start_idx < len(self.incremental_data)
                                else []
                            )
                    if "COUNT(*)" in str(data) and params.get("from") == "users":
                        if "gt" in where and where["gt"][0] == "updated_at":
                            return [[len(self.incremental_data)]]
                        return [[len(self.full_data)]]
                    if limit == 1 and offset == 0 and params.get("from") == "users":
                        return [self.full_data[0]]
                return []

        mock_client.execute.side_effect = IncrementalSyncMock()

        # 3. Execute incremental sync (force=True to bypass staleness check)
        result2 = await sync_manager.sync_table("users", strategy="incremental", force=True)

        # 4. Verify incremental results
        assert result2.status == "success"
        assert result2.strategy == "incremental"
        assert result2.rows_fetched == 2
        assert result2.rows_inserted == 2  # New records
        assert result2.rows_updated == 0

        # 5. Verify total data
        users_data = database.execute_query("users", "SELECT COUNT(*) as count FROM users")
        assert users_data[0]["count"] == 5  # 3 original + 2 new

        # 6. Verify checkpoint updated
        metadata = database.get_metadata("users")
        assert metadata is not None
        assert metadata["total_syncs"] == 2
        assert metadata is not None and "last_sync_checkpoint" in metadata

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_concurrent_table_syncs(self, temp_db_path, settings, mock_client):
        """Test syncing multiple tables concurrently."""
        # Setup database and schemas
        database = SyncDatabase(temp_db_path, settings)
        database.initialize()

        schema_registry = SchemaRegistry()

        # Create schemas for multiple tables
        users_schema = TableSchema(
            table_name="users",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="name", position=1, field_type=FieldType.STRING),
            },
            total_fields=2,
            sync_config=SyncConfig(cache_strategy="full", chunk_size=50),
        )

        products_schema = TableSchema(
            table_name="products",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="title", position=1, field_type=FieldType.STRING),
                2: FieldDefinition(name="price", position=2, field_type=FieldType.FLOAT),
            },
            total_fields=3,
            sync_config=SyncConfig(cache_strategy="full", chunk_size=50),
        )

        schema_registry.register(users_schema)
        schema_registry.register(products_schema)

        # Create tables in database
        database.create_data_table(users_schema)
        database.register_table(users_schema)
        database.create_data_table(products_schema)
        database.register_table(products_schema)

        sync_manager = SyncManager(database, mock_client, schema_registry, settings)

        # Mock responses for both tables
        call_count = 0

        def mock_multi_table_execute(query):
            nonlocal call_count
            call_count += 1

            if isinstance(query, dict) and "method" in query:
                params = query.get("params", {})
                from_table = params.get("from", "")

                if from_table == "users":
                    if call_count % 2 == 1:  # Sample query
                        return [[1, "Alice"]]
                    # Count query
                    return [[1]]
                if from_table == "products":
                    if call_count % 2 == 1:  # Sample query
                        return [[1, "Widget", 19.99]]
                    # Count query
                    return [[1]]

            return []

        mock_client.execute.side_effect = mock_multi_table_execute

        # Sync all tables concurrently
        results = await sync_manager.sync_all(max_concurrent=2)

        # Verify results
        assert len(results) == 2
        assert "users" in results
        assert "products" in results

        assert results["users"].status == "success"
        assert results["products"].status == "success"

        # Verify data was inserted
        users_count = database.execute_query("users", "SELECT COUNT(*) as count FROM users")
        products_count = database.execute_query(
            "products", "SELECT COUNT(*) as count FROM products"
        )

        assert users_count[0]["count"] == 1
        assert products_count[0]["count"] == 1

    @pytest.mark.parametrize("where_clause,expected_rows,expected_count", [
        ("active = true", [
            [1, "alice@example.com", True],
            [3, "charlie@example.com", True],
        ], 2),
        ("active = false", [
            [2, "bob@example.com", False],
        ], 1),
    ])
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_sync_with_where_clause_filtering(
        self,
        temp_db_path: str,
        settings: IPTVPortalSettings,
        mock_client: AsyncMock,
        where_clause: str,
        expected_rows: List[List[Any]],
        expected_count: int
    ) -> None:
        """Test full sync honoring various WHERE clauses to filter records."""
        database = SyncDatabase(temp_db_path, settings)
        database.initialize()

        schema = TableSchema(
            table_name="users",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="email", position=1, field_type=FieldType.STRING),
                2: FieldDefinition(name="active", position=2, field_type=FieldType.BOOLEAN),
            },
            total_fields=3,
            sync_config=SyncConfig(where=where_clause, cache_strategy="full", chunk_size=50),
        )

        schema_registry = SchemaRegistry()
        schema_registry.register(schema)
        database.register_table(schema)

        sync_manager = SyncManager(database, mock_client, schema_registry, settings)

        # All possible rows for different WHERE conditions
        all_rows = [
            [1, "alice@example.com", True],
            [2, "bob@example.com", False],
            [3, "charlie@example.com", True],
        ]

        def mock_filtered_execute(query: Dict[str, Any]) -> List[List[Any]]:
            if isinstance(query, dict) and query.get("method") == "select":
                params = query.get("params", {})
                where = params.get("where")
                data = params.get("data")
                offset = params.get("offset", 0)

                if data == ["*"] and params.get("from") == "users":
                    # Apply WHERE filtering based on the clause
                    if where and isinstance(where, dict):
                        if "eq" in where:
                            col, val = where["eq"]
                            if col == "active":
                                filtered = [row for row in all_rows if row[2] == (val == "true")]
                                return filtered if offset == 0 else []
                            elif col == "id" and ">" in str(where):
                                # For id > 2, return rows where id > 2
                                filtered = [row for row in all_rows if row[0] > 2]
                                return filtered if offset == 0 else []
                        elif "gt" in where:
                            col, val = where["gt"]
                            if col == "id":
                                filtered = [row for row in all_rows if row[0] > int(val)]
                                return filtered if offset == 0 else []

                    # Sample row during schema introspection (limit=1, offset=0, no where)
                    if params.get("limit") == 1 and offset == 0:
                        return [expected_rows[0]] if expected_rows else [all_rows[0]]

                # COUNT query with WHERE clause
                if (
                    isinstance(data, list)
                    and any(
                        isinstance(item, dict) and item.get("function") == "count"
                        for item in data
                    )
                    and where
                ):
                    return [[expected_count]]

            return []

        mock_client.execute.side_effect = mock_filtered_execute

        result = await sync_manager.sync_table("users", strategy="full", force=True)
        assert result.status == "success", f"Sync failed for WHERE '{where_clause}': {result.error_message}"
        assert result.rows_fetched == expected_count, f"Expected {expected_count} rows, got {result.rows_fetched}"

        users_data = database.execute_query("users", "SELECT * FROM users ORDER BY id")
        assert len(users_data) == expected_count, f"Expected {expected_count} rows in database, got {len(users_data)}"

        # Verify the correct rows were inserted
        for i, expected_row in enumerate(expected_rows):
            actual_row = users_data[i]
            assert actual_row["id"] == expected_row[0], f"ID mismatch for row {i}"
            assert actual_row["email"] == expected_row[1], f"Email mismatch for row {i}"
            assert actual_row["active"] in (expected_row[2], int(expected_row[2])), f"Active status mismatch for row {i}"

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_sync_error_recovery(self, temp_db_path, settings, mock_client):
        """Test error handling: network failure should produce failed result and metadata update."""
        database = SyncDatabase(temp_db_path, settings)
        database.initialize()

        schema = TableSchema(
            table_name="users",
            fields={0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER)},
            total_fields=1,
            sync_config=SyncConfig(cache_strategy="full"),
        )
        schema_registry = SchemaRegistry()
        schema_registry.register(schema)
        database.register_table(schema)

        sync_manager = SyncManager(database, mock_client, schema_registry, settings)

        mock_client.execute.side_effect = Exception("Connection timeout")

        result = await sync_manager.sync_table("users", strategy="full", force=True)
        assert result.status == "failed"
        assert result.error_message and "Connection timeout" in result.error_message
        assert result.rows_fetched == 0

        metadata = database.get_metadata("users")
        assert metadata is not None
        assert metadata["last_error"] == "Connection timeout"
        assert metadata["failed_syncs"] == 1

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_schema_changes_detection(self, temp_db_path, settings, mock_client):
        """Schema hash should change when new field added."""
        database = SyncDatabase(temp_db_path, settings)
        database.initialize()

        schema1 = TableSchema(
            table_name="users",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="name", position=1, field_type=FieldType.STRING),
            },
            total_fields=2,
            sync_config=SyncConfig(cache_strategy="full"),
        )
        database.register_table(schema1)

        schema2 = TableSchema(
            table_name="users",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="name", position=1, field_type=FieldType.STRING),
                2: FieldDefinition(name="email", position=2, field_type=FieldType.STRING),
            },
            total_fields=3,
            sync_config=SyncConfig(cache_strategy="full"),
        )

        hash1 = database._calculate_schema_hash(schema1)
        hash2 = database._calculate_schema_hash(schema2)
        assert hash1 != hash2

        database.register_table(schema2)

        metadata = database.get_metadata("users")
        assert metadata is not None
        assert metadata["schema_hash"] == hash2

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_large_dataset_chunking(self, temp_db_path, settings, mock_client):
        """Full sync should process multiple chunks for large dataset."""
        database = SyncDatabase(temp_db_path, settings)
        database.initialize()

        total_rows = 25
        chunk_size = 10
        rows = [[i + 1] for i in range(total_rows)]  # Single-column id rows

        schema = TableSchema(
            table_name="large_table",
            fields={0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER)},
            total_fields=1,
            sync_config=SyncConfig(cache_strategy="full", chunk_size=chunk_size),
            metadata=TableMetadata(row_count=total_rows),
        )
        schema_registry = SchemaRegistry()
        schema_registry.register(schema)
        database.register_table(schema)

        sync_manager = SyncManager(database, mock_client, schema_registry, settings)

        def mock_large_execute(query):
            if isinstance(query, dict) and query.get("method") == "select":
                params = query.get("params", {})
                data = params.get("data")
                if data == ["*"] and params.get("from") == "large_table":
                    offset = params.get("offset", 0)
                    limit = params.get("limit", 100)
                    return rows[offset : offset + limit]
            return []

        mock_client.execute.side_effect = mock_large_execute

        result = await sync_manager.sync_table("large_table", strategy="full", force=True)
        assert result.status == "success"
        assert result.rows_fetched == total_rows
        # Expect 3 chunks: 10 + 10 + 5
        assert result.chunks_processed == 3

        count_result = database.execute_query(
            "large_table", "SELECT COUNT(*) as count FROM large_table"
        )
        assert count_result[0]["count"] == total_rows
