# GitHub Copilot Workspace Instructions

This file provides instructions to GitHub Copilot for maintaining code quality and documentation consistency in the iptvportal-client project.

## Documentation Consistency Rules

### 1. Always Check Documentation Before Code Changes

When making changes to core functionality, **ALWAYS**:

1. Check if the change affects:
   - `README.md` - Quick start, CLI examples, API usage
   - `docs/cli.md` - Comprehensive CLI documentation
   - `docs/jsonsql.md` - JSONSQL specification reference

2. Update all affected documentation files in the **same commit** as code changes

3. Verify examples still work with the new implementation

### 2. CLI Command Structure Verification

**Current CLI Structure** (as of Nov 2025):
```bash
iptvportal config <subcommand>    # Configuration management
iptvportal auth [--renew]         # Authentication
iptvportal sql [options]          # SQL queries (auto-transpiled)
iptvportal jsonsql <subcommand>   # Native JSONSQL queries
iptvportal transpile [options]    # SQL to JSONSQL transpilation
```

**DEPRECATED** (Do NOT use in docs):
```bash
iptvportal query select    # OLD - replaced by 'iptvportal sql' or 'iptvportal jsonsql select'
iptvportal query insert    # OLD - replaced by 'iptvportal sql' or 'iptvportal jsonsql insert'
iptvportal query update    # OLD - replaced by 'iptvportal sql' or 'iptvportal jsonsql update'
iptvportal query delete    # OLD - replaced by 'iptvportal sql' or 'iptvportal jsonsql delete'
```

When adding CLI features:
- Update the command structure table in `docs/cli.md`
- Update examples in `README.md`
- Add to the CLI cheat sheet in `docs/cli.md`

### 3. Transpiler Feature Coverage

When adding SQL transpilation features:

1. Update the "Supported Features" section in `README.md`
2. Add examples to `docs/cli.md` under appropriate sections
3. Update the coverage percentage (currently ~95%)
4. Add test cases in `tests/test_transpiler.py`

### 4. Error Handling Documentation

When modifying error handling in `client.py` or `async_client.py`:

1. Update the "Enhanced Error Handling" section in `README.md`
2. Document new exception types in docstrings
3. Add examples of error messages to documentation

### 5. API Examples Accuracy

Before suggesting code examples:

1. Verify imports match actual module structure
2. Check that method signatures are current
3. Ensure examples use the latest API patterns
4. Test examples actually work (don't hallucinate)

## File-Specific Rules

### README.md

**Always update when:**
- CLI command structure changes
- New features are added
- API signatures change
- New transpiler features are implemented
- Error handling is modified

**Sections to verify:**
- Features list
- Quick Start examples
- CLI Usage section
- SQL to JSONSQL Transpiler section
- Supported Features list

### docs/cli.md

**Always update when:**
- New CLI commands or flags are added
- Command syntax changes
- Output format options change
- New use cases are implemented

**Sections to verify:**
- Quick Start
- All command examples
- Special Modes (dry-run, show-request)
- Common Use Cases
- Command Cheat Sheet

### docs/jsonsql.md

**Always update when:**
- JSONSQL specification changes
- New operators or functions are supported
- Transpilation behavior changes

## Code Quality Standards

### Type Hints

- All public functions must have complete type hints
- Use Pydantic models for structured data
- Prefer `from __future__ import annotations` for forward references

### Docstrings

- All public classes and functions must have docstrings
- Use Google-style docstring format
- Include examples for complex functionality

### Testing

- New features require tests in `tests/`
- CLI changes require tests in `tests/test_cli.py`
- Transpiler changes require tests in `tests/test_transpiler.py`
- Maintain test coverage above 80%

## Common Patterns

### Adding a New CLI Command

1. Implement command in `src/iptvportal/cli/`
2. Add tests in `tests/test_cli.py`
3. Update `docs/cli.md` with:
   - Command syntax
   - Options documentation
   - Usage examples
   - Add to Command Cheat Sheet
4. Update `README.md` CLI Usage section
5. Verify all examples work

### Adding Transpiler Features

1. Implement in `src/iptvportal/transpiler/transpiler.py`
2. Add operator/function mappings if needed
3. Add tests with SQL input and expected JSONSQL output
4. Update "Supported Features" in `README.md`
5. Add examples to `docs/cli.md`
6. Update coverage percentage

### Modifying Client API

1. Update both `client.py` and `async_client.py` for consistency
2. Update type hints and docstrings
3. Update examples in `README.md` Quick Start
4. Add/update tests
5. Check if error handling needs documentation updates

## Documentation Verification Checklist

Before completing any PR, verify:

- [ ] All CLI examples use current command structure (no `iptvportal query`)
- [ ] Import statements match actual module structure
- [ ] Code examples are syntactically correct
- [ ] Method signatures match implementation
- [ ] New features are documented in README.md
- [ ] CLI changes are reflected in docs/cli.md
- [ ] Test coverage is maintained
- [ ] Docstrings are updated
- [ ] CHANGELOG entries are added (if applicable)

## Anti-Patterns to Avoid

### ❌ Don't:
- Leave outdated examples in documentation
- Add features without updating docs
- Use deprecated CLI command structure
- Reference non-existent modules or functions
- Mix old and new API patterns in examples

### ✅ Do:
- Update docs in the same commit as code
- Verify examples actually work
- Use consistent command structure throughout
- Reference actual module paths
- Follow established patterns

## Review Process

When reviewing changes suggested by Copilot:

1. **Code Changes**: Verify logic and type safety
2. **Documentation**: Check for consistency with code
3. **Examples**: Ensure they're accurate and current
4. **Tests**: Confirm new code is tested
5. **Completeness**: All affected files are updated

## Examples of Good Documentation Sync

### Example 1: Adding a new CLI flag

```markdown
Commit: feat: add --verbose flag to CLI commands

Files changed:
✓ src/iptvportal/cli/main.py         # Implementation
✓ docs/cli.md                        # Document flag
✓ README.md                          # Update examples
✓ tests/test_cli.py                  # Test flag behavior
```

### Example 2: Adding transpiler feature

```markdown
Commit: feat: add COALESCE function support to transpiler

Files changed:
✓ src/iptvportal/transpiler/functions.py  # Implementation
✓ src/iptvportal/transpiler/transpiler.py # Integration
✓ tests/test_transpiler.py                # Test cases
✓ README.md                               # Update Supported Features
✓ docs/cli.md                             # Add examples
```

## Conclusion

These instructions ensure that iptvportal-client maintains high quality, accurate documentation, and consistency across all changes. When in doubt, update the docs!
