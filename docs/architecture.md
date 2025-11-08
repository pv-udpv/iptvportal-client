# Architecture and Data Flows

This document consolidates the diagrams that appear in the root `README.md` with a bit more detail for future maintainers. All diagrams use Mermaid and render natively on GitHub.

## High-level architecture

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

## Notes for maintainers

- Keep diagrams aligned with CLI surface in `docs/cli.md` and schema rules in `docs/schema-driven.md`.
- When changing schema mapping behavior or transpiler output shapes, update both the sequence diagrams and the ER diagram samples.
- If sync metadata tables or views change, update the dataflow diagram and list of metadata objects.
