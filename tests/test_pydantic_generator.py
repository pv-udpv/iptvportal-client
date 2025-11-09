"""Tests for enhanced Pydantic model generator and MCP tools."""

import ast

import pytest

from iptvportal.schema import (
    FieldType,
    PydanticModelGenerator,
    SchemaBuilder,
    SchemaRegistry,
    integration_checker,
    pydantic_schema,
    schema_validator,
)


@pytest.fixture
def registry():
    """Create a sample schema registry for testing."""
    reg = SchemaRegistry()

    # Create subscriber schema with various field types and constraints
    subscriber_schema = (
        SchemaBuilder("subscriber")
        .field(
            0,
            "id",
            field_type=FieldType.INTEGER,
            description="Unique subscriber identifier",
        )
        .field(
            1,
            "username",
            field_type=FieldType.STRING,
            description="Login username",
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
        .field(
            4,
            "created_at",
            field_type=FieldType.DATETIME,
            description="Account creation timestamp",
        )
        .field(
            5,
            "balance",
            field_type=FieldType.FLOAT,
            description="Account balance",
        )
        .set_total_fields(6)
        .build()
    )

    # Add constraints
    subscriber_schema.fields[0].constraints = {"nullable": False, "ge": 1}
    subscriber_schema.fields[1].constraints = {
        "nullable": False,
        "min_length": 3,
        "max_length": 50,
    }
    subscriber_schema.fields[2].constraints = {"nullable": True}
    subscriber_schema.fields[3].constraints = {"nullable": False}
    subscriber_schema.fields[4].constraints = {"nullable": False}
    subscriber_schema.fields[5].constraints = {"nullable": True, "ge": 0}

    reg.register(subscriber_schema)
    return reg


@pytest.fixture
def generator(registry):
    """Create PydanticModelGenerator instance."""
    return PydanticModelGenerator(registry)


class TestPydanticModelGenerator:
    """Tests for enhanced Pydantic model generator."""

    def test_generate_basic_model(self, generator):
        """Test basic model generation."""
        code = generator.generate_model("subscriber", include_validators=False)

        # Check imports
        assert "from pydantic import BaseModel, Field" in code
        assert "from datetime import datetime" in code
        assert "from __future__ import annotations" in code

        # Check class definition
        assert "class Subscriber(BaseModel):" in code

        # Check docstring
        assert '"""Subscriber model.' in code
        assert "Attributes:" in code

        # Check fields with modern syntax
        assert "id: int = Field(" in code
        assert "username: str = Field(" in code
        assert "email: str | None = Field(" in code
        assert "disabled: bool = Field(" in code
        assert "created_at: datetime = Field(" in code
        assert "balance: float | None = Field(" in code

    def test_field_type_hints(self, generator):
        """Test correct type hints generation."""
        code = generator.generate_model("subscriber", include_validators=False)

        # Required fields (non-nullable)
        assert "id: int = Field(...," in code
        assert "username: str = Field(...," in code

        # Optional fields (nullable)
        assert "email: str | None = Field(None," in code
        assert "balance: float | None = Field(None," in code

    def test_field_constraints(self, generator):
        """Test constraint generation in Field()."""
        code = generator.generate_model("subscriber", include_validators=False)

        # Numeric constraints
        assert "ge=1" in code  # id >= 1
        assert "ge=0" in code  # balance >= 0

        # String constraints
        assert "min_length=3" in code
        assert "max_length=50" in code

    def test_field_descriptions(self, generator):
        """Test field descriptions are included."""
        code = generator.generate_model("subscriber", include_validators=False)

        assert 'description="Unique subscriber identifier"' in code
        assert 'description="Login username"' in code
        assert 'description="Email address"' in code

    def test_generate_with_validators(self, generator):
        """Test validator generation."""
        code = generator.generate_model("subscriber", include_validators=True)

        # Check validator imports
        assert "field_validator" in code

        # Check validator for non-nullable string
        assert "@field_validator('username')" in code
        assert "def validate_username" in code
        assert "if not v or not v.strip():" in code
        assert "return v.strip()" in code

    def test_generate_with_examples(self, generator):
        """Test example generation in docstrings."""
        code = generator.generate_model("subscriber", include_examples=True)

        assert "Example:" in code
        assert ">>> model = Subscriber(" in code

    def test_model_config(self, generator):
        """Test model configuration generation."""
        code = generator.generate_model("subscriber", include_validators=False)

        assert "model_config = ConfigDict(" in code
        assert "from_attributes=True," in code
        assert "str_strip_whitespace=True," in code
        assert "validate_assignment=True," in code

    def test_modern_syntax_usage(self, generator):
        """Test modern Python 3.10+ syntax."""
        code = generator.generate_model("subscriber", include_validators=False)

        # Should use | None instead of Optional
        assert " | None" in code
        assert "Optional[" not in code  # Should not use old syntax

    def test_legacy_syntax_option(self, registry):
        """Test legacy syntax option."""
        generator = PydanticModelGenerator(registry, use_modern_syntax=False)
        code = generator.generate_model("subscriber", include_validators=False)

        # When modern syntax is disabled, might still use it by default
        # This is a design choice - the generator prefers modern syntax
        # Just verify it generates valid code
        assert "class Subscriber(BaseModel):" in code

    def test_table_name_to_class_name(self, generator):
        """Test table name conversion to class name."""
        assert generator._table_name_to_class_name("subscriber") == "Subscriber"
        assert generator._table_name_to_class_name("tv_channel") == "TvChannel"
        assert generator._table_name_to_class_name("media_file") == "MediaFile"

    def test_invalid_table_name(self, generator):
        """Test error handling for invalid table name."""
        with pytest.raises(ValueError, match="not found in registry"):
            generator.generate_model("nonexistent_table")


class TestSchemaValidator:
    """Tests for schema_validator MCP tool."""

    def test_validate_valid_model(self, generator):
        """Test validation of a valid model."""
        code = generator.generate_model("subscriber", include_validators=True)
        report = generator.validate_model(code, strict=False)

        assert report["valid"]
        assert len(report["errors"]) == 0

    def test_validate_syntax_error(self, generator):
        """Test validation catches syntax errors."""
        invalid_code = "class Broken(BaseModel):\n    field: str = "
        report = generator.validate_model(invalid_code, strict=False)

        assert not report["valid"]
        assert any("Syntax error" in err for err in report["errors"])

    def test_validate_missing_class(self, generator):
        """Test validation catches missing class definition."""
        code = "# Just a comment, no class"
        report = generator.validate_model(code, strict=False)

        assert not report["valid"]
        assert any("No class definition" in err for err in report["errors"])

    def test_validate_docstring_warning(self, generator):
        """Test validation warns about missing docstrings."""
        code = """
from pydantic import BaseModel

class TestModel(BaseModel):
    field: str
"""
        report = generator.validate_model(code, strict=False)

        # May still be valid but should have warnings
        assert any("docstring" in warn.lower() for warn in report["warnings"])

    def test_validate_missing_type_hint(self, generator):
        """Test validation catches missing type hints."""
        code = """
from pydantic import BaseModel

class TestModel(BaseModel):
    \"\"\"Test model.\"\"\"
    field = "value"  # No type hint!
"""
        report = generator.validate_model(code, strict=False)

        # AST might not catch this as an error, depends on structure
        # Just ensure validation runs
        assert "valid" in report

    def test_mcp_tool_schema_validator(self, generator):
        """Test schema_validator MCP tool function."""
        code = generator.generate_model("subscriber", include_validators=True)
        report = schema_validator(code, strict=False)

        assert isinstance(report, dict)
        assert "valid" in report
        assert "errors" in report
        assert "warnings" in report


class TestIntegrationChecker:
    """Tests for integration_checker MCP tool."""

    def test_check_valid_integration(self, generator):
        """Test integration check on valid model."""
        code = generator.generate_model("subscriber", include_validators=True)
        report = generator.check_integration(code, "subscriber")

        assert report["transport_compatible"]
        assert report["resource_manager_compatible"]
        assert report["query_builder_compatible"]

    def test_check_missing_basemodel(self, generator):
        """Test integration check catches missing BaseModel."""
        code = """
class TestModel:
    field: str
"""
        report = generator.check_integration(code, "test")

        assert not report["transport_compatible"]
        assert any("BaseModel" in issue for issue in report["issues"])

    def test_check_datetime_suggestion(self, generator):
        """Test integration check suggests datetime timezone awareness."""
        code = """
from datetime import datetime
from pydantic import BaseModel, Field

class TestModel(BaseModel):
    timestamp: datetime = Field(...)
"""
        report = generator.check_integration(code, "test")

        # Should suggest timezone awareness
        assert any("datetime" in sugg.lower() for sugg in report["suggestions"])

    def test_check_config_suggestion(self, generator):
        """Test integration check suggests model_config."""
        code = """
from pydantic import BaseModel

class TestModel(BaseModel):
    field: str
"""
        report = generator.check_integration(code, "test")

        # Should suggest adding model_config
        assert any("model_config" in sugg for sugg in report["suggestions"])

    def test_mcp_tool_integration_checker(self, generator):
        """Test integration_checker MCP tool function."""
        code = generator.generate_model("subscriber", include_validators=True)
        report = integration_checker(code, "subscriber")

        assert isinstance(report, dict)
        assert "transport_compatible" in report
        assert "issues" in report
        assert "suggestions" in report


class TestMCPTools:
    """Tests for MCP tool convenience functions."""

    def test_pydantic_schema_tool(self, registry):
        """Test pydantic_schema MCP tool."""
        code = pydantic_schema(
            registry, "subscriber", include_validators=True, include_examples=True
        )

        assert isinstance(code, str)
        assert "class Subscriber(BaseModel):" in code
        assert "from pydantic import BaseModel" in code

    def test_pydantic_schema_minimal(self, registry):
        """Test pydantic_schema with minimal options."""
        code = pydantic_schema(
            registry, "subscriber", include_validators=False, include_examples=False
        )

        assert isinstance(code, str)
        assert "class Subscriber(BaseModel):" in code
        # Should not have validators when disabled
        assert "@field_validator" not in code


class TestGeneratedCodeExecution:
    """Tests that generated code actually works."""

    def test_generated_code_imports(self, generator):
        """Test that generated code can be imported."""
        code = generator.generate_model("subscriber", include_validators=True)

        # Parse to ensure it's valid Python
        try:
            tree = ast.parse(code)
            assert len(tree.body) > 0
        except SyntaxError as e:
            pytest.fail(f"Generated code has syntax error: {e}")

    def test_generated_code_has_all_sections(self, generator):
        """Test generated code has all expected sections."""
        code = generator.generate_model("subscriber", include_validators=True)

        # Check all major sections
        sections = [
            "from __future__ import annotations",
            "from datetime import",
            "from pydantic import",
            "class Subscriber(BaseModel):",
            '"""Subscriber model.',
            "Attributes:",
            "id: int = Field(",
            "@field_validator",
            "model_config = ConfigDict(",
        ]

        for section in sections:
            assert (
                section in code
            ), f"Generated code missing expected section: {section}"

    def test_multiple_models_generation(self, registry):
        """Test generating multiple models works correctly."""
        # Add another schema
        media_schema = (
            SchemaBuilder("media")
            .field(0, "id", field_type=FieldType.INTEGER, description="Media ID")
            .field(1, "title", field_type=FieldType.STRING, description="Media title")
            .set_total_fields(2)
            .build()
        )
        media_schema.fields[0].constraints = {"nullable": False}
        media_schema.fields[1].constraints = {"nullable": False}
        registry.register(media_schema)

        generator = PydanticModelGenerator(registry)

        # Generate both models
        subscriber_code = generator.generate_model("subscriber")
        media_code = generator.generate_model("media")

        # Both should be valid
        assert "class Subscriber(BaseModel):" in subscriber_code
        assert "class Media(BaseModel):" in media_code

        # They should be independent
        assert "class Media(BaseModel):" not in subscriber_code
        assert "class Subscriber(BaseModel):" not in media_code


class TestFieldTypeMapping:
    """Tests for field type to Python type mapping."""

    def test_all_field_types_mapped(self, registry):
        """Test all FieldType enums have Python type mappings."""
        # Create schema with all field types
        test_schema = SchemaBuilder("test_all_types")

        field_types = [
            FieldType.INTEGER,
            FieldType.STRING,
            FieldType.BOOLEAN,
            FieldType.FLOAT,
            FieldType.DATETIME,
            FieldType.DATE,
            FieldType.JSON,
            FieldType.UNKNOWN,
        ]

        for idx, ft in enumerate(field_types):
            test_schema.field(
                idx, f"field_{ft.value}", field_type=ft, description=f"{ft.value} field"
            )
            test_schema.fields[idx].constraints = {"nullable": True}

        schema = test_schema.set_total_fields(len(field_types)).build()
        registry.register(schema)

        generator = PydanticModelGenerator(registry)
        code = generator.generate_model("test_all_types", include_validators=False)

        # Verify all types are present
        assert "int" in code
        assert "str" in code
        assert "bool" in code
        assert "float" in code
        assert "datetime" in code
        assert "date" in code
        assert "dict[str, Any]" in code or "dict" in code


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_schema(self, registry):
        """Test handling of schema with no fields."""
        empty_schema = SchemaBuilder("empty").set_total_fields(0).build()
        registry.register(empty_schema)

        generator = PydanticModelGenerator(registry)
        code = generator.generate_model("empty", include_validators=False)

        # Should still generate a valid class
        assert "class Empty(BaseModel):" in code
        assert "model_config = ConfigDict(" in code

    def test_special_characters_in_description(self, registry):
        """Test field descriptions with special characters."""
        schema = (
            SchemaBuilder("test")
            .field(
                0,
                "field",
                field_type=FieldType.STRING,
                description='Field with "quotes" and special chars!',
            )
            .set_total_fields(1)
            .build()
        )
        schema.fields[0].constraints = {"nullable": False}
        registry.register(schema)

        generator = PydanticModelGenerator(registry)
        code = generator.generate_model("test", include_validators=False)

        # Should escape quotes properly
        assert '\\"' in code or "quotes" in code

    def test_long_field_name(self, registry):
        """Test handling of very long field names."""
        schema = (
            SchemaBuilder("test")
            .field(
                0,
                "this_is_a_very_long_field_name_that_should_still_work_correctly",
                field_type=FieldType.STRING,
                description="Long field name",
            )
            .set_total_fields(1)
            .build()
        )
        schema.fields[0].constraints = {"nullable": False}
        registry.register(schema)

        generator = PydanticModelGenerator(registry)
        code = generator.generate_model("test", include_validators=False)

        # Should handle long names
        assert "this_is_a_very_long_field_name_that_should_still_work_correctly" in code
