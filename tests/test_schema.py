"""Tests for the schema system."""

import pytest
from iptvportal.schema import (
    FieldType,
    FieldDefinition,
    TableSchema,
    SchemaRegistry,
    SchemaBuilder,
    SchemaLoader,
    SchemaExtractor,
)


class TestFieldDefinition:
    """Tests for FieldDefinition dataclass."""
    
    def test_field_definition_basic(self):
        """Test basic field definition creation."""
        field = FieldDefinition(
            name="id",
            position=0,
            field_type=FieldType.INTEGER
        )
        assert field.name == "id"
        assert field.position == 0
        assert field.field_type == FieldType.INTEGER
        assert field.mapped_name == "id"
    
    def test_field_definition_with_alias(self):
        """Test field definition with alias."""
        field = FieldDefinition(
            name="subscriber_id",
            position=1,
            alias="sub_id",
            field_type=FieldType.INTEGER
        )
        assert field.mapped_name == "sub_id"
    
    def test_field_definition_with_python_name(self):
        """Test field definition with python_name (takes precedence over alias)."""
        field = FieldDefinition(
            name="subscriber_id",
            position=1,
            alias="sub_id",
            python_name="subscriber_identifier",
            field_type=FieldType.INTEGER
        )
        assert field.mapped_name == "subscriber_identifier"


class TestTableSchema:
    """Tests for TableSchema class."""
    
    def test_resolve_select_star_partial(self):
        """Test SELECT * expansion with partial field descriptions."""
        fields = {
            0: FieldDefinition("id", 0, field_type=FieldType.INTEGER),
            2: FieldDefinition("name", 2, field_type=FieldType.STRING),
            4: FieldDefinition("email", 4, field_type=FieldType.STRING),
        }
        schema = TableSchema("users", fields, total_fields=6)
        
        result = schema.resolve_select_star()
        expected = ["id", "Field_1", "name", "Field_3", "email", "Field_5"]
        assert result == expected
    
    def test_resolve_select_star_with_aliases(self):
        """Test SELECT * expansion using aliases."""
        fields = {
            0: FieldDefinition("id", 0, alias="user_id", field_type=FieldType.INTEGER),
            1: FieldDefinition("name", 1, alias="full_name", field_type=FieldType.STRING),
        }
        schema = TableSchema("users", fields, total_fields=2)
        
        result = schema.resolve_select_star(use_aliases=True)
        assert result == ["user_id", "full_name"]
    
    def test_resolve_select_star_empty(self):
        """Test SELECT * expansion with no fields defined."""
        schema = TableSchema("users", {})
        result = schema.resolve_select_star()
        assert result == ["*"]
    
    def test_get_field_by_name(self):
        """Test getting field by name."""
        field_def = FieldDefinition("subscriber_id", 0, alias="sub_id")
        schema = TableSchema("subscribers", {0: field_def})
        
        # Should find by name
        assert schema.get_field_by_name("subscriber_id") == field_def
        # Should find by alias
        assert schema.get_field_by_name("sub_id") == field_def
        # Should not find non-existent
        assert schema.get_field_by_name("nonexistent") is None
    
    def test_get_field_by_position(self):
        """Test getting field by position."""
        field_def = FieldDefinition("id", 0)
        schema = TableSchema("users", {0: field_def})
        
        assert schema.get_field_by_position(0) == field_def
        assert schema.get_field_by_position(1) is None
    
    def test_map_row_to_dict(self):
        """Test mapping a result row to dictionary."""
        fields = {
            0: FieldDefinition("id", 0, field_type=FieldType.INTEGER),
            1: FieldDefinition("name", 1, alias="full_name", field_type=FieldType.STRING),
            2: FieldDefinition("active", 2, field_type=FieldType.BOOLEAN),
        }
        schema = TableSchema("users", fields, total_fields=5)
        
        row = [123, "John Doe", True, "extra1", "extra2"]
        result = schema.map_row_to_dict(row)
        
        assert result == {
            "id": 123,
            "full_name": "John Doe",
            "active": True,
            "Field_3": "extra1",
            "Field_4": "extra2",
        }
    
    def test_map_row_with_transformer(self):
        """Test mapping with transformer function."""
        transformer = lambda x: x.upper() if isinstance(x, str) else x
        fields = {
            0: FieldDefinition("id", 0, field_type=FieldType.INTEGER),
            1: FieldDefinition("name", 1, field_type=FieldType.STRING, transformer=transformer),
        }
        schema = TableSchema("users", fields, total_fields=2)
        
        row = [1, "john"]
        result = schema.map_row_to_dict(row)
        
        assert result == {"id": 1, "name": "JOHN"}
    
    def test_to_dict(self):
        """Test exporting schema to dictionary."""
        fields = {
            0: FieldDefinition("id", 0, field_type=FieldType.INTEGER, description="User ID"),
            1: FieldDefinition("name", 1, alias="full_name", field_type=FieldType.STRING),
        }
        schema = TableSchema("users", fields, total_fields=5)
        
        result = schema.to_dict()
        
        assert result["total_fields"] == 5
        assert "0" in result["fields"]
        assert result["fields"]["0"]["name"] == "id"
        assert result["fields"]["0"]["type"] == "integer"
        assert result["fields"]["0"]["description"] == "User ID"
        assert result["fields"]["1"]["alias"] == "full_name"


class TestSchemaRegistry:
    """Tests for SchemaRegistry."""
    
    def test_register_and_get(self):
        """Test registering and retrieving schemas."""
        registry = SchemaRegistry()
        schema = TableSchema("users", {})
        
        registry.register(schema)
        
        assert registry.has("users")
        assert registry.get("users") == schema
        assert not registry.has("nonexistent")
        assert registry.get("nonexistent") is None
    
    def test_list_tables(self):
        """Test listing all registered tables."""
        registry = SchemaRegistry()
        schema1 = TableSchema("users", {})
        schema2 = TableSchema("posts", {})
        
        registry.register(schema1)
        registry.register(schema2)
        
        tables = registry.list_tables()
        assert "users" in tables
        assert "posts" in tables
        assert len(tables) == 2


class TestSchemaBuilder:
    """Tests for SchemaBuilder fluent API."""
    
    def test_builder_basic(self):
        """Test basic schema building."""
        schema = (
            SchemaBuilder("users")
            .field(0, "id", field_type=FieldType.INTEGER)
            .field(1, "name", field_type=FieldType.STRING)
            .set_total_fields(3)
            .build()
        )
        
        assert schema.table_name == "users"
        assert len(schema.fields) == 2
        assert schema.total_fields == 3
        assert 0 in schema.fields
        assert 1 in schema.fields
    
    def test_builder_with_aliases(self):
        """Test building schema with aliases."""
        schema = (
            SchemaBuilder("subscribers")
            .field(0, "id", alias="subscriber_id", field_type=FieldType.INTEGER)
            .field(1, "name", python_name="full_name", field_type=FieldType.STRING)
            .build()
        )
        
        assert schema.fields[0].alias == "subscriber_id"
        assert schema.fields[1].python_name == "full_name"
    
    def test_builder_with_transformer(self):
        """Test building schema with transformer."""
        upper_transformer = lambda x: x.upper() if isinstance(x, str) else x
        
        schema = (
            SchemaBuilder("test")
            .field(0, "code", transformer=upper_transformer)
            .build()
        )
        
        assert schema.fields[0].transformer is not None
        assert schema.fields[0].transformer("test") == "TEST"


class TestSchemaLoader:
    """Tests for SchemaLoader."""
    
    def test_from_dict_basic(self):
        """Test loading schema from dictionary."""
        config = {
            "schemas": {
                "users": {
                    "total_fields": 3,
                    "fields": {
                        "0": {"name": "id", "type": "integer"},
                        "1": {"name": "name", "type": "string", "alias": "full_name"},
                    }
                }
            }
        }
        
        registry = SchemaLoader.from_dict(config)
        
        assert registry.has("users")
        schema = registry.get("users")
        assert schema.total_fields == 3
        assert len(schema.fields) == 2
        assert schema.fields[1].alias == "full_name"
    
    def test_from_dict_with_transformer(self):
        """Test loading schema with built-in transformer."""
        config = {
            "schemas": {
                "data": {
                    "total_fields": 2,
                    "fields": {
                        "0": {"name": "id", "type": "integer"},
                        "1": {"name": "count", "type": "string", "transformer": "int"},
                    }
                }
            }
        }
        
        registry = SchemaLoader.from_dict(config)
        schema = registry.get("data")
        
        # Test transformer is applied
        assert schema.fields[1].transformer is not None
        assert schema.fields[1].transformer("42") == 42
    
    def test_builtin_transformers(self):
        """Test all built-in transformers."""
        # Test int transformer
        assert SchemaLoader.BUILTIN_TRANSFORMERS['int']("42") == 42
        
        # Test float transformer
        assert SchemaLoader.BUILTIN_TRANSFORMERS['float']("3.14") == 3.14
        
        # Test str transformer
        assert SchemaLoader.BUILTIN_TRANSFORMERS['str'](123) == "123"
        
        # Test bool transformer
        assert SchemaLoader.BUILTIN_TRANSFORMERS['bool'](1) is True


class TestSchemaIntegration:
    """Integration tests for schema system."""
    
    def test_full_workflow(self):
        """Test complete workflow: build -> register -> query -> map."""
        # Build schema
        schema = (
            SchemaBuilder("media")
            .field(0, "id", field_type=FieldType.INTEGER)
            .field(1, "title", field_type=FieldType.STRING)
            .field(3, "duration", field_type=FieldType.INTEGER)
            .set_total_fields(5)
            .build()
        )
        
        # Register schema
        registry = SchemaRegistry()
        registry.register(schema)
        
        # Simulate query result
        query_result = [
            [1, "Movie 1", "unknown_field", 120, "extra"],
            [2, "Movie 2", "unknown_field", 90, "extra"],
        ]
        
        # Map results
        mapped_results = [schema.map_row_to_dict(row) for row in query_result]
        
        assert len(mapped_results) == 2
        assert mapped_results[0]["id"] == 1
        assert mapped_results[0]["title"] == "Movie 1"
        assert mapped_results[0]["duration"] == 120
        assert "Field_2" in mapped_results[0]
        assert "Field_4" in mapped_results[0]
