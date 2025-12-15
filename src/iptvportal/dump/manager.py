"""Core dump manager with incremental state tracking."""

import asyncio
import json
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator

from .models import DumpConfig, DumpFormat, DumpProgress, DumpStrategy

logger = logging.getLogger(__name__)


class DumpState(str, Enum):
    """Dump operation state."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class DumpStats:
    """Aggregated dump statistics."""
    
    def __init__(self, config: DumpConfig, progress: DumpProgress):
        self.config = config
        self.progress = progress
    
    @property
    def state(self) -> DumpState:
        """Infer state from progress."""
        if self.progress.is_complete:
            return DumpState.COMPLETED
        if self.progress.last_error:
            return DumpState.FAILED
        if self.progress.dumped_rows > 0:
            return DumpState.RUNNING
        return DumpState.PENDING
    
    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "config": self.config.to_dict(),
            "progress": self.progress.to_dict(),
        }


class DumpManager:
    """Manages incremental dump operations with state tracking.
    
    Features:
    - Resumable dumps via state persistence
    - Multiple traversal strategies (OFFSET, ID_RANGE, CURSOR)
    - Progress tracking with ETA estimation
    - Configurable output formats (JSONL, Parquet, CSV, JSON)
    - Automatic state management with SQLite backend
    """
    
    def __init__(self, config: DumpConfig):
        """Initialize dump manager.
        
        Args:
            config: Dump configuration
        """
        config.validate()
        self.config = config
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize progress
        self.progress = self._load_progress() if config.resume else DumpProgress(
            table=config.table
        )
        
        # State tracking
        self._state = DumpState.PENDING
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Initially not paused
    
    @property
    def state(self) -> DumpState:
        """Get current dump state."""
        return self._state
    
    @property
    def stats(self) -> DumpStats:
        """Get dump statistics."""
        return DumpStats(self.config, self.progress)
    
    def _load_progress(self) -> DumpProgress:
        """Load progress from state file if exists."""
        state_file = self._get_state_file()
        if state_file.exists():
            with open(state_file) as f:
                data = json.load(f)
                progress = DumpProgress.from_dict(data)
                logger.info(
                    f"Resuming {self.config.table} from offset "
                    f"{progress.current_offset} "
                    f"({progress.dumped_rows}/{progress.total_rows} rows)"
                )
                return progress
        return DumpProgress(table=self.config.table)
    
    def _save_progress(self) -> None:
        """Persist progress to state file."""
        state_file = self._get_state_file()
        with open(state_file, "w") as f:
            json.dump(self.progress.to_dict(), f, indent=2, default=str)
    
    def _get_state_file(self) -> Path:
        """Get state file path."""
        return self.config.output_dir / f".{self.config.table}.state.json"
    
    def _get_output_file(self, chunk_num: int = 0) -> Path:
        """Get output file path."""
        ext = self.config.format.value
        if self.config.compress and self.config.format in (DumpFormat.JSONL, DumpFormat.JSON):
            ext += ".gz"
        
        # Single file for JSONL (streaming), split for others
        if self.config.format == DumpFormat.JSONL:
            return self.config.output_dir / f"{self.config.table}.{ext}"
        else:
            return self.config.output_dir / f"{self.config.table}-{chunk_num:05d}.{ext}"
    
    async def dump_all(self) -> DumpStats:
        """Execute full dump with resumable state.
        
        Returns:
            DumpStats with final statistics
        """
        try:
            self._state = DumpState.RUNNING
            self.progress.started_at = datetime.utcnow()
            
            async for chunk in self.iter_chunks():
                await self._pause_event.wait()  # Check pause flag
                await self._write_chunk(chunk)
                self.progress.last_updated_at = datetime.utcnow()
                self._save_progress()
            
            self.progress.is_complete = True
            self.progress.completed_at = datetime.utcnow()
            self._state = DumpState.COMPLETED
            self._save_progress()
            
            logger.info(
                f"Dump complete: {self.progress.dumped_rows} rows "
                f"in {self.progress.elapsed_seconds():.1f}s "
                f"({self.progress.rows_per_second():.0f} rows/sec)"
            )
        
        except Exception as e:
            self._state = DumpState.FAILED
            self.progress.last_error = str(e)
            self._save_progress()
            logger.exception(f"Dump failed: {e}")
            raise
        
        return self.stats
    
    async def iter_chunks(
        self,
        limit: int | None = None,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        """Iterate over data chunks.
        
        Args:
            limit: Maximum chunks to yield (for testing)
        
        Yields:
            Chunk of rows
        """
        raise NotImplementedError("Use AsyncDumpManager for async iteration")
    
    async def _write_chunk(
        self,
        chunk: list[dict[str, Any]],
        chunk_num: int | None = None,
    ) -> None:
        """Write chunk to output file.
        
        Args:
            chunk: List of rows
            chunk_num: Chunk number (for multi-file formats)
        """
        if not chunk:
            return
        
        output_file = self._get_output_file(chunk_num or 0)
        
        if self.config.format == DumpFormat.JSONL:
            await self._write_jsonl(chunk, output_file)
        elif self.config.format == DumpFormat.JSON:
            await self._write_json(chunk, output_file)
        elif self.config.format == DumpFormat.CSV:
            await self._write_csv(chunk, output_file)
        elif self.config.format == DumpFormat.PARQUET:
            await self._write_parquet(chunk, output_file)
        
        self.progress.dumped_rows += len(chunk)
        self.progress.chunks_completed += 1
        logger.debug(f"Wrote chunk: {len(chunk)} rows to {output_file.name}")
    
    async def _write_jsonl(self, rows: list[dict], path: Path) -> None:
        """Write rows as JSONL (append mode)."""
        import gzip
        
        mode = "ab" if self.config.compress else "a"
        open_fn = gzip.open if self.config.compress else open
        
        with open_fn(path, mode) as f:
            for row in rows:
                line = json.dumps(row, default=str) + "\n"
                if self.config.compress:
                    f.write(line.encode())
                else:
                    f.write(line)
    
    async def _write_json(self, rows: list[dict], path: Path) -> None:
        """Write rows as JSON array (whole file)."""
        import gzip
        
        # Load existing or create new
        if path.exists():
            open_fn = gzip.open if self.config.compress else open
            with open_fn(path, "rb" if self.config.compress else "r") as f:
                content = f.read()
                data = json.loads(content.decode() if isinstance(content, bytes) else content)
            data.extend(rows)
        else:
            data = rows
        
        open_fn = gzip.open if self.config.compress else open
        mode = "wb" if self.config.compress else "w"
        
        with open_fn(path, mode) as f:
            content = json.dumps(data, default=str, indent=2)
            if self.config.compress:
                f.write(content.encode())
            else:
                f.write(content)
    
    async def _write_csv(self, rows: list[dict], path: Path) -> None:
        """Write rows as CSV."""
        import csv
        
        if not rows:
            return
        
        fieldnames = list(rows[0].keys())
        write_header = not path.exists()
        
        with open(path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerows(rows)
    
    async def _write_parquet(self, rows: list[dict], path: Path) -> None:
        """Write rows as Parquet."""
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            try:
                import pandas as pd
                df = pd.DataFrame(rows)
                df.to_parquet(path, index=False, mode="append" if path.exists() else "overwrite")
                return
            except ImportError:
                raise ImportError("Parquet format requires 'pyarrow' or 'pandas'")
        
        table = pa.Table.from_pylist(rows)
        
        if path.exists():
            existing = pq.read_table(path)
            table = pa.concat_tables([existing, table])
        
        pq.write_table(table, path)
    
    def pause(self) -> None:
        """Pause dump operation."""
        self._pause_event.clear()
        self._state = DumpState.PAUSED
        logger.info(f"Dump paused at offset {self.progress.current_offset}")
    
    def resume(self) -> None:
        """Resume paused dump operation."""
        self._pause_event.set()
        self._state = DumpState.RUNNING
        logger.info(f"Dump resumed from offset {self.progress.current_offset}")
    
    def reset(self) -> None:
        """Reset progress and delete state file."""
        self._get_state_file().unlink(missing_ok=True)
        self.progress = DumpProgress(table=self.config.table)
        self._state = DumpState.PENDING
        logger.info(f"Dump state reset for {self.config.table}")
