# GitHub Copilot Agents for IPTVPortal Client

This directory contains specialized GitHub Copilot agents designed to automate and streamline development workflows for the IPTVPortal client project. Each agent has specific responsibilities and custom MCP (Model Context Protocol) tools to handle different aspects of the codebase.

## Overview

The agent architecture enables efficient, consistent, and high-quality development through specialized AI agents that work together under the coordination of an orchestrator agent. Each agent focuses on a specific domain (API integration, testing, documentation, etc.) and has access to custom tools designed for its specialty.

## Available Agents

### 1. [Orchestrator Agent](./orchestrator.md)
**Primary Coordinator**

- Analyzes incoming issues and determines task scope
- Breaks down complex tasks into sub-issues with dependencies
- Creates PR infrastructure and coordinates specialized agents
- Tracks overall progress and ensures completion criteria
- Enforces quality gates and code standards

**When to use**: For complex features that span multiple components or when coordinating work across different areas of the codebase.

---

### 2. [API Integration Agent](./api-integration.md)
**API & Models Specialist**

- Implements IPTVPortal JSONSQL API endpoints
- Generates resource managers for new entities
- Ensures proper error handling and retry logic
- Maintains consistency with existing transport layer

**When to use**: When adding new API endpoints, creating data models, or implementing resource managers.

**Key tools**: `iptvportal-api-spec`, `pydantic-generator`

---

### 3. [Query Builder Agent](./query-builder.md)
**Query DSL Expert**

- Extends JSONSQL query builder DSL
- Adds new operators and query methods
- Ensures type safety and runtime validation
- Generates tests for query constructions

**When to use**: When adding new query operators, functions, or extending the query builder DSL.

**Key tools**: `sql-validator`, `ast-analyzer`

---

### 4. [Testing Agent](./testing.md)
**Quality Assurance Specialist**

- Generates unit tests for new components
- Creates integration tests with httpx-mock
- Ensures test coverage meets 80% threshold
- Updates fixtures and test utilities

**When to use**: For generating comprehensive test suites, improving coverage, or creating test utilities.

**Key tools**: `pytest-generator`, `coverage-analyzer`

---

### 5. [Documentation Agent](./documentation.md)
**Documentation Maintainer**

- Syncs documentation with code changes
- Generates API reference from docstrings
- Updates examples and quickstart guides
- Maintains CHANGELOG.md

**When to use**: When documenting new features, updating API reference, or maintaining project documentation.

**Key tools**: `sphinx-generator`, `example-validator`

---

### 6. [CLI Agent](./cli.md)
**Command-Line Interface Specialist**

- Adds new CLI commands for resource managers
- Implements rich formatting and tables
- Adds command completion and help text
- Ensures consistent CLI UX

**When to use**: When adding CLI commands, improving CLI output formatting, or enhancing user experience.

**Key tools**: `typer-generator`, `rich-templates`

---

### 7. [Resource Manager Agent](./resource-manager.md)
**Resource Manager Implementation Expert**

- Scaffolds new resource managers (Terminal, Media, Package, etc.)
- Implements CRUD operations with proper validation
- Integrates with query builder and transport layer
- Follows existing patterns from SubscriberResource

**When to use**: When creating new resource managers or extending entity management capabilities.

**Key tools**: `template-engine`, `crud-validator`

---

## Workflow Example

Here's how agents work together on a typical feature:

### Example: Adding a Terminal Resource Manager

**1. Orchestrator Agent** analyzes the issue and creates a plan:
```markdown
Sub-tasks:
1. Create Terminal models (API Integration Agent)
2. Implement TerminalResource (Resource Manager Agent)
3. Add CLI commands (CLI Agent)
4. Generate tests (Testing Agent)
5. Update documentation (Documentation Agent)
```

**2. API Integration Agent** creates models:
- `Terminal`, `TerminalCreate`, `TerminalUpdate` models
- Request/response models
- Validation rules

**3. Resource Manager Agent** implements the resource manager:
- `TerminalResource` class with CRUD operations
- `AsyncTerminalResource` for async support
- Query builder integration
- Client integration

**4. CLI Agent** adds CLI commands:
- `iptvportal terminal list`
- `iptvportal terminal get <id>`
- `iptvportal terminal create`
- Rich formatted output

**5. Testing Agent** generates tests:
- Unit tests for TerminalResource
- CLI command tests
- Integration tests
- Async tests

**6. Documentation Agent** updates docs:
- API reference for TerminalResource
- CLI command documentation
- Usage examples
- CHANGELOG.md entry

**7. Orchestrator Agent** reviews and validates:
- Runs `make lint`, `make type-check`, `make test`
- Verifies 80%+ coverage
- Ensures documentation is complete
- Requests human review

---

## Agent Communication Protocol

### Orchestrator → Specialized Agent
The orchestrator provides:
- Clear task description
- Relevant context and requirements
- References to existing patterns
- Acceptance criteria

### Specialized Agent → Orchestrator
The specialized agent reports:
- Completion status
- Files modified/created
- Any issues encountered
- Recommendations for follow-up

### Between Specialized Agents
Agents may reference each other's work:
- API Integration → Resource Manager: "Use these models"
- Resource Manager → CLI: "Expose these operations"
- All → Testing: "Test these components"

---

## Quality Standards

All agents must ensure:

### Code Quality
- ✅ Passes `ruff` linting (100 char line length)
- ✅ Passes `mypy --strict` type checking
- ✅ Google-style docstrings for all public APIs
- ✅ Consistent with existing codebase patterns

### Testing
- ✅ 80%+ test coverage for new code
- ✅ Unit tests for all components
- ✅ Integration tests where appropriate
- ✅ Async/sync parity maintained

### Documentation
- ✅ API reference is complete
- ✅ Examples demonstrate new features
- ✅ CHANGELOG.md is updated
- ✅ Migration guides for breaking changes

### Integration
- ✅ Context managers work correctly
- ✅ Error handling follows project patterns
- ✅ Type hints are comprehensive
- ✅ Follows existing code organization

---

## MCP Tools Reference

### Priority 1 (Core) - To Be Developed

#### `iptvportal-api-spec`
Live access to IPTVPortal API documentation and schemas.
```python
schema = iptvportal_api_spec.get_table_schema("subscriber")
validation = iptvportal_api_spec.validate_jsonsql(query)
```

#### `template-engine`
Code scaffolding from templates for consistent implementations.
```python
code = template_engine.generate_resource_manager("Terminal")
crud = template_engine.generate_crud_methods("Terminal")
```

#### `pytest-generator`
Intelligent test generation from code analysis.
```python
tests = pytest_generator.generate_tests("iptvportal.service.query")
params = pytest_generator.parametrize(test_cases)
```

### Priority 2 (Enhancement) - To Be Developed

#### `coverage-analyzer`
Test coverage gap detection and suggestions.
```python
gaps = coverage_analyzer.find_gaps("iptvportal.client")
suggestions = coverage_analyzer.suggest_tests(uncovered_lines)
```

#### `sql-validator`
JSONSQL syntax validation and correctness checking.
```python
validation = sql_validator.validate_jsonsql(jsonsql_query)
is_valid = sql_validator.check_operator("like", "%test%")
```

#### `crud-validator`
CRUD completeness checker for resource managers.
```python
validation = crud_validator.validate_resource("TerminalResource")
signatures = crud_validator.check_signatures("TerminalResource")
```

### Priority 3 (Nice-to-have) - To Be Developed

#### `sphinx-generator`
Documentation auto-generation from code and docstrings.
```python
docs = sphinx_generator.generate_api_docs("iptvportal.client")
```

#### `example-validator`
Example code execution validator to ensure examples work.
```python
validation = example_validator.validate("examples/auth.py")
```

#### `rich-templates`
CLI formatting patterns and templates.
```python
table = rich_templates.get_table("Subscribers", columns)
```

---

## Development Guidelines

### For Agent Developers

When creating or modifying agents:

1. **Maintain Consistency**: Follow the structure and format of existing agents
2. **Clear Responsibilities**: Each agent should have a focused, well-defined role
3. **Tool Integration**: Specify custom MCP tools and their usage clearly
4. **Pattern Documentation**: Include concrete code examples and patterns
5. **Quality Standards**: Document quality gates and success criteria

### For Users of Agents

When working with agents:

1. **Choose the Right Agent**: Use the agent that best matches your task
2. **Provide Context**: Give agents sufficient context about the task
3. **Follow Patterns**: Reference existing code patterns for consistency
4. **Validate Results**: Always review and test agent-generated code
5. **Iterate**: Work with agents iteratively for complex tasks

### For Orchestrator

When coordinating agents:

1. **Analyze First**: Understand the full scope before delegating
2. **Order Dependencies**: Ensure tasks are ordered correctly
3. **Clear Interfaces**: Define clear boundaries between sub-tasks
4. **Monitor Progress**: Track completion of all sub-tasks
5. **Enforce Quality**: Ensure all quality gates pass

---

## Expected Benefits

### Speed
- **70% reduction** in boilerplate code time through automated scaffolding
- **Faster iterations** with immediate feedback from specialized agents
- **Parallel development** as multiple agents can work simultaneously

### Consistency
- **Automatic adherence** to established patterns and conventions
- **Uniform code quality** across different contributors
- **Standardized testing** and documentation practices

### Quality
- **Built-in validation** ensures standards compliance
- **Comprehensive testing** generated automatically
- **Complete documentation** maintained in sync with code

### Maintainability
- **Clear separation** of concerns through specialized agents
- **Reusable patterns** captured in agent instructions
- **Knowledge preservation** in agent documentation

---

## Getting Started

### As a Developer

1. Review the agent documentation relevant to your task
2. Follow the patterns and examples provided
3. Use the custom MCP tools when available
4. Validate your changes meet quality standards

### As an Orchestrator

1. Read the [Orchestrator Agent](./orchestrator.md) documentation
2. Analyze incoming issues using the decision framework
3. Break down complex tasks following the workflow process
4. Coordinate specialized agents according to dependencies

### As a Project Maintainer

1. Keep agent documentation updated with new patterns
2. Add new agents as project needs evolve
3. Develop custom MCP tools to enhance agent capabilities
4. Monitor agent effectiveness and refine as needed

---

## Contributing

When contributing to agent development:

1. **Discuss First**: Propose new agents or major changes in issues
2. **Follow Structure**: Maintain consistency with existing agent format
3. **Test Thoroughly**: Validate that agent instructions work as intended
4. **Document Clearly**: Provide comprehensive examples and patterns
5. **Update This README**: Keep the overview and reference up to date

---

## Support

For questions or issues with agents:

1. Check the specific agent documentation
2. Review examples in the agent markdown files
3. Reference existing code patterns in the repository
4. Open an issue with the `agent` label for discussion

---

## Future Enhancements

Planned improvements to the agent system:

- **Custom MCP Tools**: Develop Priority 1 tools first
- **Agent Templates**: Create templates for new agent types
- **Workflow Automation**: Enhanced orchestrator capabilities
- **Metrics & Monitoring**: Track agent effectiveness
- **Agent Chaining**: More sophisticated inter-agent workflows

---

## License

These agent instructions are part of the IPTVPortal client project and follow the same MIT license.
