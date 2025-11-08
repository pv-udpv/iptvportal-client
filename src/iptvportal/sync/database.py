"""SQLite database layer for sync operations."""

import sqlite3
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Union
from datetime import datetime, timedelta
from contextlib import contextmanager

from iptvportal.config import IPTVPortalSettings
from iptvportal.schema import TableSchema, FieldDefinition, FieldType
from iptvportal.sync.exceptions import DatabaseError, SchemaVersionError, TableNotFoundError


class SyncDatabase:
    """
    SQLite database manager for sync operations.

    Handles:
    - Database initialization with optimized settings
    - Dynamic table creation from TableSchema
    - Metadata tracking for sync operations
    - Bulk data operations with transactions
    - Query execution with proper parameter binding
    - Maintenance operations (VACUUM, ANALYZE)
    """

    def __init__(self, db_path: str, settings):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
            settings: Settings object with cache configuration attributes
        """
        self.db_path = Path(db_path).expanduser()
        self.settings = settings
        self._connection: Optional[sqlite3.Connection] = None

        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        """Create all metadata tables and indexes."""
        with self._get_connection() as conn:
            # Enable foreign keys and set pragmas for performance
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(f"PRAGMA journal_mode = {self.settings.cache_db_journal_mode}")
            conn.execute(f"PRAGMA synchronous = NORMAL")
            conn.execute(f"PRAGMA cache_size = {self.settings.cache_db_cache_size}")
            conn.execute(f"PRAGMA page_size = {self.settings.cache_db_page_size}")
            conn.execute("PRAGMA temp_store = MEMORY")
            conn.execute("PRAGMA mmap_size = 268435456")  # 256MB

            # Create metadata tables
            self._create_metadata_tables(conn)
            self._create_views(conn)

            # Initialize global stats if not exists
            conn.execute("""
                INSERT OR IGNORE INTO _cache_stats (id, initialized_at)
                VALUES (1, ?)
            """, (datetime.now().isoformat(),))

            conn.commit()

    def _create_metadata_tables(self, conn: sqlite3.Connection) -> None:
        """Create all metadata tables."""

        # Sync metadata table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _sync_metadata (
                table_name TEXT PRIMARY KEY,
                last_sync_at TEXT NOT NULL,
                next_sync_at TEXT,
                sync_version INTEGER DEFAULT 1,
                last_sync_checkpoint TEXT,
                incremental_field TEXT,
                row_count INTEGER DEFAULT 0,
                local_row_count INTEGER DEFAULT 0,
                max_id INTEGER,
                min_id INTEGER,
                strategy TEXT NOT NULL,
                ttl INTEGER,
                chunk_size INTEGER DEFAULT 1000,
                where_clause TEXT,
                order_by TEXT DEFAULT 'id',
                schema_hash TEXT NOT NULL,
                schema_version INTEGER DEFAULT 1,
                total_fields INTEGER,
                last_sync_duration_ms INTEGER,
                last_sync_rows INTEGER,
                total_syncs INTEGER DEFAULT 0,
                failed_syncs INTEGER DEFAULT 0,
                last_error TEXT,
                last_error_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Field mappings table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _field_mappings (
                table_name TEXT NOT NULL,
                position INTEGER NOT NULL,
                field_name TEXT NOT NULL,
                local_column TEXT NOT NULL,
                field_type TEXT NOT NULL,
                is_primary_key BOOLEAN DEFAULT FALSE,
                is_incremental_field BOOLEAN DEFAULT FALSE,
                is_nullable BOOLEAN DEFAULT TRUE,
                description TEXT,
                PRIMARY KEY (table_name, position),
                FOREIGN KEY (table_name) REFERENCES _sync_metadata(table_name) ON DELETE CASCADE
            )
        """)

        # Sync history table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _sync_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                sync_type TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                duration_ms INTEGER,
                rows_fetched INTEGER DEFAULT 0,
                rows_inserted INTEGER DEFAULT 0,
                rows_updated INTEGER DEFAULT 0,
                rows_deleted INTEGER DEFAULT 0,
                chunks_processed INTEGER DEFAULT 0,
                status TEXT NOT NULL,
                error_message TEXT,
                triggered_by TEXT,
                checkpoint_before TEXT,
                checkpoint_after TEXT,
                FOREIGN KEY (table_name) REFERENCES _sync_metadata(table_name) ON DELETE CASCADE
            )
        """)

        # Cache stats table (singleton)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _cache_stats (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                total_tables INTEGER DEFAULT 0,
                total_rows INTEGER DEFAULT 0,
                database_size_bytes INTEGER DEFAULT 0,
                total_syncs INTEGER DEFAULT 0,
                successful_syncs INTEGER DEFAULT 0,
                failed_syncs INTEGER DEFAULT 0,
                last_activity_at TEXT,
                initialized_at TEXT NOT NULL,
                last_vacuum_at TEXT,
                last_analyze_at TEXT,
                cache_version TEXT DEFAULT '1.0.0',
                schema_format_version INTEGER DEFAULT 1
            )
        """)

        # Create indexes for performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_meta_next_sync ON _sync_metadata(next_sync_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_meta_strategy ON _sync_metadata(strategy)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_field_map_table ON _field_mappings(table_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_history_table ON _sync_history(table_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_history_started ON _sync_history(started_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_history_status ON _sync_history(status)")

    def _create_views(self, conn: sqlite3.Connection) -> None:
        """Create convenience views."""

        # Sync status view
        conn.execute("""
            CREATE VIEW IF NOT EXISTS v_sync_status AS
            SELECT
                m.table_name,
                m.strategy,
                m.row_count,
                m.local_row_count,
                m.last_sync_at,
                m.next_sync_at,
                CASE
                    WHEN datetime(m.next_sync_at) < datetime('now') THEN 'stale'
                    WHEN datetime(m.next_sync_at) > datetime('now') THEN 'fresh'
                    ELSE 'unknown'
                END as cache_status,
                m.last_sync_duration_ms,
                m.total_syncs,
                m.failed_syncs,
                m.last_error
            FROM _sync_metadata m
            ORDER BY m.table_name
        """)

        # Recent sync history view
        conn.execute("""
            CREATE VIEW IF NOT EXISTS v_recent_sync_history AS
            SELECT
                h.table_name,
                h.sync_type,
                h.started_at,
                h.duration_ms,
                h.rows_fetched,
                h.rows_inserted + h.rows_updated as rows_modified,
                h.status,
                h.triggered_by
            FROM _sync_history h
            ORDER BY h.started_at DESC
            LIMIT 100
        """)

    @contextmanager
    def _get_connection(self):
        """Get database connection with proper cleanup."""
        if self._connection:
            yield self._connection
            return

        conn = sqlite3.connect(
            str(self.db_path),
            timeout=30.0,
            isolation_level=None  # Enable autocommit mode
        )
        conn.row_factory = sqlite3.Row

        try:
            yield conn
        finally:
            conn.close()

    def create_data_table(self, schema: TableSchema) -> None:
        """
        Create data table from schema definition.

        Args:
            schema: TableSchema with field definitions
        """
        with self._get_connection() as conn:
            # Generate CREATE TABLE statement
            columns = []
            used_names = set()

            # Create Field_X columns for ALL remote fields (0 to total_fields-1)
            total_fields = schema.total_fields or max(schema.fields.keys()) + 1
            for pos in range(total_fields):
                if pos in schema.fields:
                    # Use configured field name if available
                    field_def = schema.fields[pos]
                    col_name = self._get_unique_column_name(field_def, used_names)
                    col_type = self._get_sqlite_type(field_def.field_type)
                    nullable = "" if field_def.name.lower() == "id" else " NULL"
                    columns.append(f"{col_name} {col_type}{nullable}")
                else:
                    # Create generic Field_X column for unknown fields
                    col_name = f"Field_{pos}"
                    columns.append(f"{col_name} TEXT NULL")

            # Add sync metadata columns
            columns.extend([
                "_synced_at TEXT NOT NULL",
                "_sync_version INTEGER DEFAULT 1",
                "_is_partial BOOLEAN DEFAULT FALSE"
            ])

            # Create primary key if id field exists
            if any(f.name.lower() == "id" for f in schema.fields.values()):
                # Find the column name for the id field
                id_field = next(f for f in schema.fields.values() if f.name.lower() == "id")
                id_col_name = self._get_column_name(id_field)
                columns.append(f"PRIMARY KEY ({id_col_name})")

            create_sql = f"""
                CREATE TABLE IF NOT EXISTS {schema.table_name} (
                    {', '.join(columns)}
                )
            """

            conn.execute(create_sql)

            # Create indexes for common query patterns
            self._create_table_indexes(conn, schema)

    def _get_column_name(self, field_def: FieldDefinition) -> str:
        """Get SQLite column name for field."""
        # Use python_name if available, otherwise field name
        name = field_def.python_name or field_def.name

        # Ensure valid SQLite identifier
        return name.replace("-", "_").replace(" ", "_")

    def _get_unique_column_name(self, field_def: FieldDefinition, used_names: set) -> str:
        """Get a unique SQLite column name for field, avoiding duplicates."""
        base_name = self._get_column_name(field_def)
        name = base_name
        counter = 1

        # If name is already used, append a number suffix
        while name in used_names:
            name = f"{base_name}_{counter}"
            counter += 1

        used_names.add(name)
        return name

    def _get_sqlite_type(self, field_type: FieldType) -> str:
        """Map FieldType to SQLite column type."""
        type_map = {
            FieldType.INTEGER: "INTEGER",
            FieldType.STRING: "TEXT",
            FieldType.BOOLEAN: "BOOLEAN",
            FieldType.FLOAT: "REAL",
            FieldType.DATETIME: "TEXT",
            FieldType.DATE: "TEXT",
            FieldType.JSON: "TEXT",
            FieldType.UNKNOWN: "TEXT",
        }
        return type_map.get(field_type, "TEXT")

    def _create_table_indexes(self, conn: sqlite3.Connection, schema: TableSchema) -> None:
        """Create indexes for table."""
        table_name = schema.table_name

        # Index on synced_at for temporal queries
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_synced_at ON {table_name}(_synced_at)")

        # Index on common fields
        for field_def in schema.fields.values():
            col_name = self._get_column_name(field_def)

            # Index primary key and incremental fields
            if field_def.name.lower() == "id" or field_def.name == schema.sync_config.incremental_field:
                conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_{col_name} ON {table_name}({col_name})")

    def _create_user_view(self, conn: sqlite3.Connection, schema: TableSchema) -> None:
        """Create user-friendly view with proper column aliases."""
        table_name = schema.table_name
        view_name = f"{table_name}_view"

        # Build SELECT clause with aliases
        select_parts = []
        used_names = set()

        # First, add configured fields with their aliases
        for pos, field_def in schema.fields.items():
            local_column = self._get_unique_column_name(field_def, used_names)
            # Use remote_name if available, otherwise use field name
            alias_name = field_def.remote_name or field_def.name
            select_parts.append(f"{local_column} AS {alias_name}")

        # Then add unknown fields as Field_X (for completeness)
        total_fields = schema.total_fields or max(schema.fields.keys()) + 1
        for pos in range(total_fields):
            if pos not in schema.fields:
                # Unknown field - keep as Field_X
                select_parts.append(f"Field_{pos}")

        # Add sync metadata columns
        select_parts.extend([
            "_synced_at",
            "_sync_version",
            "_is_partial"
        ])

        select_clause = ", ".join(select_parts)
        create_view_sql = f"""
            CREATE VIEW IF NOT EXISTS {view_name} AS
            SELECT {select_clause}
            FROM {table_name}
        """

        conn.execute(create_view_sql)

    def register_table(self, schema: TableSchema) -> None:
        """
        Register table in metadata and create structure.

        Args:
            schema: TableSchema to register
        """
        with self._get_connection() as conn:
            # Create data table
            self.create_data_table(schema)

            # Calculate schema hash
            schema_hash = self._calculate_schema_hash(schema)

            # Insert/update metadata
            now = datetime.now().isoformat()
            conn.execute("""
                INSERT OR REPLACE INTO _sync_metadata (
                    table_name, last_sync_at, next_sync_at, strategy, ttl,
                    chunk_size, where_clause, order_by, schema_hash,
                    schema_version, total_fields, incremental_field,
                    row_count, min_id, max_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                schema.table_name,
                now,  # last_sync_at
                None,  # next_sync_at (will be set after sync)
                schema.sync_config.cache_strategy,
                schema.sync_config.ttl,
                schema.sync_config.chunk_size,
                schema.sync_config.where,
                schema.sync_config.order_by,
                schema_hash,
                1,  # schema_version
                schema.total_fields,
                schema.sync_config.incremental_field,
                schema.metadata.row_count if schema.metadata else None,
                schema.metadata.min_id if schema.metadata else None,
                schema.metadata.max_id if schema.metadata else None,
                now,  # created_at
                now,  # updated_at
            ))

            # Insert field mappings (use same unique column names as table creation)
            used_names = set()
            for pos, field_def in schema.fields.items():
                local_column = self._get_unique_column_name(field_def, used_names)
                conn.execute("""
                    INSERT OR REPLACE INTO _field_mappings (
                        table_name, position, field_name, local_column,
                        field_type, is_primary_key, is_incremental_field,
                        is_nullable, description
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    schema.table_name,
                    pos,
                    field_def.name,
                    local_column,
                    field_def.field_type.value,
                    field_def.name.lower() == "id",
                    field_def.name == schema.sync_config.incremental_field,
                    True,  # is_nullable (for now)
                    field_def.description,
                ))

            # Create user-friendly view with proper column aliases
            self._create_user_view(conn, schema)

            conn.commit()

    def _calculate_schema_hash(self, schema: TableSchema) -> str:
        """Calculate hash of schema for change detection."""
        # Include field definitions and sync config in hash
        hash_data = {
            "table_name": schema.table_name,
            "fields": {
                pos: {
                    "name": f.name,
                    "type": f.field_type.value,
                    "position": f.position
                }
                for pos, f in schema.fields.items()
            },
            "sync_config": {
                "strategy": schema.sync_config.cache_strategy,
                "incremental_field": schema.sync_config.incremental_field,
                "chunk_size": schema.sync_config.chunk_size,
                "where": schema.sync_config.where,
                "order_by": schema.sync_config.order_by,
            }
        }

        json_str = json.dumps(hash_data, sort_keys=True)
        return hashlib.md5(json_str.encode()).hexdigest()

    def get_metadata(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get sync metadata for table."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM _sync_metadata WHERE table_name = ?",
                (table_name,)
            ).fetchone()

            return dict(row) if row else None

    def update_metadata(self, table_name: str, **kwargs) -> None:
        """Update sync metadata."""
        if not kwargs:
            return

        with self._get_connection() as conn:
            set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
            values = list(kwargs.values()) + [datetime.now().isoformat(), table_name]

            conn.execute(f"""
                UPDATE _sync_metadata
                SET {set_clause}, updated_at = ?
                WHERE table_name = ?
            """, values)

            conn.commit()

    def is_stale(self, table_name: str) -> bool:
        """Check if cache is expired."""
        metadata = self.get_metadata(table_name)
        if not metadata:
            return True

        next_sync = metadata.get("next_sync_at")
        if not next_sync:
            return True

        try:
            next_sync_dt = datetime.fromisoformat(next_sync)
            return datetime.now() > next_sync_dt
        except (ValueError, TypeError):
            return True

    def bulk_insert(self, table_name: str, rows: List[List[Any]],
                   schema: TableSchema, on_conflict: str = "FAIL") -> int:
        """
        Insert multiple rows efficiently.

        Args:
            table_name: Target table name
            rows: List of row data (each row is list of values)
            schema: TableSchema for field mapping
            on_conflict: What to do on constraint violations ("FAIL", "REPLACE", "IGNORE")

        Returns:
            Number of rows inserted
        """
        if not rows:
            return 0

        with self._get_connection() as conn:
            # Get column names for ALL remote fields (Field_0, Field_1, ..., Field_N)
            total_fields = schema.total_fields or max(schema.fields.keys()) + 1
            columns = []
            used_names = set()

            for pos in range(total_fields):
                if pos in schema.fields:
                    # Use configured field name if available
                    field_def = schema.fields[pos]
                    col_name = self._get_unique_column_name(field_def, used_names)
                    columns.append(col_name)
                else:
                    # Use generic Field_X name for unknown fields
                    col_name = f"Field_{pos}"
                    columns.append(col_name)

            # Add sync metadata columns
            columns.extend(["_synced_at", "_sync_version", "_is_partial"])

            # Prepare INSERT statement with conflict resolution
            placeholders = ", ".join("?" * len(columns))
            col_names = ", ".join(columns)

            if on_conflict == "REPLACE":
                insert_sql = f"INSERT OR REPLACE INTO {table_name} ({col_names}) VALUES ({placeholders})"
            elif on_conflict == "IGNORE":
                insert_sql = f"INSERT OR IGNORE INTO {table_name} ({col_names}) VALUES ({placeholders})"
            else:  # FAIL (default)
                insert_sql = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"

            # Prepare data with sync metadata
            now = datetime.now().isoformat()
            data_rows = []
            for row in rows:
                # Extract ALL values from remote data (no position filtering)
                row_values = []
                for pos in range(total_fields):
                    if pos < len(row):
                        row_values.append(row[pos])
                    else:
                        row_values.append(None)  # Pad with NULL if position missing

                # Add sync metadata
                sync_row = row_values + [now, 1, False]
                data_rows.append(sync_row)

            # Execute bulk insert
            conn.executemany(insert_sql, data_rows)
            conn.commit()

            return len(rows)

    def upsert_rows(self, table_name: str, rows: List[List[Any]],
                   schema: TableSchema) -> Tuple[int, int]:
        """
        Upsert rows (insert or update).

        Args:
            table_name: Target table name
            rows: List of row data
            schema: TableSchema for field mapping

        Returns:
            Tuple of (inserted_count, updated_count)
        """
        if not rows:
            return 0, 0

        with self._get_connection() as conn:
            inserted = 0
            updated = 0

            # Get primary key column (assume 'id')
            pk_column = "id"

            for row in rows:
                # Check if row exists
                pk_value = row[0] if row else None  # Assume ID is first column
                exists = conn.execute(
                    f"SELECT 1 FROM {table_name} WHERE {pk_column} = ?",
                    (pk_value,)
                ).fetchone()

                if exists:
                    # Update
                    self._update_row(conn, table_name, row, schema)
                    updated += 1
                else:
                    # Insert
                    self._insert_row(conn, table_name, row, schema)
                    inserted += 1

            conn.commit()
            return inserted, updated

    def _insert_row(self, conn: sqlite3.Connection, table_name: str,
                   row: List[Any], schema: TableSchema) -> None:
        """Insert single row."""
        # Get column names for ALL remote fields (Field_0, Field_1, ..., Field_N)
        total_fields = schema.total_fields or max(schema.fields.keys()) + 1
        columns = []
        used_names = set()

        for pos in range(total_fields):
            if pos in schema.fields:
                # Use configured field name if available
                field_def = schema.fields[pos]
                col_name = self._get_unique_column_name(field_def, used_names)
                columns.append(col_name)
            else:
                # Use generic Field_X name for unknown fields
                col_name = f"Field_{pos}"
                columns.append(col_name)

        columns.extend(["_synced_at", "_sync_version", "_is_partial"])
        placeholders = ", ".join("?" * len(columns))
        col_names = ", ".join(columns)

        now = datetime.now().isoformat()

        # Extract ALL values from remote data (no position filtering)
        row_values = []
        for pos in range(total_fields):
            if pos < len(row):
                row_values.append(row[pos])
            else:
                row_values.append(None)  # Pad with NULL if position missing

        # Add sync metadata
        values = row_values + [now, 1, False]

        conn.execute(f"""
            INSERT INTO {table_name} ({col_names})
            VALUES ({placeholders})
        """, values)

    def _update_row(self, conn: sqlite3.Connection, table_name: str,
                   row: List[Any], schema: TableSchema) -> None:
        """Update single row."""
        # Get primary key value (assume first configured field is ID)
        configured_positions = sorted(schema.fields.keys())
        pk_value = None
        pk_column = None

        # Find primary key field
        for pos in configured_positions:
            if pos < len(row):
                field_def = schema.fields[pos]
                if field_def.name.lower() == "id":
                    pk_value = row[pos]
                    pk_column = self._get_column_name(field_def)
                    break

        if pk_value is None or pk_column is None:
            return

        # Build SET clause for ALL remote fields (Field_0, Field_1, ..., Field_N)
        total_fields = schema.total_fields or max(schema.fields.keys()) + 1
        set_parts = []
        values = []
        used_names = set()

        for pos in range(total_fields):
            if pos < len(row):
                if pos in schema.fields:
                    # Use configured field name if available
                    field_def = schema.fields[pos]
                    col_name = self._get_unique_column_name(field_def, used_names)
                    set_parts.append(f"{col_name} = ?")
                    values.append(row[pos])
                else:
                    # Use generic Field_X name for unknown fields
                    col_name = f"Field_{pos}"
                    set_parts.append(f"{col_name} = ?")
                    values.append(row[pos])

        # Update sync metadata
        set_parts.extend(["_synced_at = ?", "_sync_version = _sync_version + 1"])
        values.extend([datetime.now().isoformat()])

        set_clause = ", ".join(set_parts)
        values.append(pk_value)  # WHERE clause

        conn.execute(f"""
            UPDATE {table_name}
            SET {set_clause}
            WHERE {pk_column} = ?
        """, values)

    def clear_table(self, table_name: str) -> int:
        """Clear all data from table. Returns rows deleted."""
        with self._get_connection() as conn:
            # Get count before deletion
            count_row = conn.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()
            count = count_row[0] if count_row else 0

            # Clear table
            conn.execute(f"DELETE FROM {table_name}")
            conn.commit()

            return count

    def execute_query(self, table_name: str, sql: str,
                     params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Execute SQL query on cached table.

        Args:
            table_name: Table to query
            sql: SQL query string
            params: Query parameters

        Returns:
            List of result rows as dictionaries
        """
        with self._get_connection() as conn:
            # Ensure table exists
            table_exists = conn.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name=?
            """, (table_name,)).fetchone()

            if not table_exists:
                raise TableNotFoundError(f"Table '{table_name}' not found in cache")

            # Execute query
            cursor = conn.execute(sql, params or {})
            rows = cursor.fetchall()

            # Convert to dicts
            result = []
            for row in rows:
                result.append(dict(row))

            return result

    def get_stats(self) -> Dict[str, Any]:
        """Get global cache statistics."""
        with self._get_connection() as conn:
            # Get database file size
            db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

            # Get stats from table
            stats_row = conn.execute("SELECT * FROM _cache_stats WHERE id = 1").fetchone()
            if not stats_row:
                return {"error": "Cache not initialized"}

            stats = dict(stats_row)
            stats["database_size_bytes"] = db_size

            # Get table count and row count
            table_stats = conn.execute("""
                SELECT
                    COUNT(DISTINCT table_name) as table_count,
                    SUM(local_row_count) as total_rows
                FROM _sync_metadata
            """).fetchone()

            if table_stats:
                stats["total_tables"] = table_stats["table_count"] or 0
                stats["total_rows"] = table_stats["total_rows"] or 0

            return stats

    def vacuum(self) -> None:
        """Vacuum database to reclaim space."""
        with self._get_connection() as conn:
            conn.execute("VACUUM")
            conn.execute("""
                UPDATE _cache_stats
                SET last_vacuum_at = ?
                WHERE id = 1
            """, (datetime.now().isoformat(),))

    def analyze(self) -> None:
        """Run ANALYZE for query optimization."""
        with self._get_connection() as conn:
            conn.execute("ANALYZE")
            conn.execute("""
                UPDATE _cache_stats
                SET last_analyze_at = ?
                WHERE id = 1
            """, (datetime.now().isoformat(),))

    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
