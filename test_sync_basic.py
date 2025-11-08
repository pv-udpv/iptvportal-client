#!/usr/bin/env python3
"""Basic test script for sync functionality."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_sync_database():
    """Test basic sync database functionality."""
    try:
        from iptvportal.sync.database import SyncDatabase

        # Create minimal settings
        class TestSettings:
            def __init__(self):
                self.cache_db_path = ":memory:"  # In-memory database for testing
                self.cache_db_journal_mode = "MEMORY"
                self.cache_db_page_size = 4096
                self.cache_db_cache_size = -64000

        settings = TestSettings()
        db = SyncDatabase(settings.cache_db_path, settings)

        # Initialize database
        db.initialize()
        print("✅ Database initialized successfully")

        # Test stats
        stats = db.get_stats()
        print(f"✅ Database stats: {stats}")

        # Test query execution
        result = db.execute_query("_sync_metadata", "SELECT COUNT(*) as count FROM _sync_metadata")
        print(f"✅ Metadata table query: {result}")

        print("✅ All sync database tests passed!")
        return True

    except Exception as e:
        print(f"❌ Sync database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sync_cli():
    """Test basic CLI functionality."""
    try:
        from iptvportal.cli.commands.sync import get_database

        # Test database creation
        db = get_database()
        db.initialize()
        print("✅ CLI database initialization successful")

        # Test stats
        stats = db.get_stats()
        print(f"✅ CLI database stats: {stats}")

        print("✅ All sync CLI tests passed!")
        return True

    except Exception as e:
        print(f"❌ Sync CLI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Testing sync functionality...")

    success = True
    success &= test_sync_database()
    success &= test_sync_cli()

    if success:
        print("\n🎉 All sync tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some sync tests failed!")
        sys.exit(1)
