#!/usr/bin/env python3
"""Example: Incremental dump service for bulk table exports.

Demonstrates:
- Single table dump with resumable state
- Multiple table concurrent dumps
- Progress tracking and ETA estimation
- Different output formats (JSONL, Parquet, CSV)
- Pause/resume functionality
"""

import asyncio
import logging
from pathlib import Path

from iptvportal import AsyncIPTVPortalClient
from iptvportal.dump import DumpConfig, DumpFormat, DumpService, DumpStrategy

logging.basicConfig(level=logging.INFO)


async def example_single_table_dump():
    """Example: Dump single table with JSONL format."""
    print("\n=== Single Table Dump Example ===")
    
    config = DumpConfig(
        table="tv_channel",
        output_dir=Path("./dumps"),
        chunk_size=5000,
        strategy=DumpStrategy.OFFSET,
        format=DumpFormat.JSONL,
        resume=True,  # Auto-resume from last checkpoint
    )
    
    async with AsyncIPTVPortalClient() as client:
        service = DumpService(client)
        
        def progress_cb(progress):
            pct = progress.percent_complete()
            eta = progress.eta_seconds()
            eta_str = f"{eta:.0f}s" if eta else "N/A"
            print(
                f"  {pct:5.1f}% | "
                f"{progress.dumped_rows:8d} / {progress.total_rows:8d} rows | "
                f"{progress.rows_per_second():6.0f} rows/s | "
                f"ETA: {eta_str}"
            )
        
        stats = await service.dump(config, progress_callback=progress_cb)
        
        print(f"\nDump Complete:")
        print(f"  Table: {stats.config.table}")
        print(f"  Rows: {stats.progress.dumped_rows}")
        print(f"  Time: {stats.progress.elapsed_seconds():.1f}s")
        print(f"  Throughput: {stats.progress.rows_per_second():.0f} rows/s")
        print(f"  Output: {config.output_dir / f'{config.table}.jsonl'}")


async def example_multiple_tables():
    """Example: Dump multiple tables concurrently."""
    print("\n=== Multiple Tables Concurrent Dump ===")
    
    configs = [
        DumpConfig(
            table="tv_channel",
            output_dir=Path("./dumps"),
            format=DumpFormat.JSONL,
            chunk_size=5000,
        ),
        DumpConfig(
            table="tv_program",
            output_dir=Path("./dumps"),
            format=DumpFormat.JSONL,
            chunk_size=5000,
        ),
        DumpConfig(
            table="media",
            output_dir=Path("./dumps"),
            format=DumpFormat.JSONL,
            chunk_size=5000,
        ),
    ]
    
    async with AsyncIPTVPortalClient() as client:
        service = DumpService(client)
        
        def progress_cb(table, progress):
            pct = progress.percent_complete()
            print(f"  {table:20s} | {pct:5.1f}% | {progress.dumped_rows:8d} rows")
        
        print("Starting concurrent dumps (max 2 parallel)...\n")
        all_stats = await service.dump_many(
            configs,
            max_concurrent=2,
            progress_callback=progress_cb,
        )
        
        print(f"\nAll dumps complete:")
        for stats in all_stats:
            print(
                f"  {stats.config.table:20s} | "
                f"{stats.progress.dumped_rows:8d} rows | "
                f"{stats.progress.elapsed_seconds():6.1f}s"
            )


async def example_parquet_dump():
    """Example: Dump to Parquet format for analytics."""
    print("\n=== Parquet Format Dump ===")
    
    config = DumpConfig(
        table="subscriber",
        output_dir=Path("./dumps/parquet"),
        format=DumpFormat.PARQUET,  # Columnar, compressed
        chunk_size=10000,
        chunk_size=10000,  # Larger chunks for Parquet
    )
    
    async with AsyncIPTVPortalClient() as client:
        service = DumpService(client)
        stats = await service.dump(config)
        
        print(f"\nParquet dump complete:")
        print(f"  Rows: {stats.progress.dumped_rows}")
        print(f"  Output: {config.output_dir}")
        print(f"  Format: Parquet (columnar, compressed)")


async def example_id_range_strategy():
    """Example: Use ID_RANGE strategy for faster large-table traversal.
    
    ID_RANGE is faster than OFFSET for large tables:
    - Doesn't require full row count estimation
    - Uses indexed id > last_id instead of expensive OFFSET
    - Parallelizable per ID range
    """
    print("\n=== ID_RANGE Strategy (Faster for Large Tables) ===")
    
    config = DumpConfig(
        table="terminal",
        output_dir=Path("./dumps"),
        format=DumpFormat.JSONL,
        strategy=DumpStrategy.ID_RANGE,  # id > last_id instead of OFFSET
        chunk_size=5000,
    )
    
    async with AsyncIPTVPortalClient() as client:
        service = DumpService(client)
        stats = await service.dump(config)
        
        print(f"\nID_RANGE dump complete:")
        print(f"  Strategy: ID_RANGE (id > {stats.progress.current_id})")
        print(f"  Rows: {stats.progress.dumped_rows}")
        print(f"  Throughput: {stats.progress.rows_per_second():.0f} rows/s")


async def example_pause_resume():
    """Example: Pause and resume dump operations."""
    print("\n=== Pause/Resume Example ===")
    
    config = DumpConfig(
        table="media",
        output_dir=Path("./dumps"),
        format=DumpFormat.JSONL,
        chunk_size=5000,
        resume=True,  # Can resume after pause
    )
    
    async with AsyncIPTVPortalClient() as client:
        service = DumpService(client)
        
        # Simulate pause after some time
        async def dump_with_pause():
            dump_task = asyncio.create_task(service.dump(config))
            await asyncio.sleep(5)  # Let it run for 5 seconds
            
            service.pause(config.table)
            print(f"\nPaused at: {service.get_stats(config.table).progress.dumped_rows} rows")
            
            await asyncio.sleep(2)  # Wait while paused
            
            service.resume(config.table)
            print("Resumed...\n")
            
            return await dump_task
        
        stats = await dump_with_pause()
        print(f"\nDump complete after pause/resume:")
        print(f"  Total rows: {stats.progress.dumped_rows}")
        print(f"  State: {stats.state.value}")


async def main():
    """Run all examples."""
    print("""\n╔══════════════════════════════════════════════════════════════╗
║         IPTVPortal Incremental Dump Service Examples          ║
╚══════════════════════════════════════════════════════════════╝""")
    
    # Note: These examples require valid IPTVPortal credentials
    # Set IPTVPORTAL_DOMAIN, IPTVPORTAL_USERNAME, IPTVPORTAL_PASSWORD
    
    try:
        # await example_single_table_dump()
        # await example_multiple_tables()
        # await example_parquet_dump()
        # await example_id_range_strategy()
        # await example_pause_resume()
        
        print("\nExamples are commented out. Uncomment to run with valid credentials.")
        print("Set environment variables:")
        print("  export IPTVPORTAL_DOMAIN=your_domain")
        print("  export IPTVPORTAL_USERNAME=your_username")
        print("  export IPTVPORTAL_PASSWORD=your_password")
    
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
