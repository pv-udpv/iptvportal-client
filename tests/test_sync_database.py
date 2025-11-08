"""Tests for SyncDatabase SQLite operations.

Run with:
    uv run pytest tests/test_sync_database.py
    uv run pytest tests/test_sync_database.py -v
"""

import os
import tempfile
from unittest.mock import MagicMock

import pytest

from iptvportal.config import IPTVPortalSettings
from iptvportal.schema import FieldDefinition, FieldType, SyncConfig, TableMetadata, TableSchema
from iptvportal.sync.database import SyncDatabase


class TestSyncDatabase:
    """Test SyncDatabase functionality."""

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
        """Create mock settings."""
        settings = MagicMock(spec=IPTVPortalSettings)
        settings.cache_db_journal_mode = "WAL"
        settings.cache_db_cache_size = -64000  # 64MB
        settings.cache_db_page_size = 4096
        settings.default_sync_strategy = "full"
        settings.default_chunk_size = 1000
        settings.default_sync_ttl = 3600
        return settings

    @pytest.fixture
    def db(self, temp_db_path, settings):
        """Create SyncDatabase instance."""
        database = SyncDatabase(temp_db_path, settings)
        database.initialize()
        return database

    def test_initialization(self, db):
        """Test database initialization creates metadata tables."""
        # Check that metadata tables exist
        with db._get_connection() as conn:
            tables = conn.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name LIKE '_%'
            """).fetchall()

            table_names = [row[0] for row in tables]
            expected_tables = ["_sync_metadata", "_field_mappings", "_sync_history", "_cache_stats"]

            for table in expected_tables:
                assert table in table_names

    def test_register_table(self, db):
        """Test registering a table schema."""
        schema = TableSchema(
            table_name="test_table",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="name", position=1, field_type=FieldType.STRING),
                2: FieldDefinition(name="active", position=2, field_type=FieldType.BOOLEAN),
            },
            total_fields=3,
            sync_config=SyncConfig(cache_strategy="full", chunk_size=100, ttl=3600),
            metadata=TableMetadata(row_count=1000, max_id=1000, min_id=1),
        )

        db.register_table(schema)

        # Check metadata was stored
        metadata = db.get_metadata("test_table")
        assert metadata is not None
        assert metadata["table_name"] == "test_table"
        assert metadata["strategy"] == "full"
        assert metadata["chunk_size"] == 100
        assert metadata["ttl"] == 3600
        assert metadata["row_count"] == 1000
        assert metadata["max_id"] == 1000
        assert metadata["min_id"] == 1

        # Check field mappings were stored
        with db._get_connection() as conn:
            mappings = conn.execute(
                """
                SELECT * FROM _field_mappings
                WHERE table_name = ?
                ORDER BY position
            """,
                ("test_table",),
            ).fetchall()

            assert len(mappings) == 3

            # Check field mapping data
            id_mapping = mappings[0]
            assert id_mapping["position"] == 0
            assert id_mapping["field_name"] == "id"
            assert id_mapping["local_column"] == "id"
            assert id_mapping["field_type"] == "integer"
            assert id_mapping["is_primary_key"] == True

            name_mapping = mappings[1]
            assert name_mapping["position"] == 1
            assert name_mapping["field_name"] == "name"
            assert name_mapping["local_column"] == "name"
            assert name_mapping["field_type"] == "string"

    def test_bulk_insert(self, db):
        """Test bulk insert operations."""
        schema = TableSchema(
            table_name="bulk_test",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="name", position=1, field_type=FieldType.STRING),
            },
            total_fields=2,
        )

        # Register table first
        db.register_table(schema)

        # Test data
        rows = [[1, "Alice"], [2, "Bob"], [3, "Charlie"]]

        # Insert data
        inserted = db.bulk_insert("bulk_test", rows, schema)
        assert inserted == 3

        # Verify data was inserted
        results = db.execute_query("bulk_test", "SELECT * FROM bulk_test ORDER BY id")
        assert len(results) == 3

        assert results[0]["id"] == 1
        assert results[0]["name"] == "Alice"
        assert results[0]["_synced_at"] is not None  # Sync metadata added

        assert results[1]["id"] == 2
        assert results[1]["name"] == "Bob"

        assert results[2]["id"] == 3
        assert results[2]["name"] == "Charlie"

    def test_bulk_insert_with_conflicts_replace(self, db):
        """Test bulk insert with REPLACE conflict resolution."""
        schema = TableSchema(
            table_name="conflict_test",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="name", position=1, field_type=FieldType.STRING),
            },
            total_fields=2,
        )

        db.register_table(schema)

        # Insert initial data
        db.bulk_insert("conflict_test", [[1, "Alice"]], schema)

        # Insert conflicting data with REPLACE
        db.bulk_insert("conflict_test", [[1, "Alice Updated"]], schema, on_conflict="REPLACE")

        # Verify data was replaced
        results = db.execute_query("conflict_test", "SELECT * FROM conflict_test WHERE id = 1")
        assert len(results) == 1
        assert results[0]["name"] == "Alice Updated"

    def test_bulk_insert_with_conflicts_ignore(self, db):
        """Test bulk insert with IGNORE conflict resolution."""
        schema = TableSchema(
            table_name="ignore_test",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="name", position=1, field_type=FieldType.STRING),
            },
            total_fields=2,
        )

        db.register_table(schema)

        # Insert initial data
        db.bulk_insert("ignore_test", [[1, "Alice"]], schema)

        # Try to insert conflicting data with IGNORE
        db.bulk_insert("ignore_test", [[1, "Bob"]], schema, on_conflict="IGNORE")

        # Verify original data was preserved
        results = db.execute_query("ignore_test", "SELECT * FROM ignore_test WHERE id = 1")
        assert len(results) == 1
        assert results[0]["name"] == "Alice"

    def test_upsert_rows(self, db):
        """Test upsert (insert or update) operations."""
        schema = TableSchema(
            table_name="upsert_test",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="name", position=1, field_type=FieldType.STRING),
                2: FieldDefinition(name="email", position=2, field_type=FieldType.STRING),
            },
            total_fields=3,
        )

        db.register_table(schema)

        # Insert initial data
        db.bulk_insert("upsert_test", [[1, "Alice", "alice@example.com"]], schema)

        # Upsert (update existing, insert new)
        rows = [
            [1, "Alice Updated", "alice@example.com"],  # Update
            [2, "Bob", "bob@example.com"],  # Insert
        ]

        inserted, updated = db.upsert_rows("upsert_test", rows, schema)
        assert inserted == 1
        assert updated == 1

        # Verify results
        results = db.execute_query("upsert_test", "SELECT * FROM upsert_test ORDER BY id")
        assert len(results) == 2

        # Updated record
        assert results[0]["id"] == 1
        assert results[0]["name"] == "Alice Updated"
        assert results[0]["email"] == "alice@example.com"

        # New record
        assert results[1]["id"] == 2
        assert results[1]["name"] == "Bob"
        assert results[1]["email"] == "bob@example.com"

    def test_clear_table(self, db):
        """Test clearing all data from a table."""
        schema = TableSchema(
            table_name="clear_test",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="name", position=1, field_type=FieldType.STRING),
            },
            total_fields=2,
        )

        db.register_table(schema)

        # Insert test data
        rows = [[i, f"Name{i}"] for i in range(1, 6)]
        db.bulk_insert("clear_test", rows, schema)

        # Verify data exists
        results = db.execute_query("clear_test", "SELECT COUNT(*) as count FROM clear_test")
        assert results[0]["count"] == 5

        # Clear table
        cleared = db.clear_table("clear_test")
        assert cleared == 5

        # Verify table is empty
        results = db.execute_query("clear_test", "SELECT COUNT(*) as count FROM clear_test")
        assert results[0]["count"] == 0

    def test_update_metadata(self, db):
        """Test updating sync metadata."""
        schema = TableSchema(
            table_name="metadata_test",
            fields={0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER)},
            total_fields=1,
        )

        db.register_table(schema)

        # Update metadata
        db.update_metadata(
            "metadata_test", row_count=1500, last_sync_at="2023-01-01T12:00:00", total_syncs=5
        )

        # Verify updates
        metadata = db.get_metadata("metadata_test")
        assert metadata["row_count"] == 1500
        assert metadata["last_sync_at"] == "2023-01-01T12:00:00"
        assert metadata["total_syncs"] == 5

    def test_is_stale(self, db):
        """Test staleness detection."""
        schema = TableSchema(
            table_name="stale_test",
            fields={0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER)},
            total_fields=1,
            sync_config=SyncConfig(ttl=3600),  # 1 hour TTL
        )

        db.register_table(schema)

        # Initially should be stale (no sync yet)
        assert db.is_stale("stale_test") == True

        # Set next sync to future
        from datetime import datetime, timedelta

        future_time = (datetime.now() + timedelta(hours=2)).isoformat()
        db.update_metadata("stale_test", next_sync_at=future_time)

        # Should not be stale
        assert db.is_stale("stale_test") == False

        # Set next sync to past
        past_time = (datetime.now() - timedelta(hours=1)).isoformat()
        db.update_metadata("stale_test", next_sync_at=past_time)

        # Should be stale again
        assert db.is_stale("stale_test") == True

    def test_get_stats(self, db):
        """Test getting global cache statistics."""
        # Register a couple tables
        schema1 = TableSchema(
            table_name="stats_test1",
            fields={0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER)},
            total_fields=1,
            metadata=TableMetadata(row_count=100),
        )

        schema2 = TableSchema(
            table_name="stats_test2",
            fields={0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER)},
            total_fields=1,
            metadata=TableMetadata(row_count=200),
        )

        db.register_table(schema1)
        db.register_table(schema2)

        # Update local row counts
        db.update_metadata("stats_test1", local_row_count=100)
        db.update_metadata("stats_test2", local_row_count=200)

        # Get stats
        stats = db.get_stats()

        assert stats["total_tables"] == 2
        assert stats["total_rows"] == 300
        assert "database_size_bytes" in stats
        assert stats["cache_version"] == "1.0.0"

    def test_execute_query(self, db):
        """Test executing SQL queries on cached tables."""
        schema = TableSchema(
            table_name="query_test",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="name", position=1, field_type=FieldType.STRING),
                2: FieldDefinition(name="active", position=2, field_type=FieldType.BOOLEAN),
            },
            total_fields=3,
        )

        db.register_table(schema)

        # Insert test data
        rows = [[1, "Alice", True], [2, "Bob", False], [3, "Charlie", True]]
        db.bulk_insert("query_test", rows, schema)

        # Test various queries
        results = db.execute_query("query_test", "SELECT COUNT(*) as count FROM query_test")
        assert results[0]["count"] == 3

        results = db.execute_query(
            "query_test", "SELECT * FROM query_test WHERE active = 1 ORDER BY name"
        )
        assert len(results) == 2
        assert results[0]["name"] == "Alice"
        assert results[1]["name"] == "Charlie"

        results = db.execute_query("query_test", "SELECT name FROM query_test WHERE id = ?", (2,))
        assert len(results) == 1
        assert results[0]["name"] == "Bob"

    def test_execute_query_nonexistent_table(self, db):
        """Test executing query on non-existent table."""
        from iptvportal.sync.exceptions import TableNotFoundError

        with pytest.raises(TableNotFoundError):  # Should raise TableNotFoundError
            db.execute_query("nonexistent_table", "SELECT 1")

    def test_vacuum_and_analyze(self, db):
        """Test VACUUM and ANALYZE operations."""
        # These should not raise exceptions
        db.vacuum()
        db.analyze()

        # Check that timestamps were updated
        stats = db.get_stats()
        assert stats["last_vacuum_at"] is not None
        assert stats["last_analyze_at"] is not None

    def test_schema_hash_calculation(self, db):
        """Test that schema hash is calculated consistently."""
        schema1 = TableSchema(
            table_name="hash_test",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="name", position=1, field_type=FieldType.STRING),
            },
            total_fields=2,
            sync_config=SyncConfig(cache_strategy="full", chunk_size=1000),
        )

        schema2 = TableSchema(
            table_name="hash_test",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="name", position=1, field_type=FieldType.STRING),
            },
            total_fields=2,
            sync_config=SyncConfig(cache_strategy="full", chunk_size=1000),
        )

        # Same schemas should have same hash
        hash1 = db._calculate_schema_hash(schema1)
        hash2 = db._calculate_schema_hash(schema2)
        assert hash1 == hash2

        # Different schema should have different hash
        schema3 = TableSchema(
            table_name="hash_test",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="name", position=1, field_type=FieldType.STRING),
                2: FieldDefinition(name="email", position=2, field_type=FieldType.STRING),
            },
            total_fields=3,
            sync_config=SyncConfig(cache_strategy="full", chunk_size=1000),
        )

        hash3 = db._calculate_schema_hash(schema3)
        assert hash3 != hash1
