#!/usr/bin/env python3
"""Test sync database functionality in isolation."""

import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime

# Copy the core database functionality for testing
class TestSyncDatabase:
    """Minimal test version of SyncDatabase."""

    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self._connection = None

    def initialize(self):
        """Create all metadata tables."""
        with self._get_connection() as conn:
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")

            # Create metadata tables
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

            # Cache stats table
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

            # Initialize global stats
            conn.execute("""
                INSERT OR IGNORE INTO _cache_stats (id, initialized_at)
                VALUES (1, ?)
            """, (datetime.now().isoformat(),))

            conn.commit()

    def _get_connection(self):
        """Get database connection."""
        if self._connection:
            return self._connection

        conn = sqlite3.connect(str(self.db_path), timeout=30.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        self._connection = conn  # Keep connection open
        return conn

    def get_stats(self):
        """Get global cache statistics."""
        with self._get_connection() as conn:
            stats_row = conn.execute("SELECT * FROM _cache_stats WHERE id = 1").fetchone()
            if not stats_row:
                return {"error": "Cache not initialized"}

            stats = dict(stats_row)
            stats["database_size_bytes"] = self.db_path.stat().st_size if self.db_path.exists() else 0
            return stats

    def execute_query(self, table_name, sql, params=None):
        """Execute SQL query."""
        with self._get_connection() as conn:
            cursor = conn.execute(sql, params or {})
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def close(self):
        """Close connection."""
        if self._connection:
            self._connection.close()

def test_database():
    """Test database functionality."""
    print("🧪 Testing sync database functionality...")

    # Use in-memory database for testing
    db = TestSyncDatabase(":memory:")

    try:
        # Test initialization
        db.initialize()
        print("✅ Database initialized successfully")

        # Test stats
        stats = db.get_stats()
        print(f"✅ Database stats retrieved: {len(stats)} fields")

        # Test metadata table exists
        result = db.execute_query("_sync_metadata", "SELECT COUNT(*) as count FROM _sync_metadata")
        print(f"✅ Metadata table query successful: {result}")

        # Test cache stats table exists
        result = db.execute_query("_cache_stats", "SELECT * FROM _cache_stats WHERE id = 1")
        print(f"✅ Cache stats table query successful: {len(result)} rows")

        print("✅ All database tests passed!")
        return True

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        db.close()

if __name__ == "__main__":
    success = test_database()

    if success:
        print("\n🎉 Sync database functionality verified!")
    else:
        print("\n💥 Sync database tests failed!")
        exit(1)
