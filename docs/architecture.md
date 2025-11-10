# Architecture and Data Flows

This document consolidates the diagrams that appear in the root `README.md` with comprehensive system architecture details for future maintainers, contributors, and reverse engineers. All diagrams use Mermaid and render natively on GitHub.

## Table of Contents

1. [System Architecture Overview](#system-architecture-overview)
2. [Proxy-Centric Architecture](#proxy-centric-architecture)
3. [Multi-Level Caching Strategy](#multi-level-caching-strategy)
4. [Schema-Driven Architecture](#schema-driven-architecture)
5. [Sequence Diagrams](#sequence-diagrams)
   - [Query Execution Flow](#query-execution-flow)
   - [Cache Sync Lifecycle](#cache-sync-lifecycle)
   - [Authentication Lifecycle](#authentication-lifecycle)
6. [High-Level Component Architecture](#high-level-component-architecture)
7. [Architecture Narrative](#architecture-narrative)

---

## System Architecture Overview

The iptvportal-client is built on a **proxy-centric, schema-driven, highly cache-optimized, and configuration-driven architecture**. This section provides a complete system view showing all layers, entities, and their relationships.

```mermaid
graph TB
    subgraph "Local Environment"
        subgraph "User Interface Layer"
            CLI[CLI Interface<br/>Typer-based<br/>Auto-discovery]
            API[Python API<br/>Sync/Async Clients]
        end
        
        subgraph "Service Layer"
            SVC[Service Layer<br/>Query Orchestration<br/>Business Logic]
        end
        
        subgraph "Proxy/Core Layer"
            PROXY[Core Client<br/>Protocol Translation<br/>Field Mapping<br/>Retries & Timeout]
            TRANS[SQL Transpiler<br/>SQL → JSONSQL]
            SCHEMA_SYS[Schema System<br/>Field Resolution<br/>Type Mapping<br/>Validation]
            AUTH_MGR[Auth Manager<br/>Session Persistence<br/>Auto-renewal]
            CACHE_MGR[Cache Manager<br/>Query Result Cache<br/>TTL Management]
        end
        
        subgraph "Data Layer"
            CONF[Configuration<br/>Dynaconf-based<br/>Hierarchical<br/>Environment Vars]
            SCHEMA_REG[Schema Registry<br/>YAML-based<br/>Field Definitions<br/>Sync Config]
            SYNC_DB[(SQLite Cache<br/>Local Mirror<br/>Sync Metadata<br/>Full/Incremental)]
            SESSION_CACHE[(Session Cache<br/>Auth Tokens<br/>Expiration)]
            MEM_CACHE[(In-Memory Cache<br/>Query Results<br/>TTL-based)]
        end
        
        subgraph "Code Generation"
            CODEGEN[Schema Codegen<br/>Pydantic Models<br/>SQLModel ORM<br/>Type-safe APIs]
        end
    end
    
    subgraph "Remote Environment"
        RPC[IPTVPortal API<br/>JSON-RPC Endpoint<br/>JSONSQL DML]
        REMOTE_DB[(Remote Database<br/>Subscriber<br/>Terminal<br/>Package<br/>Media<br/>etc.)]
        AUTH_SVC[Auth Service<br/>authorize_user<br/>Session Management]
    end
    
    %% User Interface connections
    CLI --> SVC
    API --> SVC
    CLI --> CONF
    
    %% Service Layer connections
    SVC --> PROXY
    SVC --> SCHEMA_SYS
    SVC --> CACHE_MGR
    
    %% Proxy Layer connections
    PROXY --> TRANS
    PROXY --> SCHEMA_SYS
    PROXY --> AUTH_MGR
    PROXY --> CACHE_MGR
    PROXY --> RPC
    
    %% Transpiler connections
    TRANS --> SCHEMA_SYS
    
    %% Schema System connections
    SCHEMA_SYS --> SCHEMA_REG
    SCHEMA_SYS --> CODEGEN
    
    %% Auth connections
    AUTH_MGR --> SESSION_CACHE
    AUTH_MGR --> AUTH_SVC
    
    %% Cache connections
    CACHE_MGR --> MEM_CACHE
    PROXY --> SYNC_DB
    SYNC_DB -.sync.-> RPC
    
    %% Configuration connections
    CONF --> PROXY
    CONF --> SYNC_DB
    CONF --> SCHEMA_REG
    
    %% Remote connections
    RPC --> REMOTE_DB
    AUTH_SVC --> REMOTE_DB
    
    %% Codegen outputs
    CODEGEN -.generates.-> API
    
    classDef localLayer fill:#e1f5ff,stroke:#0066cc,stroke-width:2px
    classDef proxyLayer fill:#fff4e1,stroke:#ff9900,stroke-width:2px
    classDef dataLayer fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    classDef remoteLayer fill:#fce4ec,stroke:#e91e63,stroke-width:2px
    
    class CLI,API,SVC localLayer
    class PROXY,TRANS,SCHEMA_SYS,AUTH_MGR,CACHE_MGR proxyLayer
    class CONF,SCHEMA_REG,SYNC_DB,SESSION_CACHE,MEM_CACHE dataLayer
    class RPC,REMOTE_DB,AUTH_SVC remoteLayer
```

### Layer Responsibilities

#### User Interface Layer
- **CLI**: Service-oriented CLI with auto-discovery, rich formatting, debug mode, dry-run capabilities
- **Python API**: Sync and async client APIs with query builder, Field API, Q objects

#### Service Layer
- Orchestrates query execution with business logic
- Coordinates between proxy, schema system, and cache layers
- Provides high-level abstractions for common operations

#### Proxy/Core Layer (Central Hub)
The proxy layer is the heart of the architecture, managing:
- **Protocol Translation**: SQL → JSONSQL transpilation
- **Field Mapping**: Position-based to named field translation using schema system
- **Schema Resolution**: Field type inference, validation, and transformation
- **Cache Coordination**: Multi-level cache strategy (in-memory, SQLite, remote)
- **Authentication**: Session lifecycle, token persistence, auto-renewal
- **Retries & Resilience**: Automatic retry logic, timeout management, error handling
- **Configuration Injection**: Hierarchical config resolution and application

#### Data Layer
- **Configuration**: Dynaconf-based hierarchical configuration with environment variable support
- **Schema Registry**: YAML-based schema definitions with field mappings and sync configuration
- **SQLite Cache**: Local mirror of remote tables with sync metadata
- **Session Cache**: Persistent authentication token storage
- **In-Memory Cache**: Fast query result caching with TTL

#### Code Generation
- Generates type-safe Pydantic models and SQLModel ORM classes from schemas
- Enables compile-time type checking and IDE autocomplete
- Includes validators, relationships, and constraints

---

## Proxy-Centric Architecture

The proxy layer acts as an intelligent intermediary between local and remote systems, providing abstraction, optimization, and resilience.

```mermaid
graph LR
    subgraph "Client Applications"
        APP[Application Code]
        CLI_APP[CLI Commands]
    end
    
    subgraph "Proxy Layer Responsibilities"
        direction TB
        TRANSFORM[Transform<br/>SQL→JSONSQL<br/>Field Mapping<br/>Type Conversion]
        CACHE[Cache Management<br/>Multi-level Strategy<br/>TTL & Invalidation]
        SCHEMA_RES[Schema Resolution<br/>Field Lookup<br/>Type Inference<br/>Validation]
        AUTH_SESS[Auth & Sessions<br/>Token Management<br/>Auto-renewal<br/>Persistence]
        RETRY[Retry Logic<br/>Exponential Backoff<br/>Circuit Breaking<br/>Timeout Management]
        CONFIG[Config Injection<br/>Hierarchical Merge<br/>Environment Override<br/>Schema-specific]
    end
    
    subgraph "Remote System"
        REMOTE[IPTVPortal API<br/>JSON-RPC<br/>JSONSQL]
    end
    
    APP --> TRANSFORM
    CLI_APP --> TRANSFORM
    TRANSFORM --> CACHE
    CACHE --> SCHEMA_RES
    SCHEMA_RES --> AUTH_SESS
    AUTH_SESS --> RETRY
    RETRY --> CONFIG
    CONFIG --> REMOTE
    
    CACHE -.cache hit.-> APP
    CACHE -.cache hit.-> CLI_APP
    
    classDef proxyBox fill:#fff4e1,stroke:#ff9900,stroke-width:2px
    class TRANSFORM,CACHE,SCHEMA_RES,AUTH_SESS,RETRY,CONFIG proxyBox
```

### Proxy Layer Features

1. **Transparent Protocol Translation**
   - Accepts SQL queries or native JSONSQL
   - Automatic transpilation with schema-aware optimization
   - Preserves semantic equivalence

2. **Intelligent Caching**
   - Three-tier strategy: in-memory → SQLite → remote
   - Automatic cache population and invalidation
   - Configurable TTL per table

3. **Schema-Driven Operations**
   - Field position resolution using schema registry
   - Automatic type conversion and validation
   - Support for SELECT * expansion

4. **Resilient Communication**
   - Automatic retry with exponential backoff
   - Configurable timeout and retry limits
   - Detailed error context and logging

5. **Configuration-Driven Behavior**
   - Hierarchical configuration (global → service → table)
   - Environment variable overrides
   - Runtime configuration inspection

---

## Multi-Level Caching Strategy

The client implements a sophisticated three-tier caching strategy for optimal performance and offline capability.

```mermaid
graph TB
    subgraph "Cache Hierarchy"
        APP[Application Request]
        
        subgraph "Level 1: In-Memory Cache"
            L1[In-Memory Cache<br/>Query Results<br/>TTL: Seconds to Minutes<br/>LRU Eviction]
            L1_CHECK{Cache Hit?}
        end
        
        subgraph "Level 2: SQLite Cache"
            L2[SQLite Local Cache<br/>Table Mirrors<br/>TTL: Minutes to Hours<br/>Sync Metadata]
            L2_CHECK{Data Fresh?}
            SYNC_STRAT{Sync Strategy}
            FULL_SYNC[Full Sync<br/>Replace All Rows]
            INCR_SYNC[Incremental Sync<br/>Updated Since Last]
            ON_DEMAND[On-Demand<br/>Lazy Load by ID]
        end
        
        subgraph "Level 3: Remote API"
            L3[IPTVPortal API<br/>JSON-RPC<br/>Source of Truth]
        end
    end
    
    APP --> L1_CHECK
    L1_CHECK -->|Hit| L1
    L1 -->|Return Cached| APP
    
    L1_CHECK -->|Miss| L2_CHECK
    L2_CHECK -->|Fresh| L2
    L2 -->|Store in L1| L1
    
    L2_CHECK -->|Stale/Missing| SYNC_STRAT
    SYNC_STRAT --> FULL_SYNC
    SYNC_STRAT --> INCR_SYNC
    SYNC_STRAT --> ON_DEMAND
    
    FULL_SYNC --> L3
    INCR_SYNC --> L3
    ON_DEMAND --> L3
    
    L3 -->|Update L2| L2
    L3 -->|Update L1| L1
    L1 -->|Return Fresh Data| APP
    
    classDef l1Style fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    classDef l2Style fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    classDef l3Style fill:#fce4ec,stroke:#e91e63,stroke-width:2px
    
    class L1,L1_CHECK l1Style
    class L2,L2_CHECK,SYNC_STRAT,FULL_SYNC,INCR_SYNC,ON_DEMAND l2Style
    class L3 l3Style
```

### Cache Level Details

#### Level 1: In-Memory Cache
- **Purpose**: Ultra-fast repeated query results
- **Storage**: Python dict/LRU cache
- **TTL**: Configurable (default: 5-60 seconds)
- **Scope**: Per-process, lost on restart
- **Best for**: High-frequency reads, dashboard data

#### Level 2: SQLite Cache
- **Purpose**: Persistent local mirror with rich query capabilities
- **Storage**: SQLite database (~/.iptvportal/cache.db)
- **TTL**: Configurable per table (default: 15-60 minutes)
- **Sync Strategies**:
  - **Full Sync**: Complete table replacement (for small/volatile tables)
  - **Incremental**: Updates based on `updated_at` field (for large tables)
  - **On-Demand**: Lazy load individual records (for sparse access patterns)
- **Features**: 
  - Full SQL query support (JOINs, aggregates, CTEs)
  - Sync metadata tracking (last_sync, row_count)
  - Offline query capability
- **Best for**: Complex queries, offline operations, JOIN-heavy workloads

#### Level 3: Remote API
- **Purpose**: Authoritative data source
- **Protocol**: JSON-RPC over HTTPS
- **Authentication**: Session-based with auto-renewal
- **Rate Limiting**: Configurable request throttling
- **Best for**: Write operations, real-time data, cache misses

### Cache Invalidation
- **Time-based**: Automatic expiration via TTL
- **Manual**: `iptvportal cache clear` command
- **Event-based**: Invalidate on write operations
- **Partial**: Table-level or query-pattern-based invalidation

---

## Schema-Driven Architecture

Schemas are the foundation of the entire system, driving code generation, validation, caching, and API interactions.

```mermaid
graph TB
    subgraph "Schema Definition"
        YAML[Schema YAML Files<br/>Field Definitions<br/>Types & Constraints<br/>Sync Config<br/>Relationships]
    end
    
    subgraph "Schema System"
        REGISTRY[Schema Registry<br/>Load & Parse<br/>Validate Structure<br/>Merge Overrides]
        INTROSPECT[Schema Introspection<br/>Auto-detect Fields<br/>Type Inference<br/>Statistical Analysis]
        VALIDATE[Data-Driven Validation<br/>Match Ratio Analysis<br/>Pandas Comparison<br/>Remote Mapping]
    end
    
    subgraph "Consumers"
        CODEGEN_SYS[Code Generation<br/>Pydantic Models<br/>SQLModel ORM<br/>Type Annotations]
        TRANSPILER[SQL Transpiler<br/>Field Resolution<br/>Type Conversion<br/>SELECT * Expansion]
        CACHE_SYS[Cache System<br/>Table DDL<br/>Sync Strategy<br/>Index Creation]
        API_CLIENT[API Clients<br/>Field Mapping<br/>Response Parsing<br/>Validation]
        CLI_FMT[CLI Formatters<br/>Column Names<br/>Pretty Tables<br/>JSON Output]
    end
    
    subgraph "Outputs"
        MODELS[Generated Models<br/>Type-safe APIs<br/>IDE Autocomplete<br/>Validators]
        QUERIES[Optimized Queries<br/>Correct Field Positions<br/>Proper Types]
        DB_SCHEMA[Database Schema<br/>Correct DDL<br/>Indexes<br/>Constraints]
        DISPLAY[Rich Display<br/>Named Columns<br/>Formatted Values]
    end
    
    YAML --> REGISTRY
    INTROSPECT --> REGISTRY
    
    REGISTRY --> VALIDATE
    VALIDATE -.feedback.-> INTROSPECT
    
    REGISTRY --> CODEGEN_SYS
    REGISTRY --> TRANSPILER
    REGISTRY --> CACHE_SYS
    REGISTRY --> API_CLIENT
    REGISTRY --> CLI_FMT
    
    CODEGEN_SYS --> MODELS
    TRANSPILER --> QUERIES
    CACHE_SYS --> DB_SCHEMA
    API_CLIENT --> QUERIES
    CLI_FMT --> DISPLAY
    
    classDef schemaStyle fill:#fff3e0,stroke:#ff6f00,stroke-width:2px
    classDef consumerStyle fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    classDef outputStyle fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    
    class YAML,REGISTRY,INTROSPECT,VALIDATE schemaStyle
    class CODEGEN_SYS,TRANSPILER,CACHE_SYS,API_CLIENT,CLI_FMT consumerStyle
    class MODELS,QUERIES,DB_SCHEMA,DISPLAY outputStyle
```

### Schema Workflow

1. **Definition**
   - Manual YAML authoring with field definitions
   - Or automatic introspection from remote tables
   - Includes field positions, types, constraints, relationships

2. **Validation**
   - Data-driven validation using pandas
   - Compares local schema with remote data samples
   - Produces match ratio metrics and type analysis

3. **Registration**
   - Loaded into schema registry at startup
   - Merged with configuration overrides
   - Available to all system components

4. **Code Generation**
   - Generates Pydantic/SQLModel classes
   - Includes validators, relationships, docstrings
   - Enables type-safe development

5. **Runtime Usage**
   - Field position → name mapping
   - Type conversion and validation
   - Query optimization (auto ORDER BY id)
   - SELECT * expansion to specific fields

### Schema Benefits

- **Type Safety**: Compile-time type checking via generated models
- **Consistency**: Single source of truth for field definitions
- **Automation**: Auto-generates boilerplate code
- **Validation**: Data-driven correctness verification
- **Documentation**: Self-documenting schemas with descriptions
- **Flexibility**: Override configurations per table/environment

---

## Sequence Diagrams

### Query Execution Flow

Complete flow from SQL query to formatted results, showing all layers and caching.

```mermaid
sequenceDiagram
    actor User
    participant CLI as CLI Interface
    participant SVC as Service Layer
    participant CACHE as Cache Manager
    participant TRANS as SQL Transpiler
    participant SCHEMA as Schema System
    participant PROXY as Core Client
    participant AUTH as Auth Manager
    participant RPC as Remote API
    participant DB as Remote Database
    
    User->>CLI: iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 5"
    CLI->>SVC: Execute query
    
    SVC->>CACHE: Check in-memory cache
    alt Cache Hit (L1)
        CACHE-->>SVC: Return cached results
        SVC-->>CLI: Format results
        CLI-->>User: Display table
    else Cache Miss
        SVC->>TRANS: Transpile SQL to JSONSQL
        TRANS->>SCHEMA: Resolve fields for SELECT *
        SCHEMA-->>TRANS: [id, username, email, disabled, balance, created_at]
        TRANS->>SCHEMA: Get field types
        SCHEMA-->>TRANS: Types and positions
        TRANS-->>SVC: JSONSQL with auto ORDER BY id
        
        SVC->>CACHE: Check SQLite cache (L2)
        alt SQLite Has Fresh Data
            CACHE-->>SVC: Return from SQLite
            SVC->>CACHE: Store in L1 cache
        else SQLite Stale/Missing
            SVC->>AUTH: Check session
            alt Session Valid
                AUTH-->>SVC: Session OK
            else Session Expired/Missing
                AUTH->>RPC: authorize_user
                RPC->>DB: Validate credentials
                DB-->>RPC: Session token
                RPC-->>AUTH: {session_id, expires_at}
                AUTH->>AUTH: Persist to session cache
                AUTH-->>SVC: Session ready
            end
            
            SVC->>PROXY: Execute JSONSQL query
            Note over PROXY: Add session header<br/>Apply retry logic<br/>Handle timeouts
            PROXY->>RPC: POST /json-rpc<br/>{method: "select", params: {...}}
            RPC->>DB: Execute JSONSQL
            DB-->>RPC: Raw rows (positional arrays)
            RPC-->>PROXY: {result: [[1, "user1", ...], ...]}
            
            PROXY->>SCHEMA: Map positions to field names
            SCHEMA-->>PROXY: [{id: 1, username: "user1", ...}, ...]
            PROXY-->>SVC: Mapped results
            
            SVC->>CACHE: Store in SQLite (L2)
            SVC->>CACHE: Store in memory (L1)
        end
        
        SVC->>SCHEMA: Get display formats
        SCHEMA-->>SVC: Column names and formatters
        SVC-->>CLI: Formatted results
        CLI-->>User: Display rich table
    end
```

### Cache Sync Lifecycle

Detailed sync workflow for SQLite cache with full/incremental strategies.

```mermaid
sequenceDiagram
    actor User
    participant CLI as CLI
    participant SYNC as Sync Manager
    participant DB as SQLite Cache
    participant META as Sync Metadata
    participant SCHEMA as Schema Registry
    participant CLIENT as Core Client
    participant RPC as Remote API
    
    User->>CLI: iptvportal sync run --table subscriber
    CLI->>SYNC: Initialize sync for table
    
    SYNC->>SCHEMA: Load table schema
    SCHEMA-->>SYNC: Schema with sync_config
    
    SYNC->>META: Get last sync metadata
    META-->>SYNC: {last_sync_at, row_count, strategy}
    
    alt First Sync or Force Full
        Note over SYNC: Strategy: Full Sync
        SYNC->>DB: BEGIN TRANSACTION
        SYNC->>DB: DELETE FROM subscriber
        
        loop Chunked fetch (e.g., 10k rows/chunk)
            SYNC->>CLIENT: SELECT * LIMIT 10000 OFFSET N
            CLIENT->>RPC: JSON-RPC select request
            RPC-->>CLIENT: Chunk of rows
            CLIENT->>SCHEMA: Map positions to fields
            SCHEMA-->>CLIENT: Named row dicts
            CLIENT-->>SYNC: Mapped chunk
            
            SYNC->>DB: INSERT INTO subscriber VALUES (...)
            Note over SYNC: Repeat until no more rows
        end
        
        SYNC->>META: UPDATE sync_metadata<br/>SET last_sync=NOW(), row_count=N
        SYNC->>DB: COMMIT TRANSACTION
        
    else Incremental Sync
        Note over SYNC: Strategy: Incremental<br/>Field: updated_at
        
        SYNC->>CLIENT: SELECT * WHERE updated_at > last_sync
        CLIENT->>RPC: JSON-RPC with WHERE clause
        RPC-->>CLIENT: Updated rows only
        CLIENT->>SCHEMA: Map positions to fields
        SCHEMA-->>CLIENT: Named row dicts
        CLIENT-->>SYNC: Updated records
        
        SYNC->>DB: BEGIN TRANSACTION
        loop For each updated record
            SYNC->>DB: INSERT OR REPLACE INTO subscriber<br/>VALUES (...)
        end
        SYNC->>META: UPDATE sync_metadata<br/>SET last_sync=NOW()
        SYNC->>DB: COMMIT TRANSACTION
        
    else On-Demand Sync
        Note over SYNC: Strategy: On-Demand<br/>Lazy load by ID
        Note over SYNC: Only fetches records<br/>when specifically requested
        SYNC->>DB: Skip bulk sync
    end
    
    SYNC->>DB: VACUUM (optional, periodic)
    SYNC-->>CLI: Sync complete: N rows
    CLI-->>User: Display sync summary with stats
```

### Authentication Lifecycle

Session management with auto-renewal and persistence.

```mermaid
sequenceDiagram
    actor User
    participant CLI as CLI
    participant AUTH as Auth Manager
    participant CACHE as Session Cache
    participant CONFIG as Configuration
    participant CLIENT as Core Client
    participant RPC as Auth Service
    
    User->>CLI: iptvportal jsonsql auth
    CLI->>AUTH: Authenticate user
    
    AUTH->>CACHE: Check existing session
    alt Session Exists and Valid
        CACHE-->>AUTH: {session_id, expires_at}
        AUTH->>AUTH: Check expiration
        alt Still Valid
            AUTH-->>CLI: Session already active
            CLI-->>User: Already authenticated
        else Expired
            Note over AUTH: Auto-renewal flow
            AUTH->>CONFIG: Get credentials
            CONFIG-->>AUTH: {username, password, domain}
            AUTH->>CLIENT: Request new session
            CLIENT->>RPC: POST authorize_user<br/>{username, password, domain}
            RPC-->>CLIENT: {session_id, expires_at}
            CLIENT-->>AUTH: New session token
            AUTH->>CACHE: Persist session
            AUTH-->>CLI: Re-authenticated
            CLI-->>User: Session renewed
        end
    else No Session
        AUTH->>CONFIG: Get credentials
        
        alt Credentials from Env Vars
            CONFIG-->>AUTH: Environment variables
        else Credentials from Config File
            CONFIG-->>AUTH: cli-config.yaml values
        else Interactive Prompt
            CLI->>User: Enter username
            User->>CLI: username
            CLI->>User: Enter password (hidden)
            User->>CLI: password
            CLI->>User: Enter domain
            User->>CLI: domain
            CLI-->>AUTH: User-provided credentials
        end
        
        AUTH->>CLIENT: Request session
        CLIENT->>RPC: POST authorize_user
        
        alt Authentication Success
            RPC-->>CLIENT: {session_id, expires_at, user_id}
            CLIENT-->>AUTH: Session token
            AUTH->>CACHE: Persist to ~/.iptvportal/session-cache
            AUTH-->>CLI: Authentication successful
            CLI-->>User: ✓ Authenticated (session expires in X hours)
        else Authentication Failed
            RPC-->>CLIENT: {error: "Invalid credentials"}
            CLIENT-->>AUTH: Error
            AUTH-->>CLI: Auth failed
            CLI-->>User: ✗ Authentication failed: Invalid credentials
        end
    end
    
    Note over AUTH,RPC: Subsequent API calls<br/>include header:<br/>Iptvportal-Authorization: sessionid={sid}
    
    alt Session Expires During Operation
        CLIENT->>RPC: API request with expired session
        RPC-->>CLIENT: 401 Unauthorized
        CLIENT->>AUTH: Session expired
        AUTH->>AUTH: Auto-renewal attempt
        AUTH->>RPC: Re-authenticate
        RPC-->>AUTH: New session
        AUTH->>CACHE: Update session
        CLIENT->>RPC: Retry original request with new session
        RPC-->>CLIENT: Success
    end
```

---

## High-Level Component Architecture

This is the original high-level architecture diagram, now in context with the detailed system views above.

```mermaid
flowchart LR
  subgraph CLI["iptvportal CLI (Typer)"]
    CMD["Commands:\n- auth\n- sql\n- jsonsql\n- transpile\n- config\n- sync"]
  end

  subgraph Core["Core Library"]
    AUTH["auth.py\n(session mgmt)"]
    CLIENT["client.py / async_client.py\n(httpx JSON-RPC)"]
    TRANS["transpiler/\n(SQL → JSONSQL)"]
    SCHEMA["schema.py\n(mapping, validation)"]
    SYNC["sync/\n(SQLite cache: database.py)"]
  end

  subgraph Server["IPTVPortal"]
    RPC["JSON-RPC endpoint\n(JSONSQL DML)"]
  end

  CMD --> AUTH
  CMD --> TRANS
  CMD --> CLIENT
  CMD --> SCHEMA
  CMD --> SYNC
  CLIENT <--> RPC
  CLIENT <--> SYNC

  SCHEMA -. maps .-> TRANS
  SCHEMA -. maps .-> SYNC
```

## CLI SELECT call flow

```mermaid
sequenceDiagram
  participant U as User
  participant CLI as iptvportal (Typer)
  participant TRANS as SQLTranspiler
  participant SCHEMA as schema.py
  participant CLIENT as client.py (httpx)
  participant RPC as IPTVPortal JSON-RPC

  U->>CLI: iptvportal sql -q "SELECT id, username FROM subscriber LIMIT 5"
  CLI->>TRANS: transpile(SQL, auto_order_by_id=True)
  TRANS->>SCHEMA: resolve fields, mapping, types
  SCHEMA-->>TRANS: field positions, types, order_by="id"
  TRANS-->>CLI: JSONSQL payload
  alt --dry-run
    CLI-->>U: Print JSONSQL + request (no network)
  else execute
    CLI->>CLIENT: send JSON-RPC request (w/ session header)
    CLIENT->>RPC: POST /json-rpc {method:"select", params:{...}}
    RPC-->>CLIENT: rows (positional arrays)
    CLIENT->>SCHEMA: map positions → named fields
    SCHEMA-->>CLIENT: mapped rows
    CLIENT-->>CLI: result set
    CLI-->>U: formatted output
  end
```

## Sync/cache dataflow

```mermaid
sequenceDiagram
  participant SYNC as SyncDatabase (SQLite)
  participant CLIENT as client.py
  participant SCHEMA as TableSchema
  participant DB as SQLite

  CLIENT->>SYNC: bulk_insert(table, rows, schema)
  SYNC->>DB: BEGIN
  SYNC->>DB: CREATE TABLE IF NOT EXISTS <table> (...)
  SYNC->>DB: INSERT OR [REPLACE|IGNORE] ... VALUES (...)
  SYNC->>DB: UPDATE _sync_metadata (row_count, last_sync_at, etc.)
  SYNC->>DB: COMMIT
```

## Auth/session lifecycle

```mermaid
sequenceDiagram
  participant CLI as iptvportal
  participant AUTH as auth.py
  participant CLIENT as client.py
  participant RPC as IPTVPortal

  CLI->>AUTH: authorize_user (login/renew)
  AUTH->>CLIENT: request JSON-RPC authorize_user
  CLIENT->>RPC: POST authorize_user
  RPC-->>CLIENT: {session_id, expires_at}
  CLIENT-->>AUTH: store session
  AUTH-->>CLI: session ready
  Note over CLIENT: Subsequent calls include header:\nIptvportal-Authorization: sessionid={sid}
```

## ER diagram (examples schema)

```mermaid
erDiagram
  SUBSCRIBER ||--o{ TERMINAL : "has many"
  SUBSCRIBER {
    int id PK
    string username
    string email
    bool disabled
    float balance
    datetime created_at
  }
  TERMINAL {
    int id PK
    int subscriber_id FK
    string mac_addr
    bool active
    datetime last_seen
  }
  PACKAGE {
    int id PK
    string name
    float price
  }
```

---

## Architecture Narrative

### Design Philosophy

The iptvportal-client is designed around three core principles:

1. **Proxy-Centric Design**: A smart intermediary layer that abstracts complexity, provides caching, and ensures resilient communication
2. **Schema-Driven Everything**: Single source of truth for field definitions that drives code generation, validation, and runtime behavior
3. **Configuration Over Convention**: Hierarchical, environment-aware configuration that adapts to different deployment scenarios

### The Proxy Layer: Heart of the Architecture

The proxy/core layer is the central nervous system of the application. It sits between user-facing interfaces (CLI, Python API) and the remote IPTVPortal API, providing:

**Protocol Translation**: Users can write SQL queries, which are automatically transpiled to JSONSQL. The transpiler is schema-aware, performing SELECT * expansion, auto-adding ORDER BY id for consistency, and ensuring field positions match the schema registry.

**Multi-Level Caching**: Three caching tiers work together:
- **In-memory**: Ultra-fast repeated queries (seconds-level TTL)
- **SQLite**: Persistent local mirror with full SQL capabilities (minutes-level TTL)
- **Remote API**: Source of truth accessed only on cache misses

This design provides:
- Sub-millisecond query response for cached data
- Offline query capability via SQLite
- Reduced load on remote API
- Rich local query support (JOINs, aggregates) impossible in JSONSQL

**Schema Resolution**: Every query passes through the schema system, which:
- Maps field positions to human-readable names
- Applies type conversions (e.g., string to datetime)
- Validates field access
- Enables SELECT * by expanding to actual field list

**Resilience**: The proxy implements retry logic with exponential backoff, timeout management, and detailed error context. Transient failures are automatically recovered.

**Authentication**: Session management is transparent - tokens are cached, auto-renewed before expiration, and re-established on failure. Users authenticate once; the system handles the rest.

### Schema-Driven Architecture

Schemas are not just metadata - they are executable specifications that drive the entire system:

**Code Generation**: From a single YAML schema, the system generates:
- Pydantic models for validation
- SQLModel ORM classes for database access
- Type annotations for IDE autocomplete
- Docstrings for documentation

**Runtime Behavior**: Schemas control:
- How queries are transpiled (field positions, types)
- How results are formatted (column names, pretty-printing)
- How data is cached (table DDL, indexes, sync strategies)
- How validation occurs (type checking, constraint enforcement)

**Data-Driven Validation**: The system can validate schemas against live data:
- Fetch sample rows from remote API
- Compare local field definitions with actual data
- Calculate match ratios using pandas
- Identify type mismatches and missing fields

This approach ensures schemas stay accurate as the remote API evolves.

### Configuration-Driven Behavior

Configuration is hierarchical and composable:

```
Global defaults (config/settings.yaml)
  ↓
Service-level overrides (cache, schema, sync)
  ↓
Table-specific overrides (subscriber, terminal, etc.)
  ↓
Environment variables (IPTVPORTAL_*)
  ↓
Runtime flags (--timeout, --no-cache)
```

Each level can override the previous, enabling:
- **Development**: Quick config changes via environment variables
- **Production**: Locked-down configuration files
- **Testing**: Override everything via runtime flags
- **Multi-tenant**: Different configs per table/service

### Service-Oriented CLI

The CLI uses automatic service discovery:
- Each package with `__cli__.py` becomes a CLI service
- Services can have nested subcommands
- Configuration is hierarchical (global and per-service)
- No manual registration needed - just create the file

This design enables:
- Independent service development
- Consistent command structure
- Easy extension without modifying core code
- Self-documenting help text

### Sync System: Local Mirror Strategy

The SQLite sync system is designed for:
- **Performance**: Local JOINs and aggregates impossible in JSONSQL
- **Offline**: Continue working when API is unavailable
- **Efficiency**: Three sync strategies (full, incremental, on-demand) optimize for different table characteristics

Sync strategies are configurable per table:
- **Full Sync**: Small or frequently-changing tables (e.g., active sessions)
- **Incremental**: Large tables with `updated_at` field (e.g., subscribers)
- **On-Demand**: Sparse access patterns (e.g., lookup by specific ID)

Metadata tracking enables smart sync:
- Last sync timestamp
- Row counts (detect deletions)
- Sync duration (performance monitoring)
- Schema hash (detect schema changes)

### Error Handling Philosophy

Errors are handled at multiple levels:

1. **Client Level**: Network errors, timeouts, rate limiting
2. **Proxy Level**: Session expiration, auth failures, retry exhaustion
3. **Schema Level**: Field resolution errors, type mismatches
4. **Service Level**: Business logic errors, validation failures

Each level provides context for the next, building detailed error messages that help users diagnose issues.

### Performance Characteristics

The architecture is designed for performance:

- **In-memory cache**: < 1ms query time
- **SQLite cache**: 1-10ms for complex queries with JOINs
- **Remote API**: 100-500ms (network + database)

Cache hit rates typically exceed 90% for read-heavy workloads, providing 100x+ speedup.

### Extension Points

The architecture is designed for extension:

1. **Custom Transformers**: Add field transformers in schema system
2. **New Services**: Create `__cli__.py` in any package
3. **Cache Strategies**: Implement new sync strategies in sync manager
4. **Query Builders**: Extend Field API with custom operators
5. **Formatters**: Add new output formats in CLI formatters

### Trade-offs and Limitations

**Complexity vs. Capability**: The multi-layer architecture adds complexity but provides powerful capabilities (caching, offline, type safety) that justify the cost.

**Memory Usage**: In-memory caching trades memory for speed. Configurable TTL and LRU eviction prevent unbounded growth.

**Sync Latency**: SQLite cache may serve stale data between syncs. TTL configuration balances freshness vs. performance.

**Schema Maintenance**: Schemas must be kept in sync with remote API. Introspection and validation tools minimize manual effort.

### Future Evolution

The architecture supports future enhancements:

- **Distributed Caching**: Redis/Memcached for shared cache across processes
- **Change Streams**: Real-time sync using database change feeds
- **GraphQL Layer**: Alternative query interface over JSONSQL
- **Smart Prefetching**: ML-based prediction of needed data
- **Multi-Master Sync**: Bidirectional sync with conflict resolution

---

## Notes for Maintainers

### Documentation Alignment

- Keep diagrams aligned with CLI surface in `docs/cli.md` and schema rules in `docs/schema-driven.md`.
- When changing schema mapping behavior or transpiler output shapes, update both the sequence diagrams and the ER diagram samples.
- If sync metadata tables or views change, update the dataflow diagram and list of metadata objects.
- Update architecture narrative when adding new layers, components, or design patterns.

### Diagram Maintenance

- All diagrams use Mermaid and must render correctly on GitHub.
- Test diagrams in GitHub's markdown preview or Mermaid Live Editor.
- Use consistent styling (colors, line styles) across related diagrams.
- Keep diagram complexity manageable - split into multiple diagrams if needed.

### Architecture Evolution

When making architectural changes:

1. **Document First**: Update this document before implementing major changes
2. **Diagram Impact**: Identify which diagrams need updates
3. **Backward Compatibility**: Document breaking changes clearly
4. **Migration Path**: Provide upgrade guidance for users
5. **Performance Impact**: Measure before/after performance characteristics

### Component Boundaries

Respect these architectural boundaries:

- **CLI ↔ Service Layer**: CLI only calls service layer, never client directly
- **Service ↔ Proxy**: Service orchestrates, proxy executes
- **Proxy ↔ Schema**: All field resolution goes through schema system
- **Proxy ↔ Cache**: All caching goes through cache manager
- **Proxy ↔ Remote**: All remote calls go through proxy with auth/retry

### Testing Strategy

Test at appropriate architectural levels:

- **Unit Tests**: Individual components (transpiler, schema system, cache manager)
- **Integration Tests**: Layer interactions (proxy + schema, service + cache)
- **End-to-End Tests**: Full flow (CLI command → remote API → formatted output)
- **Performance Tests**: Cache hit rates, query latency, sync duration

### Security Considerations

- Never log session tokens or credentials
- Session cache must have restricted permissions (600)
- Configuration files may contain secrets - exclude from version control
- Validate all inputs at service layer before passing to proxy
- Use parameterized queries in SQLite to prevent injection

### Performance Monitoring

Key metrics to track:

- Cache hit rates (L1, L2)
- Average query latency (cached vs. uncached)
- Sync duration and row counts
- Session renewal frequency
- Retry rates and timeout frequency

### Common Pitfalls

1. **Bypassing Proxy**: Don't call remote API directly - always go through proxy
2. **Ignoring Schema**: Don't hardcode field positions - use schema resolution
3. **Cache Coherence**: Remember SQLite cache may be stale - sync strategy matters
4. **Session Management**: Let auth manager handle sessions - don't manage manually
5. **Configuration Override**: Respect hierarchy - higher levels override lower

### Debugging Tips

- Enable debug mode: `iptvportal --debug ...`
- Use dry-run mode: `iptvportal jsonsql sql -q "..." --dry-run`
- Check cache status: `iptvportal cache status`
- Inspect sync metadata: `iptvportal sync status --table X`
- View configuration: `iptvportal config show`
- Test schema validation: `iptvportal schema validate-mapping X ...`

### Related Documentation

- [CLI Architecture](cli-architecture.md) - Service-oriented CLI design
- [SQLite Proxy Architecture](sqlite-proxy-architecture.md) - Detailed proxy layer design
- [Schema-Driven Development](schema-driven.md) - Schema system deep dive
- [Configuration Guide](configuration.md) - Hierarchical configuration details
- [Sync Workflow](sync-workflow.md) - Sync strategies and best practices
