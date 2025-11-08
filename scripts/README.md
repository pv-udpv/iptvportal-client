# Project Scripts

This directory contains utility scripts for the IPTVPortal client project.

## generate_tree_docs.py

Generate an annotated tree structure of the project with file descriptions extracted from docstrings.

### Usage

```bash
# Generate tree for src/iptvportal with max depth of 3
python scripts/generate_tree_docs.py src/iptvportal --max-depth 3

# Generate full tree (no depth limit)
python scripts/generate_tree_docs.py src/iptvportal

# Save to file
python scripts/generate_tree_docs.py src/iptvportal --max-depth 3 --output PROJECT_STRUCTURE.md

# Exclude additional patterns
python scripts/generate_tree_docs.py . --exclude examples --exclude tests --exclude docs

# Disable annotations (just show tree structure)
python scripts/generate_tree_docs.py src/iptvportal --no-annotations
```

### Via Makefile

```bash
# Generate tree structure (max depth 3)
make docs-tree

# Generate full tree structure
make docs-tree-full

# Generate and save to PROJECT_STRUCTURE.md
make docs-tree-file
```

### Features

- Automatically extracts module docstrings from Python files
- Falls back to first comment line if no docstring is found
- Excludes common build artifacts and cache directories
- Supports custom depth limits
- Can save output to file or print to stdout
- Maintains proper tree structure with UTF-8 box drawing characters

### Example Output

```
iptvportal-client/
└── src/iptvportal/
    ├── config.py          # Configuration management with Pydantic Settings.
    ├── exceptions.py      # Exception hierarchy for IPTVPortal client.
    ├── auth.py            # Authentication managers for sync and async clients.
    ├── client.py          # Synchronous IPTVPortal client with context manager.
    ├── async_client.py    # Asynchronous IPTVPortal client with async context management.
    ├── sync/
    │   ├── __init__.py    # SQLite-based sync and caching system for IPTVPortal.
    │   ├── database.py    # SQLite database layer for sync operations.
    │   ├── manager.py     # Sync manager for orchestrating data synchronization operations.
    │   └── exceptions.py  # Exceptions for sync system.
    └── ...
```

### Implementation Details

The script:
1. Uses Python's `ast` module to parse files and extract docstrings
2. Falls back to parsing comment lines if docstring extraction fails
3. Filters out common development artifacts (caches, build dirs, etc.)
4. Generates tree structure with proper UTF-8 box drawing characters
5. Only annotates Python (.py) files with their descriptions

### Default Exclusions

- `__pycache__`
- `.git`, `.venv`, `venv`
- `.pytest_cache`, `.mypy_cache`, `.ruff_cache`
- `dist`, `build`
- `.env`, `uv.lock`
- Files/directories containing `.egg-info`
