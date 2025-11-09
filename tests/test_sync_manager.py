"""Tests for SyncManager orchestration and sync strategies.

Run with:
    uv run pytest tests/test_sync_manager.py
    uv run pytest tests/test_sync_manager.py -v
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from iptvportal.core.async_client import AsyncIPTVPortalClient
from iptvportal.config.settings import IPTVPortalSettings
from iptvportal.schema import (
    FieldDefinition,
    FieldType,
    SchemaRegistry,
    SyncConfig,
    TableMetadata,
    TableSchema,
)
from iptvportal.sync.database import SyncDatabase
from iptvportal.sync.exceptions import SyncInProgressError, SyncStrategyError, TableNotFoundError
from iptvportal.sync.manager import SyncManager


class TestSyncManager:
    """Test SyncManager functionality."""

    @pytest.fixture
    def mock_client(self):
        """Mock AsyncIPTVPortalClient."""
        return AsyncMock(spec=AsyncIPTVPortalClient)

    @pytest.fixture
    def mock_database(self):
        """Mock SyncDatabase."""
        return MagicMock(spec=SyncDatabase)

    @pytest.fixture
    def schema_registry(self):
        """Create SchemaRegistry with test schema."""
        registry = SchemaRegistry()

        schema = TableSchema(
            table_name="test_table",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="name", position=1, field_type=FieldType.STRING),
            },
            total_fields=2,
            sync_config=SyncConfig(cache_strategy="full", chunk_size=100, ttl=3600),
            metadata=TableMetadata(row_count=1000),
        )

        registry.register(schema)
        return registry

    @pytest.fixture
    def settings(self):
        """Create mock settings."""
        settings = MagicMock(spec=IPTVPortalSettings)
        settings.default_sync_strategy = "full"
        settings.default_chunk_size = 1000
        settings.default_sync_ttl = 3600
        return settings

    @pytest.fixture
    def sync_manager(self, mock_database, mock_client, schema_registry, settings):
        """Create SyncManager instance."""
        return SyncManager(mock_database, mock_client, schema_registry, settings)

    @pytest.mark.asyncio
    async def test_sync_table_full_strategy(self, sync_manager, mock_database, mock_client):
        """Test full sync strategy."""
        # Setup mocks
        mock_database.is_stale.return_value = True
        mock_database.clear_table.return_value = 0  # No existing data

        # Mock chunked data fetching
        chunk1 = [[1, "Alice"], [2, "Bob"]]
        chunk2 = [[3, "Charlie"]]
        mock_client.execute.side_effect = [
            chunk1,  # First chunk
            chunk2,  # Second chunk
            [],  # Empty chunk to end
        ]

        mock_database.bulk_insert.side_effect = [2, 1]  # First chunk: 2 rows, Second chunk: 1 row
        mock_database.get_metadata.return_value = {"total_syncs": 0}  # Starting from 0 syncs

        # Execute sync
        result = await sync_manager.sync_table("test_table")

        # Verify result
        assert result.table_name == "test_table"
        assert result.strategy == "full"
        assert result.rows_fetched == 3
        assert result.rows_inserted == 3
        assert result.rows_updated == 0
        assert result.rows_deleted == 0
        assert result.chunks_processed == 2
        assert result.status == "success"

        # Verify database calls
        mock_database.clear_table.assert_called_once_with("test_table")
        assert mock_database.bulk_insert.call_count == 2  # Two chunks

        # Verify metadata update
        mock_database.update_metadata.assert_called_once()
        call_args = mock_database.update_metadata.call_args
        assert call_args[1]["row_count"] == 3
        assert call_args[1]["local_row_count"] == 3
        assert call_args[1]["last_sync_rows"] == 3
        assert call_args[1]["total_syncs"] == 1

    @pytest.mark.asyncio
    async def test_sync_table_incremental_strategy(self, sync_manager, mock_database, mock_client):
        """Test incremental sync strategy."""
        # Setup schema with incremental config
        schema = TableSchema(
            table_name="incremental_table",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="updated_at", position=1, field_type=FieldType.DATETIME),
            },
            total_fields=2,
            sync_config=SyncConfig(
                cache_strategy="incremental", incremental_mode=True, incremental_field="updated_at"
            ),
            metadata=TableMetadata(row_count=1000),
        )
        sync_manager.schema_registry.register(schema)

        # Setup mocks
        mock_database.is_stale.return_value = True
        mock_database.get_metadata.return_value = {
            "last_sync_checkpoint": "2023-01-01T00:00:00",
            "total_syncs": 1,
        }

        # Mock incremental data
        incremental_data = [[1, "2023-01-02T00:00:00"], [2, "2023-01-03T00:00:00"]]
        mock_client.execute.return_value = incremental_data
        mock_database.upsert_rows.return_value = (0, 2)  # 0 inserted, 2 updated

        # Execute sync
        result = await sync_manager.sync_table("incremental_table", strategy="incremental")

        # Verify result
        assert result.table_name == "incremental_table"
        assert result.strategy == "incremental"
        assert result.rows_fetched == 2
        assert result.rows_inserted == 0
        assert result.rows_updated == 2
        assert result.chunks_processed == 1
        assert result.status == "success"

        # Verify incremental query was made
        mock_client.execute.assert_called_once()
        call_args = mock_client.execute.call_args[0][0]
        assert call_args["params"]["where"]["gt"] == ["updated_at", "2023-01-01T00:00:00"]

    @pytest.mark.asyncio
    async def test_sync_table_incremental_fallback_to_full(
        self, sync_manager, mock_database, mock_client
    ):
        """Test incremental sync falls back to full when no checkpoint exists."""
        # Setup schema with incremental config but no previous sync
        schema = TableSchema(
            table_name="fallback_table",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
            },
            total_fields=1,
            sync_config=SyncConfig(
                cache_strategy="incremental", incremental_mode=True, incremental_field="updated_at"
            ),
        )
        sync_manager.schema_registry.register(schema)

        # Setup mocks - no checkpoint
        mock_database.is_stale.return_value = True
        mock_database.get_metadata.return_value = None  # No previous sync

        # Mock full sync data
        mock_client.execute.side_effect = [
            [[1], [2], [3]],  # Full data
            [],  # End of data
        ]
        mock_database.bulk_insert.return_value = 3
        mock_database.clear_table.return_value = 0

        # Execute sync
        result = await sync_manager.sync_table("fallback_table", strategy="incremental")

        # Should have fallen back to full sync
        assert result.strategy == "full"
        assert result.rows_fetched == 3

    @pytest.mark.asyncio
    async def test_sync_table_on_demand_strategy(self, sync_manager):
        """Test on-demand sync strategy (no-op)."""
        result = await sync_manager.sync_table("test_table", strategy="on_demand")

        assert result.table_name == "test_table"
        assert result.strategy == "on_demand"
        assert result.rows_fetched == 0
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_sync_table_not_stale_skip(self, sync_manager, mock_database):
        """Test skipping sync when data is not stale."""
        mock_database.is_stale.return_value = False

        result = await sync_manager.sync_table("test_table")

        assert result.status == "skipped"
        assert result.rows_fetched == 0

    @pytest.mark.asyncio
    async def test_sync_table_force_override_stale_check(
        self, sync_manager, mock_database, mock_client
    ):
        """Test forcing sync even when data appears fresh."""
        mock_database.is_stale.return_value = False  # Would normally skip

        # Setup full sync mocks
        mock_database.clear_table.return_value = 0
        mock_client.execute.side_effect = [
            [[1, "Alice"]],
            [],
        ]
        mock_database.bulk_insert.return_value = 1
        mock_database.get_metadata.return_value = {"total_syncs": 0}

        result = await sync_manager.sync_table("test_table", force=True)

        assert result.status == "success"
        assert result.rows_fetched == 1

    def test_sync_table_invalid_strategy(self, sync_manager):
        """Test error handling for invalid sync strategy."""
        with pytest.raises(SyncStrategyError, match="Invalid sync strategy"):
            asyncio.run(sync_manager.sync_table("test_table", strategy="invalid"))

    def test_sync_table_nonexistent_table(self, sync_manager):
        """Test error handling for non-existent table."""
        with pytest.raises(TableNotFoundError):
            asyncio.run(sync_manager.sync_table("nonexistent_table"))

    @pytest.mark.asyncio
    async def test_sync_table_concurrent_prevention(self, sync_manager, mock_database, mock_client):
        """Test preventing concurrent syncs of the same table."""
        # Setup mocks for the first sync
        mock_database.is_stale.return_value = True
        mock_database.clear_table.return_value = 0

        # Create a custom AsyncMock that delays execution
        call_count = 0

        async def slow_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                await asyncio.sleep(0.2)  # First call is slow
                return [[1, "Alice"]]
            return []  # Second call returns empty (end of chunks)

        mock_client.execute.side_effect = slow_execute
        mock_database.bulk_insert.return_value = 1
        mock_database.get_metadata.return_value = {"total_syncs": 0}

        # Start first sync
        task1 = asyncio.create_task(sync_manager.sync_table("test_table"))
        await asyncio.sleep(0.05)  # Let first task start and get into execution

        # Try second sync - should fail
        with pytest.raises(SyncInProgressError):
            await sync_manager.sync_table("test_table")

        # Complete first sync
        await task1

    @pytest.mark.asyncio
    async def test_sync_table_with_progress_callback(
        self, sync_manager, mock_database, mock_client
    ):
        """Test sync with progress callback."""
        progress_calls = []

        def progress_callback(progress):
            progress_calls.append(progress)

        # Setup mocks for full sync
        mock_database.is_stale.return_value = True
        mock_database.clear_table.return_value = 0

        mock_client.execute.side_effect = [
            [[1, "Alice"], [2, "Bob"]],
            [],
        ]
        mock_database.bulk_insert.return_value = 2
        mock_database.get_metadata.return_value = {"total_syncs": 0}

        await sync_manager.sync_table("test_table", progress_callback=progress_callback)

        assert len(progress_calls) == 1  # One chunk processed
        progress = progress_calls[0]
        assert progress.table_name == "test_table"
        assert progress.completed_chunks == 1
        assert progress.rows_synced == 2

    def test_get_sync_status(self, sync_manager, mock_database):
        """Test getting sync status for a table."""
        mock_database.get_metadata.return_value = {
            "strategy": "full",
            "last_sync_at": "2023-01-01T12:00:00",
            "next_sync_at": "2023-01-01T13:00:00",
            "row_count": 1000,
            "local_row_count": 1000,
            "last_error": None,
            "total_syncs": 5,
            "failed_syncs": 0,
        }

        with patch.object(sync_manager.database, "is_stale", return_value=False):
            status = sync_manager.get_sync_status("test_table")

        assert status["table_name"] == "test_table"
        assert status["strategy"] == "full"
        assert status["is_stale"] == False
        assert status["row_count"] == 1000
        assert status["local_row_count"] == 1000
        assert status["total_syncs"] == 5

    def test_get_sync_status_nonexistent_table(self, sync_manager, mock_database):
        """Test sync status for non-existent table."""
        mock_database.get_metadata.return_value = None

        status = sync_manager.get_sync_status("nonexistent_table")
        assert status["status"] == "not_registered"

    def test_get_all_sync_status(self, sync_manager, mock_database):
        """Test getting sync status for all tables."""
        mock_database.get_metadata.return_value = {
            "strategy": "full",
            "last_sync_at": "2023-01-01T12:00:00",
            "next_sync_at": None,
            "row_count": 1000,
            "local_row_count": 1000,
            "last_error": None,
            "total_syncs": 1,
            "failed_syncs": 0,
        }

        with patch.object(sync_manager.database, "is_stale", return_value=True):
            statuses = sync_manager.get_all_sync_status()

        assert len(statuses) == 1  # One table registered
        assert statuses[0]["table_name"] == "test_table"
        assert statuses[0]["is_stale"] == True

    @pytest.mark.asyncio
    async def test_sync_all_tables(self, sync_manager, mock_database, mock_client):
        """Test syncing all tables concurrently."""
        # Add another table
        schema2 = TableSchema(
            table_name="test_table2",
            fields={0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER)},
            total_fields=1,
            sync_config=SyncConfig(cache_strategy="full"),
        )
        sync_manager.schema_registry.register(schema2)

        # Setup mocks
        mock_database.is_stale.return_value = True
        mock_database.clear_table.return_value = 0

        # Mock responses for both tables (2 calls per table: data chunk + empty to end)
        mock_client.execute.side_effect = [
            # First table
            [[1, "Alice"]],
            [],
            # Second table
            [[1]],
            [],
        ]

        mock_database.bulk_insert.side_effect = [1, 1]  # One row each
        mock_database.get_metadata.return_value = {"total_syncs": 0}

        results = await sync_manager.sync_all(max_concurrent=2)

        assert len(results) == 2
        assert "test_table" in results
        assert "test_table2" in results

        assert results["test_table"].rows_fetched == 1
        assert results["test_table2"].rows_fetched == 1

    def test_cancel_sync(self, sync_manager):
        """Test cancelling ongoing sync operations."""
        # No active syncs initially
        assert sync_manager.cancel_sync("test_table") == False

        # Mock an active sync
        mock_task = MagicMock()
        mock_task.done.return_value = False
        sync_manager._active_syncs["test_table"] = mock_task

        # Cancel should succeed
        assert sync_manager.cancel_sync("test_table") == True
        mock_task.cancel.assert_called_once()

        # Task should still be in active syncs (cleanup happens in sync_table finally block)
        assert "test_table" in sync_manager._active_syncs

    @pytest.mark.asyncio
    async def test_sync_table_with_where_clause(self, sync_manager, mock_database, mock_client):
        """Test sync with WHERE clause filtering."""
        # Update schema with WHERE clause
        schema = sync_manager.schema_registry.get("test_table")
        schema.sync_config.where = "active = true"

        # Setup mocks
        mock_database.is_stale.return_value = True
        mock_database.clear_table.return_value = 0

        mock_client.execute.side_effect = [
            [[1, "Alice"], [3, "Charlie"]],
            [],
        ]
        mock_database.bulk_insert.return_value = 2
        mock_database.get_metadata.return_value = {"total_syncs": 0}

        result = await sync_manager.sync_table("test_table")

        assert result.rows_fetched == 2

    @pytest.mark.asyncio
    async def test_sync_table_error_handling(self, sync_manager, mock_database, mock_client):
        """Test error handling during sync operations."""
        mock_database.is_stale.return_value = True
        mock_client.execute.side_effect = Exception("Network error")

        result = await sync_manager.sync_table("test_table")

        assert result.status == "failed"
        assert "Network error" in result.error_message
        assert result.rows_fetched == 0
