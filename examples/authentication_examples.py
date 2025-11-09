"""
Authentication Examples for IPTVPortal Client

This file demonstrates various authentication scenarios and patterns.

⚠️  SAFETY NOTICE: All examples use READ-ONLY operations (SELECT queries only).
    No UPDATE or DELETE operations are performed to protect production data.
"""

import asyncio
import os

from iptvportal import AsyncIPTVPortalClient, IPTVPortalClient
from iptvportal.config import IPTVPortalSettings
from iptvportal.exceptions import AuthenticationError, ConnectionError, TimeoutError


def example_1_basic_sync_auth():
    """Example 1: Basic synchronous authentication with environment variables."""
    print("\n=== Example 1: Basic Sync Authentication ===")

    try:
        # Credentials loaded from environment variables or .env file
        with IPTVPortalClient() as client:
            print("✓ Authentication successful!")
            print(f"Session ID: {client._session_id}")

            # Execute a simple query
            result = client.execute(
                {"method": "select", "params": {"from": "subscriber", "limit": 1}}
            )
            print(f"Query result: {result}")

    except AuthenticationError as e:
        print(f"✗ Authentication failed: {e.message}")
    except Exception as e:
        print(f"✗ Error: {e}")


def example_2_explicit_config():
    """Example 2: Authentication with explicit configuration."""
    print("\n=== Example 2: Explicit Configuration ===")

    # Configure explicitly instead of using environment variables
    settings = IPTVPortalSettings(
        domain=os.getenv("IPTVPORTAL_DOMAIN", "example"),
        username=os.getenv("IPTVPORTAL_USERNAME", "admin"),
        password=os.getenv("IPTVPORTAL_PASSWORD", "password"),
        session_cache=True,
        session_ttl=3600,
        timeout=30.0,
    )

    try:
        with IPTVPortalClient(settings=settings):
            print("✓ Authentication successful!")
            print(f"Domain: {settings.domain}")
            print(f"Auth URL: {settings.auth_url}")
            print(f"Session caching: {settings.session_cache}")
            print(f"Session TTL: {settings.session_ttl}s")

    except AuthenticationError as e:
        print(f"✗ Authentication failed: {e.message}")


async def example_3_async_auth():
    """Example 3: Asynchronous authentication."""
    print("\n=== Example 3: Async Authentication ===")

    try:
        async with AsyncIPTVPortalClient() as client:
            print("✓ Async authentication successful!")
            print(f"Session ID: {client._session_id}")

            # Execute query asynchronously
            result = await client.execute(
                {"method": "select", "params": {"from": "subscriber", "limit": 1}}
            )
            print(f"Query result: {result}")

    except AuthenticationError as e:
        print(f"✗ Authentication failed: {e.message}")


def example_4_manual_connection():
    """Example 4: Manual connection and authentication control."""
    print("\n=== Example 4: Manual Connection Control ===")

    client = IPTVPortalClient()

    try:
        # Manually connect and authenticate
        client.connect()
        print("✓ Connected and authenticated")
        print(f"Session ID: {client._session_id}")

        # Execute operations
        result = client.execute({"method": "select", "params": {"from": "subscriber", "limit": 1}})
        print(f"Query executed: {len(result)} rows")

    except AuthenticationError as e:
        print(f"✗ Authentication failed: {e.message}")
    finally:
        # Always close the connection
        client.close()
        print("Connection closed")


def example_5_error_handling():
    """Example 5: Comprehensive error handling."""
    print("\n=== Example 5: Error Handling ===")

    settings = IPTVPortalSettings(
        domain="invalid_domain",  # Intentionally invalid
        username="test_user",
        password="test_password",
        timeout=5.0,
        max_retries=1,
    )

    try:
        with IPTVPortalClient(settings=settings):
            print("Connected successfully")

    except AuthenticationError as e:
        print("✗ Authentication Error:")
        print(f"  Message: {e.message}")
        print(f"  Details: {e.details}")

    except ConnectionError as e:
        print("✗ Connection Error:")
        print(f"  Message: {e.message}")

    except TimeoutError as e:
        print("✗ Timeout Error:")
        print(f"  Message: {e.message}")

    except Exception as e:
        print("✗ Unexpected Error:")
        print(f"  Type: {type(e).__name__}")
        print(f"  Message: {e}")


def example_6_session_caching():
    """Example 6: Session caching demonstration."""
    print("\n=== Example 6: Session Caching ===")

    settings = IPTVPortalSettings(
        domain=os.getenv("IPTVPORTAL_DOMAIN", "example"),
        username=os.getenv("IPTVPORTAL_USERNAME", "admin"),
        password=os.getenv("IPTVPORTAL_PASSWORD", "password"),
        session_cache=True,
        session_ttl=300,  # 5 minutes
    )

    try:
        # First connection - authenticates
        with IPTVPortalClient(settings=settings) as client:
            print("✓ First connection - authenticated")
            session_id_1 = client._session_id
            print(f"  Session ID: {session_id_1}")

        # Second connection - uses cached session
        with IPTVPortalClient(settings=settings) as client:
            print("✓ Second connection - using cached session")
            session_id_2 = client._session_id
            print(f"  Session ID: {session_id_2}")
            print(f"  Same session: {session_id_1 == session_id_2}")

    except Exception as e:
        print(f"✗ Error: {e}")


def example_7_no_cache():
    """Example 7: Authentication without caching."""
    print("\n=== Example 7: No Session Caching ===")

    settings = IPTVPortalSettings(
        domain=os.getenv("IPTVPORTAL_DOMAIN", "example"),
        username=os.getenv("IPTVPORTAL_USERNAME", "admin"),
        password=os.getenv("IPTVPORTAL_PASSWORD", "password"),
        session_cache=False,  # Disable caching
    )

    try:
        # Each connection authenticates independently
        with IPTVPortalClient(settings=settings) as client:
            print("✓ Connection 1 - authenticated")
            session_id_1 = client._session_id

        with IPTVPortalClient(settings=settings) as client:
            print("✓ Connection 2 - authenticated (no cache)")
            session_id_2 = client._session_id
            print(f"  Different sessions: {session_id_1 != session_id_2}")

    except Exception as e:
        print(f"✗ Error: {e}")


async def example_8_parallel_async():
    """Example 8: Parallel async operations with single authentication."""
    print("\n=== Example 8: Parallel Async Operations ===")

    try:
        async with AsyncIPTVPortalClient() as client:
            print("✓ Authenticated once for multiple operations")

            # Execute multiple queries in parallel
            queries = [
                client.execute({"method": "select", "params": {"from": "subscriber", "limit": 1}}),
                client.execute({"method": "select", "params": {"from": "package", "limit": 1}}),
                client.execute({"method": "select", "params": {"from": "terminal", "limit": 1}}),
            ]

            results = await asyncio.gather(*queries)
            print(f"✓ Executed {len(results)} queries in parallel")
            for i, result in enumerate(results, 1):
                print(f"  Query {i}: {len(result)} rows")

    except Exception as e:
        print(f"✗ Error: {e}")


def example_9_multiple_accounts():
    """Example 9: Using multiple accounts simultaneously."""
    print("\n=== Example 9: Multiple Accounts ===")

    # Account 1 settings
    settings1 = IPTVPortalSettings(
        domain=os.getenv("IPTVPORTAL_DOMAIN", "account1"),
        username=os.getenv("IPTVPORTAL_USERNAME", "user1"),
        password=os.getenv("IPTVPORTAL_PASSWORD", "pass1"),
    )

    # Account 2 settings (would be different in real scenario)
    settings2 = IPTVPortalSettings(
        domain=os.getenv("IPTVPORTAL_DOMAIN_2", "account2"),
        username=os.getenv("IPTVPORTAL_USERNAME_2", "user2"),
        password=os.getenv("IPTVPORTAL_PASSWORD_2", "pass2"),
    )

    try:
        # Use both accounts independently
        with IPTVPortalClient(settings=settings1) as client1:
            print(f"✓ Account 1 authenticated: {settings1.username}")
            client1.execute({"method": "select", "params": {"from": "subscriber", "limit": 1}})

        with IPTVPortalClient(settings=settings2) as client2:
            print(f"✓ Account 2 authenticated: {settings2.username}")
            client2.execute({"method": "select", "params": {"from": "subscriber", "limit": 1}})

        print("✓ Both accounts worked successfully")

    except Exception as e:
        print(f"✗ Error: {e}")


def example_10_custom_retry_logic():
    """Example 10: Custom retry and timeout configuration."""
    print("\n=== Example 10: Custom Retry Configuration ===")

    settings = IPTVPortalSettings(
        domain=os.getenv("IPTVPORTAL_DOMAIN", "example"),
        username=os.getenv("IPTVPORTAL_USERNAME", "admin"),
        password=os.getenv("IPTVPORTAL_PASSWORD", "password"),
        timeout=60.0,  # 1 minute timeout
        max_retries=5,  # 5 retry attempts
        retry_delay=2.0,  # 2 second initial delay (exponential backoff)
    )

    try:
        with IPTVPortalClient(settings=settings):
            print("✓ Connected with custom retry settings")
            print(f"  Timeout: {settings.timeout}s")
            print(f"  Max retries: {settings.max_retries}")
            print(f"  Retry delay: {settings.retry_delay}s")

    except Exception as e:
        print(f"✗ Error: {e}")


def main():
    """Run all examples."""
    print("IPTVPortal Authentication Examples")
    print("=" * 50)

    # Check if environment variables are set
    required_vars = ["IPTVPORTAL_DOMAIN", "IPTVPORTAL_USERNAME", "IPTVPORTAL_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"\n⚠ Warning: Missing environment variables: {', '.join(missing_vars)}")
        print("Some examples may fail. Set these variables or create a .env file.\n")

    # Run synchronous examples
    example_1_basic_sync_auth()
    example_2_explicit_config()
    example_4_manual_connection()
    example_5_error_handling()
    example_6_session_caching()
    example_7_no_cache()
    example_9_multiple_accounts()
    example_10_custom_retry_logic()

    # Run async examples
    print("\n--- Async Examples ---")
    asyncio.run(example_3_async_auth())
    asyncio.run(example_8_parallel_async())

    print("\n" + "=" * 50)
    print("All examples completed!")


if __name__ == "__main__":
    main()
