"""Async dump service with JSONSQL client integration."""

import asyncio
import logging
from typing import TYPE_CHECKING, Any, AsyncIterator

from .manager import DumpManager, DumpStats
from .models import DumpConfig, DumpStrategy

if TYPE_CHECKING:
    from iptvportal.core.async_client import AsyncIPTVPortalClient

logger = logging.getLogger(__name__)


class DumpService:
    """High-level async dump service.
    
    Wraps DumpManager with JSONSQL client for seamless integration.
    
    Example:
        >>> from iptvportal import AsyncIPTVPortalClient
        >>> from iptvportal.dump import DumpService, DumpConfig, DumpFormat
        >>> from pathlib import Path
        >>> 
        >>> async def main():
        ...     config = DumpConfig(
        ...         table="tv_channel",
        ...         output_dir=Path("./dumps"),
        ...         chunk_size=5000,
        ...         format=DumpFormat.JSONL,
        ...     )
        ...     
        ...     async with AsyncIPTVPortalClient() as client:
        ...         service = DumpService(client)
        ...         stats = await service.dump(config)
        ...         print(f"Dumped {stats.progress.dumped_rows} rows")
    """
    
    def __init__(self, client: "AsyncIPTVPortalClient"):
        """Initialize dump service.
        
        Args:
            client: Async JSONSQL client
        """
        self.client = client
        self._managers: dict[str, AsyncDumpManager] = {}
    
    async def dump(
        self,
        config: DumpConfig,
        progress_callback: callable | None = None,
    ) -> DumpStats:
        """Execute table dump with progress tracking.
        
        Args:
            config: Dump configuration
            progress_callback: Optional callback(progress) on each chunk
        
        Returns:
            DumpStats with final statistics
        """
        manager = AsyncDumpManager(self.client, config)
        self._managers[config.table] = manager
        
        try:
            async for _ in manager.iter_chunks():
                if progress_callback:
                    progress_callback(manager.progress)
        finally:
            self._managers.pop(config.table, None)
        
        return manager.stats
    
    async def dump_many(
        self,
        configs: list[DumpConfig],
        max_concurrent: int = 2,
        progress_callback: callable | None = None,
    ) -> list[DumpStats]:
        """Dump multiple tables concurrently.
        
        Args:
            configs: List of dump configurations
            max_concurrent: Max concurrent dumps
            progress_callback: Optional callback(table, progress)
        
        Returns:
            List of DumpStats for each table
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def dump_with_semaphore(config: DumpConfig) -> DumpStats:
            async with semaphore:
                def cb(progress):
                    if progress_callback:
                        progress_callback(config.table, progress)
                
                return await self.dump(config, progress_callback=cb)
        
        return await asyncio.gather(*[
            dump_with_semaphore(config) for config in configs
        ])
    
    def get_manager(self, table: str) -> "AsyncDumpManager | None":
        """Get active manager for table (for status/pause/resume)."""
        return self._managers.get(table)
    
    def pause(self, table: str) -> None:
        """Pause dump for table."""
        if manager := self._managers.get(table):
            manager.pause()
    
    def resume(self, table: str) -> None:
        """Resume dump for table."""
        if manager := self._managers.get(table):
            manager.resume()
    
    def get_stats(self, table: str) -> DumpStats | None:
        """Get current dump stats for table."""
        if manager := self._managers.get(table):
            return manager.stats
        return None


class AsyncDumpManager(DumpManager):
    """Async variant of DumpManager with JSONSQL integration."""
    
    def __init__(self, client: "AsyncIPTVPortalClient", config: DumpConfig):
        """Initialize async dump manager.
        
        Args:
            client: Async JSONSQL client
            config: Dump configuration
        """
        super().__init__(config)
        self.client = client
    
    async def iter_chunks(
        self,
        limit: int | None = None,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        """Iterate over data chunks from JSONSQL API.
        
        Args:
            limit: Maximum chunks to yield (for testing)
        
        Yields:
            Chunk of rows
        """
        chunk_count = 0
        
        while True:
            await self._pause_event.wait()  # Check pause
            
            if limit and chunk_count >= limit:
                break
            
            try:
                chunk = await self._fetch_chunk()
                
                if not chunk:
                    break  # No more data
                
                yield chunk
                chunk_count += 1
                
            except Exception as e:
                self.progress.chunks_failed += 1
                logger.error(f"Failed to fetch chunk: {e}")
                
                if self.config.max_retries > 0:
                    self.config.max_retries -= 1
                    await asyncio.sleep(self.config.retry_backoff ** (3 - self.config.max_retries))
                    continue
                raise
    
    async def _fetch_chunk(self) -> list[dict[str, Any]]:
        """Fetch single chunk from JSONSQL API.
        
        Returns:
            List of rows, or empty list if no more data
        """
        if self.config.strategy == DumpStrategy.OFFSET:
            return await self._fetch_offset_chunk()
        elif self.config.strategy == DumpStrategy.ID_RANGE:
            return await self._fetch_id_range_chunk()
        else:
            raise ValueError(f"Unsupported strategy: {self.config.strategy}")
    
    async def _fetch_offset_chunk(self) -> list[dict[str, Any]]:
        """Fetch chunk using OFFSET/LIMIT strategy."""
        query = self.client.query.select(
            data=["*"],
            from_=self.config.table,
            where=self.config.where_clause,
            order_by=self.config.order_by or "id ASC",
            limit=self.config.chunk_size,
            offset=self.progress.current_offset,
        )
        
        result = await self.client.execute(query)
        
        if not result:
            # Estimate total if not set
            if not self.progress.total_rows:
                count_query = self.client.query.select(
                    data=["COUNT(*) AS cnt"],
                    from_=self.config.table,
                    where=self.config.where_clause,
                )
                count_result = await self.client.execute(count_query)
                if count_result:
                    self.progress.total_rows = count_result[0].get("cnt", 0)
            return []
        
        self.progress.current_offset += len(result)
        logger.debug(
            f"Fetched {len(result)} rows from {self.config.table} "
            f"(offset: {self.progress.current_offset})"
        )
        
        return result
    
    async def _fetch_id_range_chunk(self) -> list[dict[str, Any]]:
        """Fetch chunk using ID_RANGE strategy (faster for large tables).
        
        Assumes primary key is 'id' and monotonically increasing.
        """
        from iptvportal import Q
        
        where = self.config.where_clause or {}
        
        # Add id > last_id condition
        if self.progress.current_id is not None:
            where = Q.and_(
                Q(id__gt=self.progress.current_id),
                where or {},
            )
        else:
            where = where or {}
        
        query = self.client.query.select(
            data=["*"],
            from_=self.config.table,
            where=where,
            order_by="id ASC",
            limit=self.config.chunk_size,
        )
        
        result = await self.client.execute(query)
        
        if not result:
            return []
        
        self.progress.current_id = result[-1].get("id")
        logger.debug(
            f"Fetched {len(result)} rows from {self.config.table} "
            f"(max id: {self.progress.current_id})"
        )
        
        return result
