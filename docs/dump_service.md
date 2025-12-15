# Incremental Dump Service

Lightweight async service for bulk table exports with **resumable state**, **progress tracking**, and **multiple output formats**.

## Features

- **Incremental Dumps** - Export large tables in configurable chunks (default 5000 rows)
- **Resumable State** - Automatic checkpoint saving with resume capability
- **Multiple Formats** - JSONL, Parquet, CSV, JSON with optional compression
- **Progress Tracking** - Real-time stats: rows/sec, ETA, completion %
- **Pause/Resume** - Control dump operations on-the-fly
- **Traversal Strategies** - OFFSET (standard) or ID_RANGE (faster for large tables)
- **Concurrent Dumps** - Dump multiple tables in parallel
- **Async/Await** - Full async support with minimal dependencies

## Quick Start

### Basic Single-Table Dump

```python
from pathlib import Path
from iptvportal import AsyncIPTVPortalClient
from iptvportal.dump import DumpConfig, DumpFormat, DumpService

async with AsyncIPTVPortalClient() as client:
    config = DumpConfig(
        table="tv_channel",
        output_dir=Path("./dumps"),
        format=DumpFormat.JSONL,  # or CSV, Parquet, JSON
        chunk_size=5000,
    )
    
    service = DumpService(client)
    stats = await service.dump(config)
    
    print(f"Dumped {stats.progress.dumped_rows} rows")
    print(f"Output: {config.output_dir}/tv_channel.jsonl")
```

### Multiple Tables Concurrently

```python
configs = [
    DumpConfig(table="tv_channel", output_dir=Path("./dumps")),
    DumpConfig(table="tv_program", output_dir=Path("./dumps")),
    DumpConfig(table="media", output_dir=Path("./dumps")),
]

async with AsyncIPTVPortalClient() as client:
    service = DumpService(client)
    all_stats = await service.dump_many(configs, max_concurrent=2)
    
    for stats in all_stats:
        print(f"{stats.config.table}: {stats.progress.dumped_rows} rows")
```

### Progress Tracking

```python
def progress_callback(progress):
    pct = progress.percent_complete()
    eta = progress.eta_seconds()
    print(f"{pct:.1f}% complete | ETA: {eta:.0f}s")

stats = await service.dump(config, progress_callback=progress_callback)
```

## Configuration

### DumpConfig Options

```python
from iptvportal.dump import DumpConfig, DumpFormat, DumpStrategy

config = DumpConfig(
    # Required
    table="tv_channel",
    output_dir=Path("./dumps"),
    
    # Traversal
    chunk_size=5000,              # Rows per API call
    strategy=DumpStrategy.OFFSET, # or ID_RANGE
    
    # Output
    format=DumpFormat.JSONL,      # JSONL, CSV, Parquet, JSON
    compress=False,               # gzip compression (JSONL/JSON)
    
    # Resume
    resume=True,                  # Auto-resume from last checkpoint
    resume_offset=0,              # Override last offset (optional)
    
    # Filtering
    order_by="id ASC",            # Sort order
    where_clause=None,            # JSONSQL where condition
    
    # Performance
    batch_timeout=30.0,           # HTTP timeout per batch
    max_retries=3,                # Retry failed chunks
    retry_backoff=1.5,            # Exponential backoff multiplier
    
    # Concurrency (for ID_RANGE strategy)
    max_parallel=3,               # Parallel chunks
)
```

## Traversal Strategies

### OFFSET Strategy (Default)

Uses `OFFSET/LIMIT` for pagination.

**Pros:**
- Standard SQL, works with any table
- Simple, reliable
- Good for small-medium tables (<1M rows)

**Cons:**
- Slower for large tables (OFFSET scans all skipped rows)
- Must count total rows upfront

```python
config = DumpConfig(
    table="tv_channel",
    strategy=DumpStrategy.OFFSET,
    chunk_size=5000,
)
```

### ID_RANGE Strategy (Faster)

Uses `id > last_id` instead of OFFSET.

**Pros:**
- Much faster for large tables (index-backed)
- No full count needed
- Parallelizable per ID range
- Ideal for **100k+ row tables**

**Cons:**
- Requires numeric primary key named `id`
- Assumes monotonically increasing IDs

```python
config = DumpConfig(
    table="terminal",          # Must have numeric 'id' column
    strategy=DumpStrategy.ID_RANGE,
    chunk_size=5000,
)
```

**Performance Comparison:**
```
Table: terminal (500k rows)

OFFSET:   ~45 seconds (8500 rows/sec)
ID_RANGE: ~15 seconds (33k rows/sec) ← 3x faster
```

## Output Formats

### JSONL (Recommended for streaming)

Line-delimited JSON, one row per line.

**File:** `table_name.jsonl`

**Pros:**
- Streaming-friendly (can start processing before dump completes)
- Text-based, human-readable
- Easy line-by-line processing
- Supports compression (gzip)

**Cons:**
- Not columnar (slower for analytics)
- Slightly larger than Parquet

```python
config = DumpConfig(
    table="tv_channel",
    format=DumpFormat.JSONL,
    compress=True,  # Optional: tv_channel.jsonl.gz
)
```

**Usage:**
```python
import json

with open("dumps/tv_channel.jsonl") as f:
    for line in f:
        row = json.loads(line)
        process(row)
```

### CSV (For Excel/data tools)

Standard CSV with header row.

**File:** `table_name.csv` (one per chunk if large)

**Pros:**
- Universal format (Excel, Pandas, R)
- Human-readable
- Good for tabular data

**Cons:**
- Type information lost
- No native nested data support

```python
config = DumpConfig(
    table="subscriber",
    format=DumpFormat.CSV,
)
```

**Usage:**
```python
import pandas as pd

df = pd.read_csv("dumps/subscriber.csv")
print(df.describe())
```

### Parquet (For analytics/BI)

Apache Parquet columnar format.

**File:** `table_name-00000.parquet` (chunked)

**Pros:**
- Columnar (fast aggregations, analytics)
- Highly compressed
- Type-preserving
- Direct Pandas/DuckDB support

**Cons:**
- Requires pyarrow or pandas
- Not text-readable

```python
config = DumpConfig(
    table="media",
    format=DumpFormat.PARQUET,
    chunk_size=10000,  # Larger chunks for Parquet efficiency
)
```

**Usage:**
```python
import pandas as pd
import duckdb

# Via Pandas
df = pd.read_parquet("dumps/media-00000.parquet")

# Via DuckDB (recommended for large files)
result = duckdb.query(
    "SELECT COUNT(*) FROM read_parquet('dumps/media-*.parquet')"
).fetchall()
```

### JSON (Full array)

Single JSON array file.

**File:** `table_name.json` (or `.json.gz`)

**Pros:**
- Standard format
- Pretty-printable
- Single file

**Cons:**
- Must load entire array into memory
- Not streaming-friendly
- Larger file size

```python
config = DumpConfig(
    table="package",
    format=DumpFormat.JSON,
    compress=True,
)
```

## Resume & State Management

### Automatic Resume

Dump state is saved after each chunk to `.{table}.state.json`:

```json
{
  "table": "tv_channel",
  "dumped_rows": 25000,
  "current_offset": 25000,
  "chunks_completed": 5,
  "started_at": "2025-12-15T20:30:00",
  "last_updated_at": "2025-12-15T20:31:30",
  "is_complete": false
}
```

On next run with `resume=True`, dump continues from last offset:

```python
config = DumpConfig(
    table="tv_channel",
    output_dir=Path("./dumps"),
    resume=True,  # Loads .tv_channel.state.json
)

# Continues from offset 25000, not 0
stats = await service.dump(config)
```

### Reset State

To start over:

```python
manager = AsyncDumpManager(client, config)
manager.reset()  # Delete state file, reset progress
```

Or override resume offset:

```python
config = DumpConfig(
    table="tv_channel",
    resume_offset=50000,  # Start from row 50000
)
```

## Pause/Resume Operations

Control dumps on-the-fly:

```python
async with AsyncIPTVPortalClient() as client:
    service = DumpService(client)
    
    # Start dump
    dump_task = asyncio.create_task(service.dump(config))
    await asyncio.sleep(5)
    
    # Pause
    service.pause("tv_channel")
    print("Paused. Current progress:", service.get_stats("tv_channel").progress)
    
    await asyncio.sleep(10)  # Do something else
    
    # Resume
    service.resume("tv_channel")
    
    # Wait for completion
    stats = await dump_task
```

State is automatically saved during pause for resilience.

## Progress Tracking

### DumpProgress API

```python
progress = manager.progress

# Counts
print(progress.dumped_rows)         # 25000
print(progress.total_rows)          # 100000
print(progress.chunks_completed)    # 5

# Metrics
print(progress.percent_complete())  # 25.0
print(progress.rows_per_second())   # 8500
print(progress.elapsed_seconds())   # 2.9
print(progress.eta_seconds())       # 8.8

# Timestamps
print(progress.started_at)          # 2025-12-15 20:30:00
print(progress.completed_at)        # None (if running)
```

### Real-time Callback

```python
def progress_cb(progress):
    pct = progress.percent_complete()
    throughput = progress.rows_per_second()
    eta = progress.eta_seconds()
    
    print(f"\r{pct:5.1f}% | {throughput:6.0f} rows/s | ETA {eta:5.0f}s", end="")

stats = await service.dump(config, progress_callback=progress_cb)
```

## Filtering & WHERE Conditions

### Filter by Condition

```python
from iptvportal import Q

# Using Q objects
where = Q(disabled=False) & Q(balance__gte=10)

config = DumpConfig(
    table="subscriber",
    where_clause=where,
)

# Only exports active subscribers with balance >= 10
stats = await service.dump(config)
```

### Custom Ordering

```python
config = DumpConfig(
    table="terminal",
    order_by="last_seen DESC",  # Order by timestamp
)
```

## Concurrency & Performance

### Dump Multiple Tables

```python
configs = [
    DumpConfig(table="tv_channel", output_dir=Path("./dumps")),
    DumpConfig(table="tv_program", output_dir=Path("./dumps")),
    DumpConfig(table="media", output_dir=Path("./dumps")),
    DumpConfig(table="subscriber", output_dir=Path("./dumps")),
]

stats_list = await service.dump_many(
    configs,
    max_concurrent=2,  # 2 tables in parallel
)

for stats in stats_list:
    print(f"{stats.config.table}: {stats.progress.dumped_rows} rows")
```

### Tuning Chunk Size

```python
# Small tables or fast API
config = DumpConfig(chunk_size=10000)  # Fewer, larger chunks

# Large tables or slow network
config = DumpConfig(chunk_size=1000)   # More, smaller chunks
```

**Recommendation:** Start with 5000, adjust based on:
- API timeout: Increase chunk_size if timeouts occur
- Memory: Decrease chunk_size if memory-constrained
- Throughput: 5000-10000 usually optimal

## Error Handling

### Automatic Retries

```python
config = DumpConfig(
    table="tv_channel",
    max_retries=3,       # Retry failed chunks
    retry_backoff=1.5,   # Exponential backoff: 1.5^n seconds
    batch_timeout=30.0,  # HTTP timeout per batch
)
```

Retry delays: 1.5s → 2.25s → 3.375s

### Exception Handling

```python
try:
    stats = await service.dump(config)
except Exception as e:
    print(f"Dump failed: {e}")
    print(f"Last successful offset: {service.get_stats(config.table).progress.current_offset}")
    # State is saved, can resume later
```

## Use Cases

### 1. Daily Analytics Export

```python
# Export all tables to Parquet for BI tool
configs = [
    DumpConfig(table=t, format=DumpFormat.PARQUET)
    for t in ["subscriber", "terminal", "media", "tv_program"]
]

await service.dump_many(configs, max_concurrent=2)
# → Load into DuckDB, create daily snapshots
```

### 2. Incremental Data Sync

```python
# Sync only new/updated rows using ID_RANGE
config = DumpConfig(
    table="terminal",
    strategy=DumpStrategy.ID_RANGE,
    where_clause=Q(last_seen__gte="2025-12-15"),
    chunk_size=10000,
)

await service.dump(config)
# → Much faster than full export
```

### 3. Database Migration

```python
# Export all tables to JSONL for import into different DB
for table in ["tv_channel", "tv_program", "subscriber"]:
    config = DumpConfig(
        table=table,
        format=DumpFormat.JSONL,
        resume=True,  # Resume if interrupted
    )
    await service.dump(config)
# → Reliable, resumable export
```

### 4. Data Science Workflows

```python
# Export to Parquet, analyze with Pandas
config = DumpConfig(
    table="media",
    format=DumpFormat.PARQUET,
    chunk_size=50000,  # Large chunks for efficiency
)

await service.dump(config)

# Now analyze
import pandas as pd
df = pd.read_parquet("dumps/media-*.parquet")
print(df.groupby("type").size())
```

## Troubleshooting

### Slow Dumps

**Problem:** Dump is very slow (< 1000 rows/sec)

**Solutions:**
1. Try ID_RANGE strategy: `strategy=DumpStrategy.ID_RANGE`
2. Increase chunk_size: `chunk_size=10000`
3. Increase max_retries: `max_retries=1` (reduce overhead)
4. Check API latency: `--debug` flag

### Memory Issues

**Problem:** High memory usage during dump

**Solutions:**
1. Reduce chunk_size: `chunk_size=1000`
2. Use JSONL format (streaming): `format=DumpFormat.JSONL`
3. Process output files as they're written

### Timeout Errors

**Problem:** `TimeoutError: Request timeout`

**Solutions:**
1. Increase timeout: `batch_timeout=60.0`
2. Reduce chunk_size: `chunk_size=2000`
3. Check network: May need to increase retries

### Resume Not Working

**Problem:** Dump always starts from beginning

**Solutions:**
1. Ensure `resume=True`
2. Check state file exists: `.{table}.state.json`
3. Override with: `resume_offset=25000`

## API Reference

See docstrings for detailed parameter documentation:

```python
from iptvportal.dump import (
    DumpConfig,      # Configuration
    DumpFormat,      # Output formats
    DumpStrategy,    # Traversal strategies
    DumpService,     # High-level service
    AsyncDumpManager, # Low-level manager
    DumpProgress,    # Progress tracking
    DumpStats,       # Aggregated stats
)
```

## Examples

See `examples/dump_service_example.py` for full working examples:

- Single-table dump
- Multi-table concurrent dumps
- Different output formats
- ID_RANGE strategy
- Pause/resume operations

---

**Next Steps:**
- Start with basic JSONL dump: `DumpFormat.JSONL`
- Use ID_RANGE for large tables: `DumpStrategy.ID_RANGE`
- Set up automated exports with cron/APScheduler
- Integrate with data warehouse (ClickHouse, DuckDB, etc.)
