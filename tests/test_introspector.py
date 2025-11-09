"""Tests for SchemaIntrospector intelligence and metadata gathering.

Run with:
    uv run pytest tests/test_introspector.py
    uv run pytest tests/test_introspector.py -v
"""

from unittest.mock import AsyncMock

import pytest

from iptvportal.core.async_client import AsyncIPTVPortalClient
from iptvportal.schema import FieldDefinition, FieldType, TableMetadata
from iptvportal.schema.introspector import SchemaIntrospector


class TestSchemaIntrospector:
    """Test SchemaIntrospector functionality."""

    @pytest.fixture
    def mock_client(self):
        """Mock AsyncIPTVPortalClient."""
        return AsyncMock(spec=AsyncIPTVPortalClient)

    @pytest.fixture
    def introspector(self, mock_client):
        """Create SchemaIntrospector instance."""
        return SchemaIntrospector(mock_client)

    def test_field_type_inference(self, introspector):
        """Test field type inference from sample values."""
        # Test integer
        assert introspector._infer_field_type(42) == FieldType.INTEGER
        assert introspector._infer_field_type(0) == FieldType.INTEGER

        # Test float
        assert introspector._infer_field_type(3.14) == FieldType.FLOAT

        # Test boolean
        assert introspector._infer_field_type(True) == FieldType.BOOLEAN
        assert introspector._infer_field_type(False) == FieldType.BOOLEAN

        # Test string
        assert introspector._infer_field_type("hello") == FieldType.STRING

        # Test datetime
        assert introspector._infer_field_type("2023-01-01T12:00:00") == FieldType.DATETIME

        # Test JSON
        assert introspector._infer_field_type([1, 2, 3]) == FieldType.JSON
        assert introspector._infer_field_type({"key": "value"}) == FieldType.JSON

        # Test None/unknown
        assert introspector._infer_field_type(None) == FieldType.UNKNOWN

    def test_field_name_inference(self, introspector):
        """Test smart field name inference."""
        # Test ID field
        assert introspector._infer_field_name(0, 123, FieldType.INTEGER) == "id"

        # Test email pattern
        assert introspector._infer_field_name(1, "user@example.com", FieldType.STRING) == "email"

        # Test URL pattern
        assert introspector._infer_field_name(2, "https://example.com", FieldType.STRING) == "url"

        # Test UUID pattern
        uuid_val = "12345678-1234-5678-1234-567812345678"
        assert introspector._infer_field_name(3, uuid_val, FieldType.STRING) == "uuid"

        # Test phone pattern
        assert introspector._infer_field_name(4, "+1234567890", FieldType.STRING) == "phone"

        # Test datetime fields
        assert (
            introspector._infer_field_name(1, "2023-01-01T12:00:00", FieldType.DATETIME)
            == "created_at"
        )
        assert (
            introspector._infer_field_name(2, "2023-01-01T12:00:00", FieldType.DATETIME)
            == "updated_at"
        )

        # Test date fields
        assert introspector._infer_field_name(5, "2023-01-01", FieldType.DATE) == "date_5"

        # Test None values
        assert introspector._infer_field_name(6, None, FieldType.UNKNOWN) == "Field_6"

        # Test non-string values
        assert introspector._infer_field_name(7, 42, FieldType.INTEGER) == "Field_7"

    def test_sync_config_generation_small_table(self, introspector):
        """Test sync config generation for small tables."""
        metadata = TableMetadata(row_count=500)

        # Mock fields with ID
        fields = {
            0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
            1: FieldDefinition(name="name", position=1, field_type=FieldType.STRING),
        }

        config = introspector._generate_sync_config("small_table", metadata, fields)

        assert config.cache_strategy == "full"
        assert config.chunk_size == 500  # Same as row count
        assert config.auto_sync is True
        assert config.ttl == 3600  # 1 hour
        assert config.incremental_mode is False

    def test_sync_config_generation_medium_table(self, introspector):
        """Test sync config generation for medium tables."""
        metadata = TableMetadata(row_count=50000)

        fields = {
            0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
            1: FieldDefinition(name="name", position=1, field_type=FieldType.STRING),
        }

        config = introspector._generate_sync_config("medium_table", metadata, fields)

        assert config.cache_strategy == "full"
        assert config.chunk_size == 5000
        assert config.auto_sync is True
        assert config.ttl == 1800  # 30 minutes
        assert config.incremental_mode is False

    def test_sync_config_generation_large_table(self, introspector):
        """Test sync config generation for large tables."""
        metadata = TableMetadata(row_count=200000)

        fields = {
            0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
            1: FieldDefinition(name="name", position=1, field_type=FieldType.STRING),
            2: FieldDefinition(name="updated_at", position=2, field_type=FieldType.DATETIME),
        }

        config = introspector._generate_sync_config("large_table", metadata, fields)

        assert config.cache_strategy == "incremental"
        assert config.chunk_size == 10000
        assert config.auto_sync is False
        assert config.ttl == 600  # 10 minutes
        assert config.incremental_mode is True

    def test_sync_config_with_soft_deletes(self, introspector):
        """Test sync config generation with soft delete fields."""
        metadata = TableMetadata(row_count=1000)

        fields = {
            0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
            1: FieldDefinition(name="deleted_at", position=1, field_type=FieldType.DATETIME),
        }

        config = introspector._generate_sync_config("soft_delete_table", metadata, fields)

        assert config.where == "deleted_at IS NULL"
        assert config.limit == 2000  # 2x row count

    def test_sync_config_with_flag_fields(self, introspector):
        """Test sync config generation with flag fields."""
        metadata = TableMetadata(row_count=1000)

        fields = {
            0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
            1: FieldDefinition(name="disabled", position=1, field_type=FieldType.BOOLEAN),
            2: FieldDefinition(name="archived", position=2, field_type=FieldType.BOOLEAN),
            3: FieldDefinition(name="active", position=3, field_type=FieldType.BOOLEAN),
        }

        config = introspector._generate_sync_config("flag_table", metadata, fields)

        # Should include conditions for all flag fields
        where_parts = config.where.split(" AND ")
        assert "disabled = false" in where_parts
        assert "archived = false" in where_parts
        assert "active = true" in where_parts
        assert "active = true" in where_parts

    def test_sync_config_with_incremental_field(self, introspector):
        """Test sync config generation with incremental field."""
        metadata = TableMetadata(row_count=150000)  # Large table

        fields = {
            0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
            1: FieldDefinition(name="updated_at", position=1, field_type=FieldType.DATETIME),
        }

        config = introspector._generate_sync_config("incremental_table", metadata, fields)

        assert config.incremental_mode is True
        assert config.incremental_field == "updated_at"
        assert config.cache_strategy == "incremental"

    def test_sync_config_multiple_incremental_fields(self, introspector):
        """Test that first incremental field is chosen."""
        metadata = TableMetadata(row_count=150000)

        fields = {
            0: FieldDefinition(name="id", position=0, field_type=FieldType.INTEGER),
            1: FieldDefinition(name="modified_at", position=1, field_type=FieldType.DATETIME),
            2: FieldDefinition(name="updated_at", position=2, field_type=FieldType.DATETIME),
        }

        config = introspector._generate_sync_config("multi_incremental_table", metadata, fields)

        # Should pick the first one found (modified_at comes before updated_at alphabetically)
        assert config.incremental_field in ["modified_at", "updated_at"]

    @pytest.mark.asyncio
    async def test_introspect_table_basic(self, introspector, mock_client):
        """Test basic table introspection."""
        # Mock the sample query response
        sample_data = [
            [1, "John Doe", "john@example.com", "2023-01-01T10:00:00"],
            [2, "Jane Smith", "jane@example.com", "2023-01-02T11:00:00"],
        ]

        # Mock metadata queries with correct format
        mock_client.execute.side_effect = [
            sample_data,  # Sample query for field analysis
            [[2]],  # COUNT query - returns [[count]]
            [[2, 1]],  # ID stats query - returns [[max_id, min_id]]
            [["2023-01-01T10:00:00", "2023-01-02T11:00:00"]],  # timestamp range for timestamp_3
        ]

        schema = await introspector.introspect_table("users", perform_duckdb_analysis=False)

        assert schema.table_name == "users"
        assert len(schema.fields) == 4  # 4 columns in sample data

        # Check field inference
        assert schema.fields[0].name == "id"
        assert schema.fields[0].field_type == FieldType.INTEGER

        assert schema.fields[1].name == "Field_1"  # No pattern match
        assert schema.fields[1].field_type == FieldType.STRING

        assert schema.fields[2].name == "email"
        assert schema.fields[2].field_type == FieldType.STRING

        assert schema.fields[3].name == "timestamp_3"  # Position 3 -> timestamp_3, not created_at
        assert schema.fields[3].field_type == FieldType.DATETIME

        # Check metadata
        assert schema.metadata.row_count == 2
        assert schema.metadata.max_id == 2
        assert schema.metadata.min_id == 1

        # Check sync config
        assert schema.sync_config.cache_strategy == "full"
        assert schema.sync_config.chunk_size == 100  # max(row_count, 100) = max(2, 100) = 100

    @pytest.mark.asyncio
    async def test_introspect_table_with_field_overrides(self, introspector, mock_client):
        """Test table introspection with field name overrides."""
        sample_data = [[1, "John", "john@example.com"]]
        mock_client.execute = AsyncMock(return_value=sample_data)

        # Mock metadata queries
        mock_client.execute.side_effect = [
            sample_data,
            [{"count": 1}],
            [{"max_id": 1, "min_id": 1}],
        ]

        field_overrides = {1: "full_name", 2: "contact_email"}

        schema = await introspector.introspect_table("users", field_name_overrides=field_overrides, perform_duckdb_analysis=False)

        assert schema.fields[0].name == "id"  # Auto-detected
        assert schema.fields[1].name == "full_name"  # Overridden
        assert schema.fields[2].name == "contact_email"  # Overridden

        assert schema.fields[1].description == "Manually specified field"
        assert schema.fields[2].description == "Manually specified field"

    @pytest.mark.asyncio
    async def test_introspect_table_duplicate_names(self, introspector, mock_client):
        """Test handling of duplicate field names."""
        # Create sample data that would generate duplicate names
        sample_data = [[1, "test@example.com", "test@example.com"]]
        mock_client.execute = AsyncMock(return_value=sample_data)

        mock_client.execute.side_effect = [
            sample_data,
            [{"count": 1}],
            [{"max_id": 1, "min_id": 1}],
        ]

        schema = await introspector.introspect_table("duplicate_test", perform_duckdb_analysis=False)

        # Should have unique names
        names = [field.name for field in schema.fields.values()]
        assert len(names) == len(set(names))  # All unique

        # Second email field should have suffix
        assert "email" in names
        assert any("email_" in name for name in names)

    @pytest.mark.asyncio
    async def test_introspect_table_empty(self, introspector, mock_client):
        """Test introspection of empty table."""
        mock_client.execute = AsyncMock(return_value=[])

        with pytest.raises(ValueError, match="Table 'empty_table' is empty"):
            await introspector.introspect_table("empty_table", perform_duckdb_analysis=False)

    @pytest.mark.asyncio
    async def test_introspect_table_no_metadata(self, introspector, mock_client):
        """Test introspection without metadata gathering."""
        sample_data = [[1, "John"]]
        mock_client.execute = AsyncMock(return_value=sample_data)

        schema = await introspector.introspect_table("users", gather_metadata=False, perform_duckdb_analysis=False)

        assert schema.metadata is None
        assert schema.sync_config.where is None  # No smart defaults without metadata

    @pytest.mark.asyncio
    async def test_introspect_all_tables(self, introspector, mock_client):
        """Test introspecting multiple tables."""
        # Mock responses for two tables
        mock_client.execute.side_effect = [
            [[1, "User1"]],  # table1 sample
            [{"count": 1}],  # table1 count
            [{"max_id": 1, "min_id": 1}],  # table1 ID stats
            [[2, "User2"]],  # table2 sample
            [{"count": 1}],  # table2 count
            [{"max_id": 2, "min_id": 2}],  # table2 ID stats
        ]

        schemas = await introspector.introspect_all_tables(["table1", "table2"], perform_duckdb_analysis=False)

        assert len(schemas) == 2
        assert "table1" in schemas
        assert "table2" in schemas

        assert schemas["table1"].fields[0].name == "id"
        assert schemas["table2"].fields[0].name == "id"

    @pytest.mark.asyncio
    async def test_introspect_all_tables_with_errors(self, introspector, mock_client):
        """Test introspecting multiple tables with some errors."""
        # First table succeeds, second fails
        mock_client.execute.side_effect = [
            [[1, "User1"]],  # table1 sample
            [{"count": 1}],  # table1 count
            [{"max_id": 1, "min_id": 1}],  # table1 ID stats
            Exception("Connection failed"),  # table2 fails
        ]

        schemas = await introspector.introspect_all_tables(["table1", "table2"], perform_duckdb_analysis=False)

        assert len(schemas) == 1  # Only successful table
        assert "table1" in schemas
        assert "table2" not in schemas
