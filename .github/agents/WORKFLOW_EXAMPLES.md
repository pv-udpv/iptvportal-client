# Agent Workflow Examples

This document provides detailed examples of how GitHub Copilot agents work together to accomplish different types of tasks in the IPTVPortal client project.

## Table of Contents

- [Simple Task: Add a CLI Option](#simple-task-add-a-cli-option)
- [Medium Task: Add a New Query Operator](#medium-task-add-a-new-query-operator)
- [Complex Task: Add a Terminal Resource Manager](#complex-task-add-a-terminal-resource-manager)
- [Maintenance Task: Fix a Bug](#maintenance-task-fix-a-bug)
- [Documentation Task: Update API Reference](#documentation-task-update-api-reference)

---

## Simple Task: Add a CLI Option

**Task**: Add `--output-file` option to the `sql` command to save query results to a file.

### Agent Assignment
- **Single Agent**: CLI Agent

### Workflow

1. **CLI Agent** receives the task:
   - Analyzes existing `sql` command implementation
   - Adds `--output-file` option using Typer
   - Implements file writing logic
   - Updates help text

2. **Implementation**:
```python
@app.command("sql")
def sql_command(
    query: str = typer.Option(..., "--query", "-q"),
    output_file: Optional[str] = typer.Option(
        None,
        "--output-file",
        "-o",
        help="Save results to file instead of displaying"
    ),
    # ... other options
):
    """Execute SQL query."""
    results = execute_query(query)
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        console.print(f"[green]Results saved to {output_file}[/green]")
    else:
        display_results(results)
```

3. **Testing** (CLI Agent):
   - Add test for new option
   - Verify file creation and content
   - Test error handling (invalid path, permissions)

4. **Documentation** (CLI Agent):
   - Update `docs/cli.md` with new option
   - Add example to README.md
   - Update command help text

**Duration**: ~30 minutes
**Files Modified**: 3-4 files
**Agents Used**: 1

---

## Medium Task: Add a New Query Operator

**Task**: Add support for `BETWEEN` operator in the query builder.

### Agent Assignment
- **Primary**: Query Builder Agent
- **Supporting**: Testing Agent, Documentation Agent

### Workflow

1. **Orchestrator** analyzes task:
   - Identifies as medium complexity
   - Assigns to Query Builder Agent with support

2. **Query Builder Agent** implements operator:

```python
# In src/iptvportal/query/operators.py

class BetweenOperator(Operator):
    """BETWEEN operator for range queries.
    
    Examples:
        >>> Field("age").between(18, 65)
        >>> Field("price").between(10.0, 100.0)
    """
    
    operator_key = "between"
    
    def __init__(self, field: str, min_value: Any, max_value: Any):
        self.field = field
        self.min_value = min_value
        self.max_value = max_value
        self._validate_range()
    
    def _validate_range(self) -> None:
        if self.min_value > self.max_value:
            raise ValueError("min_value must be <= max_value")
    
    def to_jsonsql(self) -> dict:
        return {
            self.field: {
                "between": [self.min_value, self.max_value]
            }
        }

# Add to Field class
class Field:
    # ... existing methods
    
    def between(self, min_value: Any, max_value: Any) -> "Field":
        """Create BETWEEN operator for range queries."""
        return BetweenOperator(self.name, min_value, max_value)
```

3. **Testing Agent** generates tests:

```python
def test_between_operator():
    """Test BETWEEN operator."""
    result = Field("age").between(18, 65)
    assert result.to_jsonsql() == {
        "age": {"between": [18, 65]}
    }

def test_between_operator_validation():
    """Test BETWEEN validation."""
    with pytest.raises(ValueError):
        Field("age").between(65, 18)  # Invalid range

def test_between_with_other_operators():
    """Test BETWEEN composed with other operators."""
    query = Field("age").between(18, 65) & Field("status").eq("active")
    assert query.to_jsonsql() == {
        "and": [
            {"age": {"between": [18, 65]}},
            {"status": {"eq": "active"}}
        ]
    }
```

4. **Documentation Agent** updates docs:
   - Add BETWEEN operator to query builder docs
   - Include examples in README.md
   - Update CHANGELOG.md

**Duration**: ~2 hours
**Files Modified**: 5-7 files
**Agents Used**: 3

---

## Complex Task: Add a Terminal Resource Manager

**Task**: Implement complete Terminal resource manager with models, CRUD operations, CLI commands, tests, and documentation.

### Agent Assignment
- **Coordinator**: Orchestrator Agent
- **Workers**: 
  - API Integration Agent
  - Resource Manager Agent
  - CLI Agent
  - Testing Agent
  - Documentation Agent

### Workflow

#### Phase 1: Planning (Orchestrator)

The Orchestrator creates a task breakdown:

```markdown
## Terminal Resource Manager Implementation

### Dependencies
1. Models → Resource Manager → CLI
2. All implementation → Testing
3. All implementation → Documentation

### Task Breakdown

**Task 1: Create Terminal Models** (API Integration Agent)
- Create `Terminal`, `TerminalCreate`, `TerminalUpdate` models
- Add validation rules
- Create request/response models

**Task 2: Implement TerminalResource** (Resource Manager Agent)
- Implement `TerminalResource` class
- Add all CRUD operations
- Create `AsyncTerminalResource`
- Integrate with client

**Task 3: Add CLI Commands** (CLI Agent)
- Create `terminal` command group
- Implement list, get, create, update, delete subcommands
- Add rich formatting

**Task 4: Generate Tests** (Testing Agent)
- Unit tests for models
- Unit tests for resource manager
- CLI command tests
- Integration tests

**Task 5: Update Documentation** (Documentation Agent)
- API reference for TerminalResource
- CLI command documentation
- Usage examples
- CHANGELOG entry
```

#### Phase 2: Implementation

**Step 1: API Integration Agent**

Creates models in `src/iptvportal/models/terminal.py`:

```python
from pydantic import BaseModel, Field

class TerminalBase(BaseModel):
    """Base terminal model."""
    mac_addr: str = Field(..., description="MAC address")
    subscriber_id: int = Field(..., description="Subscriber ID")
    model: Optional[str] = Field(None, description="Terminal model")
    status: str = Field(default="active", description="Terminal status")

class TerminalCreate(TerminalBase):
    """Model for creating terminals."""
    pass

class Terminal(TerminalBase):
    """Complete terminal model."""
    id: int = Field(..., description="Terminal ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")
```

**Step 2: Resource Manager Agent**

Creates `src/iptvportal/service/terminal.py`:

```python
class TerminalResource:
    """Resource manager for Terminal entities."""
    
    def __init__(self, client: IPTVPortalClient):
        self.client = client
        self.table_name = "terminal"
    
    def list(self, limit=None, offset=None, where=None):
        """List terminals with filtering."""
        # Implementation...
    
    def get(self, terminal_id: int):
        """Get terminal by ID."""
        # Implementation...
    
    def create(self, terminal: TerminalCreate):
        """Create new terminal."""
        # Implementation...
    
    def update(self, terminal_id: int, updates):
        """Update terminal."""
        # Implementation...
    
    def delete(self, terminal_id: int):
        """Delete terminal."""
        # Implementation...
```

Updates `src/iptvportal/client.py`:

```python
class IPTVPortalClient:
    def __init__(self, ...):
        # ... existing code
        self.terminal = TerminalResource(self)
```

**Step 3: CLI Agent**

Creates `src/iptvportal/cli/commands/terminal.py`:

```python
app = typer.Typer(help="Manage terminal devices")

@app.command("list")
def list_terminals(
    limit: int = LimitOption,
    format: str = FormatOption,
):
    """List terminals."""
    client = get_client()
    terminals = client.terminal.list(limit=limit)
    
    if format == "table":
        _display_table(terminals)
    else:
        format_output(terminals, format)

@app.command("get")
def get_terminal(terminal_id: int):
    """Get terminal by ID."""
    # Implementation...

# ... other commands
```

Registers in `src/iptvportal/cli/__main__.py`:

```python
from iptvportal.cli.commands import terminal

app.add_typer(terminal.app, name="terminal")
```

**Step 4: Testing Agent**

Creates comprehensive tests in `tests/test_terminal.py`:

```python
class TestTerminalResource:
    """Tests for TerminalResource."""
    
    def test_list_terminals(self, mock_client):
        """Test listing terminals."""
        terminals = TerminalResource(mock_client).list(limit=10)
        assert len(terminals) <= 10
    
    def test_get_terminal(self, mock_client):
        """Test getting terminal by ID."""
        terminal = TerminalResource(mock_client).get(123)
        assert terminal.id == 123
    
    # ... more tests

class TestTerminalCLI:
    """Tests for terminal CLI commands."""
    
    def test_terminal_list_command(self, cli_runner):
        """Test terminal list command."""
        result = cli_runner.invoke(app, ["terminal", "list"])
        assert result.exit_code == 0
    
    # ... more tests
```

**Step 5: Documentation Agent**

Updates documentation:

1. `docs/api-reference.md` - Add TerminalResource section
2. `docs/cli.md` - Add terminal commands
3. `README.md` - Add terminal example
4. `CHANGELOG.md` - Add entry:

```markdown
### Added
- Terminal resource manager with full CRUD operations
- CLI commands for terminal management (`iptvportal terminal`)
- Support for terminal filtering and pagination
```

#### Phase 3: Validation (Orchestrator)

The Orchestrator runs quality checks:

```bash
# Linting
make lint          # ✅ Passed

# Type checking
make type-check    # ✅ Passed

# Tests
make test          # ✅ All 47 tests passed

# Coverage
make test-cov      # ✅ 85% coverage (target: 80%)
```

Creates summary PR description and requests review.

**Duration**: ~4-6 hours
**Files Modified**: 15-20 files
**Agents Used**: 6

---

## Maintenance Task: Fix a Bug

**Task**: Fix bug where `COUNT(DISTINCT col)` transpiles incorrectly.

### Agent Assignment
- **Primary**: Query Builder Agent (if in query builder) OR Transpiler specialist
- **Supporting**: Testing Agent, Documentation Agent

### Workflow

1. **Orchestrator** identifies the issue:
   - Reviews bug report
   - Identifies affected component (transpiler)
   - Assigns to appropriate agent

2. **Query Builder Agent** analyzes and fixes:

```python
# Before (incorrect)
def transpile_count_distinct(expr):
    return {"function": "count", "args": ["DISTINCT", field]}

# After (correct)
def transpile_count_distinct(expr):
    return {
        "function": "count",
        "args": {
            "function": "distinct",
            "args": field
        }
    }
```

3. **Testing Agent** adds regression test:

```python
def test_count_distinct_transpilation():
    """Test COUNT(DISTINCT col) transpiles correctly."""
    sql = "SELECT COUNT(DISTINCT username) FROM subscriber"
    result = transpiler.transpile(sql)
    
    expected = {
        "from": "subscriber",
        "data": [{
            "function": "count",
            "args": {
                "function": "distinct",
                "args": "username"
            }
        }]
    }
    assert result == expected
```

4. **Documentation Agent** updates:
   - Fix examples in `docs/jsonsql.md`
   - Update CHANGELOG.md with fix note
   - Verify all examples are correct

**Duration**: ~1 hour
**Files Modified**: 3-5 files
**Agents Used**: 2-3

---

## Documentation Task: Update API Reference

**Task**: Generate complete API reference documentation for all resource managers.

### Agent Assignment
- **Primary**: Documentation Agent
- **Tool**: `sphinx-generator` MCP tool

### Workflow

1. **Documentation Agent** analyzes scope:
   - Identifies all resource manager classes
   - Reviews existing docstrings
   - Plans documentation structure

2. **Generate API reference**:

Using `sphinx-generator` MCP tool:

```python
# Generate docs for SubscriberResource
subscriber_docs = sphinx_generator.generate_api_docs(
    module="iptvportal.service.subscriber",
    format="markdown"
)

# Generate docs for all resource managers
resource_managers = [
    "subscriber", "terminal", "media", "package"
]

for manager in resource_managers:
    docs = sphinx_generator.generate_api_docs(
        module=f"iptvportal.service.{manager}",
        include_examples=True
    )
    # Write to docs/api/resource-managers.md
```

3. **Organize documentation**:

```markdown
# Resource Managers API Reference

## SubscriberResource

### Methods

#### list(limit, offset, where, order_by)
List subscribers with optional filtering.

**Parameters:**
- `limit` (int, optional): Maximum records to return
- `offset` (int, optional): Number of records to skip
- `where` (dict, optional): Filter conditions
- `order_by` (str, optional): Field to sort by

**Returns:** `list[Subscriber]`

**Example:**
```python
subscribers = client.subscriber.list(limit=10)
```

#### get(subscriber_id)
Get subscriber by ID.
...
```

4. **Validate examples**:

Using `example-validator` MCP tool:

```python
validation = example_validator.validate_directory(
    path="docs/examples/",
    mock_api=True
)

# Fix any failing examples
for failure in validation.failures:
    print(f"Fix needed in {failure.file}: {failure.error}")
```

5. **Update index and links**:
   - Update `docs/README.md` with new sections
   - Add navigation links
   - Verify all cross-references work

**Duration**: ~3 hours
**Files Modified**: 5-10 documentation files
**Agents Used**: 1

---

## Key Takeaways

### Agent Selection Guidelines

| Complexity | Task Type | Agents | Example |
|------------|-----------|--------|---------|
| Simple | Single file/component | 1 agent | Add CLI option |
| Medium | Related components | 2-3 agents | Add query operator |
| Complex | Multiple subsystems | 4+ agents | New resource manager |
| Maintenance | Bug fix | 1-2 agents | Fix transpilation |
| Documentation | Docs only | 1 agent | API reference update |

### Success Factors

1. **Clear Task Definition**: Well-defined tasks get better results
2. **Proper Agent Selection**: Choose agents matching the task domain
3. **Dependency Management**: Orchestrator ensures correct ordering
4. **Quality Validation**: Always validate with linting, tests, coverage
5. **Documentation Sync**: Keep docs updated with code changes

### Common Patterns

- **Models First**: Always create/update models before implementations
- **Tests Alongside**: Generate tests as features are implemented
- **Docs Last**: Update documentation after implementation is stable
- **Incremental Validation**: Validate early and often during development
