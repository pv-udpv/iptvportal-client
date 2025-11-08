# IPTVPortal Client Examples

This directory contains practical examples demonstrating various features of the iptvportal-client.

## ⚠️ Safety Notice for Production Systems

**IMPORTANT**: These examples may connect to production systems. To ensure safety:

- ✅ **Authentication examples use READ-ONLY operations** (SELECT queries only)
- ❌ **No UPDATE operations** that modify existing data
- ❌ **No DELETE operations** that remove data
- ❌ **No INSERT operations** in production (use test environments)

## Examples Overview

### Authentication Examples (`authentication_examples.py`)

Demonstrates various authentication patterns and scenarios. **All examples use safe read-only operations.**

### Schema Examples

Schema definitions demonstrating various features of the iptvportal-client schema system.

## Files

### `full-schema-example.yaml`

Comprehensive example demonstrating all schema features:

- **Remote mapping validation** with match ratios and statistics
- **Database constraints** (primary keys, foreign keys, unique, index, nullable)
- **ORM relationships** (one-to-many, many-to-one)
- **Table metadata** (row counts, ID ranges, analyzed timestamps)
- **Sync configuration** (guardrails, chunking, caching strategies)

Tables included:
- `subscriber`: User accounts with relationships to terminals
- `terminal`: User devices with foreign key to subscriber
- `package`: Subscription packages

## Usage

### View Schema Structure

```bash
iptvportal schema import examples/full-schema-example.yaml
iptvportal schema list
iptvportal schema show subscriber
```

### Generate ORM Models

```bash
# SQLModel (default)
iptvportal schema generate-models examples/full-schema-example.yaml

# Pydantic
iptvportal schema generate-models examples/full-schema-example.yaml --format pydantic

# Custom output directory
iptvportal schema generate-models examples/full-schema-example.yaml --output ./models
```

### Validate Against Real Data

If you have access to a real IPTVPortal instance:

```bash
# Validate subscriber field mappings
iptvportal schema validate-mapping subscriber \
  --mappings "0:id,1:username,2:email,3:disabled,4:balance,5:created_at" \
  --sample-size 1000

# Validate terminal field mappings
iptvportal schema validate-mapping terminal \
  --mappings "0:id,1:subscriber_id,2:mac_addr,3:active" \
  --sample-size 500
```

## Generated Models Preview

When you generate models from `full-schema-example.yaml`, you'll get:

### `subscriber.py`
```python
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

class Subscriber(SQLModel, table=True):
    """Users/subscribers in the system"""
    
    __tablename__ = 'subscriber'
    
    id: int = Field(primary_key=True, unique=True, description="Primary key")
    username: str = Field(..., unique=True, index=True, description="Login username")
    email: Optional[str] = Field(default=None, unique=True, index=True, description="Email address")
    disabled: bool = Field(..., description="Account disabled flag")
    balance: float = Field(..., description="Account balance")
    created_at: datetime = Field(..., description="Registration date")
    
    terminals: list["Terminal"] = Relationship(back_populates="subscriber")
```

### `terminal.py`
```python
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

class Terminal(SQLModel, table=True):
    """User devices (set-top boxes, smart TVs)"""
    
    __tablename__ = 'terminal'
    
    id: int = Field(primary_key=True, description="Primary key")
    subscriber_id: int = Field(..., foreign_key="subscriber.id", index=True, description="Foreign key to subscriber")
    mac_addr: str = Field(..., unique=True, index=True, description="MAC address of device")
    active: bool = Field(..., description="Device active flag")
    last_seen: Optional[datetime] = Field(default=None, description="Last activity timestamp")
    
    subscriber: Optional["Subscriber"] = Relationship(back_populates="terminals")
```

## Creating Your Own Schemas

### 1. Start with Introspection

```bash
# Auto-detect table structure
iptvportal schema introspect your_table --save
```

### 2. Validate Field Mappings

```bash
# Data-driven validation
iptvportal schema validate-mapping your_table \
  --mappings "0:field1,1:field2,2:field3" \
  --save
```

### 3. Add Constraints Manually

Edit the generated YAML to add:
```yaml
constraints:
  primary_key: true
  nullable: false
  unique: true
  foreign_key: "other_table.id"
```

### 4. Define Relationships

```yaml
relationships:
  type: "one-to-many"
  target_table: "related_table"
  field_name: "related_items"
  back_populates: "parent"
```

### 5. Generate Models

```bash
iptvportal schema generate-models config/your-schema.yaml
```

## Schema Feature Matrix

| Feature | Required | Example File | Documentation |
|---------|----------|--------------|---------------|
| Basic fields | ✅ | ✅ | [Schema Guide](../docs/schema-driven.md#field-definitions) |
| Field types | ✅ | ✅ | [Schema Guide](../docs/schema-driven.md#field-definitions) |
| Constraints | ⬜ | ✅ | [Schema Guide](../docs/schema-driven.md#constraints) |
| Remote mapping | ⬜ | ✅ | [Schema Guide](../docs/schema-driven.md#validation--remote-mapping) |
| Relationships | ⬜ | ✅ | [Schema Guide](../docs/schema-driven.md#relationships) |
| Metadata | ⬜ | ✅ | [Schema Guide](../docs/schema-driven.md#schema-structure) |
| Sync config | ⬜ | ✅ | [Configuration Guide](../docs/configuration.md) |

## Tips

1. **Start Simple**: Begin with basic field definitions, then add constraints and relationships
2. **Validate Early**: Run validation commands to ensure field mappings are correct
3. **Iterate**: Generate models, test them, refine your schema
4. **Version Control**: Keep schemas in git alongside your code
5. **Document**: Add descriptions to all fields for better generated documentation
## Documentation
Documentation for the project is managed in the `docs/` directory and `mkdocs` build system. Please refer to the relevant sections for detailed information on architecture, CLI usage, schema definitions, and more.
## See Also
- [Concepts and thoughts](../docs/concepts.md)
- [Schema-Driven Development Guide](../docs/schema-driven.md)
- [Model Generation Documentation](../docs/model-generation.md)
- [Architecture Documentation](../docs/architecture/index.md)
- [CLI Documentation](../docs/cli.md)
- [API Documentation](../docs/api/index.md)
- [Configuration Guide](../docs/configuration.md)
 - Main architecture and flows in root README (Mermaid diagrams)
