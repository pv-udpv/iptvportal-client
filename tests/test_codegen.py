"""Tests for ORM model generation from schemas."""

from pathlib import Path

import pytest

from iptvportal.codegen import ORMGenerator
from iptvportal.schema import (
    FieldDefinition,
    FieldType,
    SchemaBuilder,
    SchemaRegistry,
    TableSchema,
)


@pytest.fixture
def registry():
    """Create a sample schema registry for testing."""
    reg = SchemaRegistry()

    # Simple table schema
    subscriber_schema = (
        SchemaBuilder("subscriber")
        .field(
            0,
            "id",
            field_type=FieldType.INTEGER,
            description="Subscriber ID",
        )
        .field(
            1,
            "username",
            field_type=FieldType.STRING,
            description="Login name",
        )
        .field(
            2,
            "email",
            field_type=FieldType.STRING,
            description="Email address",
        )
        .field(
            3,
            "disabled",
            field_type=FieldType.BOOLEAN,
            description="Account disabled flag",
        )
        .set_total_fields(4)
        .build()
    )

    # Add constraints to id field
    subscriber_schema.fields[0].constraints = {"primary_key": True, "nullable": False}
    subscriber_schema.fields[1].constraints = {"unique": True, "nullable": False}
    subscriber_schema.fields[2].constraints = {"nullable": True}
    subscriber_schema.fields[3].constraints = {"nullable": False}

    reg.register(subscriber_schema)
    return reg


@pytest.fixture
def generator(registry):
    """Create ORMGenerator instance."""
    return ORMGenerator(registry)


class TestORMGenerator:
    """Tests for ORM model generation."""

    def test_generate_sqlmodel_basic(self, generator):
        """Test basic SQLModel generation."""
        code = generator.generate_sqlmodel("subscriber", include_relationships=False)

        # Check imports
        assert "from sqlmodel import Field, SQLModel" in code
        assert "from datetime import" in code
        assert "from typing import Optional" in code

        # Check class definition
        assert "class Subscriber(SQLModel, table=True):" in code
        assert "__tablename__ = 'subscriber'" in code

        # Check fields
        assert "id: int = Field(primary_key=True" in code
        assert "username: str = Field(..., unique=True" in code
        assert "email: Optional[str] = Field(default=None" in code
        assert "disabled: bool = Field(..." in code

        # Check descriptions
        assert 'description="Subscriber ID"' in code
        assert 'description="Login name"' in code

    def test_generate_pydantic_basic(self, generator):
        """Test basic Pydantic generation."""
        code = generator.generate_pydantic("subscriber")

        # Check imports
        assert "from pydantic import BaseModel, Field" in code

        # Check class definition
        assert "class Subscriber(BaseModel):" in code

        # Check fields
        assert "id:" in code
        assert "username:" in code
        assert "email:" in code
        assert "disabled:" in code

        # Check Config
        assert "class Config:" in code
        assert "from_attributes = True" in code

    def test_table_name_to_class_name(self, generator):
        """Test table name to class name conversion."""
        assert generator._table_name_to_class_name("subscriber") == "Subscriber"
        assert generator._table_name_to_class_name("tv_channel") == "TvChannel"
        assert generator._table_name_to_class_name("package_channel") == "PackageChannel"
        assert generator._table_name_to_class_name("simple") == "Simple"

    def test_field_type_to_python_type(self, generator):
        """Test field type to Python type mapping."""
        assert generator._field_type_to_python_type(FieldType.INTEGER) == "int"
        assert generator._field_type_to_python_type(FieldType.STRING) == "str"
        assert generator._field_type_to_python_type(FieldType.BOOLEAN) == "bool"
        assert generator._field_type_to_python_type(FieldType.FLOAT) == "float"
        assert generator._field_type_to_python_type(FieldType.DATETIME) == "datetime"
        assert generator._field_type_to_python_type(FieldType.DATE) == "date"
        assert generator._field_type_to_python_type(FieldType.JSON) == "dict"
        assert generator._field_type_to_python_type(FieldType.UNKNOWN) == "str"

    def test_generate_with_relationships(self):
        """Test SQLModel generation with relationships."""
        reg = SchemaRegistry()

        # Subscriber schema with relationship to terminals
        subscriber_schema = (
            SchemaBuilder("subscriber")
            .field(0, "id", field_type=FieldType.INTEGER)
            .set_total_fields(1)
            .build()
        )
        subscriber_schema.fields[0].constraints = {"primary_key": True}
        subscriber_schema.fields[0].relationships = {
            "type": "one-to-many",
            "target_table": "terminal",
            "field_name": "terminals",
            "back_populates": "subscriber",
        }

        reg.register(subscriber_schema)

        generator = ORMGenerator(reg)
        code = generator.generate_sqlmodel("subscriber", include_relationships=True)

        # Check relationship import
        assert "from sqlmodel import Relationship" in code

        # Check relationship field
        assert 'terminals: list["Terminal"]' in code
        assert 'back_populates="subscriber"' in code

    def test_generate_with_foreign_key(self):
        """Test SQLModel generation with foreign key constraint."""
        reg = SchemaRegistry()

        terminal_schema = (
            SchemaBuilder("terminal")
            .field(0, "id", field_type=FieldType.INTEGER)
            .field(1, "subscriber_id", field_type=FieldType.INTEGER)
            .set_total_fields(2)
            .build()
        )
        terminal_schema.fields[0].constraints = {"primary_key": True}
        terminal_schema.fields[1].constraints = {
            "foreign_key": "subscriber.id",
            "nullable": False,
        }

        reg.register(terminal_schema)

        generator = ORMGenerator(reg)
        code = generator.generate_sqlmodel("terminal", include_relationships=False)

        # Check foreign key
        assert 'foreign_key="subscriber.id"' in code

    def test_generate_with_index(self):
        """Test field with index constraint."""
        reg = SchemaRegistry()

        schema = (
            SchemaBuilder("test_table")
            .field(0, "id", field_type=FieldType.INTEGER)
            .field(1, "indexed_field", field_type=FieldType.STRING)
            .set_total_fields(2)
            .build()
        )
        schema.fields[0].constraints = {"primary_key": True}
        schema.fields[1].constraints = {"index": True, "nullable": True}

        reg.register(schema)

        generator = ORMGenerator(reg)
        code = generator.generate_sqlmodel("test_table", include_relationships=False)

        assert "index=True" in code

    def test_generate_all_models(self, registry):
        """Test generating all models in registry."""
        generator = ORMGenerator(registry)

        results = generator.generate_all_models(output_format="sqlmodel", include_relationships=False)

        assert len(results) == 1
        assert "subscriber" in results
        assert "class Subscriber(SQLModel, table=True):" in results["subscriber"]

    def test_generate_all_models_pydantic(self, registry):
        """Test generating all models in Pydantic format."""
        generator = ORMGenerator(registry)

        results = generator.generate_all_models(output_format="pydantic")

        assert len(results) == 1
        assert "subscriber" in results
        assert "class Subscriber(BaseModel):" in results["subscriber"]

    def test_generate_with_datetime_fields(self):
        """Test generation with datetime fields."""
        reg = SchemaRegistry()

        schema = (
            SchemaBuilder("event")
            .field(0, "id", field_type=FieldType.INTEGER)
            .field(1, "created_at", field_type=FieldType.DATETIME)
            .field(2, "event_date", field_type=FieldType.DATE)
            .set_total_fields(3)
            .build()
        )
        schema.fields[0].constraints = {"primary_key": True}

        reg.register(schema)

        generator = ORMGenerator(reg)
        code = generator.generate_sqlmodel("event", include_relationships=False)

        # Check datetime imports and field types
        assert "from datetime import date, datetime" in code
        assert "created_at: Optional[datetime]" in code
        assert "event_date: Optional[date]" in code

    def test_generate_with_json_field(self):
        """Test generation with JSON field type."""
        reg = SchemaRegistry()

        schema = (
            SchemaBuilder("config")
            .field(0, "id", field_type=FieldType.INTEGER)
            .field(1, "settings", field_type=FieldType.JSON)
            .set_total_fields(2)
            .build()
        )
        schema.fields[0].constraints = {"primary_key": True}

        reg.register(schema)

        generator = ORMGenerator(reg)
        code = generator.generate_sqlmodel("config", include_relationships=False)

        # JSON fields should map to dict
        assert "settings: Optional[dict]" in code

    def test_generate_nonexistent_table(self, generator):
        """Test error handling for nonexistent table."""
        with pytest.raises(ValueError, match="Schema for table 'nonexistent' not found"):
            generator.generate_sqlmodel("nonexistent")

    def test_generate_with_output_dir(self, registry, tmp_path):
        """Test generating models with output directory."""
        generator = ORMGenerator(registry)

        output_dir = tmp_path / "models"
        results = generator.generate_all_models(
            output_format="sqlmodel", output_dir=output_dir, include_relationships=False
        )

        # Check files were created
        assert (output_dir / "subscriber.py").exists()

        # Check file content
        content = (output_dir / "subscriber.py").read_text()
        assert "class Subscriber(SQLModel, table=True):" in content

    def test_invalid_output_format(self, generator):
        """Test error handling for invalid output format."""
        with pytest.raises(ValueError, match="Unsupported output format"):
            generator.generate_all_models(output_format="invalid")
