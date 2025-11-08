#!/usr/bin/env python3
"""Test the Field_X position mapping fix."""

import tempfile
import os
from pathlib import Path

# Minimal test classes to avoid dependency issues
class MockSettings:
    def __init__(self):
        self.cache_db_journal_mode = "WAL"
        self.cache_db_cache_size = -64000
        self.cache_db_page_size = 4096

class MockFieldDefinition:
    def __init__(self, name, field_type, position):
        self.name = name
        self.field_type = field_type
        self.position = position
        self.python_name = name

class MockSyncConfig:
    def __init__(self):
        self.cache_strategy = "full"
        self.ttl = 3600
        self.chunk_size = 1000

class MockTableSchema:
    def __init__(self, table_name, fields):
        self.table_name = table_name
        self.fields = fields
        self.sync_config = MockSyncConfig()

# Import the actual SyncDatabase class
from iptvportal.sync.database import SyncDatabase

def test_field_position_fix():
    """Test that bulk_insert only uses configured positions."""
    print("🧪 Testing Field_X position mapping fix...")

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        # Initialize database with mock settings
        settings = MockSettings()
        db = SyncDatabase(db_path, settings)
        db.initialize()

        # Create schema with only positions 0, 1, 2 (simulating config with 3 fields)
        schema = MockTableSchema(
            table_name="test_table",
            fields={
                0: MockFieldDefinition(name="id", field_type="INTEGER", position=0),
                1: MockFieldDefinition(name="title", field_type="TEXT", position=1),
                2: MockFieldDefinition(name="url", field_type="TEXT", position=2),
            }
        )

        # Register table (creates table with only 3 columns)
        db.register_table(schema)

        # Simulate remote data with 5 fields (positions 0-4)
        # This simulates the real scenario where remote has more fields than config
        remote_rows = [
            [1, "Movie 1", "http://example.com/1", "extra_field_1", "extra_field_2"],
            [2, "Movie 2", "http://example.com/2", "extra_field_3", "extra_field_4"],
            [3, "Movie 3", "http://example.com/3", "extra_field_5", "extra_field_6"],
        ]

        # This should work now - only insert values at positions 0,1,2
        inserted = db.bulk_insert("test_table", remote_rows, schema)
        print(f"✅ Successfully inserted {inserted} rows")

        # Verify data was inserted correctly
        result = db.execute_query("test_table", "SELECT id, title, url FROM test_table ORDER BY id")
        print(f"✅ Retrieved {len(result)} rows from database")

        for row in result:
            print(f"  - ID: {row['id']}, Title: {row['title']}, URL: {row['url']}")

        # Verify we only have the configured columns
        expected_columns = {"id", "title", "url", "_synced_at", "_sync_version", "_is_partial"}
        actual_columns = set(result[0].keys()) if result else set()
        assert actual_columns == expected_columns, f"Unexpected columns: {actual_columns}"

        print("✅ Column structure is correct (no extra Field_X columns)")

        # Test upsert_rows as well
        upsert_rows = [
            [1, "Updated Movie 1", "http://updated.com/1", "new_extra_1", "new_extra_2"],  # Update existing
            [4, "New Movie 4", "http://example.com/4", "new_extra_3", "new_extra_4"],      # Insert new
        ]

        inserted_count, updated_count = db.upsert_rows("test_table", upsert_rows, schema)
        print(f"✅ Upsert completed: {inserted_count} inserted, {updated_count} updated")

        # Verify final count
        final_result = db.execute_query("test_table", "SELECT COUNT(*) as count FROM test_table")
        final_count = final_result[0]['count']
        print(f"✅ Final row count: {final_count}")

        assert final_count == 4, f"Expected 4 rows, got {final_count}"

        print("🎉 All Field_X position mapping tests passed!")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

if __name__ == "__main__":
    success = test_field_position_fix()
    exit(0 if success else 1)
