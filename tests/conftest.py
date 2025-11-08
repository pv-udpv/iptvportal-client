"""Shared pytest fixtures for sync testing.

Run with:
    uv run pytest tests/ -v --tb=short
"""

import os
import tempfile
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr

from iptvportal.async_client import AsyncIPTVPortalClient
from iptvportal.config import IPTVPortalSettings
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


@pytest.fixture
def temp_db_path():
    """Create temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def test_settings():
    """Create test settings optimized for testing."""
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
def mock_client():
    """Create mock AsyncIPTVPortalClient."""
    return AsyncMock(spec=AsyncIPTVPortalClient)


@pytest.fixture
def sample_user_schema():
    """Create sample user table schema for testing."""
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
        sync_config=SyncConfig(cache_strategy="full", chunk_size=100, ttl=3600),
        metadata=TableMetadata(row_count=1000, max_id=1000, min_id=1),
    )


@pytest.fixture
def sample_product_schema():
    """Create sample product table schema for testing."""
    return TableSchema(
        table_name="products",
        fields={
            0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
            1: FieldDefinition(name="title", position=1, field_type=FieldType.STRING),
            2: FieldDefinition(name="price", position=2, field_type=FieldType.FLOAT),
            3: FieldDefinition(name="category", position=3, field_type=FieldType.STRING),
        },
        total_fields=4,
        sync_config=SyncConfig(
            cache_strategy="incremental",
            incremental_mode=True,
            incremental_field="updated_at",
            chunk_size=200,
        ),
    )


@pytest.fixture
def schema_registry(sample_user_schema, sample_product_schema):
    """Create schema registry with sample schemas."""
    registry = SchemaRegistry()
    registry.register(sample_user_schema)
    registry.register(sample_product_schema)
    return registry


@pytest.fixture
def sync_database(temp_db_path, test_settings):
    """Create and initialize SyncDatabase."""
    database = SyncDatabase(temp_db_path, test_settings)
    database.initialize()
    return database


@pytest.fixture
def sync_manager(sync_database, mock_client, schema_registry, test_settings):
    """Create SyncManager with all dependencies."""
    return SyncManager(sync_database, mock_client, schema_registry, test_settings)


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return [
        [1, "alice@example.com", "Alice Johnson", "2023-01-01T10:00:00", True],
        [2, "bob@example.com", "Bob Smith", "2023-01-02T11:00:00", False],
        [3, "charlie@example.com", "Charlie Brown", "2023-01-03T12:00:00", True],
        [4, "diana@example.com", "Diana Prince", "2023-01-04T13:00:00", True],
        [5, "eve@example.com", "Eve Wilson", "2023-01-05T14:00:00", False],
    ]


@pytest.fixture
def mock_client_with_data(sample_user_data):
    """Mock client that returns realistic data responses."""
    client = AsyncMock(spec=AsyncIPTVPortalClient)

    def mock_execute(query):
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
                    # Return sample data for introspection/sync
                    if limit == 1 and offset == 0:
                        return [sample_user_data[0]]  # First row for schema detection
                    # Return chunked data
                    start_idx = offset
                    end_idx = min(offset + limit, len(sample_user_data))
                    return (
                        sample_user_data[start_idx:end_idx]
                        if start_idx < len(sample_user_data)
                        else []
                    )

                if "COUNT(*)" in str(data):
                    # COUNT query
                    return [[len(sample_user_data)]]

                if "MAX(id)" in str(data) and "MIN(id)" in str(data):
                    # ID stats query
                    ids = [row[0] for row in sample_user_data]
                    return [[max(ids), min(ids)]]

                if "MIN(" in str(data) and "MAX(" in str(data) and "created_at" in str(data):
                    # Timestamp range query
                    timestamps = [row[3] for row in sample_user_data]
                    return [[min(timestamps), max(timestamps)]]

        return []

    client.execute.side_effect = mock_execute
    return client


# Utility fixtures for common test patterns


@pytest.fixture
def registered_user_table(sync_database, sample_user_schema):
    """Register user table in database."""
    sync_database.register_table(sample_user_schema)
    return sample_user_schema


@pytest.fixture
def populated_user_table(sync_database, registered_user_table, sample_user_data):
    """Register and populate user table with sample data."""
    sync_database.bulk_insert("users", sample_user_data, registered_user_table)
    return registered_user_table
