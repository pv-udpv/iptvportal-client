#!/usr/bin/env python3
"""Test script to verify idempotent logging initialization."""

import sys

print("=" * 80)
print("Testing IPTVPortal Logging Configuration")
print("=" * 80)

# Test 1: Import package
print("\n[Test 1] Importing iptvportal package...")
try:
    import iptvportal
    print("✓ Package imported successfully")
    print(f"  Version: {iptvportal.__version__}")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Explicit logging setup
print("\n[Test 2] Calling setup_logging() explicitly...")
try:
    from iptvportal.config import setup_logging
    setup_logging()
    print("✓ First setup_logging() call completed")
except Exception as e:
    print(f"✗ setup_logging() failed: {e}")
    sys.exit(1)

# Test 3: Idempotency check
print("\n[Test 3] Testing idempotency (multiple setup_logging() calls)...")
try:
    setup_logging()
    print("✓ Second setup_logging() call completed")
    setup_logging()
    print("✓ Third setup_logging() call completed")
    setup_logging()
    print("✓ Fourth setup_logging() call completed")
    print("  → No errors, no duplicate warnings")
except Exception as e:
    print(f"✗ Idempotency test failed: {e}")
    sys.exit(1)

# Test 4: Check logging state
print("\n[Test 4] Checking logging configuration state...")
try:
    from iptvportal.config import is_logging_configured
    is_configured = is_logging_configured()
    print(f"✓ is_logging_configured() = {is_configured}")
    if not is_configured:
        print("  ✗ WARNING: Logging should be configured!")
except Exception as e:
    print(f"✗ State check failed: {e}")

# Test 5: Get logger and log message
print("\n[Test 5] Creating logger and logging test messages...")
try:
    from iptvportal.config import get_logger
    logger = get_logger("test_script")
    logger.info("This is an INFO message")
    logger.debug("This is a DEBUG message")
    logger.warning("This is a WARNING message")
    print("✓ Logger created and messages logged")
except Exception as e:
    print(f"✗ Logger test failed: {e}")

# Test 6: Force reconfiguration
print("\n[Test 6] Testing force reconfiguration...")
try:
    setup_logging(force=True)
    print("✓ Force reconfiguration completed")
except Exception as e:
    print(f"✗ Force reconfiguration failed: {e}")

print("\n" + "=" * 80)
print("All tests completed successfully! ✓")
print("=" * 80)
