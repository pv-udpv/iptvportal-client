# IPTVPortal Git Workflow Guide

This document outlines the automated Git workflow for the IPTVPortal project, including conventional commits, PR creation, and quality assurance processes.

## Table of Contents

- [Quick Start](#quick-start)
- [Workflow Scripts](#workflow-scripts)
- [Git Hooks](#git-hooks)
- [Conventional Commits](#conventional-commits)
- [Branch Management](#branch-management)
- [Pull Requests](#pull-requests)
- [Quality Assurance](#quality-assurance)
- [Troubleshooting](#troubleshooting)

## Quick Start

### 1. Setup (One-time)

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Setup git hooks
./scripts/setup-hooks.sh
```

### 2. Daily Workflow

```bash
# Create branch from issue (optional)
./scripts/issue-branch.sh 123

# Make changes, then use the full workflow
./scripts/git-workflow.sh
```

This will:
- Run tests and linting
- Format code
- Create conventional commit
- Push changes
- Offer to create PR

## Workflow Scripts

### `git-workflow.sh` - Full Workflow Automation

**Purpose**: Complete commit → test → push → PR workflow

**Usage**:
```bash
./scripts/git-workflow.sh
```

**What it does**:
1. Checks for uncommitted changes
2. Runs tests (`uv run pytest`)
3. Formats code (`uv run ruff format`)
4. Interactive commit message builder
5. Pushes to current branch
6. Offers PR creation with issue linking

### `create-pr.sh` - PR Creation

**Purpose**: Create PRs with automatic issue linking and labeling

**Usage**:
```bash
# Auto-detect issue from branch name (issue-123)
./scripts/create-pr.sh

# Link to specific issue
./scripts/create-pr.sh --issue 123

# Create draft PR
./scripts/create-pr.sh --draft --issue 456

# Add custom labels
./scripts/create-pr.sh --issue 123 --label enhancement --label testing
```

### `commit-helper.sh` - Interactive Commit Builder

**Purpose**: Create conventional commit messages interactively

**Usage**:
```bash
# Interactive mode
./scripts/commit-helper.sh

# Pre-filled options
./scripts/commit-helper.sh --type feat --scope sync --message "Add incremental sync"
```

### `issue-branch.sh` - Issue Branch Creation

**Purpose**: Create properly named branches from GitHub issues

**Usage**:
```bash
# Auto-generate branch name from issue
./scripts/issue-branch.sh 123

# Custom branch suffix
./scripts/issue-branch.sh 456 add-validation
```

### `validate-commit.sh` - Commit Validation

**Purpose**: Validate commit messages against conventional format

**Usage**:
```bash
# Validate last commit
./scripts/validate-commit.sh

# Validate all commits in branch
./scripts/validate-commit.sh --all

# Validate commits since main
./scripts/validate-commit.sh --range main

# Auto-fix simple issues
./scripts/validate-commit.sh --fix --all
```

### `setup-hooks.sh` - Git Hooks Setup

**Purpose**: Configure git to use custom hooks

**Usage**:
```bash
./scripts/setup-hooks.sh
```

## Git Hooks

Git hooks automatically run quality checks at various points in the Git workflow.

### `pre-commit` - Before Commits

Runs before each commit to ensure code quality:

- **Linting**: `uv run ruff check .`
- **Formatting**: `uv run ruff format --check .`
- **Testing**: `uv run pytest` (quick subset)
- **Debug Check**: Detects `print()`, `debugger`, `import pdb`
- **Large Files**: Prevents committing files >10MB

**Skip hooks**: `git commit --no-verify`

### `commit-msg` - Commit Message Validation

Validates commit message format:

- **Format Check**: `type(scope): description`
- **Length Check**: First line ≤72 characters
- **Issue Reference**: Suggests linking issues in issue branches
- **Content Check**: Prevents WIP commits on main

### `post-commit` - After Commits

Provides helpful information and suggestions:

- **Commit Summary**: Shows hash, message, author, date
- **Branch Status**: Ahead/behind remote status
- **PR Suggestions**: Offers PR creation for feature branches
- **Coverage Report**: Links to test coverage if available
- **Documentation**: Reminds about updating docs

### `pre-push` - Before Pushing

Comprehensive checks before pushing to remote:

- **Full Test Suite**: `uv run pytest`
- **Coverage Check**: Ensures ≥80% coverage
- **Main Branch Protection**: Confirms pushes to main
- **Commit Validation**: Checks all commits being pushed
- **Large Files**: Prevents pushing files >50MB

**Skip hooks**: `git push --no-verify`

## Conventional Commits

All commits must follow the conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

### Types

- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `test` - Testing
- `refactor` - Code refactoring
- `chore` - Maintenance
- `perf` - Performance improvement
- `style` - Code style changes
- `ci` - CI/CD changes
- `revert` - Revert changes
- `build` - Build system changes

### Scopes

- `sync` - Sync system
- `cli` - CLI commands
- `transpiler` - Transpiler
- `schema` - Schema handling
- `cache` - Caching system
- `config` - Configuration
- `docs` - Documentation
- `test` - Testing
- `ci` - CI/CD
- `deps` - Dependencies

### Examples

```
feat(sync): Add incremental sync strategy
fix(cli): Handle invalid command arguments
docs: Update installation guide
test(schema): Add validation tests
refactor(cache): Simplify cache invalidation logic

BREAKING CHANGE: Remove deprecated API endpoints
```

## Branch Management

### Branch Naming

- **Main branch**: `main`
- **Feature branches**: `issue-123-add-validation`
- **Bug fixes**: `issue-456-fix-database-connection`
- **Documentation**: `docs/update-readme`

### Creating Branches

```bash
# From issue
./scripts/issue-branch.sh 123

# Manual creation
git checkout -b feature/add-new-feature
```

### Branch Workflow

1. Create branch from issue or manually
2. Make changes with proper commits
3. Use `./scripts/git-workflow.sh` for commits
4. Push and create PR
5. Delete branch after merge

## Pull Requests

### PR Creation

PRs are created using the automated scripts:

```bash
# Full workflow (recommended)
./scripts/git-workflow.sh

# Manual PR creation
./scripts/create-pr.sh --issue 123
```

### PR Template

PRs use the standard template (`.github/pull_request_template.md`) with:

- **Description**: What changes were made
- **Type of Change**: Feature, bug fix, etc.
- **Testing**: Checklist for validation
- **Related Issues**: Auto-linked via branch names
- **Checklist**: Quality assurance items

### PR Labels

Labels are automatically applied based on:

- **Branch name**: `fix-*` → `bug`, `feat-*` → `enhancement`
- **Commit types**: `test:*` → `testing`, `docs:*` → `documentation`
- **Manual**: Use `--label` flag in `create-pr.sh`

### Issue Linking

PRs automatically link to issues when:

- Branch name contains issue number: `issue-123-feature`
- `--issue` flag is used: `--issue 123`
- Commit message contains: `Closes #123`, `Fixes #123`

## Quality Assurance

### Automated Checks

- **Pre-commit**: Linting, formatting, quick tests
- **Pre-push**: Full tests, coverage, validation
- **Commit-msg**: Message format validation
- **Post-commit**: Helpful suggestions

### Manual Checks

```bash
# Run full test suite
uv run pytest

# Check coverage
uv run pytest --cov=src/iptvportal --cov-report=html

# Validate commits
./scripts/validate-commit.sh --all

# Lint and format
uv run ruff check .
uv run ruff format .
```

### Coverage Requirements

- **Minimum**: 80% overall coverage
- **New code**: All new code must be tested
- **Critical paths**: 90%+ coverage for core functionality

## Troubleshooting

### Common Issues

#### "uv is not available"

**Problem**: Git hooks fail because `uv` is not in PATH

**Solution**:
```bash
# Check uv installation
which uv

# Add to PATH or use full path in hooks
export PATH="$HOME/.cargo/bin:$PATH"
```

#### "GitHub CLI not authenticated"

**Problem**: PR creation fails

**Solution**:
```bash
gh auth login
```

#### "Invalid commit message format"

**Problem**: Commit rejected by hook

**Solution**:
```bash
# Use the helper
./scripts/commit-helper.sh

# Or fix manually
git commit --amend
```

#### "Tests failing in pre-commit"

**Problem**: Code doesn't pass tests

**Solution**:
```bash
# Fix issues, then commit
uv run pytest

# Skip hooks if needed
git commit --no-verify
```

### Skipping Hooks

For urgent commits, you can skip hooks:

```bash
# Skip all pre-commit checks
git commit --no-verify

# Skip pre-push checks
git push --no-verify
```

**Warning**: Only skip hooks when absolutely necessary. Address the underlying issues as soon as possible.

### Resetting Hooks

If hooks configuration gets corrupted:

```bash
# Reset hooks path
git config --unset core.hooksPath

# Re-run setup
./scripts/setup-hooks.sh
```

### Manual Hook Testing

Test hooks without committing:

```bash
# Test pre-commit
.githooks/pre-commit

# Test commit-msg
echo "feat: test commit" | .githooks/commit-msg /tmp/test-commit-msg

# Test pre-push (requires remote setup)
.githooks/pre-push origin main
```

## Contributing

When contributing to this workflow:

1. Update documentation for new scripts
2. Test hooks on different environments
3. Ensure scripts work with `uv` package manager
4. Update `.clinerules` with new workflow information
5. Add examples to this guide

## Related Documentation

- [Project README](../README.md)
- [CLI Documentation](cli.md)
- [Contributing Guidelines](../CONTRIBUTING.md)
- [Code of Conduct](../CODE_OF_CONDUCT.md)
