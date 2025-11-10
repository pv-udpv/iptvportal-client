# SQLModel Wrappers for Metadata Models

This document describes the SQLModel wrapper versions of the metadata models in `iptvportal-client`.

## Overview

The `iptvportal.models.sqlmodel_wrappers` module provides SQLModel versions of the Pydantic metadata models used throughout the client. These wrappers maintain full compatibility with the original Pydantic models while providing SQLModel's additional features.

## Available Models

### SQLQueryInput
Validated SQL query input model.

**Fields:**
- `sql` (str): SQL query string to execute
- `use_cache` (bool): Whether to use query result caching (default: True)
- `use_schema_mapping` (bool): Whether to map results using schema definitions (default: True)
- `timeout` (int | None): Optional timeout in seconds (1-300)
- `dry_run` (bool): If True, transpile but don't execute the query (default: False)

**Validation:**
- SQL query must not be empty (whitespace is stripped)
- Timeout must be between 1 and 300 seconds if provided

### JSONSQLQueryInput
Validated JSONSQL query input model.

**Fields:**
- `method` (str): JSONSQL method (select, insert, update, delete)
- `params` (dict): Query parameters as dictionary
- `use_cache` (bool): Whether to use query result caching (default: True)
- `timeout` (int | None): Optional timeout in seconds (1-300)

**Validation:**
- Method must be one of: select, insert, update, delete
- Params must be a non-empty dictionary

### QueryResult
Query execution result model.

**Fields:**
- `data` (list[dict] | dict): Query result data
- `sql` (str | None): Original SQL query (if transpiled)
- `jsonsql` (dict | None): JSONSQL representation of the query
- `method` (str): JSONSQL method used
- `table` (str | None): Table name extracted from query
- `execution_time_ms` (float | None): Execution time in milliseconds
- `row_count` (int): Number of rows in result (auto-calculated)

**Auto-calculation:**
- `row_count` is automatically calculated based on data type (list length or 1 for dict)

### ExecutionMetadata
Metadata about query execution.

**Fields:**
- `cached` (bool): Whether result came from cache (default: False)
- `cache_key` (str | None): Cache key used (if cached)
- `request_id` (int | None): JSON-RPC request ID
- `timestamp` (str | None): Execution timestamp

## Installation

SQLModel is an optional dependency. Install it with:

```bash
pip install "sqlmodel>=0.0.14"
```

Or include the codegen extras:

```bash
pip install "iptvportal-client[codegen]"
```

## Usage

### Basic Import

```python
from iptvportal.models.sqlmodel_wrappers import (
    SQLQueryInput,
    JSONSQLQueryInput,
    QueryResult,
    ExecutionMetadata,
)
```

### Creating Models

```python
# SQL Query Input
query = SQLQueryInput(
    sql="SELECT * FROM subscriber WHERE disabled = false",
    use_cache=True,
    timeout=60
)

# JSONSQL Query Input
jsonsql = JSONSQLQueryInput(
    method="select",
    params={"from": "subscriber", "data": ["id", "username"]}
)

# Query Result
result = QueryResult(
    data=[{"id": 1, "username": "alice"}],
    method="select",
    table="subscriber"
)
# row_count is automatically set to 1

# Execution Metadata
metadata = ExecutionMetadata(
    cached=True,
    cache_key="query:12345"
)
```

### Serialization

All models support standard Pydantic/SQLModel serialization:

```python
# To dictionary
data = query.model_dump()

# To JSON
json_str = query.model_dump_json()

# From dictionary
query = SQLQueryInput(**data)
```

## Differences from Pydantic Models

The SQLModel wrappers are functionally equivalent to the original Pydantic models in `iptvportal.models.requests` and `iptvportal.models.responses`. The main differences are:

1. **Inheritance**: SQLModel wrappers inherit from `sqlmodel.SQLModel` instead of `pydantic.BaseModel`
2. **ORM Capabilities**: SQLModel wrappers can be extended for ORM usage if needed
3. **API Compatibility**: Both versions maintain the same API and validation logic

## When to Use SQLModel Wrappers

Use SQLModel wrappers when:
- You're already using SQLModel in your project
- You want potential ORM capabilities in the future
- You prefer SQLModel's syntax and features

Use regular Pydantic models when:
- You don't need SQLModel features
- You want to minimize dependencies
- You're only doing API validation (default choice)

## Compatibility

The SQLModel wrappers are fully compatible with:
- Python 3.12+
- Pydantic 2.9+
- SQLModel 0.0.14+

All validation rules and behaviors match the original Pydantic models exactly.

## Examples

See [examples/sqlmodel_wrappers_example.py](../examples/sqlmodel_wrappers_example.py) for complete working examples.

## Testing

The SQLModel wrappers have comprehensive test coverage (29 tests) in `tests/test_sqlmodel_wrappers.py`.

Run tests with:

```bash
pytest tests/test_sqlmodel_wrappers.py -v
```

## Graceful Degradation

The `iptvportal.models` module handles SQLModel gracefully:
- If SQLModel is installed, `sqlmodel_wrappers` module is exported
- If SQLModel is not installed, only Pydantic models are exported
- No errors occur if SQLModel is missing
