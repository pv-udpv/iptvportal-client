# IPTVPortal Client - Project Structure

This document provides an annotated tree view of the project structure, automatically generated from module docstrings.

> **Note:** This file is auto-generated using `make docs-tree-file` or `python scripts/generate_tree_docs.py`

## Source Code Structure

```
/home/runner/work/iptvportal-client/iptvportal-client/src/iptvportal/
└── iptvportal
    ├── cli
    │   ├── commands
    │   │   ├── __init__.py  # CLI commands.
    │   │   ├── auth.py  # Auth command for CLI.
    │   │   ├── cache.py  # Cache management commands.
    │   │   ├── config.py  # Config command for managing configuration.
    │   │   ├── jsonsql.py  # JSONSQL commands (select, insert, update, delete).
    │   │   ├── schema.py  # Schema management CLI commands.
    │   │   ├── sql.py  # SQL subapp for executing SQL queries via transpiler.
    │   │   ├── sync.py  # Sync cache management commands.
    │   │   └── transpile.py  # Transpile command - SQL to JSONSQL conversion.
    │   ├── core
    │   │   ├── __init__.py  # Core CLI utilities.
    │   │   └── editor.py  # Editor integration for CLI.
    │   ├── __init__.py  # CLI module for IPTVPortal client.
    │   ├── __main__.py  # Main CLI entry point.
    │   ├── formatters.py  # Output formatters for CLI.
    │   ├── introspection.py  # Configuration inspection and generation tool.
    │   └── utils.py  # CLI utilities and helpers.
    ├── query
    │   └── builder.py  # Query builder with Python DSL and operators.
    ├── sync
    │   ├── __init__.py  # SQLite-based sync and caching system for IPTVPortal.
    │   ├── database.py  # SQLite database layer for sync operations.
    │   ├── exceptions.py  # Exceptions for sync system.
    │   └── manager.py  # Sync manager for orchestrating data synchronization operations.
    ├── transpiler
    │   ├── __init__.py  # SQL to JSONSQL transpiler module.
    │   ├── __main__.py  # CLI interface for SQL to JSONSQL transpiler.
    │   ├── exceptions.py  # Transpiler-specific exceptions.
    │   ├── functions.py  # Function mappings for SQL to JSONSQL conversion.
    │   ├── operators.py  # Operator mappings for SQL to JSONSQL conversion.
    │   └── transpiler.py  # Main SQL to JSONSQL transpiler.
    ├── __init__.py  # Modern Python client for IPTVPortal JSONSQL API.
    ├── async_client.py  # Asynchronous IPTVPortal client with async context management.
    ├── auth.py  # Authentication managers for sync and async clients.
    ├── cache.py  # Query result caching for IPTVPortal client.
    ├── client.py  # Synchronous IPTVPortal client with context manager and resource support.
    ├── codegen.py  # ORM model generation from YAML schemas.
    ├── config.py  # Configuration management with Pydantic Settings.
    ├── exceptions.py  # Exception hierarchy for IPTVPortal client.
    ├── introspector.py  # Schema introspection from remote tables with automatic metadata gathering.
    ├── project_conf.py  # Project configuration loader using dynaconf.
    ├── py.typed
    ├── schema.py  # Schema system for table field definitions and SELECT * expansion.
    └── validation.py  # Data-driven validation of remote field mappings using pandas.
```

## Key Components

### CLI (`cli/`)
Command-line interface for interacting with IPTVPortal, including authentication, query execution, and cache management.

### Query (`query/`)
Python DSL for building queries with a fluent API similar to SQLAlchemy.

### Sync (`sync/`)
SQLite-based caching system with full/incremental/on-demand sync strategies for offline capability.

### Transpiler (`transpiler/`)
SQL to JSONSQL conversion engine that translates standard SQL queries to IPTVPortal's JSONSQL format.

### Core Modules
- **client.py / async_client.py**: HTTP client implementations (sync and async)
- **auth.py**: Session management and authentication
- **config.py**: Configuration management with Pydantic Settings
- **schema.py**: Table schema definitions and field mapping
- **exceptions.py**: Exception hierarchy

## Regenerating This File

To update this documentation:

```bash
# Via Makefile
make docs-tree-file

# Or directly
python scripts/generate_tree_docs.py src/iptvportal --max-depth 3 --output docs/PROJECT_STRUCTURE.md
```

See [scripts/README.md](../scripts/README.md) for more options.
