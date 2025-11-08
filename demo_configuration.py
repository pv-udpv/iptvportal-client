#!/usr/bin/env python3
"""
Demonstration of the dynaconf-based configuration system.

This script showcases the key features of the new modular configuration.
"""

import sys
from pathlib import Path

# Add src to path for direct module access
sys.path.insert(0, str(Path(__file__).parent / "src" / "iptvportal"))

import project_conf

def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def demo_basic_access():
    """Demonstrate basic configuration access."""
    print_section("1. Basic Configuration Access")
    
    conf = project_conf.get_conf()
    
    print("Core Settings:")
    print(f"  timeout: {conf.core.timeout}s")
    print(f"  max_retries: {conf.core.max_retries}")
    print(f"  session_ttl: {conf.core.session_ttl}s")
    
    print("\nCLI Settings:")
    print(f"  default_format: {conf.cli.default_format}")
    print(f"  max_limit: {conf.cli.max_limit}")
    print(f"  enable_guardrails: {conf.cli.enable_guardrails}")
    
    print("\nSync Settings:")
    print(f"  default_sync_strategy: {conf.sync.default_sync_strategy}")
    print(f"  default_chunk_size: {conf.sync.default_chunk_size}")


def demo_schema_overrides():
    """Demonstrate schema-specific configuration overrides."""
    print_section("2. Schema-Specific Configuration Overrides")
    
    conf = project_conf.get_conf()
    
    print("Global default sync strategy:", conf.sync.default_sync_strategy)
    print()
    
    print("Schema-specific overrides:")
    print(f"  Subscriber:")
    print(f"    strategy: {conf.sync.subscriber.strategy}")
    print(f"    ttl: {conf.sync.subscriber.ttl}s ({conf.sync.subscriber.ttl // 60} minutes)")
    print(f"    priority: {conf.sync.subscriber.priority}")
    
    print(f"\n  Terminal:")
    print(f"    strategy: {conf.sync.terminal.strategy}")
    print(f"    ttl: {conf.sync.terminal.ttl}s ({conf.sync.terminal.ttl // 3600} hours)")
    print(f"    priority: {conf.sync.terminal.priority}")
    
    print(f"\n  Package:")
    print(f"    strategy: {conf.sync.package.strategy}")
    print(f"    ttl: {conf.sync.package.ttl}s ({conf.sync.package.ttl // 3600} hours)")
    print(f"    priority: {conf.sync.package.priority}")


def demo_api_functions():
    """Demonstrate API functions."""
    print_section("3. Configuration API Functions")
    
    print("get_value() - Get specific values:")
    timeout = project_conf.get_value("core.timeout")
    print(f"  core.timeout = {timeout}")
    
    subscriber_ttl = project_conf.get_value("sync.subscriber.ttl")
    print(f"  sync.subscriber.ttl = {subscriber_ttl}")
    
    # Get with default
    custom = project_conf.get_value("custom.nonexistent", default="DEFAULT")
    print(f"  custom.nonexistent = {custom}")
    
    print("\nset_value() - Runtime modification:")
    original = project_conf.get_value("core.timeout")
    print(f"  Original timeout: {original}s")
    
    project_conf.set_value("core.timeout", 120.0)
    updated = project_conf.get_value("core.timeout")
    print(f"  Updated timeout: {updated}s")
    print("  (Note: Changes are runtime-only, not persisted)")
    
    # Reset for demo
    project_conf.set_value("core.timeout", original)
    
    print("\nlist_settings() - Get configuration sections:")
    core_settings = project_conf.list_settings("core")
    print(f"  Core settings keys: {list(core_settings.keys())[:5]}...")


def demo_config_files():
    """Show loaded configuration files."""
    print_section("4. Configuration Files")
    
    files = project_conf.get_config_files()
    print(f"Loaded {len(files)} configuration files:\n")
    
    for i, file_path in enumerate(files, 1):
        # Show relative path for readability
        path = Path(file_path)
        if path.is_relative_to(Path.cwd()):
            display_path = path.relative_to(Path.cwd())
        else:
            display_path = path
        print(f"  {i}. {display_path}")


def demo_use_cases():
    """Show practical use cases."""
    print_section("5. Practical Use Cases")
    
    conf = project_conf.get_conf()
    
    print("Use Case 1: Determining sync strategy for a table")
    print("  For subscriber table:")
    print(f"    strategy = {conf.sync.subscriber.strategy}")
    print(f"    chunk_size = {conf.sync.subscriber.chunk_size}")
    print(f"    This uses incremental sync for frequently updated data")
    
    print("\n  For package table:")
    print(f"    strategy = {conf.sync.package.strategy}")
    print(f"    ttl = {conf.sync.package.ttl}s")
    print(f"    This uses on-demand sync for rarely changing data")
    
    print("\nUse Case 2: CLI safety checks")
    if conf.cli.enable_guardrails:
        print(f"  Guardrails enabled:")
        print(f"    - Max LIMIT: {conf.cli.max_limit}")
        print(f"    - Warn on LIMIT > {conf.cli.warn_large_limit}")
        print(f"    - Confirm destructive queries: {conf.cli.confirm_destructive_queries}")
    
    print("\nUse Case 3: Caching configuration")
    print(f"  Query cache enabled: {conf.cli.enable_query_cache}")
    print(f"  Cache TTL: {conf.cli.cache_ttl_seconds}s")
    print(f"  Cache size: {conf.cli.cache_max_size_mb}MB")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 70)
    print("  IPTVPORTAL CONFIGURATION SYSTEM DEMONSTRATION")
    print("  Dynaconf-based Modular Configuration")
    print("=" * 70)
    
    try:
        demo_basic_access()
        demo_schema_overrides()
        demo_api_functions()
        demo_config_files()
        demo_use_cases()
        
        print("\n" + "=" * 70)
        print("  ✓ DEMONSTRATION COMPLETE")
        print("=" * 70)
        print("\nFor more information, see docs/configuration.md")
        print("\n")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
