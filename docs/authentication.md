# Authentication Guide

Complete guide to setting up and using authentication with IPTVPortal client.

## Overview

The IPTVPortal client uses session-based authentication via JSON-RPC. The authentication system supports:

- ✅ Secure credential storage using Pydantic `SecretStr`
- ✅ Session caching with configurable TTL
- ✅ Environment variable configuration
- ✅ GitHub Secrets integration for CI/CD
- ✅ Both synchronous and asynchronous modes
- ✅ Automatic session renewal
- ✅ Comprehensive error handling

## Quick Start

### 1. Set Up Credentials

#### Option A: Using `.env` File (Development)

Create a `.env` file in your project root:

```env
IPTVPORTAL_DOMAIN=your_domain
IPTVPORTAL_USERNAME=your_username
IPTVPORTAL_PASSWORD=your_password
```

The client will automatically load these variables.

#### Option B: Using Environment Variables (Production)

Export environment variables in your shell:

```bash
export IPTVPORTAL_DOMAIN=your_domain
export IPTVPORTAL_USERNAME=your_username
export IPTVPORTAL_PASSWORD=your_password
```

#### Option C: Using GitHub Secrets (CI/CD)

1. Go to your repository Settings → Secrets and variables → Actions
2. Add the following secrets:
   - `IPTVPORTAL_DOMAIN`
   - `IPTVPORTAL_USERNAME`
   - `IPTVPORTAL_PASSWORD`

3. Use in GitHub Actions workflow:

```yaml
name: Run Tests
on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests with authentication
        env:
          IPTVPORTAL_DOMAIN: ${{ secrets.IPTVPORTAL_DOMAIN }}
          IPTVPORTAL_USERNAME: ${{ secrets.IPTVPORTAL_USERNAME }}
          IPTVPORTAL_PASSWORD: ${{ secrets.IPTVPORTAL_PASSWORD }}
        run: |
          python -m pytest tests/
```

### 2. Test Authentication

Using the CLI:

```bash
# Check authentication status
iptvportal auth

# Force re-authentication (clear cache and get new session)
iptvportal auth --renew
```

## Configuration Options

### Authentication Settings

Configure authentication behavior in your `.env` file or via environment variables:

```env
# Connection timeout (default: 30.0 seconds)
IPTVPORTAL_TIMEOUT=30.0

# Maximum retry attempts (default: 3)
IPTVPORTAL_MAX_RETRIES=3

# Delay between retries in seconds (default: 1.0, uses exponential backoff)
IPTVPORTAL_RETRY_DELAY=1.0

# SSL certificate verification (default: true)
IPTVPORTAL_VERIFY_SSL=true

# Session caching (default: true)
IPTVPORTAL_SESSION_CACHE=true

# Session TTL in seconds (default: 3600 = 1 hour)
IPTVPORTAL_SESSION_TTL=3600

# Logging
IPTVPORTAL_LOG_LEVEL=INFO
IPTVPORTAL_LOG_REQUESTS=false
IPTVPORTAL_LOG_RESPONSES=false
```

## Usage Examples

### Python API - Synchronous

```python
from iptvportal import IPTVPortalClient
from iptvportal.config import IPTVPortalSettings

# Option 1: Auto-load from environment variables
with IPTVPortalClient() as client:
    # Authentication happens automatically in __enter__
    result = client.execute({
        "method": "select",
        "params": {
            "from": "subscriber",
            "limit": 5
        }
    })
    print(result)

# Option 2: Explicit configuration
settings = IPTVPortalSettings(
    domain="your_domain",
    username="your_username",
    password="your_password"
)

with IPTVPortalClient(settings=settings) as client:
    result = client.execute({
        "method": "select",
        "params": {
            "from": "subscriber",
            "limit": 5
        }
    })
```

### Python API - Asynchronous

```python
import asyncio
from iptvportal import AsyncIPTVPortalClient

async def main():
    # Auto-load from environment variables
    async with AsyncIPTVPortalClient() as client:
        # Authentication happens automatically in __aenter__
        result = await client.execute({
            "method": "select",
            "params": {
                "from": "subscriber",
                "limit": 5
            }
        })
        print(result)

asyncio.run(main())
```

### Manual Authentication Control

For advanced use cases where you need manual control:

```python
from iptvportal import IPTVPortalClient

client = IPTVPortalClient()

# Manually connect and authenticate
client.connect()

try:
    # Your operations here
    result = client.execute({"method": "select", "params": {"from": "subscriber"}})
finally:
    # Don't forget to close
    client.close()
```

### CLI Usage

```bash
# Test authentication
iptvportal auth

# Output shows:
# - Domain and username
# - Auth and API URLs
# - Session ID (after successful connection)
# - Connection status

# Force re-authentication (ignores cached session)
iptvportal auth --renew

# Use authentication with queries
iptvportal sql -q "SELECT * FROM subscriber LIMIT 5"
iptvportal jsonsql select --from subscriber --limit 5
```

## Session Caching

The authentication system includes intelligent session caching to minimize authentication requests:

### How It Works

1. **First Authentication**: Credentials are sent to the API, and a session ID is returned
2. **Session Storage**: The session ID and timestamp are cached in memory
3. **Subsequent Requests**: Cached session is reused if still valid (within TTL)
4. **Expiration**: After TTL expires, a new authentication is performed automatically

### Cache Configuration

```python
from iptvportal.config import IPTVPortalSettings

settings = IPTVPortalSettings(
    domain="your_domain",
    username="your_username",
    password="your_password",
    session_cache=True,      # Enable/disable caching
    session_ttl=3600        # Cache lifetime in seconds (1 hour)
)
```

### Disabling Cache

For testing or security-sensitive scenarios, you can disable session caching:

```python
settings = IPTVPortalSettings(
    domain="your_domain",
    username="your_username",
    password="your_password",
    session_cache=False  # Authenticate on every request
)
```

Or via environment:

```env
IPTVPORTAL_SESSION_CACHE=false
```

## Error Handling

The authentication system provides detailed error information:

### Common Errors

#### 1. Invalid Credentials

```python
from iptvportal.exceptions import AuthenticationError

try:
    with IPTVPortalClient() as client:
        pass
except AuthenticationError as e:
    print(f"Authentication failed: {e.message}")
    print(f"Details: {e.details}")
```

Output:
```
Authentication failed: Invalid credentials
Details: {'code': -32001, 'message': 'Invalid credentials'}
```

#### 2. Connection Errors

```python
from iptvportal.exceptions import ConnectionError

try:
    with IPTVPortalClient() as client:
        pass
except ConnectionError as e:
    print(f"Connection failed: {e.message}")
```

#### 3. Timeout Errors

```python
from iptvportal.exceptions import TimeoutError

settings = IPTVPortalSettings(
    domain="your_domain",
    username="your_username",
    password="your_password",
    timeout=5.0  # Short timeout for demonstration
)

try:
    with IPTVPortalClient(settings=settings) as client:
        pass
except TimeoutError as e:
    print(f"Request timeout: {e.message}")
```

### Error Hierarchy

```
IPTVPortalError (base)
├── AuthenticationError  # Authentication failures
├── ConnectionError      # Network connection issues
├── TimeoutError        # Request timeouts
├── APIError            # API-level errors
└── ValidationError     # Data validation errors
```

## Security Best Practices

### 1. Never Commit Credentials

Add to `.gitignore`:

```gitignore
.env
.env.local
*.secret
```

### 2. Use Different Credentials Per Environment

```env
# .env.development
IPTVPORTAL_DOMAIN=dev_domain
IPTVPORTAL_USERNAME=dev_user
IPTVPORTAL_PASSWORD=dev_password

# .env.production
IPTVPORTAL_DOMAIN=prod_domain
IPTVPORTAL_USERNAME=prod_user
IPTVPORTAL_PASSWORD=prod_password
```

### 3. Rotate Credentials Regularly

Update credentials periodically and clear cached sessions:

```bash
# Update environment variables
export IPTVPORTAL_USERNAME=new_username
export IPTVPORTAL_PASSWORD=new_password

# Force re-authentication
iptvportal auth --renew
```

### 4. Use Read-Only Accounts When Possible

For reporting or read-only operations, use accounts with limited permissions.

### 5. Enable SSL Verification in Production

```env
# Always verify SSL in production
IPTVPORTAL_VERIFY_SSL=true

# Only disable for local development/testing
# IPTVPORTAL_VERIFY_SSL=false
```

### 6. Monitor Authentication Logs

Enable request logging for security auditing:

```env
IPTVPORTAL_LOG_REQUESTS=true
IPTVPORTAL_LOG_LEVEL=INFO
```

## Troubleshooting

### Issue: "Authentication failed: Invalid credentials"

**Solutions:**
1. Verify credentials are correct:
   ```bash
   echo $IPTVPORTAL_USERNAME
   echo $IPTVPORTAL_DOMAIN
   ```

2. Check if password contains special characters that need escaping

3. Try authenticating via CLI:
   ```bash
   iptvportal auth
   ```

### Issue: "Connection failed" or "Request timeout"

**Solutions:**
1. Check network connectivity:
   ```bash
   curl https://your_domain.admin.iptvportal.ru/api/jsonrpc/
   ```

2. Increase timeout:
   ```env
   IPTVPORTAL_TIMEOUT=60.0
   ```

3. Check firewall/proxy settings

### Issue: Session expires too quickly

**Solutions:**
1. Increase session TTL:
   ```env
   IPTVPORTAL_SESSION_TTL=7200  # 2 hours
   ```

2. Enable session caching if disabled:
   ```env
   IPTVPORTAL_SESSION_CACHE=true
   ```

### Issue: "No session_id in response"

**Solutions:**
1. Verify API endpoint is correct
2. Check server logs for issues
3. Contact API administrator

## Advanced Topics

### Custom Authentication Flow

For advanced scenarios, you can create custom authentication logic:

```python
from iptvportal.auth import AuthManager
from iptvportal.config import IPTVPortalSettings
import httpx

settings = IPTVPortalSettings(
    domain="your_domain",
    username="your_username",
    password="your_password"
)

auth_manager = AuthManager(settings)

with httpx.Client() as http_client:
    # Get session ID
    session_id = auth_manager.authenticate(http_client)
    
    # Use session ID for custom requests
    response = http_client.post(
        settings.api_url,
        json={"method": "select", "params": {"from": "subscriber"}},
        headers={"Iptvportal-Authorization": f"sessionid={session_id}"}
    )
```

### Multi-Account Support

Managing multiple accounts:

```python
from iptvportal.config import IPTVPortalSettings
from iptvportal import IPTVPortalClient

# Account 1
settings1 = IPTVPortalSettings(
    domain="account1_domain",
    username="user1",
    password="pass1"
)

# Account 2
settings2 = IPTVPortalSettings(
    domain="account2_domain",
    username="user2",
    password="pass2"
)

# Use different clients
with IPTVPortalClient(settings=settings1) as client1:
    result1 = client1.execute({"method": "select", "params": {"from": "subscriber"}})

with IPTVPortalClient(settings=settings2) as client2:
    result2 = client2.execute({"method": "select", "params": {"from": "subscriber"}})
```

## API Reference

### AuthManager

Synchronous authentication manager.

**Methods:**
- `authenticate(http_client: httpx.Client) -> str`: Authenticate and return session ID
- `session_id -> str | None`: Get cached session ID if valid

### AsyncAuthManager

Asynchronous authentication manager.

**Methods:**
- `async authenticate(http_client: httpx.AsyncClient) -> str`: Authenticate and return session ID
- `session_id -> str | None`: Get cached session ID if valid

### IPTVPortalSettings

Configuration model for authentication.

**Key Parameters:**
- `domain: str`: Operator subdomain
- `username: str`: Admin username
- `password: SecretStr`: Admin password (securely stored)
- `session_cache: bool`: Enable session caching (default: True)
- `session_ttl: int`: Session lifetime in seconds (default: 3600)
- `timeout: float`: Request timeout (default: 30.0)
- `max_retries: int`: Max retry attempts (default: 3)
- `verify_ssl: bool`: Verify SSL certificates (default: True)

**Properties:**
- `auth_url -> str`: Authorization endpoint URL
- `api_url -> str`: API endpoint URL

## See Also

- [Configuration Guide](configuration.md)
- [CLI Documentation](cli.md)
- [Error Handling](../README.md#error-handling)
- [API Reference](../README.md#api-reference)
