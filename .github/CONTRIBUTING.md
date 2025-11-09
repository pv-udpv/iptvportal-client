# Contributing to IPTVPortal Client

Thank you for your interest in contributing to IPTVPortal Client! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Submitting Changes](#submitting-changes)
- [Working with GitHub Copilot](#working-with-github-copilot)

## Code of Conduct

Please be respectful and constructive in all interactions. We aim to maintain a welcoming and inclusive environment for all contributors.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/iptvportal-client.git
   cd iptvportal-client
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/pv-udpv/iptvportal-client.git
   ```

## Development Setup

### Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

> **Note for Container Environments (GitHub Actions, Docker, etc.):**
> If `uv` cannot be installed or astral.sh is not accessible, use `pip` instead. This is common in restricted network environments.

### Initial Setup

```bash
# Install development dependencies
make dev

# Or manually with uv
uv sync --all-extras

# Or with pip (for containers/restricted environments)
pip install -e ".[dev,cli,validation]"
```

### Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your IPTVPortal credentials

3. Initialize configuration:
   ```bash
   iptvportal config init
   ```

## Making Changes

### Before You Start

1. **Check existing issues** to see if someone is already working on it
2. **Create or comment on an issue** describing what you plan to work on
3. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

### Development Workflow

1. **Make your changes** in small, logical commits
2. **Write or update tests** to cover your changes
3. **Update documentation** if you're changing functionality
4. **Run tests frequently** to catch issues early:
   ```bash
   make test
   ```

### Key Development Commands

```bash
# Run tests
make test

# Run tests with coverage
make test-cov

# Lint code
make lint

# Format code
make format

# Type check
make type-check

# Run all checks (CI)
make ci

# Run CLI for testing
make cli ARGS="sql -q 'SELECT * FROM media' --dry-run"
```

## Testing

### Writing Tests

- Place tests in the `tests/` directory
- Follow the existing test structure and naming conventions
- Test file names should match `test_*.py`
- Test function names should match `test_*`

### Test Categories

- **CLI tests**: `tests/test_cli.py` - Test command-line interface behavior
- **Transpiler tests**: `tests/test_transpiler.py` - Test SQL to JSONSQL conversion
- **Client tests**: `tests/test_client.py`, `tests/test_async_client.py` - Test API clients
- **Sync tests**: `tests/test_sync_*.py` - Test cache and sync functionality

### Running Specific Tests

```bash
# Run specific test file
uv run pytest tests/test_cli.py

# Run specific test function
uv run pytest tests/test_cli.py::test_sql_command

# Run with verbose output
uv run pytest -v

# Run with debug output
uv run pytest -s
```

## Code Style

### Python Style Guide

We use:
- **Ruff** for linting and formatting
- **MyPy** for type checking
- **Line length**: 100 characters
- **Target Python**: 3.12+

### Style Requirements

- Use type hints for all function parameters and return values
- Write descriptive docstrings for public functions and classes
- Follow existing code patterns and conventions
- Keep functions focused and modular

### Automatic Formatting

```bash
# Format all code
make format

# Check formatting without making changes
uv run ruff format --check .

# Check for linting issues
make lint
```

## Submitting Changes

### Commit Messages

Follow conventional commit format:

```
type(scope): brief description

Longer description if needed

Fixes #123
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(cli): add CSV export option for sql command
fix(transpiler): handle COUNT(DISTINCT col) correctly
docs(cli): update authentication examples
test(sync): add tests for incremental sync
```

### Pull Request Process

1. **Update your branch** with the latest upstream changes:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Push your changes** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create a Pull Request** on GitHub with:
   - Clear title describing the change
   - Detailed description of what changed and why
   - Link to related issues (use "Fixes #123" or "Closes #123")
   - Screenshots for UI changes (if applicable)

4. **Respond to review feedback** promptly

5. **Update documentation** as needed:
   - `README.md` for user-facing changes
   - `docs/cli.md` for CLI changes
   - `docs/jsonsql.md` for transpiler/query changes
   - Inline code documentation for API changes

### Pull Request Checklist

- [ ] Tests pass locally (`make test`)
- [ ] Code follows project style (`make lint`)
- [ ] Code is properly formatted (`make format`)
- [ ] Type checking passes (`make type-check`)
- [ ] Documentation updated if needed
- [ ] Commit messages follow conventional format
- [ ] No debug statements left in code
- [ ] All related files updated in same commit (code + tests + docs)

## Working with GitHub Copilot

If you're using GitHub Copilot or the Copilot Coding Agent, please note:

### Repository Instructions

The repository includes `.github/copilot-instructions.md` with project-specific guidance for AI assistants. Key points:

- **Python 3.12+** is required
- Use **uv** for dependency management
- Follow the **Makefile** commands for common tasks
- **Always update docs and tests** in the same commit as code changes

### Copilot-Friendly Issues

When creating issues that might be assigned to Copilot:

- Be specific about the requirements and acceptance criteria
- Include relevant file paths and code locations
- Provide examples of expected behavior
- Link to relevant documentation
- Specify which tests should be updated

### Documentation Sync Rule

When making changes, update ALL affected documentation:
- `README.md` - User-facing features and examples
- `docs/cli.md` - CLI commands and usage
- `docs/jsonsql.md` - Query syntax and transpiler behavior
- Inline docstrings - API documentation

## Need Help?

- **Questions**: Open a [Discussion](https://github.com/pv-udpv/iptvportal-client/discussions)
- **Bugs**: Open an [Issue](https://github.com/pv-udpv/iptvportal-client/issues/new/choose)
- **Security**: See [SECURITY.md](SECURITY.md)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
