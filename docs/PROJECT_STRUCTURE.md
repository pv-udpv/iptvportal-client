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
    │   ├── debug.py  # Debug logging utilities for CLI.
    │   ├── formatters.py  # Output formatters for CLI.
    │   ├── introspection.py  # Configuration inspection and generation tool.
    │   └── utils.py  # CLI utilities and helpers.
    ├── config
    │   ├── __init__.py  # Configuration management.
    │   ├── project.py  # Project configuration loader using dynaconf.
    │   └── settings.py  # Configuration management with Pydantic Settings.
    ├── core
    │   ├── __init__.py  # Core infrastructure and transport layer.
    │   ├── async_client.py  # Asynchronous IPTVPortal client with async context management.
    │   ├── auth.py  # Authentication managers for sync and async clients.
    │   ├── cache.py  # Query result caching for IPTVPortal client.
    │   └── client.py  # Synchronous IPTVPortal client with context manager and resource support.
    ├── jsonsql
    │   ├── __init__.py  # SQL to JSONSQL transpiler module.
    │   ├── __main__.py  # CLI interface for SQL to JSONSQL transpiler.
    │   ├── builder.py  # Query builder with Python DSL and operators.
    │   ├── exceptions.py  # Transpiler-specific exceptions.
    │   ├── functions.py  # Function mappings for SQL to JSONSQL conversion.
    │   ├── operators.py  # Operator mappings for SQL to JSONSQL conversion.
    │   └── transpiler.py  # Main SQL to JSONSQL transpiler.
    ├── models
    │   ├── __init__.py  # Pydantic models for requests and responses.
    │   ├── requests.py  # Request models for input validation.
    │   └── responses.py  # Response models for query results.
    ├── schema
    │   ├── __init__.py  # Schema system for table field definitions and SELECT * expansion.
    │   ├── codegen.py  # ORM model generation from YAML schemas.
    │   ├── introspector.py  # Schema introspection from remote tables with automatic metadata gathering.
    │   └── table.py  # Schema system for table field definitions and SELECT * expansion.
    ├── service
    │   ├── __init__.py  # Service layer for business logic.
    │   └── query.py  # Query service for orchestrating query execution with business logic.
    ├── sync
    │   ├── __init__.py  # SQLite-based sync and caching system for IPTVPortal.
    │   ├── database.py  # SQLite database layer for sync operations.
    │   ├── exceptions.py  # Exceptions for sync system.
    │   └── manager.py  # Sync manager for orchestrating data synchronization operations.
    ├── __init__.py  # Modern Python client for IPTVPortal JSONSQL API.
    ├── async_client.py  # Async client module (backward compatibility).
    ├── auth.py  # Auth module (backward compatibility).
    ├── cache.py  # Cache module (backward compatibility).
    ├── client.py  # Client module (backward compatibility).
    ├── config.py  # Config module (backward compatibility).
    ├── exceptions.py  # Exception hierarchy for IPTVPortal client.
    ├── introspector.py  # Introspector module (backward compatibility).
    ├── project_conf.py  # Project configuration (backward compatibility).
    ├── py.typed
    └── validation.py  # Data-driven validation of remote field mappings using pandas.