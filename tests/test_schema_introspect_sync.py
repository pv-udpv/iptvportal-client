"""Tests for schema introspect command with sync integration.

Run with:
    pytest tests/test_schema_introspect_sync.py
    pytest tests/test_schema_introspect_sync.py -v
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from iptvportal.schema import FieldDefinition, FieldType, TableMetadata, TableSchema
from iptvportal.sync.database import SyncDatabase


class TestSyncDatabase:
    """Test SyncDatabase fetch_rows functionality."""

    @pytest.fixture
    def temp_db_path(self, tmp_path):
        """Create temporary database path."""
        return str(tmp_path / "test_cache.db")

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.cache_db_journal_mode = "WAL"
        settings.cache_db_page_size = 4096
        settings.cache_db_cache_size = -64000
        return settings

    @pytest.fixture
    def database(self, temp_db_path, mock_settings):
        """Create SyncDatabase instance."""
        db = SyncDatabase(temp_db_path, mock_settings)
        db.initialize()
        return db

    def test_fetch_rows_from_synced_table(self, database):
        """Test fetching rows from synced table."""
        # Create a test table with schema
        schema = TableSchema(
            table_name="test_table",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="name", position=1, field_type=FieldType.STRING),
                2: FieldDefinition(name="value", position=2, field_type=FieldType.INTEGER),
            },
            total_fields=3,
        )

        # Create table
        database.create_data_table(schema)
        database.register_table_schema("test_table", schema)

        # Insert test data
        import sqlite3
        from datetime import datetime

        with database._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO test_table (id, name, value, _synced_at)
                VALUES (?, ?, ?, ?)
            """,
                (1, "test1", 100, datetime.now().isoformat()),
            )
            conn.execute(
                """
                INSERT INTO test_table (id, name, value, _synced_at)
                VALUES (?, ?, ?, ?)
            """,
                (2, "test2", 200, datetime.now().isoformat()),
            )
            conn.execute(
                """
                INSERT INTO test_table (id, name, value, _synced_at)
                VALUES (?, ?, ?, ?)
            """,
                (3, "test3", 300, datetime.now().isoformat()),
            )
            conn.commit()

        # Fetch rows
        rows = database.fetch_rows("test_table")

        # Verify
        assert len(rows) == 3
        assert rows[0] == [1, "test1", 100]
        assert rows[1] == [2, "test2", 200]
        assert rows[2] == [3, "test3", 300]

    def test_fetch_rows_with_limit(self, database):
        """Test fetching rows with limit."""
        # Create test schema and table
        schema = TableSchema(
            table_name="test_table_limit",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="data", position=1, field_type=FieldType.STRING),
            },
            total_fields=2,
        )

        database.create_data_table(schema)
        database.register_table_schema("test_table_limit", schema)

        # Insert test data
        from datetime import datetime

        with database._get_connection() as conn:
            for i in range(10):
                conn.execute(
                    """
                    INSERT INTO test_table_limit (id, data, _synced_at)
                    VALUES (?, ?, ?)
                """,
                    (i, f"data_{i}", datetime.now().isoformat()),
                )
            conn.commit()

        # Fetch with limit
        rows = database.fetch_rows("test_table_limit", limit=5)

        # Verify
        assert len(rows) == 5
        assert rows[0][0] == 0  # First id
        assert rows[4][0] == 4  # Fifth id

    def test_fetch_rows_nonexistent_table(self, database):
        """Test fetching from non-existent table raises error."""
        from iptvportal.sync.exceptions import TableNotFoundError

        with pytest.raises(TableNotFoundError):
            database.fetch_rows("nonexistent_table")

    def test_fetch_rows_empty_table(self, database):
        """Test fetching from empty table returns empty list."""
        # Create empty table
        schema = TableSchema(
            table_name="empty_table",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
            },
            total_fields=1,
        )

        database.create_data_table(schema)
        database.register_table_schema("empty_table", schema)

        # Fetch rows
        rows = database.fetch_rows("empty_table")

        # Verify
        assert rows == []

    def test_fetch_rows_excludes_sync_metadata(self, database):
        """Test that fetch_rows excludes sync metadata columns."""
        # Create table
        schema = TableSchema(
            table_name="test_metadata",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="data", position=1, field_type=FieldType.STRING),
            },
            total_fields=2,
        )

        database.create_data_table(schema)
        database.register_table_schema("test_metadata", schema)

        # Insert data
        from datetime import datetime

        with database._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO test_metadata (id, data, _synced_at, _sync_version)
                VALUES (?, ?, ?, ?)
            """,
                (1, "test", datetime.now().isoformat(), 1),
            )
            conn.commit()

        # Fetch rows
        rows = database.fetch_rows("test_metadata")

        # Verify - should only have id and data, not _synced_at or _sync_version
        assert len(rows) == 1
        assert len(rows[0]) == 2
        assert rows[0] == [1, "test"]


class TestSchemaIntrospectCLI:
    """Test schema introspect CLI command with sync."""

    def test_introspect_help_shows_sync_options(self):
        """Test that introspect help shows sync-related options."""
        from typer.testing import CliRunner

        from iptvportal.cli.__main__ import app

        runner = CliRunner()
        result = runner.invoke(app, ["schema", "introspect", "--help"])

        assert result.exit_code == 0
        assert "--sync" in result.stdout
        assert "--sync-chunk" in result.stdout
        assert "--order-by-fields" in result.stdout
        assert "--sync-run-timeout" in result.stdout
        assert "--analyze-from-cache" in result.stdout

    def test_introspect_validates_table_name_required(self):
        """Test that table name is required."""
        from typer.testing import CliRunner

        from iptvportal.cli.__main__ import app

        runner = CliRunner()
        # Try without any table specification
        result = runner.invoke(app, ["schema", "introspect"])

        # Should fail with error about missing table name
        assert result.exit_code == 1
        assert "Table name is required" in result.stdout or "required" in result.stdout.lower()


class TestDuckDBAnalyzerWithSyncedData:
    """Test DuckDB analyzer with synced cache data."""

    @pytest.mark.skipif(
        not _duckdb_available(), reason="DuckDB not installed"
    )
    def test_analyze_synced_data(self, tmp_path):
        """Test analyzing data from synced cache."""
        from iptvportal.schema.duckdb_analyzer import DuckDBAnalyzer

        # Create mock database with test data
        mock_settings = MagicMock()
        mock_settings.cache_db_journal_mode = "WAL"
        mock_settings.cache_db_page_size = 4096
        mock_settings.cache_db_cache_size = -64000

        db_path = str(tmp_path / "test_cache.db")
        database = SyncDatabase(db_path, mock_settings)
        database.initialize()

        # Create and populate table
        schema = TableSchema(
            table_name="test_analysis",
            fields={
                0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
                1: FieldDefinition(name="name", position=1, field_type=FieldType.STRING),
                2: FieldDefinition(name="value", position=2, field_type=FieldType.INTEGER),
            },
            total_fields=3,
        )

        database.create_data_table(schema)
        database.register_table_schema("test_analysis", schema)

        from datetime import datetime

        with database._get_connection() as conn:
            for i in range(100):
                conn.execute(
                    """
                    INSERT INTO test_analysis (id, name, value, _synced_at)
                    VALUES (?, ?, ?, ?)
                """,
                    (i, f"name_{i % 10}", i * 10, datetime.now().isoformat()),
                )
            conn.commit()

        # Fetch and analyze
        data = database.fetch_rows("test_analysis", limit=50)
        analyzer = DuckDBAnalyzer()

        if analyzer.available:
            field_names = ["id", "name", "value"]
            results = analyzer.analyze_sample(data, field_names)

            # Verify analysis results
            assert "id" in results
            assert "name" in results
            assert "value" in results

            # Check ID statistics
            id_stats = results["id"]
            assert id_stats["sample_size"] == 50
            assert id_stats["unique_count"] == 50
            assert id_stats["null_count"] == 0
            assert id_stats["min_value"] == 0
            assert id_stats["max_value"] == 49

            # Check name statistics (low cardinality)
            name_stats = results["name"]
            assert name_stats["unique_count"] == 10  # Only 10 unique names
            assert name_stats["cardinality"] < 0.3  # Low cardinality

            # Check value statistics
            value_stats = results["value"]
            assert value_stats["min_value"] == 0
            assert value_stats["max_value"] == 490


def _duckdb_available() -> bool:
    """Check if DuckDB is available."""
    try:
        import duckdb  # noqa: F401

        return True
    except ImportError:
        return False
