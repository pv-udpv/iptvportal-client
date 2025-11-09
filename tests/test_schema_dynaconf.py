#!/usr/bin/env python3
"""Test schema loading functionality with Dynaconf."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

# We're in tests/ directory, so repo is parent
REPO_DIR = Path(__file__).parent.parent

# Ensure we run from repo directory for Dynaconf to find config/
import os
os.chdir(REPO_DIR)

# Now import after cwd is set
from iptvportal.cli.utils import load_config
from iptvportal.core.client import IPTVPortalClient
from iptvportal.schema import SchemaLoader


def test_dynaconf_config_loading():
    """Test that Dynaconf config is loaded correctly."""
    print("Test 1: Dynaconf config loading")
    settings = load_config()
    
    assert settings.schema_file is not None, f"schema_file should be set, got: {settings.schema_file}"
    assert settings.auto_load_schemas is True, "auto_load_schemas should be True"
    assert settings.schema_format == "yaml", "schema_format should be yaml"
    
    print(f"  ✓ schema_file: {settings.schema_file}")
    print(f"  ✓ auto_load_schemas: {settings.auto_load_schemas}")
    print(f"  ✓ schema_format: {settings.schema_format}")
    print()


def test_directory_schema_loading():
    """Test that schemas are loaded from directory."""
    print("Test 2: Directory schema loading")
    settings = load_config()
    
    # Mock connect to avoid network call
    with patch.object(IPTVPortalClient, 'connect', Mock()):
        client = IPTVPortalClient(settings)
        tables = client.schema_registry.list_tables()
        
        assert len(tables) > 0, f"Should load at least one schema (got {len(tables)})"
        
        print(f"  ✓ Loaded {len(tables)} schemas:")
        for table_name in sorted(tables):
            schema = client.schema_registry.get(table_name)
            print(f"    - {table_name}: {schema.total_fields} fields")
    print()


def test_empty_schema_file():
    """Test that empty schema files don't cause errors."""
    print("Test 3: Empty schema file handling")
    
    # Use the actual empty schemas.yaml file
    empty_yaml = REPO_DIR / "config" / "schemas.yaml"
    
    registry = SchemaLoader.from_yaml(str(empty_yaml))
    tables = registry.list_tables()
    
    assert len(tables) == 0, "Empty file should load 0 schemas"
    print("  ✓ Empty file handled gracefully (0 schemas)")
    print()


def test_single_schema_file():
    """Test loading from a single schema file."""
    print("Test 4: Single schema file loading")
    
    schema_file = REPO_DIR / "config" / "media-schema.yaml"
    if schema_file.exists():
        registry = SchemaLoader.from_yaml(str(schema_file))
        tables = registry.list_tables()
        
        assert len(tables) == 1, f"Should load exactly 1 schema, got {len(tables)}"
        assert "media" in tables, f"Should have 'media' table, got: {tables}"
        
        schema = registry.get("media")
        print(f"  ✓ Loaded media schema: {schema.total_fields} fields")
    else:
        print("  ⚠ Skipped (media-schema.yaml not found)")
    print()


def test_none_config_handling():
    """Test that None config is handled."""
    print("Test 5: None config handling")
    
    registry = SchemaLoader.from_dict(None)
    tables = registry.list_tables()
    
    assert len(tables) == 0, "None config should load 0 schemas"
    print("  ✓ None config handled gracefully")
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("Schema Loading Tests")
    print("=" * 60)
    print()
    
    try:
        test_dynaconf_config_loading()
        test_directory_schema_loading()
        test_empty_schema_file()
        test_single_schema_file()
        test_none_config_handling()
        
        print("=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        sys.exit(0)
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
