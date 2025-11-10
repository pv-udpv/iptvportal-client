# Environment Variable Authentication - Summary

## What Was Done

This PR documents and tests the **already existing** environment variable authentication feature in the IPTVPortal client.

## Key Finding

**The IPTVPortal client already fully supports authentication via environment variables!** 

The implementation has been in place since the beginning using Pydantic Settings with the `IPTVPORTAL_` prefix. No code changes were needed.

## What Was Added

### 1. Comprehensive Test Suite
**File:** `tests/test_auth_env_vars.py`

Complete unit test coverage for environment variable authentication:
- ✓ Settings loading from IPTVPORTAL_* environment variables
- ✓ Authentication flow using environment variable credentials
- ✓ URL generation from domain
- ✓ Environment variable precedence over .env files
- ✓ Optional vs required environment variables
- ✓ Error handling for missing credentials
- ✓ Configuration override behavior

### 2. Detailed Documentation
**File:** `docs/ENV_VAR_AUTH.md`

Comprehensive guide covering:
- Complete list of all 40+ IPTVPORTAL_* environment variables
- Usage examples for CLI and Python API (sync and async)
- Configuration priority explanation
- Current CI environment setup details
- Security considerations
- Implementation architecture

### 3. Working Example
**File:** `examples/auth_with_env_vars.py`

Practical example script demonstrating:
- Automatic authentication without explicit configuration
- Running multiple queries
- Clear error messages
- Best practices

### 4. Updated README
**File:** `README.md`

Enhanced configuration section to:
- Highlight environment variable support prominently
- Show both environment variable and .env file approaches
- Link to detailed documentation

## How Environment Variables Work

### Current Implementation

```python
# src/iptvportal/config.py
class IPTVPortalSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="IPTVPORTAL_",  # Automatic loading!
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )
    
    domain: str      # Loaded from IPTVPORTAL_DOMAIN
    username: str    # Loaded from IPTVPORTAL_USERNAME  
    password: SecretStr  # Loaded from IPTVPORTAL_PASSWORD
    # ... 40+ more settings
```

### Usage

```bash
# Set environment variables
export IPTVPORTAL_DOMAIN=adstat
export IPTVPORTAL_USERNAME=pasha
export IPTVPORTAL_PASSWORD=secret

# Run queries directly - automatically authenticated
iptvportal sql -q "SELECT * FROM tv_channel LIMIT 10"
iptvportal sql -q "SELECT id, username FROM subscriber LIMIT 20"
iptvportal sql -q "SELECT COUNT(*) FROM media"
```

```python
# Python - no configuration needed
from iptvportal import IPTVPortalClient

with IPTVPortalClient() as client:
    # Automatically uses env vars for auth
    query = client.query.select(
        data=["id", "name"],
        from_="tv_channel",
        limit=10
    )
    result = client.execute(query)
```

## Environment Variables Available

### Required
- `IPTVPORTAL_DOMAIN` - Operator subdomain
- `IPTVPORTAL_USERNAME` - Admin username
- `IPTVPORTAL_PASSWORD` - Admin password

### Optional (40+ settings)
- HTTP: `TIMEOUT`, `MAX_RETRIES`, `RETRY_DELAY`, `VERIFY_SSL`
- Session: `SESSION_CACHE`, `SESSION_TTL`
- Logging: `LOG_LEVEL`, `LOG_REQUESTS`, `LOG_RESPONSES`
- Schema: `SCHEMA_FILE`, `SCHEMA_FORMAT`, `AUTO_LOAD_SCHEMAS`
- Caching: `ENABLE_QUERY_CACHE`, `CACHE_TTL`, `CACHE_MAX_SIZE`
- SQLite: `CACHE_DB_PATH`, `ENABLE_PERSISTENT_CACHE`, `CACHE_DB_JOURNAL_MODE`
- Sync: `DEFAULT_SYNC_STRATEGY`, `DEFAULT_SYNC_TTL`, `DEFAULT_CHUNK_SIZE`
- Maintenance: `AUTO_VACUUM_ENABLED`, `VACUUM_THRESHOLD_MB`
- And many more...

See `docs/ENV_VAR_AUTH.md` for complete list.

## CI Environment Verification

The following environment variables are confirmed working in GitHub Actions:

```bash
IPTVPORTAL_DOMAIN=adstat
IPTVPORTAL_USERNAME=pasha
IPTVPORTAL_PASSWORD=********** (injected via secrets)
IPTVPORTAL_TIMEOUT=30
IPTVPORTAL_VERIFY_SSL=false
IPTVPORTAL_MAX_RETRIES=2
```

## Configuration Priority

Settings are loaded in this order (later overrides earlier):

1. Default values in `IPTVPortalSettings`
2. Values from `.env` file in current directory
3. Environment variables (`IPTVPORTAL_*`)
4. Direct constructor arguments (highest priority)

## Security Features

- Passwords stored as `SecretStr` (Pydantic)
- Passwords not logged or printed by default
- Session IDs cached for performance (configurable)
- SSL verification enabled by default
- Secrets automatically redacted in logs and error messages

## Testing

Run the test suite:
```bash
pytest tests/test_auth_env_vars.py -v
```

Run the example:
```bash
python examples/auth_with_env_vars.py
```

Manual verification:
```bash
python test_config_env_simple.py
```

## Documentation References

1. **Environment Variable Guide**: `docs/ENV_VAR_AUTH.md` - Complete reference
2. **Configuration Guide**: `docs/configuration.md` - Full configuration system
3. **CLI Guide**: `docs/cli.md` - CLI usage and commands
4. **API Reference**: Source code in `src/iptvportal/config.py`

## Conclusion

The IPTVPortal client has always supported environment variable authentication through Pydantic Settings. This PR:
- ✓ Documents the feature comprehensively
- ✓ Adds extensive test coverage
- ✓ Provides working examples
- ✓ Updates user-facing documentation

**No code changes were required** - the feature was already fully implemented and working!

Users can now confidently use environment variables for authentication by referring to the new documentation.
