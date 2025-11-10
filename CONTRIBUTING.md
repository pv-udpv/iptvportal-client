# Contributing to IPTVPortal Client

Thank you for your interest in contributing to IPTVPortal Client! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)

## Code of Conduct

Please be respectful and professional in all interactions. We aim to maintain a welcoming and inclusive environment for all contributors.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/iptvportal-client.git`
3. Add upstream remote: `git remote add upstream https://github.com/pv-udpv/iptvportal-client.git`

## Development Setup

### Prerequisites

- Python 3.12 or higher
- `uv` package manager (recommended) or `pip`

### Using uv (Recommended)

```bash
# Create virtual environment and install dependencies
make dev

# Or manually:
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync --dev
```

### Using pip

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

### Verify Installation

```bash
# Run tests
make test

# Run linter
make lint

# Run type checker
make type-check
```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Your Changes

- Write clean, readable code
- Follow the coding standards (see below)
- Add tests for new functionality
- Update documentation as needed

### 3. Run Quality Checks

```bash
# Format code
make format

# Fix linting issues
make lint-fix

# Run type checker
make type-check

# Run tests
make test

# Or run all checks at once
make check-fix
```

### 4. Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with a descriptive message
git commit -m "feat: add new feature description"
# or
git commit -m "fix: resolve issue with X"
```

Follow [Conventional Commits](https://www.conventionalcommits.org/) format:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `test:` for test additions/changes
- `refactor:` for code refactoring
- `chore:` for maintenance tasks

### 5. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create a pull request on GitHub
```

## Coding Standards

### Python Style Guide

- Follow PEP 8
- Use type hints for all function signatures
- Maximum line length: 100 characters
- Use descriptive variable and function names

### Code Quality Tools

We use the following tools to maintain code quality:

- **Ruff**: Linting and formatting
- **mypy**: Static type checking
- **pytest**: Testing framework

### Type Hints

All public functions and methods must have complete type hints:

```python
from typing import Any

def process_data(input_data: dict[str, Any], limit: int = 10) -> list[str]:
    """Process data and return results.
    
    Args:
        input_data: Dictionary containing input data
        limit: Maximum number of results to return
        
    Returns:
        List of processed strings
    """
    # Implementation
    pass
```

### Docstrings

Use Google-style docstrings for all public modules, classes, and functions:

```python
def example_function(param1: str, param2: int) -> bool:
    """Brief description of function.
    
    Longer description if needed. Explain what the function does,
    any important details, edge cases, etc.
    
    Args:
        param1: Description of first parameter
        param2: Description of second parameter
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param2 is negative
        
    Examples:
        >>> example_function("test", 5)
        True
    """
    if param2 < 0:
        raise ValueError("param2 must be non-negative")
    return len(param1) > param2
```

### Error Handling

- Use specific exception types from `iptvportal.exceptions`
- Provide informative error messages
- Include context in error details where appropriate

```python
from iptvportal.exceptions import ValidationError

def validate_input(data: dict[str, Any]) -> None:
    """Validate input data."""
    if "required_field" not in data:
        raise ValidationError(
            "Missing required field: 'required_field'",
            details={"provided_keys": list(data.keys())}
        )
```

## Testing

### Writing Tests

- Place tests in the `tests/` directory
- Use descriptive test names: `test_function_name_scenario`
- Follow the Arrange-Act-Assert pattern
- Use pytest fixtures for common setup

```python
def test_query_builder_creates_valid_select():
    """Test that QueryBuilder creates a valid SELECT query."""
    # Arrange
    builder = QueryBuilder()
    
    # Act
    query = builder.select("id", "name").from_table("users").limit(10).build()
    
    # Assert
    assert query["from"] == "users"
    assert query["data"] == ["id", "name"]
    assert query["limit"] == 10
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
make test-specific TEST=test_client.py

# Run tests in verbose mode
make test-verbose
```

### Test Coverage

- Aim for high test coverage (>80%)
- Focus on testing critical paths and edge cases
- Use pytest-cov to generate coverage reports

## Documentation

### Code Documentation

- All public APIs must have docstrings
- Include examples in docstrings where helpful
- Document parameters, return values, and exceptions

### User Documentation

- Update `README.md` for user-facing changes
- Update relevant files in `docs/` directory
- Include examples and use cases
- Keep CLI documentation in sync with code

### Documentation Files

- `README.md`: Quick start and overview
- `docs/cli.md`: CLI command reference
- `docs/jsonsql.md`: JSONSQL specification
- `docs/authentication.md`: Authentication guide
- `docs/configuration.md`: Configuration options

## Submitting Changes

### Pull Request Guidelines

1. **Title**: Use a clear, descriptive title
2. **Description**: Explain what changes you made and why
3. **Tests**: Include tests for new functionality
4. **Documentation**: Update relevant documentation
5. **Checklist**: Complete the PR template checklist

### PR Checklist

- [ ] Code follows project style guidelines
- [ ] All tests pass (`make test`)
- [ ] New code has tests
- [ ] Documentation is updated
- [ ] Commit messages follow Conventional Commits format
- [ ] No linting errors (`make lint`)
- [ ] Type checking passes (`make type-check`)
- [ ] Code is formatted (`make format`)

### Review Process

1. Automated checks must pass (CI/CD)
2. At least one maintainer review required
3. Address review feedback
4. Squash commits if requested
5. Maintainer will merge when approved

## Common Tasks

### Adding a New CLI Command

1. Create command file in `src/iptvportal/cli/commands/`
2. Implement command using Typer
3. Register in `src/iptvportal/cli/__main__.py`
4. Add tests in `tests/test_cli.py`
5. Update `docs/cli.md`

### Adding a New Feature

1. Create feature branch
2. Implement feature with tests
3. Update documentation
4. Run all quality checks
5. Submit pull request

### Fixing a Bug

1. Create bug fix branch
2. Add test that reproduces the bug
3. Fix the bug
4. Verify test passes
5. Submit pull request

## Getting Help

- **Issues**: Check existing issues or create a new one
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Refer to docs/ directory

## License

By contributing to IPTVPortal Client, you agree that your contributions will be licensed under the MIT License.

## Questions?

If you have any questions about contributing, please open an issue or start a discussion on GitHub.

Thank you for contributing! 🎉
