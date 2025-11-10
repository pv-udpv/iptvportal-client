# Changelog

All notable changes to this project will be documented in this file.

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

[Unreleased]: https://github.com/pv-udpv/iptvportal-client/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pv-udpv/iptvportal-client/releases/tag/v0.1.0
