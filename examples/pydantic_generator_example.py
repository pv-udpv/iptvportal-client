"""Example demonstrating the Pydantic model generator usage.

This example shows how to use the enhanced Pydantic model generator
with MCP tools for automated model generation from schemas.
"""

from iptvportal.schema import (
    FieldType,
    PydanticModelGenerator,
    SchemaBuilder,
    SchemaRegistry,
    pydantic_schema,
    schema_validator,
)


def main() -> None:
    """Demonstrate Pydantic model generation."""
    # Step 1: Create a schema registry and add table schemas
    registry = SchemaRegistry()

    # Create subscriber schema
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
        .set_total_fields(5)
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

    # Register the schema
    registry.register(subscriber_schema)

    # Step 2: Generate Pydantic model using the generator
    print("=" * 80)
    print("Pydantic Model Generation Example")
    print("=" * 80)
    print()

    generator = PydanticModelGenerator(registry)
    model_code = generator.generate_model(
        "subscriber", include_validators=True, include_examples=True
    )

    print("Generated Model:")
    print("-" * 80)
    print(model_code)
    print("-" * 80)
    print()

    # Step 3: Validate the generated model
    print("Validating generated model...")
    validation_report = generator.validate_model(model_code, strict=False)

    print(f"Valid: {validation_report['valid']}")
    print(f"Errors: {len(validation_report['errors'])}")
    print(f"Warnings: {len(validation_report['warnings'])}")
    print(f"Info: {len(validation_report['info'])}")

    if validation_report["warnings"]:
        print("\nWarnings:")
        for warning in validation_report["warnings"]:
            print(f"  - {warning}")

    if validation_report["info"]:
        print("\nInfo:")
        for info_item in validation_report["info"]:
            print(f"  - {info_item}")

    print()

    # Step 4: Check integration
    print("Checking integration compatibility...")
    integration_report = generator.check_integration(model_code, "subscriber")

    print(f"Transport compatible: {integration_report['transport_compatible']}")
    print(
        f"Resource manager compatible: {integration_report['resource_manager_compatible']}"
    )
    print(f"Query builder compatible: {integration_report['query_builder_compatible']}")

    if integration_report["suggestions"]:
        print("\nSuggestions:")
        for suggestion in integration_report["suggestions"]:
            print(f"  - {suggestion}")

    print()

    # Step 5: Use MCP tool functions
    print("=" * 80)
    print("Using MCP Tools")
    print("=" * 80)
    print()

    # Use pydantic_schema tool
    print("1. Using pydantic_schema MCP tool:")
    mcp_model = pydantic_schema(
        registry, "subscriber", include_validators=True, include_examples=True
    )
    print(f"Generated {len(mcp_model.splitlines())} lines of code")
    print()

    # Use schema_validator tool
    print("2. Using schema_validator MCP tool:")
    validation = schema_validator(mcp_model, strict=False)
    print(f"Valid: {validation['valid']}")
    print(f"Total checks: {len(validation['errors']) + len(validation['warnings'])}")
    print()

    print("=" * 80)
    print("Example completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
