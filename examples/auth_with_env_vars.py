#!/usr/bin/env python3
"""
Example: Authenticating with Environment Variables

This example demonstrates how the IPTVPortal client automatically
authenticates using credentials from environment variables.

Prerequisites:
    Set these environment variables:
    - IPTVPORTAL_DOMAIN
    - IPTVPORTAL_USERNAME
    - IPTVPORTAL_PASSWORD

Usage:
    python examples/auth_with_env_vars.py
"""

from iptvportal import IPTVPortalClient


def main():
    """Demonstrate environment variable authentication."""
    
    print("=" * 70)
    print("IPTVPortal Environment Variable Authentication Example")
    print("=" * 70)
    print()
    
    print("Creating client without explicit configuration...")
    print("(Automatically loads from IPTVPORTAL_* environment variables)")
    print()
    
    try:
        # Create client without passing any settings
        # It will automatically use environment variables
        with IPTVPortalClient() as client:
            print("✓ Successfully authenticated!")
            print(f"  Domain: {client.settings.domain}")
            print(f"  Username: {client.settings.username}")
            print(f"  Auth URL: {client.settings.auth_url}")
            print()
            
            # Example 1: Count subscribers
            print("Example 1: Counting subscribers...")
            query = client.query.select(
                data=[{"function": "count", "args": ["*"]}],
                from_="subscriber"
            )
            result = client.execute(query)
            print(f"  Total subscribers: {result[0][0] if result else 'N/A'}")
            print()
            
            # Example 2: Get first 5 subscribers
            print("Example 2: Fetching first 5 subscribers...")
            query = client.query.select(
                data=["id", "username", "login"],
                from_="subscriber",
                limit=5
            )
            result = client.execute(query)
            print(f"  Retrieved {len(result)} subscribers")
            for row in result:
                print(f"    - ID: {row[0]}, Username: {row[1]}, Login: {row[2]}")
            print()
            
            # Example 3: Get TV channels count
            print("Example 3: Counting TV channels...")
            query = client.query.select(
                data=[{"function": "count", "args": ["*"]}],
                from_="tv_channel"
            )
            result = client.execute(query)
            print(f"  Total channels: {result[0][0] if result else 'N/A'}")
            print()
            
            print("=" * 70)
            print("✓ All examples completed successfully!")
            print("=" * 70)
            
    except Exception as e:
        print(f"✗ Error: {e}")
        print()
        print("Make sure these environment variables are set:")
        print("  - IPTVPORTAL_DOMAIN")
        print("  - IPTVPORTAL_USERNAME")
        print("  - IPTVPORTAL_PASSWORD")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
