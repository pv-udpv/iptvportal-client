# Schema-Driven Development Guide

This guide covers the schema-driven features of iptvportal-client, including data-driven validation, ORM code generation, and advanced schema management.

## Overview

The schema-driven architecture enables:
- **Data-driven field mapping validation** using pandas
- **ORM model generation** from schema definitions (SQLModel/Pydantic)
- **Database constraints** and relationship definitions
- **Validated remote field mappings** with match ratios and statistical analysis

## Table of Contents

1. [Schema Structure](#schema-structure)
2. [Field Definitions](#field-definitions)
3. [Validation & Remote Mapping](#validation--remote-mapping)
4. [ORM Model Generation](#orm-model-generation)
5. [CLI Commands](#cli-commands)
6. [Workflow Examples](#workflow-examples)

---

## Schema Structure

A complete schema definition includes:

```yaml
schemas:
  table_name:
    total_fields: 10
    description: "Table description"
    
    fields:
      0:  # Field position
        name: "field_name"
        type: "integer|string|boolean|float|datetime|date|json"
        description: "Field description"
        
        # Optional: Constraints
        constraints:
          primary_key: true
          nullable: false
          unique: true
          index: true
          foreign_key: "other_table.id"
          default: value
        
        # Optional: Remote mapping validation metadata
        remote_mapping:
          match_ratio: 1.0
          sample_size: 1000
          validated_at: "2025-01-01T10:00:00"
          dtype: "int64"
          null_count: 0
          unique_count: 1000
          remote_column: "id"
        
        # Optional: ORM relationships
        relationships:
          type: "one-to-many|many-to-one|many-to-many"
          target_table: "other_table"
          field_name: "related_field"
          back_populates: "back_reference"
    
    # Optional: Table metadata
    metadata:
      row_count: 150000
      max_id: 150000
      min_id: 1
      analyzed_at: "2025-01-01T10:00:00"
    
    # Optional: Sync configuration
    sync_config:
      where: "disabled = false"
      chunk_size: 10000
      cache_strategy: "incremental"
      incremental_field: "created_at"
```

## Field Definitions

### Basic Field Attributes

Every field must have:
- `name`: Field name in the database
- `type`: One of: `integer`, `string`, `boolean`, `float`, `datetime`, `date`, `json`, `unknown`
- `position`: 0-based position in SELECT * results

Optional attributes:
- `alias`: Alternative name for the field
- `python_name`: Python-friendly name (snake_case)
- `remote_name`: Name in remote schema
- `description`: Human-readable description
- `transformer`: Built-in transformer (`datetime`, `date`, `int`, `float`, `str`, `bool`, `json`)

### Constraints

Define database constraints for ORM generation:

```yaml
constraints:
  primary_key: true      # Is this a primary key?
  nullable: false        # Can field be NULL?
  unique: true          # Must be unique?
  index: true           # Create index?
  foreign_key: "table.field"  # Foreign key reference
  default: value        # Default value
```

### Remote Mapping

Validation metadata from data-driven comparison:

```yaml
remote_mapping:
  match_ratio: 0.98          # Percentage of matching values (0.0-1.0)
  sample_size: 1000          # Sample size used for validation
  validated_at: "2025-01-01T10:00:00"  # Validation timestamp
  dtype: "object"            # pandas dtype
  null_count: 15             # Number of NULL values
  unique_count: 985          # Number of unique values
  min_value: 0.0            # Min value (for numeric/datetime)
  max_value: 10000.0        # Max value (for numeric/datetime)
  remote_column: "email"     # Remote column name
```

### Relationships

ORM relationship definitions:

```yaml
relationships:
  type: "one-to-many"              # Relationship type
  target_table: "terminal"         # Target table
  field_name: "terminals"          # Relationship field name
  back_populates: "subscriber"     # Back reference field
```

Supported relationship types:
- `one-to-many`: One parent, many children
- `many-to-one`: Many children, one parent
- `many-to-many`: Many-to-many via junction table

## Validation & Remote Mapping

### Data-Driven Validation

Validate field mappings using pandas-based comparison:

```bash
# Validate specific field mappings
iptvportal schema validate-mapping subscriber \
  --mappings "0:id,1:username,2:email" \
  --sample-size 1000 \
  --save
```

This command:
1. Fetches sample data (default: 1000 rows)
2. Compares local field positions with remote columns
3. Calculates match ratios using pandas
4. Analyzes data types, NULL counts, and uniqueness
5. Optionally saves validation metadata to schema

### Match Ratio Interpretation

- **≥95%**: Excellent match (green) - mapping is correct
- **80-94%**: Good match (yellow) - review discrepancies
- **<80%**: Poor match (red) - mapping likely incorrect

### Validation Output

```
Validation Results:

Position | Remote Column | Match Ratio | Sample Size | Dtype  | Null Count | Unique
---------|--------------|-------------|-------------|--------|------------|--------
0        | id           | 100.00%     | 1000        | int64  | 0          | 1000
1        | username     | 100.00%     | 1000        | object | 0          | 1000
2        | email        | 98.00%      | 1000        | object | 15         | 985
```

## ORM Model Generation

### Generate SQLModel Models

```bash
# Generate SQLModel from schema file
iptvportal schema generate-models schemas.yaml

# Specify output directory
iptvportal schema generate-models schemas.yaml --output ./models

# Generate Pydantic instead of SQLModel
iptvportal schema generate-models schemas.yaml --format pydantic

# Exclude relationships
iptvportal schema generate-models schemas.yaml --no-relationships
```

### Generated SQLModel Example

From schema:
```yaml
subscriber:
  fields:
    0:
      name: id
      type: integer
      constraints:
        primary_key: true
    1:
      name: username
      type: string
      constraints:
        unique: true
        index: true
```

Generated code:
```python
from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel

class Subscriber(SQLModel, table=True):
    """ORM model for subscriber table."""

    __tablename__ = 'subscriber'

    id: int = Field(primary_key=True, description="Primary key")
    username: str = Field(..., unique=True, index=True, description="Login username")
```

### With Relationships

Schema:
```yaml
subscriber:
  fields:
    0:
      relationships:
        type: "one-to-many"
        target_table: "terminal"
        field_name: "terminals"
        back_populates: "subscriber"

terminal:
  fields:
    1:
      relationships:
        type: "many-to-one"
        target_table: "subscriber"
        field_name: "subscriber"
        back_populates: "terminals"
```

Generated:
```python
class Subscriber(SQLModel, table=True):
    # ... fields ...
    
    terminals: list["Terminal"] = Relationship(back_populates="subscriber")

class Terminal(SQLModel, table=True):
    # ... fields ...
    
    subscriber: Optional["Subscriber"] = Relationship(back_populates="terminals")
```

## CLI Commands

### Schema Validation

```bash
# Validate field mappings with data comparison
iptvportal schema validate-mapping TABLE_NAME \
  --mappings "POSITION:COLUMN,..." \
  [--sample-size SIZE] \
  [--save] \
  [--output FILE]
```

Options:
- `--mappings, -m`: Field position to column name mappings (required)
- `--sample-size, -s`: Number of rows to sample (default: 1000)
- `--save`: Save validation results to schema file
- `--output, -o`: Output file path

Examples:
```bash
# Validate subscriber fields
iptvportal schema validate-mapping subscriber \
  -m "0:id,1:username,2:email,3:disabled"

# Validate with larger sample and save results
iptvportal schema validate-mapping media \
  -m "0:id,1:name,2:url" \
  --sample-size 5000 \
  --save
```

### ORM Generation

```bash
# Generate ORM models from schema
iptvportal schema generate-models SCHEMA_FILE \
  [--output DIR] \
  [--format FORMAT] \
  [--relationships/--no-relationships]
```

Options:
- `--output, -o`: Output directory (default: models/)
- `--format, -f`: Model format: sqlmodel or pydantic (default: sqlmodel)
- `--relationships`: Include relationships (default: true)

Examples:
```bash
# Generate SQLModel models
iptvportal schema generate-models schemas.yaml

# Generate Pydantic models to custom directory
iptvportal schema generate-models schemas.yaml \
  --output ./app/models \
  --format pydantic

# Generate without relationships
iptvportal schema generate-models schemas.yaml \
  --no-relationships
```

## Workflow Examples

### Complete Schema Workflow

1. **Introspect remote table** (automatic field detection):
```bash
iptvportal schema introspect subscriber --save
```

2. **Validate field mappings** (data-driven):
```bash
iptvportal schema validate-mapping subscriber \
  -m "0:id,1:username,2:email,3:disabled,4:balance,5:created_at" \
  --save
```

3. **Add constraints and relationships** manually to YAML:
```yaml
# Edit subscriber-schema.yaml
fields:
  0:
    name: id
    constraints:
      primary_key: true
      nullable: false
    relationships:
      type: "one-to-many"
      target_table: "terminal"
      field_name: "terminals"
```

4. **Generate ORM models**:
```bash
iptvportal schema generate-models config/schemas.yaml \
  --output ./app/models
```

5. **Use generated models** in your application:
```python
from app.models.subscriber import Subscriber
from sqlmodel import Session, create_engine

engine = create_engine("sqlite:///database.db")

with Session(engine) as session:
    subscriber = Subscriber(
        username="john_doe",
        email="john@example.com",
        disabled=False,
        balance=100.0
    )
    session.add(subscriber)
    session.commit()
```

### FastAPI Integration

```python
from fastapi import FastAPI, Depends
from sqlmodel import Session, select
from app.models.subscriber import Subscriber
from app.models.terminal import Terminal

app = FastAPI()

@app.get("/subscribers/{subscriber_id}")
def get_subscriber(subscriber_id: int, session: Session = Depends(get_session)):
    subscriber = session.get(Subscriber, subscriber_id)
    return subscriber

@app.get("/subscribers/{subscriber_id}/terminals")
def get_subscriber_terminals(subscriber_id: int, session: Session = Depends(get_session)):
    subscriber = session.get(Subscriber, subscriber_id)
    return subscriber.terminals  # Uses relationship
```

### Alembic Migrations

After generating models, create migrations:

```bash
# Initialize Alembic
alembic init alembic

# Edit alembic.ini and env.py to import your models

# Generate migration
alembic revision --autogenerate -m "Add subscriber and terminal tables"

# Apply migration
alembic upgrade head
```

## Best Practices

1. **Always validate field mappings** before finalizing schemas
2. **Use constraints** to enforce data integrity at the ORM level
3. **Document relationships** for better code generation
4. **Keep schemas in version control** alongside your code
5. **Regenerate models** when schemas change
6. **Use sample sizes** appropriate for your data volume (1000-5000 typically)
7. **Review match ratios** - investigate anything below 95%
8. **Add descriptions** to fields for better documentation

## Troubleshooting

### Low Match Ratio

If validation shows low match ratio:
1. Check field position in SELECT * results
2. Verify column name spelling
3. Check for data transformations
4. Inspect sample data manually

### Import Errors

Missing pandas:
```bash
pip install pandas  # or uv add pandas
```

Missing SQLModel:
```bash
pip install sqlmodel  # or uv add sqlmodel
```

### Generation Errors

If model generation fails:
1. Validate schema YAML syntax
2. Check field types are valid
3. Verify relationship references exist
4. Review foreign key format (table.field)

## See Also

- [Schema Management CLI](cli.md#schema-commands)
- [Configuration Guide](configuration.md)
- [Example Schemas](../examples/)
