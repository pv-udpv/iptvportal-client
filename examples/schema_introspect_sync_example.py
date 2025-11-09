#!/usr/bin/env python3
"""
Example: Schema Introspection with Sync Integration

This example demonstrates the enhanced schema introspect command with sync capabilities.

Prerequisites:
    - Valid IPTVPortal credentials configured
    - DuckDB installed for analysis (optional): pip install duckdb pandas

Usage:
    python examples/schema_introspect_sync_example.py
"""

import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def example_basic_introspect():
    """Basic introspection without sync."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Basic Introspection (No Sync)")
    print("=" * 70)
    
    print("""
Command:
    iptvportal schema introspect tv_channel

What it does:
    - Connects to remote IPTVPORTAL server
    - Analyzes table structure (field names, types)
    - Gathers metadata (row count, ID ranges)
    - Performs DuckDB statistical analysis on sample (default: 1000 rows)
    - Generates smart sync configuration recommendations

Output includes:
    ✓ Field detection and type inference
    ✓ Row count and ID statistics
    ✓ Timestamp ranges
    ✓ DuckDB analysis (nulls, unique values, cardinality, min/max)
    ✓ Recommended sync settings
    """)


def example_introspect_with_sync():
    """Introspection with sync to local cache."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Introspection with Sync")
    print("=" * 70)
    
    print("""
Command:
    iptvportal schema introspect tv_channel --sync

What it does:
    1. Introspects table structure (same as Example 1)
    2. Registers the auto-generated schema
    3. Creates local SQLite cache database
    4. Syncs all data from remote table to local cache
    5. Shows progress during sync
    
Benefits:
    ✓ Local offline access to data
    ✓ Faster queries on cached data
    ✓ Can analyze full dataset (not just sample)
    ✓ Automatic schema registration
    """)


def example_sync_with_custom_options():
    """Sync with custom options."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Sync with Custom Options")
    print("=" * 70)
    
    print("""
Command:
    iptvportal schema introspect tv_program \\
        --fields='0:channel_id,1:start,2:stop' \\
        --sync \\
        --sync-chunk=5000 \\
        --order-by-fields='id:asc' \\
        --sync-run-timeout=300

What it does:
    - Manually specifies field mappings (position:name)
    - Sets custom chunk size (5000 rows per chunk)
    - Specifies sort order for sync
    - Sets 5-minute timeout for sync operation
    
Use cases:
    - Large tables that need specific chunking
    - Tables without standard 'id' field
    - Long-running syncs that need timeouts
    """)


def example_analyze_from_cache():
    """Comprehensive analysis on synced cache data."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Analyze from Cache (Most Comprehensive)")
    print("=" * 70)
    
    print("""
Command:
    iptvportal schema introspect media \\
        --sync \\
        --analyze-from-cache

What it does:
    1. Introspects table
    2. Syncs all data to local cache
    3. Runs DuckDB analysis on synced cache data (not just remote sample)
    
Key difference:
    - Without --analyze-from-cache: Analyzes ~1000 sample rows from remote
    - With --analyze-from-cache: Analyzes full synced dataset from local cache
    
Best for:
    ✓ Most accurate statistics
    ✓ Full dataset analysis
    ✓ Tables with varied data distributions
    ✓ Quality assessment before production use
    """)


def example_workflow():
    """Real-world workflow example."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Complete Workflow")
    print("=" * 70)
    
    print("""
Step-by-step workflow for a new table:

1. Quick introspection (no sync):
   iptvportal schema introspect tv_channel
   
   → Review: field names, types, row count, recommended settings

2. Introspect with sync (if data looks good):
   iptvportal schema introspect tv_channel --sync --save
   
   → Creates: local cache + schema file (config/tv_channel-schema.yaml)

3. Verify synced data:
   iptvportal sync status
   iptvportal sql -q "SELECT COUNT(*) FROM tv_channel"
   
   → Check: sync was successful, data is accessible

4. Comprehensive analysis (optional):
   iptvportal schema introspect tv_channel --analyze-from-cache
   
   → Get: full dataset statistics from cache

5. Use the data:
   iptvportal sql -q "SELECT * FROM tv_channel WHERE enabled = true"
   
   → Queries: now use local cache (fast!)
    """)


def example_comparison():
    """Compare different approaches."""
    print("\n" + "=" * 70)
    print("COMPARISON: Different Introspection Modes")
    print("=" * 70)
    
    print("""
┌─────────────────────────┬──────────────┬──────────────┬───────────────────┐
│ Feature                 │ Basic        │ With --sync  │ + --analyze-cache │
├─────────────────────────┼──────────────┼──────────────┼───────────────────┤
│ Field detection         │ ✓            │ ✓            │ ✓                 │
│ Type inference          │ ✓            │ ✓            │ ✓                 │
│ Row count               │ ✓            │ ✓            │ ✓                 │
│ ID ranges               │ ✓            │ ✓            │ ✓                 │
│ Timestamp ranges        │ ✓            │ ✓            │ ✓                 │
│ Sample analysis         │ ✓ (~1K rows) │ ✓ (~1K rows) │ -                 │
│ Local cache created     │ ✗            │ ✓            │ ✓                 │
│ Data synced             │ ✗            │ ✓ (all)      │ ✓ (all)           │
│ Full dataset analysis   │ ✗            │ ✗            │ ✓                 │
│ Offline access          │ ✗            │ ✓            │ ✓                 │
│ Execution time          │ Fast (~5s)   │ Slow (~30s+) │ Slower (~45s+)    │
└─────────────────────────┴──────────────┴──────────────┴───────────────────┘

Recommendations:
    - Development: Use basic (fast feedback)
    - Testing: Use --sync (verify full sync works)
    - Production: Use --sync --analyze-from-cache (comprehensive validation)
    """)


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  Schema Introspection with Sync Integration - Examples".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    
    example_basic_introspect()
    example_introspect_with_sync()
    example_sync_with_custom_options()
    example_analyze_from_cache()
    example_workflow()
    example_comparison()
    
    print("\n" + "=" * 70)
    print("For more information, see:")
    print("  - docs/cli.md - Full CLI documentation")
    print("  - README.md - Quick start guide")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
