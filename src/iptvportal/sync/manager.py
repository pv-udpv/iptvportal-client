"""Sync manager for orchestrating data synchronization operations."""

import asyncio
import time
from typing import Optional, Callable, Awaitable, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timedelta

from iptvportal.config import IPTVPortalSettings
from iptvportal.schema import TableSchema, SchemaRegistry
from iptvportal.async_client import AsyncIPTVPortalClient
from iptvportal.sync.database import SyncDatabase
from iptvportal.sync.exceptions import (
    SyncError,
    SyncStrategyError,
    TableNotFoundError,
    ConfigurationError,
    ConnectionError,
    SyncInProgressError,
)

@dataclass
class SyncProgress:
    """Progress information for sync operation."""
    table_name: str
    total_chunks: int
    completed_chunks: int
    rows_synced: int
    bytes_transferred: int
    elapsed_seconds: float
    estimated_remaining_seconds: Optional[float] = None

@dataclass
class SyncResult:
    """Result of a sync operation."""
    table_name: str
    strategy: str
    rows_fetched: int
    rows_inserted: int
    rows_updated: int
    rows_deleted: int
    chunks_processed: int
    duration_ms: int
    status: str  # "success", "failed", "partial"
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class SyncManager:
    """
    Orchestrates sync operations with different strategies.

    Handles:
    - Full sync with chunking
    - Incremental sync with checkpoint tracking
    - On-demand lazy loading
    - Progress reporting and error handling
    - Concurrent sync operations
    """

    def __init__(
        self,
        database: SyncDatabase,
        client: AsyncIPTVPortalClient,
        schema_registry: SchemaRegistry,
        settings: IPTVPortalSettings
    ):
        """
        Initialize sync manager.

        Args:
            database: SyncDatabase instance
            client: AsyncIPTVPortalClient instance
            schema_registry: SchemaRegistry with table schemas
            settings: IPTVPortalSettings for configuration
        """
        self.database = database
        self.client = client
        self.schema_registry = schema_registry
        self.settings = settings

        # Active sync operations (table_name -> task)
        self._active_syncs: Dict[str, asyncio.Task] = {}

    async def sync_table(
        self,
        table_name: str,
        strategy: Optional[str] = None,
        force: bool = False,
        progress_callback: Optional[Callable[[SyncProgress], Awaitable[None]]] = None
    ) -> SyncResult:
        """
        Sync a table using specified strategy.

        Args:
            table_name: Name of table to sync
            strategy: Sync strategy ("full", "incremental", "on_demand")
            force: Force sync even if not stale
            progress_callback: Optional callback for progress updates

        Returns:
            SyncResult with operation details

        Raises:
            TableNotFoundError: If table not registered
            SyncStrategyError: If invalid strategy
            ConfigurationError: If sync config invalid
        """
        # Check if sync already in progress
        if table_name in self._active_syncs and not self._active_syncs[table_name].done():
            raise SyncInProgressError(f"Sync already in progress for table '{table_name}'")

        # Get table schema
        schema = self.schema_registry.get(table_name)
        if not schema:
            raise TableNotFoundError(f"Table '{table_name}' not registered in schema registry")

        # Determine strategy
        sync_strategy = strategy or schema.sync_config.cache_strategy or self.settings.default_sync_strategy

        # Validate strategy
        if sync_strategy not in ("full", "incremental", "on_demand"):
            raise SyncStrategyError(f"Invalid sync strategy: {sync_strategy}")

        # Check if sync needed (unless forced)
        if not force and not self.database.is_stale(table_name):
            # Return empty result for already fresh data
            return SyncResult(
                table_name=table_name,
                strategy=sync_strategy,
                rows_fetched=0,
                rows_inserted=0,
                rows_updated=0,
                rows_deleted=0,
                chunks_processed=0,
                duration_ms=0,
                status="skipped",
                started_at=datetime.now(),
                completed_at=datetime.now()
            )

        # Start sync operation
        started_at = datetime.now()
        task = asyncio.create_task(self._sync_table_internal(
            table_name, schema, sync_strategy, progress_callback
        ))

        self._active_syncs[table_name] = task

        try:
            result = await task
            result.started_at = started_at
            result.completed_at = datetime.now()
            result.duration_ms = int((result.completed_at - started_at).total_seconds() * 1000)
            return result
        finally:
            # Clean up completed task
            if table_name in self._active_syncs:
                del self._active_syncs[table_name]

    async def _sync_table_internal(
        self,
        table_name: str,
        schema: TableSchema,
        strategy: str,
        progress_callback: Optional[Callable] = None
    ) -> SyncResult:
        """Internal sync implementation."""
        try:
            if strategy == "full":
                return await self._sync_full(table_name, schema, progress_callback)
            elif strategy == "incremental":
                return await self._sync_incremental(table_name, schema, progress_callback)
            elif strategy == "on_demand":
                # On-demand doesn't do bulk sync
                return SyncResult(
                    table_name=table_name,
                    strategy=strategy,
                    rows_fetched=0,
                    rows_inserted=0,
                    rows_updated=0,
                    rows_deleted=0,
                    chunks_processed=0,
                    duration_ms=0,
                    status="success",
                    started_at=datetime.now()
                )
            else:
                raise SyncStrategyError(f"Unsupported strategy: {strategy}")

        except Exception as e:
            return SyncResult(
                table_name=table_name,
                strategy=strategy,
                rows_fetched=0,
                rows_inserted=0,
                rows_updated=0,
                rows_deleted=0,
                chunks_processed=0,
                duration_ms=0,
                status="failed",
                started_at=datetime.now(),
                error_message=str(e)
            )

    async def _sync_full(
        self,
        table_name: str,
        schema: TableSchema,
        progress_callback: Optional[Callable] = None
    ) -> SyncResult:
        """Execute full sync strategy."""
        chunk_size = schema.sync_config.chunk_size or self.settings.default_chunk_size
        where_clause = schema.sync_config.where
        order_by = schema.sync_config.order_by

        # Clear existing data for full sync
        cleared_count = self.database.clear_table(table_name)

        # Calculate total chunks (if possible)
        total_chunks = None
        if schema.metadata and schema.metadata.row_count:
            total_chunks = (schema.metadata.row_count + chunk_size - 1) // chunk_size

        # Sync in chunks
        offset = 0
        total_fetched = 0
        total_inserted = 0
        chunks_processed = 0
        bytes_transferred = 0

        start_time = time.time()

        while True:
            # Fetch chunk from remote
            rows = await self._fetch_chunk(
                table_name, offset, chunk_size, where_clause, order_by
            )

            if not rows:
                break

            # Insert chunk into database (use REPLACE for full sync to handle duplicates)
            inserted = self.database.bulk_insert(table_name, rows, schema, on_conflict="REPLACE")
            total_inserted += inserted
            total_fetched += len(rows)
            chunks_processed += 1
            bytes_transferred += self._estimate_bytes(rows)

            # Report progress
            if progress_callback:
                elapsed = time.time() - start_time
                progress = SyncProgress(
                    table_name=table_name,
                    total_chunks=total_chunks or chunks_processed,
                    completed_chunks=chunks_processed,
                    rows_synced=total_fetched,
                    bytes_transferred=bytes_transferred,
                    elapsed_seconds=elapsed,
                    estimated_remaining_seconds=self._estimate_remaining_time(
                        chunks_processed, total_chunks, elapsed
                    ) if total_chunks else None
                )
                await progress_callback(progress)

            offset += chunk_size

            # Safety check: don't sync more than configured limit
            if schema.sync_config.limit and total_fetched >= schema.sync_config.limit:
                break

        # Update metadata with enhanced statistics
        metadata = self.database.get_metadata(table_name)
        current_syncs = metadata.get("total_syncs", 0) if metadata else 0

        # Calculate min/max IDs from synced data
        min_id = max_id = None
        if rows and len(rows) > 0:
            # Find ID field position
            id_pos = None
            for pos, field_def in schema.fields.items():
                if field_def.name.lower() == "id":
                    id_pos = pos
                    break

            if id_pos is not None:
                ids = [row[id_pos] for row in rows if id_pos < len(row) and row[id_pos] is not None]
                if ids:
                    min_id = min(ids)
                    max_id = max(ids)

        self.database.update_metadata(
            table_name,
            last_sync_at=datetime.now().isoformat(),
            next_sync_at=self._calculate_next_sync(schema),
            row_count=total_fetched,
            local_row_count=total_inserted,
            last_sync_rows=total_fetched,
            total_syncs=current_syncs + 1,
            max_id=max_id,
            min_id=min_id
        )

        return SyncResult(
            table_name=table_name,
            strategy="full",
            rows_fetched=total_fetched,
            rows_inserted=total_inserted,
            rows_updated=0,
            rows_deleted=cleared_count,
            chunks_processed=chunks_processed,
            duration_ms=0,  # Will be set by caller
            status="success",
            started_at=datetime.now()
        )

    async def _sync_incremental(
        self,
        table_name: str,
        schema: TableSchema,
        progress_callback: Optional[Callable] = None
    ) -> SyncResult:
        """Execute incremental sync strategy."""
        if not schema.sync_config.incremental_field:
            raise ConfigurationError(
                f"Incremental sync requires incremental_field for table '{table_name}'"
            )

        incremental_field = schema.sync_config.incremental_field
        metadata = self.database.get_metadata(table_name)

        # Get last checkpoint
        last_checkpoint = metadata.get("last_sync_checkpoint") if metadata else None

        # If no previous sync, fall back to full sync
        if not last_checkpoint:
            return await self._sync_full(table_name, schema, progress_callback)

        # Fetch incremental updates
        rows = await self._fetch_incremental(
            table_name, incremental_field, last_checkpoint, schema.sync_config.limit
        )

        if not rows:
            # No updates, just update metadata
            self.database.update_metadata(
                table_name,
                last_sync_at=datetime.now().isoformat(),
                next_sync_at=self._calculate_next_sync(schema)
            )
            return SyncResult(
                table_name=table_name,
                strategy="incremental",
                rows_fetched=0,
                rows_inserted=0,
                rows_updated=0,
                rows_deleted=0,
                chunks_processed=0,
                duration_ms=0,
                status="success",
                started_at=datetime.now()
            )

        # Upsert rows
        inserted, updated = self.database.upsert_rows(table_name, rows, schema)

        # Find new checkpoint (max value of incremental field)
        new_checkpoint = self._find_max_checkpoint(rows, schema, incremental_field)

        # Update metadata
        current_count = metadata.get("local_row_count", 0) if metadata else 0
        self.database.update_metadata(
            table_name,
            last_sync_at=datetime.now().isoformat(),
            next_sync_at=self._calculate_next_sync(schema),
            last_sync_checkpoint=new_checkpoint,
            local_row_count=current_count + inserted,
            last_sync_rows=len(rows),
            total_syncs=metadata.get("total_syncs", 0) + 1 if metadata else 1
        )

        return SyncResult(
            table_name=table_name,
            strategy="incremental",
            rows_fetched=len(rows),
            rows_inserted=inserted,
            rows_updated=updated,
            rows_deleted=0,
            chunks_processed=1,  # Incremental is typically one operation
            duration_ms=0,
            status="success",
            started_at=datetime.now()
        )

    async def _fetch_chunk(
        self,
        table_name: str,
        offset: int,
        limit: int,
        where: Optional[str] = None,
        order_by: str = "id"
    ) -> List[List[Any]]:
        """Fetch a chunk of data from remote."""
        query = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "select",
            "params": {
                "data": ["*"],
                "from": table_name,
                "limit": limit,
                "offset": offset,
                "order_by": order_by
            }
        }

        if where:
            # Parse simple WHERE clause (basic implementation)
            query["params"]["where"] = self._parse_where_clause(where)

        try:
            response = await self.client.execute(query)
            return response if isinstance(response, list) else []
        except Exception as e:
            raise ConnectionError(f"Failed to fetch chunk from remote: {e}")

    async def _fetch_incremental(
        self,
        table_name: str,
        incremental_field: str,
        last_value: str,
        limit: Optional[int] = None
    ) -> List[List[Any]]:
        """Fetch incremental updates from remote."""
        query = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "select",
            "params": {
                "data": ["*"],
                "from": table_name,
                "where": {"gt": [incremental_field, last_value]},
                "order_by": incremental_field
            }
        }

        if limit:
            query["params"]["limit"] = limit

        try:
            response = await self.client.execute(query)
            return response if isinstance(response, list) else []
        except Exception as e:
            raise ConnectionError(f"Failed to fetch incremental updates: {e}")

    def _parse_where_clause(self, where: str) -> Dict[str, Any]:
        """Parse simple WHERE clause into JSONSQL format."""
        # Very basic parser for simple conditions
        # This could be enhanced with a proper SQL parser
        where = where.strip()

        # Handle simple equality: column = 'value'
        if " = " in where:
            col, val = where.split(" = ", 1)
            col = col.strip()
            val = val.strip().strip("'\"")
            return {"eq": [col, val]}

        # Handle simple LIKE: column LIKE 'pattern'
        if " LIKE " in where:
            col, pattern = where.split(" LIKE ", 1)
            col = col.strip()
            pattern = pattern.strip().strip("'\"")
            return {"like": [col, pattern]}

        # For complex WHERE clauses, return as-is (let remote handle it)
        # This is a limitation of the basic parser
        raise ConfigurationError(f"Complex WHERE clause not supported: {where}")

    def _calculate_next_sync(self, schema: TableSchema) -> str:
        """Calculate next sync timestamp based on TTL."""
        ttl = schema.sync_config.ttl or self.settings.default_sync_ttl
        next_sync = datetime.now() + timedelta(seconds=ttl)
        return next_sync.isoformat()

    def _estimate_bytes(self, rows: List[List[Any]]) -> int:
        """Estimate bytes transferred for progress reporting."""
        # Rough estimation: average 100 bytes per row
        return len(rows) * 100

    def _estimate_remaining_time(
        self, completed: int, total: Optional[int], elapsed: float
    ) -> Optional[float]:
        """Estimate remaining time for sync operation."""
        if not total or completed == 0:
            return None
        avg_time_per_chunk = elapsed / completed
        remaining_chunks = total - completed
        return avg_time_per_chunk * remaining_chunks

    def _find_max_checkpoint(
        self, rows: List[List[Any]], schema: TableSchema, incremental_field: str
    ) -> str:
        """Find maximum value of incremental field for checkpoint."""
        # Find field position
        field_pos = None
        for pos, field_def in schema.fields.items():
            if field_def.name == incremental_field:
                field_pos = pos
                break

        if field_pos is None:
            return datetime.now().isoformat()  # Fallback

        # Find max value
        max_value = None
        for row in rows:
            if field_pos < len(row):
                value = row[field_pos]
                if value is not None and (max_value is None or value > max_value):
                    max_value = value

        return str(max_value) if max_value is not None else datetime.now().isoformat()

    def get_sync_status(self, table_name: str) -> Dict[str, Any]:
        """Get current sync status for table."""
        metadata = self.database.get_metadata(table_name)
        if not metadata:
            return {"status": "not_registered"}

        is_stale = self.database.is_stale(table_name)
        is_active = table_name in self._active_syncs and not self._active_syncs[table_name].done()

        return {
            "table_name": table_name,
            "strategy": metadata.get("strategy"),
            "last_sync_at": metadata.get("last_sync_at"),
            "next_sync_at": metadata.get("next_sync_at"),
            "is_stale": is_stale,
            "is_active": is_active,
            "row_count": metadata.get("row_count"),
            "local_row_count": metadata.get("local_row_count"),
            "last_error": metadata.get("last_error"),
            "total_syncs": metadata.get("total_syncs", 0),
            "failed_syncs": metadata.get("failed_syncs", 0),
        }

    def get_all_sync_status(self) -> List[Dict[str, Any]]:
        """Get sync status for all registered tables."""
        return [
            self.get_sync_status(table_name)
            for table_name in self.schema_registry.list_tables()
        ]

    async def sync_all(
        self,
        max_concurrent: int = 3,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, SyncResult]:
        """
        Sync all tables with concurrency control.

        Args:
            max_concurrent: Maximum concurrent sync operations
            progress_callback: Optional progress callback

        Returns:
            Dict mapping table names to SyncResult
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results = {}

        async def sync_with_semaphore(table_name: str):
            async with semaphore:
                try:
                    result = await self.sync_table(table_name, progress_callback=progress_callback)
                    results[table_name] = result
                except Exception as e:
                    results[table_name] = SyncResult(
                        table_name=table_name,
                        strategy="unknown",
                        rows_fetched=0,
                        rows_inserted=0,
                        rows_updated=0,
                        rows_deleted=0,
                        chunks_processed=0,
                        duration_ms=0,
                        status="failed",
                        error_message=str(e),
                        started_at=datetime.now(),
                        completed_at=datetime.now()
                    )

        # Start all sync operations
        tasks = [
            sync_with_semaphore(table_name)
            for table_name in self.schema_registry.list_tables()
        ]

        await asyncio.gather(*tasks, return_exceptions=True)
        return results

    def cancel_sync(self, table_name: str) -> bool:
        """
        Cancel ongoing sync operation.

        Returns:
            True if sync was cancelled, False if not found or already completed
        """
        if table_name in self._active_syncs:
            task = self._active_syncs[table_name]
            if not task.done():
                task.cancel()
                return True
        return False
