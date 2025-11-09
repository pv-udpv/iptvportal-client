# Quick Reference: GitHub Copilot Agents

Quick guide for selecting and using specialized GitHub Copilot agents in the IPTVPortal client project.

## Agent Selection Matrix

| Your Task | Agent to Use | Tools | Typical Duration |
|-----------|--------------|-------|------------------|
| **Fix a bug in one file** | Single domain agent | Standard tools | 30 min - 1 hour |
| **Add CLI option/command** | CLI Agent | `typer-generator`, `rich-templates` | 30 min - 1 hour |
| **Add query operator** | Query Builder Agent + Testing Agent | `sql-validator`, `ast-analyzer` | 1-2 hours |
| **Create API endpoint** | API Integration Agent + Testing Agent | `iptvportal-api-spec`, `pydantic-generator` | 2-3 hours |
| **New resource manager** | Orchestrator coordinates all agents | All tools | 4-6 hours |
| **Update documentation** | Documentation Agent | `sphinx-generator`, `example-validator` | 1-3 hours |
| **Improve test coverage** | Testing Agent | `pytest-generator`, `coverage-analyzer` | 1-2 hours |

## Quick Commands

### Using a Single Agent

When you have a focused task in one area:

```markdown
@agent:cli Please add a --format option to the sync status command that supports table, json, and csv output formats.
```

```markdown
@agent:testing Generate comprehensive tests for the TerminalResource class including all CRUD operations and error cases.
```

```markdown
@agent:documentation Update the API reference documentation to include the new Terminal resource manager methods.
```

### Using the Orchestrator

For complex tasks spanning multiple areas:

```markdown
@agent:orchestrator I need to add a Media resource manager with:
- Pydantic models for Media entity
- Full CRUD operations (sync + async)
- CLI commands for media management
- Rich table output with thumbnails
- Comprehensive tests (80%+ coverage)
- Complete documentation

Please break this down into sub-tasks and coordinate the specialized agents.
```

### Agent Tags for Issues

When creating GitHub issues:

```markdown
<!-- Simple task -->
Labels: enhancement, agent:cli

<!-- Medium task -->
Labels: enhancement, agent:query-builder, agent:testing

<!-- Complex task -->
Labels: feature, agent:orchestrator, needs-coordination
```

## Agent Specializations

### Orchestrator Agent
**Use when**: Multi-component features, complex coordination needed
- Breaks down complex tasks
- Coordinates multiple agents
- Ensures quality gates
- Manages dependencies

### API Integration Agent
**Use when**: Working with API endpoints, models, or data validation
- Creates Pydantic models
- Implements API endpoints
- Handles error cases
- Maintains transport layer consistency

### Query Builder Agent
**Use when**: Extending query DSL or adding operators
- Adds query operators
- Implements functions
- Ensures type safety
- Validates JSONSQL output

### Testing Agent
**Use when**: Need tests or coverage improvements
- Generates unit tests
- Creates integration tests
- Fills coverage gaps
- Updates fixtures

### Documentation Agent
**Use when**: Docs need updating or API reference generation
- Syncs docs with code
- Generates API reference
- Updates examples
- Maintains CHANGELOG

### CLI Agent
**Use when**: Adding/modifying CLI commands
- Creates CLI commands
- Implements rich formatting
- Adds help text
- Ensures UX consistency

### Resource Manager Agent
**Use when**: Creating or modifying resource managers
- Scaffolds resource managers
- Implements CRUD operations
- Integrates with query builder
- Follows established patterns

## Common Workflows

### Adding a New Feature

1. **Analyze**: What components are affected?
2. **Select**: Choose agent(s) based on matrix above
3. **Provide Context**: Include requirements and examples
4. **Validate**: Run `make ci` to check quality
5. **Iterate**: Refine based on results

### Fixing a Bug

1. **Identify**: Which component has the bug?
2. **Assign**: Use appropriate domain agent
3. **Test**: Agent should add regression test
4. **Document**: Update CHANGELOG if user-facing

### Improving Code Quality

1. **Coverage**: Use Testing Agent for gaps
2. **Documentation**: Use Documentation Agent
3. **Type Hints**: Use appropriate domain agent
4. **Validation**: Run `make type-check` and `make lint`

## Quality Checklist

Before marking work complete, ensure:

- [ ] `make lint` passes (ruff)
- [ ] `make type-check` passes (mypy --strict)
- [ ] `make test` passes (all tests)
- [ ] `make test-cov` shows ≥80% coverage
- [ ] Documentation updated (`README.md`, `docs/*.md`)
- [ ] CHANGELOG.md updated (if user-facing)
- [ ] Examples tested and working
- [ ] Code follows existing patterns

## MCP Tools Status

### Available Now (Standard Tools)
✅ `view`, `edit`, `create` - File operations
✅ `bash` - Shell commands and testing
✅ `github-mcp-server-*` - GitHub API operations

### To Be Developed (Priority 1)
🚧 `iptvportal-api-spec` - API documentation access
🚧 `template-engine` - Code scaffolding
🚧 `pytest-generator` - Intelligent test generation

### To Be Developed (Priority 2)
🔮 `coverage-analyzer` - Coverage gap detection
🔮 `sql-validator` - JSONSQL validation
🔮 `crud-validator` - CRUD completeness checker

### To Be Developed (Priority 3)
💡 `sphinx-generator` - Documentation auto-generation
💡 `example-validator` - Example execution validation
💡 `rich-templates` - CLI formatting templates

## Tips for Success

### 1. Be Specific
❌ "Add terminal support"
✅ "Add Terminal resource manager with CRUD operations, CLI commands, and tests following the Subscriber pattern"

### 2. Provide Context
Include:
- What you want to accomplish
- Any constraints or requirements
- Examples of similar existing code
- Acceptance criteria

### 3. Reference Patterns
- "Follow the SubscriberResource pattern"
- "Use the same CLI structure as the sync commands"
- "Match the test style in test_transpiler.py"

### 4. Iterate
- Start with core functionality
- Add features incrementally
- Validate early and often
- Refine based on results

### 5. Validate Quality
- Always run the full CI suite
- Check coverage reports
- Review generated documentation
- Test the actual functionality

## Getting Help

- **Agent Documentation**: See individual `.md` files in `.github/agents/`
- **Workflow Examples**: See `.github/agents/WORKFLOW_EXAMPLES.md`
- **Project Patterns**: See `.github/copilot-instructions.md`
- **Contributing Guide**: See `.github/CONTRIBUTING.md`

## Examples

### Example 1: Simple CLI Enhancement
```markdown
@agent:cli

Add a --verbose flag to the `iptvportal sync status` command that shows:
- Detailed sync statistics for each table
- Last sync timestamp
- Number of records synced
- Any sync errors

Follow the pattern used in other commands.
```

### Example 2: Medium Feature
```markdown
@agent:query-builder @agent:testing

Add support for the IN operator in the query builder:
- Field("status").in_(["active", "pending"])
- Should convert to {"status": {"in": ["active", "pending"]}}
- Include comprehensive tests
- Update documentation with examples
```

### Example 3: Complex Feature
```markdown
@agent:orchestrator

Implement complete Package resource manager:

Requirements:
- Pydantic models (Package, PackageCreate, PackageUpdate)
- Full CRUD operations in PackageResource
- Async variant (AsyncPackageResource)
- CLI commands: `iptvportal package list|get|create|update|delete`
- Rich table output with package details
- Query builder integration for filtering
- 80%+ test coverage
- Complete API documentation
- Usage examples in README.md

Please coordinate the specialized agents to implement this systematically.
```

---

For complete documentation, see [.github/agents/README.md](./README.md)
