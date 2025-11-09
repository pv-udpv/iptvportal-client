# GitHub Copilot Agents Architecture

Visual reference for the agent system architecture and workflows.

## Agent Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR AGENT                       │
│                                                               │
│  • Analyzes issues and determines scope                      │
│  • Breaks down complex tasks into sub-issues                 │
│  • Coordinates specialized agents                            │
│  • Tracks progress and enforces quality                      │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┬──────────────┬───────────────┐
        │               │               │              │               │
        ▼               ▼               ▼              ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
│     API      │ │   Resource   │ │  Query   │ │   CLI    │ │    Testing   │
│ Integration  │ │   Manager    │ │ Builder  │ │  Agent   │ │    Agent     │
└──────────────┘ └──────────────┘ └──────────┘ └──────────┘ └──────────────┘
        │               │               │              │               │
        └───────────────┴───────────────┴──────────────┴───────────────┘
                                        │
                                        ▼
                              ┌──────────────────┐
                              │  Documentation   │
                              │      Agent       │
                              └──────────────────┘
```

## Agent Interaction Flow

### Simple Task (1 Agent)
```
┌──────────┐     ┌─────────────┐     ┌──────────┐
│  Issue   │────▶│  CLI Agent  │────▶│   Done   │
│ Created  │     │ (30-60 min) │     │          │
└──────────┘     └─────────────┘     └──────────┘
```

### Medium Task (2-3 Agents)
```
┌──────────┐     ┌─────────────┐     ┌──────────────┐     ┌──────────┐
│  Issue   │────▶│   Query     │────▶│   Testing    │────▶│   Done   │
│ Created  │     │  Builder    │     │    Agent     │     │          │
└──────────┘     │  (1-2 hrs)  │     │  (30-60 min) │     └──────────┘
                 └─────────────┘     └──────────────┘
                        │                    │
                        ▼                    ▼
                 ┌─────────────┐     ┌──────────────┐
                 │    Code     │     │    Tests     │
                 │   Changes   │     │   Created    │
                 └─────────────┘     └──────────────┘
```

### Complex Task (6+ Agents - Orchestrated)
```
┌──────────┐     ┌──────────────┐
│  Issue   │────▶│ Orchestrator │
│ Created  │     │   Analyzes   │
└──────────┘     └──────┬───────┘
                        │
        ┌───────────────┼───────────────┬──────────────┬───────────────┐
        │               │               │              │               │
        ▼               ▼               ▼              ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
│   1. API     │ │  2. Resource │ │  3. CLI  │ │ 4. Test  │ │   5. Docs    │
│ Integration  │ │   Manager    │ │   Agent  │ │  Agent   │ │    Agent     │
│              │ │              │ │          │ │          │ │              │
│   Models &   │ │  CRUD Ops &  │ │ Commands │ │  Tests   │ │ API Ref &    │
│  Validation  │ │ Integration  │ │& Format  │ │& Coverage│ │  Examples    │
└──────┬───────┘ └──────┬───────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘
       │                │              │            │              │
       └────────────────┴──────────────┴────────────┴──────────────┘
                                      │
                                      ▼
                            ┌──────────────────┐
                            │   Orchestrator   │
                            │  Validates & QA  │
                            └────────┬─────────┘
                                     │
                                     ▼
                              ┌──────────┐
                              │   Done   │
                              └──────────┘
```

## Component Dependencies

```
┌─────────────────────────────────────────────────────────────────┐
│                        DEPENDENCY FLOW                           │
└─────────────────────────────────────────────────────────────────┘

  Models           Resource         CLI            Tests        Docs
  (API)           Manager         Commands
    │                │               │               │            │
    │                │               │               │            │
    ▼                │               │               │            │
  Create             │               │               │            │
  Pydantic           │               │               │            │
  Models             │               │               │            │
    │                │               │               │            │
    │─────────────▶  │               │               │            │
    │              Build             │               │            │
    │              CRUD Ops          │               │            │
    │                │               │               │            │
    │                │───────────▶   │               │            │
    │                │            Create             │            │
    │                │            Commands           │            │
    │                │               │               │            │
    │                │               │               │            │
    │────────────────┴───────────────┴──────────▶    │            │
    │                                             Generate         │
    │                                             Tests            │
    │                                                │             │
    │────────────────────────────────────────────────┴────────▶   │
    │                                                           Write
    │                                                           Docs
    ▼                                                              │
  DONE ◀──────────────────────────────────────────────────────────┘
```

## Quality Gates

```
┌─────────────────────────────────────────────────────────────────┐
│                      QUALITY VALIDATION                          │
└─────────────────────────────────────────────────────────────────┘

  Agent              Code               Quality
  Completes    ────▶ Changes      ────▶ Gates
    │                  │                  │
    │                  │                  │
    │                  ▼                  │
    │         ┌──────────────┐            │
    │         │  make lint   │────────────┼──▶ PASS ✓
    │         └──────────────┘            │
    │                  │                  │
    │                  ▼                  │
    │         ┌──────────────┐            │
    │         │ make type-   │────────────┼──▶ PASS ✓
    │         │    check     │            │
    │         └──────────────┘            │
    │                  │                  │
    │                  ▼                  │
    │         ┌──────────────┐            │
    │         │  make test   │────────────┼──▶ PASS ✓
    │         └──────────────┘            │
    │                  │                  │
    │                  ▼                  │
    │         ┌──────────────┐            │
    │         │ make test-   │────────────┼──▶ ≥80% ✓
    │         │     cov      │            │
    │         └──────────────┘            │
    │                  │                  │
    │                  ▼                  │
    │         ┌──────────────┐            │
    │         │  Docs Check  │────────────┼──▶ PASS ✓
    │         └──────────────┘            │
    │                  │                  │
    │                  ▼                  ▼
    │                                  Ready for
    └──────────────────────────────▶    Review
```

## MCP Tools Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                     MCP TOOLS ECOSYSTEM                          │
└─────────────────────────────────────────────────────────────────┘

Priority 1 (Core)                  Agents Using
─────────────────                  ─────────────
┌──────────────────────┐          ┌──────────────────┐
│ iptvportal-api-spec  │◀─────────│ API Integration  │
└──────────────────────┘          └──────────────────┘
                                  ┌──────────────────┐
┌──────────────────────┐          │  Orchestrator    │
│   template-engine    │◀─────────│ Resource Manager │
└──────────────────────┘          └──────────────────┘
                                  ┌──────────────────┐
┌──────────────────────┐          │     Testing      │
│  pytest-generator    │◀─────────│  Documentation   │
└──────────────────────┘          └──────────────────┘

Priority 2 (Enhancement)           Agents Using
────────────────────────          ─────────────
┌──────────────────────┐          ┌──────────────────┐
│  coverage-analyzer   │◀─────────│     Testing      │
└──────────────────────┘          └──────────────────┘
                                  ┌──────────────────┐
┌──────────────────────┐          │  Query Builder   │
│    sql-validator     │◀─────────│  API Integration │
└──────────────────────┘          └──────────────────┘
                                  ┌──────────────────┐
┌──────────────────────┐          │ Resource Manager │
│   crud-validator     │◀─────────│     Testing      │
└──────────────────────┘          └──────────────────┘

Priority 3 (Nice-to-have)          Agents Using
─────────────────────────          ─────────────
┌──────────────────────┐          ┌──────────────────┐
│  sphinx-generator    │◀─────────│  Documentation   │
└──────────────────────┘          └──────────────────┘
                                  ┌──────────────────┐
┌──────────────────────┐          │  Documentation   │
│  example-validator   │◀─────────│     Testing      │
└──────────────────────┘          └──────────────────┘
                                  ┌──────────────────┐
┌──────────────────────┐          │       CLI        │
│   rich-templates     │◀─────────│  Documentation   │
└──────────────────────┘          └──────────────────┘
```

## Task Complexity Matrix

```
┌─────────────────────────────────────────────────────────────────┐
│               TASK COMPLEXITY vs AGENT COUNT                     │
└─────────────────────────────────────────────────────────────────┘

Agents
  6+ │                                              ╔════════╗
     │                                              ║Complex ║
     │                                              ║Features║
   5 │                                              ╚════════╝
     │
     │
   4 │
     │
     │                            ╔════════╗
   3 │                            ║ Medium ║
     │                            ║Features║
     │                            ╚════════╝
   2 │        ╔════════╗
     │        ║ Simple ║
     │        ║Features║
   1 │        ╚════════╝
     │   ╔════╗
     └───┴────┴────┴────┴────┴────┴────┴────┴────▶ Complexity
      Bug  CLI  Query  API   Rsrc  Multi  Full
      Fix  Opt  Op    Model  Mgr   Comp   Feature

Legend:
  ╔════╗  Simple   (< 1 hour,  1 agent)
  ╔════╗  Medium   (1-3 hours, 2-3 agents)  
  ╔════╗  Complex  (4+ hours,  4+ agents + orchestrator)
```

## File Organization

```
.github/agents/
│
├── README.md                    ← Main documentation
├── QUICK_REFERENCE.md           ← Quick lookup guide
├── WORKFLOW_EXAMPLES.md         ← Detailed examples
│
├── orchestrator.md              ← Coordinator agent
│
├── Core Implementation Agents
│   ├── api-integration.md       ← API & models
│   ├── resource-manager.md      ← CRUD operations
│   └── query-builder.md         ← Query DSL
│
├── Support Agents
│   ├── cli.md                   ← CLI commands
│   ├── testing.md               ← Test generation
│   └── documentation.md         ← Docs maintenance
│
└── (This file)
    └── ARCHITECTURE.md          ← Visual reference
```

## Workflow Patterns

### Pattern 1: Single Agent (Simple)
```
Request ──▶ Agent ──▶ Implementation ──▶ Tests ──▶ Done
          (30-60m)
```

### Pattern 2: Sequential (Medium)
```
Request ──▶ Agent 1 ──▶ Agent 2 ──▶ Agent 3 ──▶ Done
          (1 hour)    (1 hour)    (30 min)
```

### Pattern 3: Orchestrated (Complex)
```
                    ┌─▶ Agent A ──┐
Request ──▶ Orch ───┼─▶ Agent B ──┼──▶ Orch ──▶ QA ──▶ Done
                    ├─▶ Agent C ──┤
                    └─▶ Agent D ──┘
             (Plan)   (Parallel)    (Validate)
```

## Key Metrics

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXPECTED IMPROVEMENTS                         │
└─────────────────────────────────────────────────────────────────┘

Metric                Before      After       Improvement
──────────────────   ────────    ────────    ───────────
Boilerplate Time     10 hours    3 hours        -70%
Test Coverage        60%         85%            +25%
Doc Sync Issues      Common      Rare           -80%
Pattern Adherence    Variable    Consistent     100%
Code Review Time     High        Medium         -40%
```

## Agent Communication Protocol

```
┌─────────────────────────────────────────────────────────────────┐
│                   AGENT COMMUNICATION                            │
└─────────────────────────────────────────────────────────────────┘

Orchestrator                Specialized Agent
     │                              │
     │  1. Task Assignment          │
     │──────────────────────────▶   │
     │     • Description            │
     │     • Requirements           │
     │     • Context                │
     │                              │
     │  2. Progress Update          │
     │  ◀──────────────────────────│
     │     • Status                 │
     │     • Blockers               │
     │                              │
     │  3. Completion Report        │
     │  ◀──────────────────────────│
     │     • Files modified         │
     │     • Tests added            │
     │     • Next steps             │
     │                              │
     │  4. Validation Results       │
     │──────────────────────────▶   │
     │     • Quality gates          │
     │     • Issues found           │
     │                              │
     ▼                              ▼
   Done                          Done
```

---

**Note**: This architecture is designed to be extensible. New agents can be added by following the patterns established in existing agent documentation.

For detailed implementation guides, see:
- [README.md](./README.md) - Complete documentation
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - Quick lookup
- [WORKFLOW_EXAMPLES.md](./WORKFLOW_EXAMPLES.md) - Detailed examples
