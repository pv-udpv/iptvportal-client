# Changelog

All notable changes to this project will be documented in this file.
All notable changes to the IPTVPortal Client project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Enhanced .gitignore with comprehensive coverage
- CHANGELOG.md to track project changes
- Improved project organization (tests and documentation structure)

### Changed
- Moved root-level test files to tests/ directory
- Moved demo_configuration.py to examples/ directory
- Organized documentation summary files into docs/summaries/

### Fixed
- Project structure organization for better maintainability
- Implemented selective cache clearing by table name in QueryCache
- Added CONTRIBUTING.md with comprehensive development guidelines
- Added CHANGELOG.md for tracking project changes
- Enhanced cache.set() method to store table metadata for selective clearing

### Changed
- Updated .gitignore to exclude root-level test scripts

### Fixed
- Completed TODO implementation for selective table cache clearing

## [0.1.0] - 2024-11-10

### Added
- Initial release
- Schema-aware CLI with auto-generated table schemas
- SQLite sync cache with full/incremental/on-demand strategies
- Dynaconf-based modular configuration
- Pydantic model generator
- Debug mode with comprehensive logging
- Environment variable configuration support
- Sync management CLI commands
- SQL to JSONSQL transpiler
- Async and sync client support
- Query builder with Field and Q objects

### Security
- Session token caching with proper file permissions
- Environment variable-based configuration
- Comprehensive security documentation in SECURITY.md
- Modern Python client for IPTVPortal JSONSQL API
- Schema-aware formatting with auto-generated table schemas
- SQLite sync cache with full/incremental/on-demand sync strategies
- Modular Dynaconf-based configuration system
- Pydantic model generator for type-safe schema models
- Comprehensive CLI with multiple commands:
  - `config`: Configuration management
  - `jsonsql`: API operations (auth, SQL, JSONSQL, utilities)
  - `schema`: Schema management and introspection
  - `cache`: Cache management
  - `sync`: SQLite sync operations
- SQL to JSONSQL transpiler with auto ORDER BY id
- Debug mode with step-by-step logging
- Async and sync client implementations
- Query result caching with LRU eviction
- Authentication management with session caching
- Environment variable configuration support
- Comprehensive test suite with 21 test files
- Documentation:
  - README.md with quick start guide
  - CLI command reference
  - JSONSQL specification
  - Authentication guide
  - Configuration options
  - Schema-driven development guide

### Changed
- N/A (initial release)

### Deprecated
- Legacy `query` commands (use `jsonsql` instead)

### Removed
- N/A (initial release)

### Fixed
- N/A (initial release)

### Security
- Secure password handling with SecretStr type
- Session cache with proper file permissions
- No hardcoded credentials in codebase

---

## Release Types

### Added
For new features.

### Changed
For changes in existing functionality.

### Deprecated
For soon-to-be removed features.

### Removed
For now removed features.

### Fixed
For any bug fixes.

### Security
In case of vulnerabilities.

---

## Version Format

Versions follow Semantic Versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality (backwards-compatible)
- **PATCH**: Bug fixes (backwards-compatible)

[Unreleased]: https://github.com/pv-udpv/iptvportal-client/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pv-udpv/iptvportal-client/releases/tag/v0.1.0
