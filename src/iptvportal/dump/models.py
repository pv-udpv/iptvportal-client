"""Data models for incremental dump operations."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Literal
import json


class DumpFormat(str, Enum):
    """Supported output formats."""
    JSONL = "jsonl"        # Line-delimited JSON (streaming-friendly)
    PARQUET = "parquet"    # Apache Parquet (columnar, compressed)
    CSV = "csv"           # CSV with header
    JSON = "json"         # Full JSON array


class DumpStrategy(str, Enum):
    """Dump traversal strategy."""
    OFFSET = "offset"      # Use OFFSET/LIMIT (standard SQL)
    ID_RANGE = "id_range"  # Use id > last_id (faster for large tables)
    CURSOR = "cursor"      # Custom cursor (manual state)


@dataclass
class DumpConfig:
    """Dump operation configuration."""
    
    # Core
    table: str
    output_dir: Path
    
    # Traversal
    chunk_size: int = 5000                  # rows per API call
    strategy: DumpStrategy = DumpStrategy.OFFSET
    
    # Format & Output
    format: DumpFormat = DumpFormat.JSONL
    compress: bool = False                  # gzip compression for JSONL/JSON
    
    # Resume capability
    resume: bool = True
    resume_offset: int | None = None       # Override last known offset
    
    # Filtering
    order_by: str | None = None             # Default: "id ASC"
    where_clause: dict | None = None        # JSONSQL where condition
    
    # Performance
    batch_timeout: float = 30.0             # HTTP timeout per batch
    max_retries: int = 3
    retry_backoff: float = 1.5
    
    # Concurrency
    max_parallel: int = 3                   # parallel chunks (for ID_RANGE)
    
    def validate(self) -> None:
        """Validate configuration."""
        if self.chunk_size < 1:
            raise ValueError(f"chunk_size must be > 0, got {self.chunk_size}")
        if self.max_parallel < 1:
            raise ValueError(f"max_parallel must be > 0, got {self.max_parallel}")
        if self.format == DumpFormat.PARQUET and not _has_parquet():
            raise ImportError("parquet format requires 'pyarrow' or 'pandas'")
    
    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        data = asdict(self)
        data["output_dir"] = str(self.output_dir)
        data["strategy"] = self.strategy.value
        data["format"] = self.format.value
        return data


@dataclass
class DumpProgress:
    """Tracks dump progress and state."""
    
    table: str
    total_rows: int | None = None           # Estimated or actual
    dumped_rows: int = 0
    current_offset: int = 0
    current_id: int | None = None           # For ID_RANGE strategy
    
    chunks_completed: int = 0
    chunks_failed: int = 0
    
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    
    is_complete: bool = False
    last_error: str | None = None
    
    def percent_complete(self) -> float:
        """Get completion percentage."""
        if not self.total_rows or self.total_rows == 0:
            return 0.0
        return (self.dumped_rows / self.total_rows) * 100
    
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        end = self.completed_at or datetime.utcnow()
        return (end - self.started_at).total_seconds()
    
    def rows_per_second(self) -> float:
        """Get throughput (rows/sec)."""
        elapsed = self.elapsed_seconds()
        if elapsed == 0:
            return 0.0
        return self.dumped_rows / elapsed
    
    def eta_seconds(self) -> float | None:
        """Estimated time to completion in seconds."""
        if not self.total_rows or self.dumped_rows == 0:
            return None
        rps = self.rows_per_second()
        if rps == 0:
            return None
        remaining = self.total_rows - self.dumped_rows
        return remaining / rps
    
    def to_dict(self) -> dict:
        """Convert to dict for JSON/storage."""
        return {
            "table": self.table,
            "total_rows": self.total_rows,
            "dumped_rows": self.dumped_rows,
            "current_offset": self.current_offset,
            "current_id": self.current_id,
            "chunks_completed": self.chunks_completed,
            "chunks_failed": self.chunks_failed,
            "started_at": self.started_at.isoformat(),
            "last_updated_at": self.last_updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "is_complete": self.is_complete,
            "last_error": self.last_error,
            "percent_complete": self.percent_complete(),
            "elapsed_seconds": self.elapsed_seconds(),
            "rows_per_second": self.rows_per_second(),
            "eta_seconds": self.eta_seconds(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "DumpProgress":
        """Create from dict."""
        return cls(
            table=data["table"],
            total_rows=data.get("total_rows"),
            dumped_rows=data.get("dumped_rows", 0),
            current_offset=data.get("current_offset", 0),
            current_id=data.get("current_id"),
            chunks_completed=data.get("chunks_completed", 0),
            chunks_failed=data.get("chunks_failed", 0),
            started_at=datetime.fromisoformat(data["started_at"]),
            last_updated_at=datetime.fromisoformat(data["last_updated_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            is_complete=data.get("is_complete", False),
            last_error=data.get("last_error"),
        )


def _has_parquet() -> bool:
    """Check if parquet libraries are available."""
    try:
        import pyarrow  # noqa: F401
        return True
    except ImportError:
        try:
            import pandas  # noqa: F401
            return True
        except ImportError:
            return False
