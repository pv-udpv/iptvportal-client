"""Integration tests for sync functionality end-to-end.

Run with:
    uv run pytest tests/test_sync_integration.py
    uv run pytest tests/test_sync_integration.py -v -s
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

from iptvportal.schema import TableSchema, FieldDefinition, FieldType, SyncConfig, TableMetadata, SchemaRegistry
from iptvportal.introspector import SchemaIntrospector
from iptvportal.sync.database import SyncDatabase
from iptvportal.sync.manager import SyncManager
from iptvportal.async_client import AsyncIPTVPortalClient
from iptvportal.config import IPTVPortalSettings

class TestSyncIntegration:
    """End-to-end sync integration tests."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database file."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        settings = IPTVPortalSettings()
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
            [3, "charlie@example.com", "Charlie Brown", "2023-01-03T12:00:00", True]
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
                    elif limit == 1 and offset == 0 and "COUNT(*)" in str(data):
                        return [[len(sample_data)]]
                    else:
                        # Return chunked data
                        start_idx = offset
                        end_idx = min(offset + limit, len(sample_data))
                        return sample_data[start_idx:end_idx] if start_idx < len(sample_data) else []

                elif "COUNT(*)" in str(data):
                    # COUNT query
                    return [[len(sample_data)]]

                elif "MAX(id)" in str(data) and "MIN(id)" in str(data):
                    # ID stats query
                    ids = [row[0] for row in sample_data]
                    return [[max(ids), min(ids)]]

                elif "MIN(" in str(data) and "MAX(" in str(data):
                    # Timestamp range query
                    if "created_at" in str(data):
                        timestamps = [row[3] for row in sample_data]
                        return [[min(timestamps), max(timestamps)]]

        return []

    @pytest.mark.asyncio
    async def test_full_sync_workflow(self, temp_db_path, settings, mock_client):
        """Test complete full sync workflow from introspection to sync."""
        # 1. Setup components
        database = SyncDatabase(temp_db_path, settings)
        database.initialize()

        introspector = SchemaIntrospector(mock_client)
        schema_registry = SchemaRegistry()

        # 2. Introspect table schema
        schema = await introspector.introspect_table("users", gather_metadata=True)
        schema_registry.register(schema)

        # 3. Create sync manager
        sync_manager = SyncManager(database, mock_client, schema_registry, settings)

        # 4. Execute full sync
        result = await sync_manager.sync_table("users")

        # 5. Verify results
        assert result.status == "success"
        assert result.strategy == "full"
        assert result.rows_fetched == 3
        assert result.rows_inserted == 3
        assert result.chunks_processed >= 1

        # 6. Verify data in database
        users_data = database.execute_query("users", "SELECT * FROM users ORDER BY id")
        assert len(users_data) == 3

        # Check data integrity
        assert users_data[0]["id"] == 1
        assert users_data[0]["name"] == "Alice Johnson"
        assert users_data[0]["email"] == "alice@example.com"
        assert users_data[0]["active"] == True

        assert users_data[1]["id"] == 2
        assert users_data[1]["name"] == "Bob Smith"
        assert users_data[1]["email"] == "bob@example.com"
        assert users_data[1]["active"] == False

        # 7. Verify metadata tracking
        metadata = database.get_metadata("users")
        assert metadata is not None
        assert metadata["row_count"] == 3
        assert metadata["local_row_count"] == 3
        assert metadata["total_syncs"] == 1
        assert metadata["strategy"] == "full"

    @pytest.mark.asyncio
    async def test_incremental_sync_workflow(self, temp_db_path, settings, mock_client):
        """Test incremental sync workflow."""
        # 1. Setup initial full sync
        database = SyncDatabase(temp_db_path, settings)
        database.initialize()

        introspector = SchemaIntrospector(mock_client)
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
                chunk_size=50
            ),
            metadata=TableMetadata(row_count=100)
        )
        schema_registry.register(schema)

        sync_manager = SyncManager(database, mock_client, schema_registry, settings)

        # Initial full sync
        result1 = await sync_manager.sync_table("users", strategy="full")
        assert result1.status == "success"

        # 2. Setup incremental sync with new data
        def mock_incremental_execute(query):
            """Mock incremental data response."""
            if isinstance(query, dict) and "method" in query:
                params = query.get("params", {})
                where = params.get("where", {})

                # Check if this is an incremental query
                if "gt" in where and where["gt"][0] == "updated_at":
                    # Return "new" data with timestamps after checkpoint
                    return [
                        [4, "diana@example.com", "Diana Prince", "2023-01-04T13:00:00", True],
                        [5, "eve@example.com", "Eve Wilson", "2023-01-05T14:00:00", False]
                    ]
            return []

        mock_client.execute.side_effect = mock_incremental_execute

        # 3. Execute incremental sync
        result2 = await sync_manager.sync_table("users", strategy="incremental")

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
        assert metadata["total_syncs"] == 2
        assert "last_sync_checkpoint" in metadata

    @pytest.mark.asyncio
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
            sync_config=SyncConfig(cache_strategy="full", chunk_size=50)
        )

        products_schema = TableSchema(
            table_name="products",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="title", position=1, field_type=FieldType.STRING),
                2: FieldDefinition(name="price", position=2, field_type=FieldType.FLOAT),
            },
            total_fields=3,
            sync_config=SyncConfig(cache_strategy="full", chunk_size=50)
        )

        schema_registry.register(users_schema)
        schema_registry.register(products_schema)

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
                    else:  # Count query
                        return [[1]]
                elif from_table == "products":
                    if call_count % 2 == 1:  # Sample query
                        return [[1, "Widget", 19.99]]
                    else:  # Count query
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
        products_count = database.execute_query("products", "SELECT COUNT(*) as count FROM products")

        assert users_count[0]["count"] == 1
        assert products_count[0]["count"] == 1

    @pytest.mark.asyncio
    async def test_sync_with_where_clause_filtering(self, temp_db_path, settings, mock_client):
        """Test sync with WHERE clause filtering active records."""
        # Setup schema with WHERE clause
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
            sync_config=SyncConfig(
                where="active = true",
                cache_strategy="full",
                chunk_size=50
            )
        )

        schema_registry = SchemaRegistry()
        schema_registry.register(schema)

        sync_manager = SyncManager(database, mock_client, schema_registry, settings)

        # Mock data with WHERE clause filtering
        def mock_filtered_execute(query):
            if isinstance(query, dict) and "method" in query:
                params = query.get("params", {})
                where = params.get("where", {})

                # Check if WHERE clause includes active filter
                if where and "eq" in where and where["eq"] == ["active", True]:
                    # Return only active users
                    return [
                        [1, "alice@example.com", True],
                        [3, "charlie@example.com", True]
                    ]
                elif params.get("limit") == 1:  # Sample query
                    return [[1, "alice@example.com", True]]
                elif "COUNT(*)" in str(params.get("data", [])):
                    return [[2]]  # Only 2 active users

            return []

        mock_client.execute.side_effect = mock_filtered_execute

        # Execute sync
        result = await sync_manager.sync_table("users")

        # Verify only active records were synced
        assert result.rows_fetched == 2
        assert result.status == "success"

        # Verify data
        users_data = database.execute_query("users", "SELECT * FROM users ORDER BY id")
        assert len(users_data) == 2

        # All synced users should be active
        for user in users_data:
            assert user["active"] == True

    @pytest.mark.asyncio
    async def test_sync_error_recovery(self, temp_db_path, settings, mock_client):
        """Test error handling and recovery in sync operations."""
        database = SyncDatabase(temp_db_path, settings)
        database.initialize()

        schema = TableSchema(
            table_name="users",
            fields={0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER)},
            total_fields=1,
            sync_config=SyncConfig(cache_strategy="full")
        )

        schema_registry = SchemaRegistry()
        schema_registry.register(schema)

        sync_manager = SyncManager(database, mock_client, schema_registry, settings)

        # Mock network failure
        mock_client.execute.side_effect = Exception("Connection timeout")

        # Execute sync - should handle error gracefully
        result = await sync_manager.sync_table("users")

        # Verify error was captured
        assert result.status == "failed"
        assert "Connection timeout" in result.error_message
        assert result.rows_fetched == 0

        # Verify error was recorded in metadata
        metadata = database.get_metadata("users")
        assert metadata["last_error"] == "Connection timeout"
        assert metadata["failed_syncs"] == 1

    @pytest.mark.asyncio
    async def test_schema_changes_detection(self, temp_db_path, settings, mock_client):
        """Test detection of schema changes between syncs."""
        database = SyncDatabase(temp_db_path, settings)
        database.initialize()

        # Initial schema
        schema1 = TableSchema(
            table_name="users",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="name", position=1, field_type=FieldType.STRING),
            },
            total_fields=2,
            sync_config=SyncConfig(cache_strategy="full")
        )

        database.register_table(schema1)

        # Simulate schema change (add email field)
        schema2 = TableSchema(
            table_name="users",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="name", position=1, field_type=FieldType.STRING),
                2: FieldDefinition(name="email", position=2, field_type=FieldType.STRING),
            },
            total_fields=3,
            sync_config=SyncConfig(cache_strategy="full")
        )

        # Schema hash should be different
        hash1 = database._calculate_schema_hash(schema1)
        hash2 = database._calculate_schema_hash(schema2)

        assert hash1 != hash2

        # Register new schema - should update hash
        database.register_table(schema2)

        metadata = database.get_metadata("users")
        assert metadata["schema_hash"] == hash2

    @pytest.mark.asyncio
    async def test_large_dataset_chunking(self, temp_db_path, settings, mock_client):
        """Test chunking behavior with large datasets."""
        database = SyncDatabase(temp_db_path, settings)
        database.initialize()

        schema = TableSchema(
            table_name="large_table",
            fields={0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER)},
            total_fields=1,
            sync_config=SyncConfig(
                cache_strategy="full",
                chunk_size=10  # Small chunks for testing
            ),
            metadata=TableMetadata(row_count=25)  # 25 rows = 3 chunks
        )

        schema_registry = SchemaRegistry()
        schema_registry.register(schema)

        sync_manager = SyncManager(database, mock_client, schema_registry, settings)

        # Mock chunked responses
        chunk_data = []
        for i in range(1, 26):  # 25 rows
            chunk_data.append([i])

        def mock_chunked_execute(query):
            if isinstance(query, dict) and "method" in query:
                params = query.get("params", {})
                offset = params.get("offset", 0)
                limit = params.get("limit", 10)

                if params.get("from") == "large_table":
                    if limit == 1 and offset == 0:  # Sample query
                        return [[1]]
                    elif "COUNT(*)" in str(params.get("data", [])):
                        return [[25]]
                    elif "MAX(id)" in str(params.get("data", [])):
                        return [[25, 1]]
                    else:
                        # Return appropriate chunk
                        start_idx = offset
                        end_idx = min(offset + limit, 25)
                        if start_idx < 25:
                            return chunk_data[start_idx:end_idx]
                        else:
                            return []

            return []

        mock_client.execute.side_effect = mock_chunked_execute

        # Execute sync
        result = await sync_manager.sync_table("large_table")

        # Verify chunking worked
        assert result.status == "success"
        assert result.rows_fetched == 25
        assert result.chunks_processed == 3  # 25 rows / 10 chunk_size = 3 chunks

        # Verify all data was inserted
        count_result = database.execute_query("large_table", "SELECT COUNT(*) as count FROM large_table")
        assert count_result[0]["count"] == 25
