# Schema Introspect with Sync - Workflow Diagram

## Command Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│  iptvportal schema introspect tv_channel --sync --analyze-from-cache│
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 1: INTROSPECTION                                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. Connect to remote IPTVPORTAL server                             │
│  2. Execute: SELECT * FROM tv_channel LIMIT 1                       │
│  3. Detect fields:                                                  │
│     - Position 0 → id (integer)                                     │
│     - Position 1 → name (string)                                    │
│     - Position 2 → enabled (boolean)                                │
│     - ...                                                           │
│  4. Execute: SELECT COUNT(*) FROM tv_channel                        │
│     Result: 1,234 rows                                              │
│  5. Execute: SELECT MAX(id), MIN(id) FROM tv_channel                │
│     Result: max=1234, min=1                                         │
│  6. Analyze timestamp fields (if any)                               │
│  7. Generate smart sync configuration:                              │
│     - chunk_size: 5000 (based on row count)                         │
│     - cache_strategy: full                                          │
│     - auto_sync: true                                               │
│                                                                      │
│  ✓ Schema generated with metadata                                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 2: SYNC (--sync flag enabled)                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. Initialize SQLite cache: ~/.iptvportal/cache.db                 │
│  2. Register schema in SchemaRegistry                               │
│  3. Create table in local cache with schema                         │
│  4. Start sync with SyncManager:                                    │
│                                                                      │
│     Chunk 1: SELECT * FROM tv_channel ORDER BY id LIMIT 5000        │
│     ┌─────────────────────────────────────────┐                    │
│     │ Progress: 1/1 chunks, 1,234 rows, 2.3s │                    │
│     └─────────────────────────────────────────┘                    │
│                                                                      │
│     → Insert into local cache                                       │
│     → Update _sync_metadata                                         │
│                                                                      │
│  ✓ Sync complete: 1,234 rows cached                                │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 3: ANALYSIS (--analyze-from-cache enabled)                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. Fetch data from local cache:                                    │
│     SELECT id, name, enabled, ... FROM tv_channel LIMIT 1000        │
│                                                                      │
│  2. Run DuckDB analysis on cached data:                             │
│     ┌──────────────────────────────────────┐                       │
│     │ Field: id                            │                       │
│     │   Type: BIGINT                       │                       │
│     │   Null %: 0.00%                      │                       │
│     │   Unique: 1,234 (100% cardinality)   │                       │
│     │   Range: [1 .. 1234]                 │                       │
│     └──────────────────────────────────────┘                       │
│     ┌──────────────────────────────────────┐                       │
│     │ Field: name                          │                       │
│     │   Type: VARCHAR                      │                       │
│     │   Null %: 0.00%                      │                       │
│     │   Unique: 1,234 (100% cardinality)   │                       │
│     │   Length: [3 .. 45]                  │                       │
│     └──────────────────────────────────────┘                       │
│     ┌──────────────────────────────────────┐                       │
│     │ Field: enabled                       │                       │
│     │   Type: BOOLEAN                      │                       │
│     │   Unique: 2 (0.16% cardinality)      │                       │
│     │   Top Values:                        │                       │
│     │     • true: 1150                     │                       │
│     │     • false: 84                      │                       │
│     └──────────────────────────────────────┘                       │
│                                                                      │
│  ✓ Analysis complete                                                │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ RESULT: Complete Schema with Sync & Analysis                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  • Schema registered in memory                                      │
│  • Data cached locally (1,234 rows)                                 │
│  • Statistical analysis complete                                    │
│  • Ready for offline queries                                        │
│  • Optional: saved to file (if --save used)                         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
┌──────────────┐
│ Remote       │
│ IPTVPORTAL   │
│ Server       │
└──────┬───────┘
       │
       │ 1. Introspect
       │    (metadata queries)
       │
       ▼
┌──────────────┐
│ Schema       │
│ Introspector │
└──────┬───────┘
       │
       │ 2. Generate schema
       │    + sync config
       │
       ▼
┌──────────────┐       ┌──────────────┐
│ Schema       │──────▶│ Sync         │
│ Registry     │       │ Manager      │
└──────────────┘       └──────┬───────┘
                              │
                              │ 3. Sync data
                              │    (chunked)
                              │
                              ▼
                       ┌──────────────┐
                       │ Local        │
                       │ SQLite       │
                       │ Cache        │
                       └──────┬───────┘
                              │
                              │ 4. Fetch for analysis
                              │
                              ▼
                       ┌──────────────┐
                       │ DuckDB       │
                       │ Analyzer     │
                       └──────┬───────┘
                              │
                              │ 5. Results
                              │
                              ▼
                       ┌──────────────┐
                       │ Console      │
                       │ Output       │
                       └──────────────┘
```

## Comparison: Before vs After

### Before (Multiple Steps)
```
Step 1: Introspect
  $ iptvportal schema introspect tv_channel --save
  ✓ Schema generated and saved

Step 2: Setup Sync (manual config)
  $ vim config/tv_channel-sync.yaml
  # Edit sync configuration...

Step 3: Initialize Cache
  $ iptvportal sync init

Step 4: Register Schema
  $ iptvportal sync register --file config/tv_channel-schema.yaml

Step 5: Perform Sync
  $ iptvportal sync run tv_channel

Step 6: Analyze (manual queries)
  $ iptvportal sql -q "SELECT COUNT(*) FROM tv_channel"
  $ iptvportal sql -q "SELECT COUNT(DISTINCT name) FROM tv_channel"
  # More manual queries...

Total: 6+ manual steps
```

### After (Single Command)
```
$ iptvportal schema introspect tv_channel --sync --analyze-from-cache --save

✓ Introspection complete
✓ Sync complete: 1,234 rows
✓ Analysis complete
✓ Schema saved

Total: 1 command, automatic
```

## Options Impact

| Option | What It Does | When to Use |
|--------|-------------|-------------|
| *none* | Basic introspection | Quick check, development |
| `--sync` | + Sync to cache | Need offline access |
| `--analyze-from-cache` | + Analyze full dataset | Production validation |
| `--sync-chunk=N` | Custom chunk size | Large tables, performance tuning |
| `--order-by-fields=X` | Custom sort order | Non-standard tables |
| `--sync-run-timeout=N` | Set timeout | Long-running syncs |
| `--save` | Save schema file | Version control, sharing |

## Performance Characteristics

```
Command Complexity vs Time:

Basic:
[▓▓░░░░░░░░] 5s
  └─ Introspect only

--sync:
[▓▓▓▓▓▓░░░░] 30s
  └─ Introspect + Sync

--sync --analyze-from-cache:
[▓▓▓▓▓▓▓▓░░] 45s
  └─ Introspect + Sync + Full Analysis

Performance scales with:
  • Row count
  • Field count
  • Network latency
  • Disk I/O speed
```

## Error Handling Flow

```
┌─────────────────┐
│ User Command    │
└────────┬────────┘
         │
         ▼
    ┌────────┐
    │ Validate│
    │ Options │
    └────┬───┘
         │
         ├─ Invalid? ──▶ Show error + help
         │
         ▼
    ┌────────┐
    │Introspect│
    └────┬───┘
         │
         ├─ Empty table? ──▶ Error: "Table empty"
         ├─ No access? ────▶ Error: "Permission denied"
         │
         ▼
    ┌────────┐
    │  Sync  │ (if --sync)
    └────┬───┘
         │
         ├─ Timeout? ──▶ Warning: "Partial sync"
         ├─ Error? ────▶ Error + rollback
         │
         ▼
    ┌────────┐
    │ Analyze│ (if --analyze-from-cache)
    └────┬───┘
         │
         ├─ DuckDB missing? ──▶ Warning: "Install DuckDB"
         ├─ Error? ──────────▶ Warning + continue
         │
         ▼
    ┌────────┐
    │ Success│
    └────────┘
```
