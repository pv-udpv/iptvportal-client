"""Incremental dump service for bulk table exports with resumable progress.

Features:
- Stateful dump manager with progress tracking
- Incremental dumps by offset/id
- Async/sync support
- SQLite metadata for resumable dumps
- Multiple output formats (JSONL, Parquet, CSV)
"""

from .manager import DumpManager, DumpState, DumpStats
from .service import DumpService
from .models import DumpConfig, DumpProgress

__all__ = [
    "DumpManager",
    "DumpService",
    "DumpState",
    "DumpStats",
    "DumpConfig",
    "DumpProgress",
]
