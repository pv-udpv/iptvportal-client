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

# Save to file (with markdown formatting by default)
python scripts/generate_tree_docs.py src/iptvportal --max-depth 3 --output PROJECT_STRUCTURE.md

# Save to file without markdown formatting
python scripts/generate_tree_docs.py src/iptvportal --output tree.txt --no-markdown

# Custom markdown title
python scripts/generate_tree_docs.py src/iptvportal --output tree.md --title "My Project Structure"

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

- **Docstring Extraction**: Automatically extracts module docstrings from Python files
- **Fallback Comments**: Falls back to first comment line if no docstring is found
- **Gitignore Integration**: Reads and respects .gitignore patterns for exclusions
- **Markdown Formatting**: When saving to file, automatically adds:
  - Header (# PROJECT STRUCTURE)
  - Timestamp with auto-generation note
  - Code block formatting (```sh)
- **Customization Options**:
  - `--no-markdown`: Disable markdown formatting for plain output
  - `--title`: Custom title for markdown header
  - `--max-depth`: Limit tree depth
  - `--exclude`: Additional patterns to exclude
  - `--no-annotations`: Disable docstring annotations
- Maintains proper tree structure with UTF-8 box drawing characters

### Example Output

**Stdout (plain format):**
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

**File output (with markdown formatting):**
```markdown
# PROJECT STRUCTURE
> Auto-generated on 2025-11-09 05:27:17 UTC

\`\`\`sh
/home/user/project/src/iptvportal/
└── iptvportal/
    ├── config.py          # Configuration management with Pydantic Settings.
    ├── exceptions.py      # Exception hierarchy for IPTVPortal client.
    └── ...
\`\`\`
```

### Implementation Details

The script:
1. Uses Python's `ast` module to parse files and extract docstrings
2. Falls back to parsing comment lines if docstring extraction fails
3. **Reads .gitignore file** from repository root and respects its patterns
4. Supports additional exclusion patterns via `--exclude` flag
5. Generates tree structure with proper UTF-8 box drawing characters
6. Only annotates Python (.py) files with their descriptions
7. **Automatically formats with markdown** when saving to file (unless `--no-markdown` is used)

### Exclusion System

The script uses a two-tier exclusion system:
1. **Gitignore patterns**: Automatically parsed from `.gitignore` in the repository root
2. **Additional excludes**: Specified via `--exclude` flag (can be used multiple times)

Always excluded:
- `.git` directory (hardcoded for safety)

### Default Exclusions (from .gitignore)

The script respects all patterns in your `.gitignore` file, which typically includes:
- `__pycache__/` and `*.pyc`
- `.git`, `.venv`, `venv`
- `.pytest_cache`, `.mypy_cache`, `.ruff_cache`
- `dist/`, `build/`
- `*.egg-info/`
- IDE directories (`.vscode/`, `.idea/`)
- And any other patterns you've defined
