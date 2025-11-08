# Cline Workflow Integration

## Overview

This document describes the comprehensive integration between Cline AI assistant and the IPTVPortal git workflow, enabling continuous checklist tracking merged with commit IDs and GitHub issues.

## System Architecture

```mermaid
graph TB
    subgraph "GitHub"
        Issue[GitHub Issue #123]
        PR[Pull Request]
        Comments[Issue Comments]
    end

    subgraph "Cline AI Assistant"
        Cline[Cline Session]
        TaskProgress[task_progress parameter]
    end

    subgraph "Local Repository"
        Progress[.cline-progress file]
        Scripts[Workflow Scripts]
        Hooks[Git Hooks]
    end

    subgraph "Git Operations"
        Commit[git commit]
        Push[git push]
        PRCreate[PR Creation]
    end

    Issue --> Cline
    Cline --> TaskProgress
    TaskProgress --> Progress
    Progress --> Scripts
    Scripts --> Commit
    Commit --> Hooks
    Hooks --> Push
    Push --> PRCreate
    PRCreate --> PR
    Scripts --> Comments
```

## Detailed Workflow Process

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant Cline as Cline AI
    participant Scripts as Workflow Scripts
    participant Hooks as Git Hooks
    participant Git as Git Repository
    participant GitHub as GitHub

    %% Initialization Phase
    rect rgb(240, 248, 255)
        Dev->>Scripts: ./scripts/cline-init.sh --issue 123
        Scripts->>Git: Create .cline-progress file
        Git->>Dev: Initialized tracking for issue #123
    end

    %% Development Phase
    rect rgb(255, 248, 240)
        loop Development Loop
            Dev->>Cline: Request task implementation
            Cline->>Cline: Generate task_progress checklist
            Cline->>Scripts: Auto-save to .cline-progress
            Scripts->>Git: Update progress file

            Dev->>Scripts: ./scripts/cline-commit.sh --items "1,2"
            Scripts->>Git: Create commit with checklist refs
            Git->>Hooks: Trigger post-commit hook
            Hooks->>Scripts: update_cline_item() - mark items complete
            Scripts->>Git: Update .cline-progress with commit SHAs
        end
    end

    %% Quality Gates
    rect rgb(248, 255, 240)
        Git->>Hooks: pre-commit hook
        Hooks->>Scripts: validate_checklist()
        Scripts->>Hooks: Checklist consistency OK

        Git->>Hooks: commit-msg hook
        Hooks->>Scripts: validate_cline_references()
        Scripts->>Hooks: References validated

        Git->>Hooks: pre-push hook
        Hooks->>Scripts: check_cline_checklist_completion()
        Scripts->>Hooks: Critical items completed
    end

    %% PR Creation Phase
    rect rgb(255, 240, 248)
        Dev->>Scripts: ./scripts/cline-pr.sh --sync-issue
        Scripts->>GitHub: Generate PR with checklist
        GitHub->>PR: PR created with task progress
        Scripts->>GitHub: Post progress to issue comments
        GitHub->>Comments: Real-time progress updates
    end
```

## Hook Integration Flow

```mermaid
flowchart TD
    A[Developer runs git command] --> B{Which hook?}

    B --> C[pre-commit]
    C --> D{Files changed?}
    D --> E[Validate checklist consistency]
    E --> F[Check for incomplete items]
    F --> G[Warn/Fail if issues found]

    B --> H[commit-msg]
    H --> I[Parse commit message]
    I --> J{Contains checklist refs?}
    J --> K[Validate item IDs exist]
    K --> L[Check items not already completed]

    B --> M[post-commit]
    M --> N[Extract checklist refs from commit]
    N --> O[Update .cline-progress items]
    O --> P[Mark items as completed]
    P --> Q[Link items to commit SHA]

    B --> R[pre-push]
    R --> S[Check completed items have commits]
    S --> T[Validate critical items completed]
    T --> U[Show progress summary]
    U --> V[Allow/Block push based on completion]
```

## Data Flow Architecture

```mermaid
graph LR
    subgraph "Input Sources"
        ClineInput[Cline task_progress]
        UserInput[User Scripts]
        GitInput[Git Operations]
    end

    subgraph "Processing Layer"
        Helpers[cline-helpers.sh]
        Validation[Hook Validation]
        Updates[Progress Updates]
    end

    subgraph "Storage Layer"
        ProgressFile[.cline-progress JSON]
        GitCommits[Git Commit History]
        GitHubIssues[GitHub Issues/PRs]
    end

    subgraph "Output Destinations"
        TerminalOutput[Terminal Display]
        CommitMessages[Commit Messages]
        PRDescriptions[PR Descriptions]
        IssueComments[Issue Comments]
    end

    ClineInput --> Helpers
    UserInput --> Helpers
    GitInput --> Validation

    Helpers --> Updates
    Validation --> Updates

    Updates --> ProgressFile
    Updates --> GitCommits

    ProgressFile --> GitHubIssues
    ProgressFile --> TerminalOutput
    ProgressFile --> CommitMessages
    ProgressFile --> PRDescriptions
    ProgressFile --> IssueComments
```

## Checklist Item Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Pending: cline-init.sh
    Pending --> InProgress: Cline task_progress update
    InProgress --> Completed: cline-commit.sh --items "1"
    Completed --> [*]: PR merged

    Pending --> Completed: Direct completion
    InProgress --> Pending: Revert status

    note right of Completed
        Linked to commit SHA
        Shows in PR description
        Updates issue comments
    end note

    note right of InProgress
        Shows progress in status
        Blocks critical item pushes
    end note
```

## Integration Points Summary

| Component | Integration Method | Purpose |
|-----------|-------------------|---------|
| **Cline AI** | `task_progress` parameter | Generate/update checklists |
| **Git Hooks** | Source `cline-helpers.sh` | Automatic validation/updates |
| **User Scripts** | Call helper functions | Interactive workflow |
| **Commit Messages** | `Completes: #X` format | Link items to commits |
| **PR Template** | Auto-generated checklist | Show progress in reviews |
| **GitHub Issues** | Comment updates | Real-time progress tracking |

## Example Complete Workflow

```mermaid
timeline
    title Cline-Git Workflow Example

    section Initialization
        Developer : ./scripts/cline-init.sh --issue 123
        System : Creates .cline-progress file

    section Development
        Cline : Generates checklist via task_progress
        Developer : Implements feature
        Developer : ./scripts/cline-commit.sh --items "1,2"
        Hooks : Auto-update checklist with commit SHAs

    section Quality Checks
        Hooks : pre-commit validates checklist
        Hooks : commit-msg validates references
        Hooks : pre-push checks completion

    section Completion
        Developer : ./scripts/cline-pr.sh --sync-issue
        System : Creates PR with full checklist
        System : Updates issue with progress
        Reviewer : Sees complete task history
```

## Key Benefits

- **Continuous Tracking**: Checklist persists across Cline sessions
- **Automatic Linking**: Commits automatically linked to checklist items
- **Quality Gates**: Git hooks enforce checklist discipline
- **Real-time Sync**: Progress updates flow to GitHub automatically
- **Audit Trail**: Complete history in git commits and PR descriptions
- **Team Visibility**: Progress visible in issues and PRs

## File Relationships

```mermaid
graph TD
    A[.clinerules] --> B[Workflow Guidelines]
    B --> C[scripts/cline-helpers.sh]
    C --> D[scripts/cline-init.sh]
    C --> E[scripts/cline-commit.sh]
    C --> F[scripts/cline-pr.sh]
    C --> G[scripts/cline-sync.sh]
    C --> H[scripts/cline-status.sh]

    C --> I[.githooks/pre-commit]
    C --> J[.githooks/commit-msg]
    C --> K[.githooks/post-commit]
    C --> L[.githooks/pre-push]

    M[.cline-progress] --> C
    N[.github/pull_request_template.md] --> F
    O[GitHub Issues] --> G
```

This integration creates a seamless workflow where Cline's task progress is continuously tracked, validated, and synchronized with git commits and GitHub issues throughout the development process.
