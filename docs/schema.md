# Schema System Documentation

The IPTVPortal Client schema system provides powerful capabilities for handling `SELECT *` queries when you cannot access `INFORMATION_SCHEMA` to get table metadata. It allows you to:

- Define partial table schemas with only the fields you know
- Auto-generate field names for undescribed columns
- Map query results to dictionaries or Pydantic/SQLModel models
- Support field aliasing (like Pydantic `Field(alias=...)`)
- Apply transformer functions to convert field values

## Table of Contents

- [Core Concepts](#core-concepts)
- [Basic Usage](#basic-usage)
- [Configuration](#configuration)
- [Programmatic API](#programmatic-api)
- [Field Mapping](#field-mapping)
- [Pydantic/SQLModel Integration](#pydanticsqlmodel-integration)
- [SELECT * Expansion](#select--expansion)
- [Advanced Usage](#advanced-usage)

## Core Concepts

### Field Positions

Fields are identified by their **0-indexed position** in the `SELECT *` result set. This is crucial because without `INFORMATION_SCHEMA` access, we rely on field order:

```python
# Position:  0    1      2       3        4
# SELECT * returns: [id, name, email, created, status, ...]
```

### Partial Schemas

You don't need to describe all fields - only the ones you care about:

```yaml
schemas:
  users:
    total_fields: 10  # Total columns in SELECT *
    fields:
      "0": {name: "id", type: "integer"}
      "1": {name: "name", type: "string"}
      "5": {name: "email", type: "string"}
      # Fields 2, 3, 4, 6, 7, 8, 9 will be auto-named as Field_2, Field_3, etc.
```

### Field Types

Supported field types:

- `integer` - Integer values
- `string` - String values
- `boolean` - Boolean values
- `float` - Floating point numbers
- `datetime` - Date and time values
- `date` - Date only values
- `json` - JSON data
- `unknown` - Unknown/unspecified type

## Basic Usage

### 1. Create Schema Configuration File

Create `config/schemas.yaml`:

```yaml
schemas:
  media:
    total_fields: 15
    fields:
      "0":
        name: "id"
        type: "integer"
        description: "Media ID"
      "1":
        name: "title"
        type: "string"
        alias: "media_title"
      "3":
        name: "duration"
        type: "integer"
        description: "Duration in seconds"
      "7":
        name: "created_at"
        type: "datetime"
        transformer: "datetime"
```

### 2. Configure Client

In your configuration file or environment:

```yaml
iptvportal:
  domain: "your_domain"
  username: "admin"
  password: "secret"
  
  # Schema configuration
  schema_file: "config/schemas.yaml"
  schema_format: "yaml"  # or "json"
  auto_load_schemas: true
```

### 3. Use with Client

```python
from iptvportal import IPTVPortalClient, IPTVPortalSettings

# Schemas are auto-loaded from config
settings = IPTVPortalSettings(
    domain="operator",
    username="admin",
    password="secret",
    schema_file="config/schemas.yaml"
)

with IPTVPortalClient(settings) as client:
    # Execute query with automatic mapping
    query = {"query": "SELECT * FROM media WHERE id < 100"}
    results = client.execute_mapped(query, table_name="media")
    
    # Results are now dictionaries with proper field names
    for row in results:
        print(f"ID: {row['id']}, Title: {row['media_title']}")
        # Unknown fields are accessible as Field_2, Field_4, etc.
```

## Configuration

### YAML Format

```yaml
schemas:
  table_name:
    total_fields: <number>  # Total columns in SELECT *
    fields:
      "<position>":
        name: "<db_field_name>"
        type: "<field_type>"
        alias: "<optional_alias>"
        python_name: "<optional_python_name>"
        description: "<optional_description>"
        transformer: "<optional_transformer>"
```

### JSON Format

```json
{
  "schemas": {
    "table_name": {
      "total_fields": 10,
      "fields": {
        "0": {
          "name": "id",
          "type": "integer",
          "description": "Primary key"
        },
        "1": {
          "name": "name",
          "type": "string",
          "alias": "full_name"
        }
      }
    }
  }
}
```

### Built-in Transformers

Available transformers for automatic value conversion:

- `datetime` - Parse ISO datetime strings to datetime objects
- `date` - Parse ISO date strings to date objects
- `int` - Convert to integer
- `float` - Convert to float
- `str` - Convert to string
- `bool` - Convert to boolean
- `json` - Parse JSON strings

```yaml
fields:
  "5":
    name: "created_at"
    type: "datetime"
    transformer: "datetime"  # Converts "2024-01-15T10:30:00" to datetime object
```

## Programmatic API

### Using SchemaBuilder

Build schemas programmatically with a fluent API:

```python
from iptvportal.schema import SchemaBuilder, FieldType, SchemaRegistry

# Build schema
schema = (
    SchemaBuilder("media")
    .field(0, "id", field_type=FieldType.INTEGER)
    .field(1, "title", alias="media_title", field_type=FieldType.STRING)
    .field(3, "duration", field_type=FieldType.INTEGER)
    .set_total_fields(15)
    .build()
)

# Register schema
registry = SchemaRegistry()
registry.register(schema)

# Use with client
client.schema_registry = registry
```

### Custom Transformers

Define custom transformer functions:

```python
def parse_custom_date(value):
    """Custom date parser."""
    if isinstance(value, str):
        # Your custom parsing logic
        return datetime.strptime(value, "%d/%m/%Y")
    return value

schema = (
    SchemaBuilder("events")
    .field(0, "id", field_type=FieldType.INTEGER)
    .field(2, "event_date", 
           field_type=FieldType.DATE,
           transformer=parse_custom_date)
    .set_total_fields(5)
    .build()
)
```

## Field Mapping

### Aliases

Use aliases to rename fields in the output:

```yaml
fields:
  "1":
    name: "subscriber_id"  # Name in database
    alias: "sub_id"         # Name in mapped output
```

```python
row = [1, 12345, "John", ...]
mapped = schema.map_row_to_dict(row)
# Result: {"id": 1, "sub_id": 12345, "name": "John", ...}
```

### Python Names

Python names take precedence over aliases (useful for snake_case conversion):

```yaml
fields:
  "1":
    name: "SubscriberID"
    alias: "subscriber_id"
    python_name: "subscriber_identifier"
```

Precedence: `python_name > alias > name`

## Pydantic/SQLModel Integration

### Automatic Schema Extraction

Extract schemas from Pydantic or SQLModel models:

```python
from pydantic import BaseModel, Field
from iptvportal.schema import SchemaExtractor

class Media(BaseModel):
    id: int
    title: str = Field(alias="media_title")
    duration: int
    created_at: datetime

# Extract schema
schema = SchemaExtractor.from_pydantic(
    model=Media,
    table_name="media",
    field_positions={
        "id": 0,
        "title": 1,
        "duration": 3,
        "created_at": 7
    },
    total_fields=15
)

# Register and use
client.schema_registry.register(schema)
```

### Mapping to Models

Map query results directly to model instances:

```python
# Execute with model mapping
results = client.execute_mapped(
    query={"query": "SELECT * FROM media"},
    table_name="media",
    model=Media
)

# Results are Media instances
for media in results:
    print(f"{media.title}: {media.duration} seconds")
    print(f"Created: {media.created_at}")
```

### Schema Decorator

Use decorator for automatic registration:

```python
from iptvportal.schema import schema_config
from sqlmodel import SQLModel

@schema_config(
    positions={"id": 0, "name": 1, "email": 2},
    total_fields=10,
    registry=client.schema_registry
)
class Subscriber(SQLModel, table=True):
    __tablename__ = "subscriber"
    
    id: int
    name: str
    email: str
```

## SELECT * Expansion

The schema system automatically expands `SELECT *` in queries when using the transpiler:

```python
from iptvportal.transpiler import SQLTranspiler

# Initialize transpiler with schema registry
transpiler = SQLTranspiler(schema_registry=client.schema_registry)

# This query:
sql = "SELECT * FROM media WHERE id < 100"

# Is automatically expanded to:
# SELECT id, title, Field_2, duration, Field_4, Field_5, Field_6,
#        created_at, Field_8, Field_9, Field_10, Field_11, Field_12,
#        Field_13, Field_14 FROM media WHERE id < 100

result = transpiler.transpile(sql)
```

This ensures:
- All fields are explicitly named
- Proper mapping can occur
- Consistent results across API calls

## CLI Usage

The CLI automatically detects table names from JSONSQL queries and applies schema mapping when the `--map-schema` flag is used.

### Basic CLI Schema Mapping

```bash
# Use schema mapping with automatic table detection
iptvportal sql select --from media --map-schema

# Works with any JSONSQL query
iptvportal sql select --from subscriber --where '{"status": "active"}' --map-schema
```

### Automatic Schema Generation

When using `--map-schema` with a table that doesn't have a predefined schema, the system will automatically generate one:

```bash
# First query to a new table - auto-generates schema
iptvportal sql select --from new_table --map-schema
```

The CLI will:
1. Extract the table name from the query parameters
2. Check if a schema exists for that table
3. If no schema exists:
   - Execute the query to get sample results
   - Inspect the first row to determine field count and types
   - Auto-generate a schema with `Field_0`, `Field_1`, etc.
   - Register the schema for future use
   - Apply the schema to map the results
4. If schema exists, use it for mapping

### Output Example

With auto-generation enabled:

```bash
$ iptvportal sql select --from unknown_table --limit 5 --map-schema

Auto-generating schema for table: unknown_table
✓ Generated schema with 8 fields

[
  {
    "Field_0": 1,
    "Field_1": "Sample Data",
    "Field_2": "2024-01-15T10:30:00",
    "Field_3": 42,
    "Field_4": true,
    "Field_5": null,
    "Field_6": 3.14,
    "Field_7": {"key": "value"}
  },
  ...
]
```

### Benefits of Auto-Generation

- **Zero Configuration**: Works immediately without predefined schemas
- **Consistent Field Names**: Uses `Field_N` pattern for predictable access
- **Type Detection**: Automatically infers field types from data
- **Persistent**: Generated schemas are cached for the session
- **Extensible**: Can be saved and manually refined later

### Refining Auto-Generated Schemas

After auto-generation, you can export and refine the schema:

```python
# In your Python code
from iptvportal import IPTVPortalClient

with IPTVPortalClient(settings) as client:
    # After auto-generation happened in CLI
    schema = client.schema_registry.get("table_name")
    
    # Export to dictionary
    schema_dict = schema.to_dict()
    
    # Save to file and manually add aliases, transformers, etc.
```

Then update your `schemas.yaml`:

```yaml
schemas:
  table_name:
    total_fields: 8
    fields:
      "0":
        name: "id"  # Was Field_0
        type: "integer"
      "1":
        name: "title"  # Was Field_1
        type: "string"
        alias: "display_title"
      # ... refine other fields as needed
```

## Advanced Usage

### Async Client Support

The async client has identical schema support:

```python
from iptvportal import AsyncIPTVPortalClient

async with AsyncIPTVPortalClient(settings) as client:
    results = await client.execute_mapped(
        query={"query": "SELECT * FROM media"},
        table_name="media"
    )
```

### Multiple Tables

Define schemas for multiple tables:

```yaml
schemas:
  media:
    total_fields: 15
    fields:
      # ... media fields ...
  
  subscriber:
    total_fields: 20
    fields:
      # ... subscriber fields ...
  
  terminal:
    total_fields: 12
    fields:
      # ... terminal fields ...
```

### Loading from Models

Load schema directly from model definition in config:

```yaml
schemas:
  subscriber:
    from_model: "myapp.models.Subscriber"
    total_fields: 20
    fields:
      "0": {name: "id"}
      "1": {name: "name"}
      # positions for each field
```

### Dynamic Schema Registration

Register schemas at runtime:

```python
# Load from file
from iptvportal.schema import SchemaLoader

registry = SchemaLoader.from_yaml("schemas.yaml")
client.schema_registry = registry

# Or build programmatically
schema = SchemaBuilder("dynamic_table")...build()
client.schema_registry.register(schema)
```

### Export Schemas

Export schemas to dictionary for serialization:

```python
schema_dict = schema.to_dict()

# Returns:
# {
#     "total_fields": 15,
#     "fields": {
#         "0": {"name": "id", "type": "integer", ...},
#         ...
#     }
# }
```

## Best Practices

1. **Document Field Positions**: Keep a reference of SELECT * field order for your tables

2. **Use Aliases Consistently**: Define aliases in schemas to maintain consistent naming

3. **Leverage Transformers**: Use built-in transformers for common conversions (dates, JSON)

4. **Version Your Schemas**: Keep schema files in version control alongside code

5. **Test with Real Data**: Verify field positions match actual query results

6. **Partial Definitions**: Only define fields you actually use - save time and reduce errors

7. **Model Integration**: For type-safe code, integrate with Pydantic/SQLModel models

## Troubleshooting

### Wrong Field Positions

If fields appear misaligned:

```python
# Verify actual SELECT * order
query = {"query": "SELECT * FROM media LIMIT 1"}
raw_result = client.execute(query)
print(raw_result[0])  # Check actual field positions
```

### Missing Transformer

If values aren't transformed:

```yaml
# Make sure transformer is specified correctly
fields:
  "5":
    name: "created_at"
    transformer: "datetime"  # Must be exact name from BUILTIN_TRANSFORMERS
```

### Schema Not Loading

Check configuration:

```python
# Verify schema file path
print(client.settings.schema_file)

# Check if schemas loaded
print(client.schema_registry.list_tables())

# Manual load if needed
client._load_schemas()
```

## Examples

See `config/schemas.yaml` for complete examples of all IPTVPortal tables including:

- media
- subscriber  
- terminal
- tv_channel
- package
- package_channel
- subscription

Each example demonstrates different features like aliases, transformers, and partial field definitions.
