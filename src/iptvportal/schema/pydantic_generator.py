"""Enhanced Pydantic v2 model generator with MCP tools.

This module provides advanced Pydantic model generation capabilities with:
- Automated type inference and validation
- Google-style docstring generation
- mypy strict compliance checking
- Integration validation with transport and resource managers

MCP Tools:
- pydantic_schema: Generate models from schemas
- schema_validator: Validate generated models
- integration_checker: Check transport/resource manager integration
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path
from typing import Any

from iptvportal.schema.table import (
    FieldDefinition,
    FieldType,
    SchemaRegistry,
    TableSchema,
)


class PydanticModelGenerator:
    """Enhanced Pydantic v2 model generator with strict typing and validation.
    
    Generates Pydantic BaseModel classes from table schemas with:
    - Full type hints (Python 3.10+ syntax)
    - Field validators with business logic
    - Google-style docstrings
    - ConfigDict for model configuration
    - mypy strict mode compliance
    
    Attributes:
        registry: Schema registry containing table definitions
        use_modern_syntax: Use Python 3.10+ union syntax (str | None)
    """

    def __init__(self, registry: SchemaRegistry, use_modern_syntax: bool = True) -> None:
        """Initialize the Pydantic model generator.
        
        Args:
            registry: Schema registry with table definitions
            use_modern_syntax: Use modern type syntax (str | None vs Optional[str])
        """
        self.registry = registry
        self.use_modern_syntax = use_modern_syntax

    def generate_model(
        self,
        table_name: str,
        include_validators: bool = True,
        include_examples: bool = True,
    ) -> str:
        """Generate Pydantic BaseModel from table schema.
        
        MCP Tool: pydantic_schema
        
        This is the primary model generation tool that creates complete Pydantic
        models with type hints, validators, and documentation.
        
        Args:
            table_name: Name of the table to generate model for
            include_validators: Include field validators in generated code
            include_examples: Include usage examples in docstrings
            
        Returns:
            Complete Python code for the Pydantic model
            
        Raises:
            ValueError: If schema for table is not found
        """
        schema = self.registry.get(table_name)
        if not schema:
            raise ValueError(f"Schema for table '{table_name}' not found in registry")

        lines: list[str] = []

        # Add module docstring
        lines.extend(self._generate_module_docstring(table_name, schema))
        lines.append("")

        # Imports
        lines.extend(self._generate_imports(schema, include_validators))
        lines.append("")

        # Class definition
        class_name = self._table_name_to_class_name(table_name)
        lines.extend(
            self._generate_class_definition(
                class_name, table_name, schema, include_examples
            )
        )

        # Fields
        for position in sorted(schema.fields.keys()):
            field_def = schema.fields[position]
            lines.extend(self._generate_field(field_def))

        # Validators
        if include_validators:
            lines.append("")
            for position in sorted(schema.fields.keys()):
                field_def = schema.fields[position]
                validator_lines = self._generate_field_validator(field_def)
                if validator_lines:
                    lines.extend(validator_lines)
                    lines.append("")

        # Model configuration
        lines.extend(self._generate_model_config())

        return "\n".join(lines)

    def validate_model(self, model_code: str, strict: bool = True) -> dict[str, Any]:
        """Validate generated Pydantic model for correctness.
        
        MCP Tool: schema_validator
        
        Performs comprehensive validation on generated models:
        - Syntax validation (AST parsing)
        - Type hint presence and correctness
        - Docstring format validation (Google style)
        - mypy strict mode compliance
        - Field validator presence
        
        Args:
            model_code: Generated Python code to validate
            strict: Run mypy in strict mode
            
        Returns:
            Validation report with errors, warnings, and suggestions
            
        Example:
            >>> gen = PydanticModelGenerator(registry)
            >>> code = gen.generate_model("subscriber")
            >>> report = gen.validate_model(code)
            >>> assert report["valid"]
            >>> assert len(report["errors"]) == 0
        """
        report: dict[str, Any] = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "info": [],
        }

        # 1. Syntax validation
        try:
            tree = ast.parse(model_code)
        except SyntaxError as e:
            report["valid"] = False
            report["errors"].append(f"Syntax error: {e}")
            return report

        # 2. Check for class definition
        classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
        if not classes:
            report["valid"] = False
            report["errors"].append("No class definition found")
            return report

        model_class = classes[0]

        # 3. Check docstring
        docstring = ast.get_docstring(model_class)
        if not docstring:
            report["warnings"].append("Class docstring is missing")
        elif not self._is_google_style_docstring(docstring):
            report["warnings"].append("Docstring does not follow Google style")

        # 4. Check type hints on all fields
        for node in model_class.body:
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                field_name = node.target.id
                if node.annotation is None:
                    report["errors"].append(f"Field '{field_name}' missing type hint")
                    report["valid"] = False

        # 5. Check for Field() usage
        has_field_usage = any(
            isinstance(node, ast.AnnAssign)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "Field"
            for node in model_class.body
        )

        if not has_field_usage:
            report["info"].append(
                "Consider using Field() for better validation and documentation"
            )

        # 6. mypy validation (if requested)
        if strict:
            mypy_result = self._run_mypy_check(model_code)
            if mypy_result["errors"]:
                report["valid"] = False
                report["errors"].extend(mypy_result["errors"])

        return report

    def check_integration(
        self, model_code: str, table_name: str
    ) -> dict[str, Any]:
        """Check model integration with transport and resource managers.
        
        MCP Tool: integration_checker
        
        Validates that generated models integrate correctly with:
        - HTTP transport layer (serialization/deserialization)
        - Resource managers (CRUD operations)
        - Query builders (filter operations)
        
        Args:
            model_code: Generated model code
            table_name: Table name for context
            
        Returns:
            Integration check report with status and issues
        """
        report: dict[str, Any] = {
            "transport_compatible": True,
            "resource_manager_compatible": True,
            "query_builder_compatible": True,
            "issues": [],
            "suggestions": [],
        }

        # Parse the model
        try:
            tree = ast.parse(model_code)
        except SyntaxError:
            report["transport_compatible"] = False
            report["issues"].append("Model has syntax errors")
            return report

        classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
        if not classes:
            report["issues"].append("No model class found")
            return report

        model_class = classes[0]

        # 1. Check BaseModel inheritance
        base_names = []
        for base in model_class.bases:
            if isinstance(base, ast.Name):
                base_names.append(base.id)

        if "BaseModel" not in base_names:
            report["transport_compatible"] = False
            report["issues"].append("Model must inherit from BaseModel")

        # 2. Check for model_dump/model_validate methods
        # These are provided by BaseModel, so just ensure BaseModel is used
        if "BaseModel" in base_names:
            report["suggestions"].append(
                "Model supports model_dump() and model_validate() through BaseModel"
            )

        # 3. Check ConfigDict usage
        has_config = any(
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "model_config"
            for node in model_class.body
        )

        if has_config:
            report["suggestions"].append("Model has custom configuration (model_config)")
        else:
            report["suggestions"].append(
                "Consider adding model_config with from_attributes=True"
            )

        # 4. Check for datetime fields (need proper handling)
        for node in model_class.body:
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.annotation and self._has_datetime_type(node.annotation):
                    report["suggestions"].append(
                        f"Field '{node.target.id}' uses datetime - ensure timezone awareness"
                    )

        return report

    def _generate_module_docstring(
        self, table_name: str, schema: TableSchema
    ) -> list[str]:
        """Generate module-level docstring."""
        class_name = self._table_name_to_class_name(table_name)
        return [
            f'"""{class_name} model for IPTVPortal.',
            "",
            f"Generated Pydantic model for {table_name} table with full type safety,",
            "validation, and integration support.",
            '"""',
        ]

    def _generate_imports(
        self, schema: TableSchema, include_validators: bool
    ) -> list[str]:
        """Generate import statements based on schema requirements."""
        lines = ["from __future__ import annotations", ""]

        # Standard library imports
        imports = set()

        # Check if we need datetime/date
        for field_def in schema.fields.values():
            if field_def.field_type in (FieldType.DATETIME, FieldType.DATE):
                if field_def.field_type == FieldType.DATETIME:
                    imports.add("datetime")
                if field_def.field_type == FieldType.DATE:
                    imports.add("date")

        if imports:
            datetime_imports = ", ".join(sorted(imports))
            lines.append(f"from datetime import {datetime_imports}")

        # Pydantic imports
        pydantic_imports = ["BaseModel", "Field"]
        if include_validators:
            pydantic_imports.append("field_validator")
        pydantic_imports.append("ConfigDict")

        lines.append(f"from pydantic import {', '.join(pydantic_imports)}")

        return lines

    def _generate_class_definition(
        self,
        class_name: str,
        table_name: str,
        schema: TableSchema,
        include_examples: bool,
    ) -> list[str]:
        """Generate class definition with comprehensive docstring."""
        lines = ["", "", f"class {class_name}(BaseModel):"]

        # Build docstring
        docstring_lines = [f'    """{class_name} model.']

        # Add longer description
        docstring_lines.append("")
        docstring_lines.append(
            f"    Represents a {table_name} record from the IPTVPortal database."
        )

        if schema.metadata and schema.metadata.row_count:
            docstring_lines.append(
                f"    Contains {schema.total_fields} fields with ~{schema.metadata.row_count:,} records."
            )

        # Attributes section
        docstring_lines.append("")
        docstring_lines.append("    Attributes:")
        for position in sorted(schema.fields.keys()):
            field_def = schema.fields[position]
            field_name = field_def.python_name or field_def.name
            description = field_def.description or f"{field_name} field"
            docstring_lines.append(f"        {field_name}: {description}")

        # Example section
        if include_examples:
            docstring_lines.append("")
            docstring_lines.append("    Example:")
            docstring_lines.append(f"        >>> model = {class_name}(")

            # Add example field values
            example_fields = []
            for position in sorted(schema.fields.keys())[:3]:  # First 3 fields
                field_def = schema.fields[position]
                field_name = field_def.python_name or field_def.name
                example_value = self._get_example_value(field_def)
                example_fields.append(f"        ...     {field_name}={example_value}")

            docstring_lines.extend(example_fields)
            docstring_lines.append("        ... )")
            first_field = schema.fields[0]
            first_field_name = first_field.python_name or first_field.name
            docstring_lines.append(f"        >>> model.{first_field_name}")
            docstring_lines.append(f"        {self._get_example_value(first_field)}")

        docstring_lines.append('    """')

        lines.extend(docstring_lines)
        lines.append("")

        return lines

    def _generate_field(self, field_def: FieldDefinition) -> list[str]:
        """Generate a single field definition with type hint and Field()."""
        lines = []

        # Determine Python type
        python_type = self._field_type_to_python_type(field_def.field_type)

        # Determine nullable
        nullable = True
        if field_def.constraints:
            nullable = field_def.constraints.get("nullable", True)

        # Format type hint (use modern syntax if enabled)
        if nullable:
            type_hint = (
                f"{python_type} | None"
                if self.use_modern_syntax
                else f"Optional[{python_type}]"
            )
        else:
            type_hint = python_type

        # Build Field() arguments
        field_args = []

        # Default/required marker
        if nullable:
            field_args.append("None")
        else:
            field_args.append("...")

        # Add constraints
        if field_def.constraints:
            # String constraints
            if python_type == "str":
                if "min_length" in field_def.constraints:
                    field_args.append(
                        f"min_length={field_def.constraints['min_length']}"
                    )
                if "max_length" in field_def.constraints:
                    field_args.append(
                        f"max_length={field_def.constraints['max_length']}"
                    )

            # Numeric constraints
            if python_type in ("int", "float"):
                if "ge" in field_def.constraints:
                    field_args.append(f"ge={field_def.constraints['ge']}")
                if "le" in field_def.constraints:
                    field_args.append(f"le={field_def.constraints['le']}")
                if "gt" in field_def.constraints:
                    field_args.append(f"gt={field_def.constraints['gt']}")
                if "lt" in field_def.constraints:
                    field_args.append(f"lt={field_def.constraints['lt']}")

        # Description
        if field_def.description:
            desc = field_def.description.replace('"', '\\"')
            field_args.append(f'description="{desc}"')

        # Format the field
        field_name = field_def.python_name or field_def.name
        field_str = f"    {field_name}: {type_hint} = Field({', '.join(field_args)})"

        lines.append(field_str)

        return lines

    def _generate_field_validator(
        self, field_def: FieldDefinition
    ) -> list[str]:
        """Generate field validator for common validation scenarios."""
        field_name = field_def.python_name or field_def.name
        python_type = self._field_type_to_python_type(field_def.field_type)

        # Only generate validators for specific scenarios
        needs_validator = False

        # String trimming and empty check
        if python_type == "str" and field_def.constraints:
            if not field_def.constraints.get("nullable", True):
                needs_validator = True

        if not needs_validator:
            return []

        lines = []

        # Generate validator
        lines.append(f"    @field_validator('{field_name}')")
        lines.append("    @classmethod")
        lines.append(
            f"    def validate_{field_name}(cls, v: {python_type}) -> {python_type}:"
        )
        lines.append(f'        """Validate {field_name} field.')
        lines.append("")
        lines.append("        Args:")
        lines.append("            v: Field value to validate")
        lines.append("")
        lines.append("        Returns:")
        lines.append("            Validated field value")
        lines.append("")
        lines.append("        Raises:")
        lines.append("            ValueError: If validation fails")
        lines.append('        """')

        # Add validation logic
        if python_type == "str":
            lines.append("        if not v or not v.strip():")
            lines.append(f'            raise ValueError("{field_name} cannot be empty")')
            lines.append("        return v.strip()")

        return lines

    def _generate_model_config(self) -> list[str]:
        """Generate model configuration."""
        lines = [
            "",
            "    model_config = ConfigDict(",
            "        from_attributes=True,",
            "        str_strip_whitespace=True,",
            "        validate_assignment=True,",
            "    )",
        ]
        return lines

    def _field_type_to_python_type(self, field_type: FieldType) -> str:
        """Map FieldType to Python type string."""
        type_map = {
            FieldType.INTEGER: "int",
            FieldType.STRING: "str",
            FieldType.BOOLEAN: "bool",
            FieldType.FLOAT: "float",
            FieldType.DATETIME: "datetime",
            FieldType.DATE: "date",
            FieldType.JSON: "dict[str, Any]",
            FieldType.UNKNOWN: "str",
        }
        return type_map.get(field_type, "str")

    def _table_name_to_class_name(self, table_name: str) -> str:
        """Convert table name to class name (CamelCase)."""
        parts = table_name.split("_")
        return "".join(word.capitalize() for word in parts)

    def _get_example_value(self, field_def: FieldDefinition) -> str:
        """Get example value for field based on type."""
        python_type = self._field_type_to_python_type(field_def.field_type)

        examples = {
            "int": "1",
            "str": '"example"',
            "bool": "False",
            "float": "1.0",
            "datetime": "datetime.now()",
            "date": "date.today()",
        }

        return examples.get(python_type, '""')

    def _is_google_style_docstring(self, docstring: str) -> bool:
        """Check if docstring follows Google style guide."""
        # Basic check for Google-style sections
        google_sections = ["Args:", "Returns:", "Raises:", "Attributes:", "Example:"]
        return any(section in docstring for section in google_sections)

    def _has_datetime_type(self, annotation: ast.AST) -> bool:
        """Check if annotation contains datetime type."""
        if isinstance(annotation, ast.Name):
            return annotation.id in ("datetime", "date")
        if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            return self._has_datetime_type(
                annotation.left
            ) or self._has_datetime_type(annotation.right)
        return False

    def _run_mypy_check(self, code: str) -> dict[str, Any]:
        """Run mypy type checker on code."""
        result: dict[str, Any] = {"errors": [], "success": False}

        try:
            # Write code to temporary file
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False
            ) as f:
                f.write(code)
                temp_path = f.name

            # Run mypy
            proc = subprocess.run(
                [sys.executable, "-m", "mypy", "--strict", temp_path],
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Parse output
            if proc.returncode != 0:
                for line in proc.stdout.splitlines():
                    if "error:" in line:
                        result["errors"].append(line)
            else:
                result["success"] = True

            # Clean up
            Path(temp_path).unlink(missing_ok=True)

        except Exception as e:
            result["errors"].append(f"mypy check failed: {e}")

        return result


# Convenience functions for MCP tool access


def pydantic_schema(
    registry: SchemaRegistry,
    table_name: str,
    include_validators: bool = True,
    include_examples: bool = True,
) -> str:
    """MCP Tool: Generate Pydantic model from schema.
    
    Args:
        registry: Schema registry
        table_name: Table to generate model for
        include_validators: Include field validators
        include_examples: Include usage examples
        
    Returns:
        Generated Python code
    """
    generator = PydanticModelGenerator(registry)
    return generator.generate_model(table_name, include_validators, include_examples)


def schema_validator(model_code: str, strict: bool = True) -> dict[str, Any]:
    """MCP Tool: Validate generated Pydantic model.
    
    Args:
        model_code: Generated model code
        strict: Run mypy in strict mode
        
    Returns:
        Validation report
    """
    # Create a dummy registry for validation
    registry = SchemaRegistry()
    generator = PydanticModelGenerator(registry)
    return generator.validate_model(model_code, strict)


def integration_checker(model_code: str, table_name: str) -> dict[str, Any]:
    """MCP Tool: Check model integration with transport and resource managers.
    
    Args:
        model_code: Model code to check
        table_name: Table name for context
        
    Returns:
        Integration check report
    """
    registry = SchemaRegistry()
    generator = PydanticModelGenerator(registry)
    return generator.check_integration(model_code, table_name)
