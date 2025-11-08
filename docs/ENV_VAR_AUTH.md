# Environment Variable Authentication - Implementation Guide

## Overview

The IPTVPortal client **already supports** authentication via environment variables using Pydantic Settings. This document demonstrates how it works and provides examples.

## How It Works

The `IPTVPortalSettings` class in `src/iptvportal/config.py` uses Pydantic's `BaseSettings` with the following configuration:

```python
model_config = SettingsConfigDict(
    env_prefix="IPTVPORTAL_",
    env_file=".env",
    env_file_encoding="utf-8",
    case_sensitive=False,
    extra="ignore",
)
```

This automatically loads configuration from:
1. Environment variables with `IPTVPORTAL_` prefix
2. `.env` file in the current directory
3. Direct constructor arguments (highest priority)

## Required Environment Variables

```bash
IPTVPORTAL_DOMAIN=your_domain       # Operator subdomain
IPTVPORTAL_USERNAME=your_username   # Admin username
IPTVPORTAL_PASSWORD=your_password   # Admin password
```

## Optional Environment Variables

```bash
# HTTP Settings
IPTVPORTAL_TIMEOUT=30.0            # Request timeout in seconds (default: 30.0)
IPTVPORTAL_MAX_RETRIES=3           # Maximum retry attempts (default: 3)
IPTVPORTAL_RETRY_DELAY=1.0         # Retry delay in seconds (default: 1.0)
IPTVPORTAL_VERIFY_SSL=true         # Verify SSL certificates (default: true)

# Session Management
IPTVPORTAL_SESSION_CACHE=true      # Cache session ID (default: true)
IPTVPORTAL_SESSION_TTL=3600        # Session TTL in seconds (default: 3600)

# Logging
IPTVPORTAL_LOG_LEVEL=INFO          # Logging level (default: INFO)
IPTVPORTAL_LOG_REQUESTS=false      # Log HTTP requests (default: false)
IPTVPORTAL_LOG_RESPONSES=false     # Log HTTP responses (default: false)

# Schema Configuration
IPTVPORTAL_SCHEMA_FILE=path/to/schema.yaml  # Path to schema file
IPTVPORTAL_SCHEMA_FORMAT=yaml      # Schema format: yaml or json
IPTVPORTAL_AUTO_LOAD_SCHEMAS=true  # Auto-load schemas (default: true)

# Query Caching
IPTVPORTAL_ENABLE_QUERY_CACHE=true # Enable query caching (default: true)
IPTVPORTAL_CACHE_TTL=300           # Cache TTL in seconds (default: 300)
IPTVPORTAL_CACHE_MAX_SIZE=1000     # Max cached queries (default: 1000)

# Query Optimization
IPTVPORTAL_AUTO_ORDER_BY_ID=true   # Auto ORDER BY id (default: true)

# SQLite Cache Settings
IPTVPORTAL_CACHE_DB_PATH=~/.iptvportal/cache.db  # SQLite cache path
IPTVPORTAL_ENABLE_PERSISTENT_CACHE=true          # Enable persistent cache
IPTVPORTAL_CACHE_DB_JOURNAL_MODE=WAL             # SQLite journal mode
IPTVPORTAL_CACHE_DB_PAGE_SIZE=4096               # SQLite page size
IPTVPORTAL_CACHE_DB_CACHE_SIZE=-64000            # SQLite cache size

# Sync Behavior
IPTVPORTAL_DEFAULT_SYNC_STRATEGY=full            # Default sync strategy
IPTVPORTAL_DEFAULT_SYNC_TTL=3600                 # Default sync TTL
IPTVPORTAL_DEFAULT_CHUNK_SIZE=1000               # Default chunk size
IPTVPORTAL_AUTO_SYNC_ON_STARTUP=false            # Auto-sync on startup
IPTVPORTAL_AUTO_SYNC_STALE_TABLES=true          # Auto-sync stale tables
IPTVPORTAL_MAX_CONCURRENT_SYNCS=3                # Max concurrent syncs

# Maintenance
IPTVPORTAL_AUTO_VACUUM_ENABLED=true              # Auto-vacuum enabled
IPTVPORTAL_VACUUM_THRESHOLD_MB=100               # Vacuum threshold
IPTVPORTAL_AUTO_ANALYZE_ENABLED=true             # Auto-analyze enabled
IPTVPORTAL_ANALYZE_INTERVAL_HOURS=24             # Analyze interval
```

## Usage Examples

### 1. Using Environment Variables Directly

```bash
# Set environment variables
export IPTVPORTAL_DOMAIN=adstat
export IPTVPORTAL_USERNAME=admin
export IPTVPORTAL_PASSWORD=secret123

# Run queries directly - automatically authenticated
iptvportal sql -q "SELECT * FROM tv_channel LIMIT 10"
iptvportal sql -q "SELECT id, name, disabled FROM subscriber WHERE login LIKE 'admin%'"
iptvportal sql -q "SELECT COUNT(*) FROM media"

# Check authentication status
iptvportal auth

# Use different query formats
iptvportal jsonsql select --from tv_channel --limit 10
```

### 2. Using .env File

Create a `.env` file in your project:

```env
IPTVPORTAL_DOMAIN=adstat
IPTVPORTAL_USERNAME=admin
IPTVPORTAL_PASSWORD=secret123
IPTVPORTAL_TIMEOUT=45.0
IPTVPORTAL_VERIFY_SSL=false
```

Then use the client:

```python
from iptvportal import IPTVPortalClient

# Automatically loads from .env file
with IPTVPortalClient() as client:
    result = client.execute(
        client.query.select(
            data=["id", "name"],
            from_="subscriber",
            limit=10
        )
    )
    print(result)
```

### 3. Python Code Without Explicit Configuration

```python
from iptvportal import IPTVPortalClient

# No need to pass settings - automatically loads from env vars
with IPTVPortalClient() as client:
    # Client is already authenticated using env var credentials
    query = client.query.select(
        data=["id", "username"],
        from_="subscriber",
        limit=5
    )
    subscribers = client.execute(query)
```

### 4. Async Client

```python
import asyncio
from iptvportal import AsyncIPTVPortalClient

async def main():
    # Automatically uses env vars for authentication
    async with AsyncIPTVPortalClient() as client:
        query = client.query.select(
            data=["id", "name"],
            from_="tv_channel",
            limit=10
        )
        channels = await client.execute(query)
        print(channels)

asyncio.run(main())
```

### 5. CLI Commands

All CLI commands automatically use environment variables:

```bash
# Run SQL queries - most common use case
iptvportal sql -q "SELECT * FROM tv_channel LIMIT 10"
iptvportal sql -q "SELECT id, username, balance FROM subscriber WHERE disabled=false LIMIT 20"
iptvportal sql -q "SELECT COUNT(*) FROM media"

# Run JSONSQL queries
iptvportal jsonsql select --from tv_channel --limit 10
iptvportal jsonsql select --from subscriber --data id,username --limit 20

# Transpile SQL to JSONSQL (dry-run - see what will be executed)
iptvportal sql -q "SELECT * FROM media WHERE active=true" --dry-run

# Check authentication status (optional - queries auto-authenticate)
iptvportal auth

# Force re-authentication if needed
iptvportal auth --renew

# Show current configuration
iptvportal config show
```

## Configuration Priority

Settings are loaded in this order (later overrides earlier):

1. Default values in `IPTVPortalSettings`
2. Values from `.env` file
3. Environment variables (`IPTVPORTAL_*`)
4. Direct constructor arguments (if provided)

Example:
```python
from iptvportal import IPTVPortalClient, IPTVPortalSettings

# Use env vars
client1 = IPTVPortalClient()

# Override specific settings while keeping env vars for others
settings = IPTVPortalSettings(timeout=60.0)  # Uses env vars for domain/username/password
client2 = IPTVPortalClient(settings)

# Completely override with explicit settings
explicit_settings = IPTVPortalSettings(
    domain="custom",
    username="custom_user",
    password="custom_pass"
)
client3 = IPTVPortalClient(explicit_settings)
```

## Current Environment (GitHub Actions)

The following environment variables are currently set:

```bash
IPTVPORTAL_DOMAIN=adstat
IPTVPORTAL_USERNAME=pasha
IPTVPORTAL_PASSWORD=********** (hidden)
IPTVPORTAL_TIMEOUT=30
IPTVPORTAL_VERIFY_SSL=false
IPTVPORTAL_MAX_RETRIES=2
```

These can be used immediately for running queries:

```bash
# Run queries directly - authentication happens automatically
iptvportal sql -q "SELECT * FROM tv_channel LIMIT 10"
iptvportal sql -q "SELECT COUNT(*) FROM subscriber"

# Check auth status if needed
iptvportal auth
# ✓ Authentication successful
# Session ID: abc123...
```

## Testing Environment Variable Authentication

See `tests/test_auth_env_vars.py` for comprehensive unit tests covering:
- Loading settings from environment variables
- Authentication flow using env var credentials
- Environment variable precedence over .env files
- Required vs optional environment variables
- Error handling for missing or invalid credentials

## Implementation Details

The authentication flow:

1. `IPTVPortalSettings()` is instantiated
   - Pydantic automatically loads `IPTVPORTAL_*` env vars
   - Domain, username, password are loaded

2. `IPTVPortalClient(settings)` or `IPTVPortalClient()` is created
   - If no settings passed, creates `IPTVPortalSettings()` internally
   - Creates `AuthManager(settings)`

3. `client.connect()` is called
   - `auth_manager.authenticate(http_client)` is called
   - Sends JSON-RPC request with username/password from settings
   - Receives session_id and caches it

4. All subsequent API calls use the session_id
   - Header: `Iptvportal-Authorization: sessionid={session_id}`

## Security Notes

- Passwords are stored as `SecretStr` (Pydantic)
- Passwords are not logged or printed by default
- Session IDs are cached for performance (configurable via `IPTVPORTAL_SESSION_CACHE`)
- SSL verification is enabled by default (override with `IPTVPORTAL_VERIFY_SSL=false`)

## Conclusion

**The IPTVPortal client already fully supports environment variable authentication.** No code changes are needed - just set the `IPTVPORTAL_*` environment variables and use the client or CLI as normal.
