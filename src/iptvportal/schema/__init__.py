"""Schema system for table field definitions and SELECT * expansion."""

from iptvportal.schema.codegen import ORMGenerator
from iptvportal.schema.introspector import SchemaIntrospector
from iptvportal.schema.table import (
    FieldDefinition,
    FieldType,
    SchemaBuilder,
    SchemaExtractor,
    SchemaLoader,
    SchemaRegistry,
    SyncConfig,
    TableMetadata,
    TableSchema,
)

__all__ = [
    # Core schema classes
    "TableSchema",
    "FieldDefinition",
    "FieldType",
    "SyncConfig",
    "TableMetadata",
    # Registry and loaders
    "SchemaRegistry",
    "SchemaLoader",
    "SchemaBuilder",
    "SchemaExtractor",
    # Utilities
    "SchemaIntrospector",
    "ORMGenerator",
]
