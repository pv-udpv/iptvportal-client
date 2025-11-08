# IPTVPortal Client

Modern Python client for IPTVPortal JSONSQL API with full typing, async/sync support, and intuitive query building.

## Features

- 🚀 **Full Type Safety** - Complete type hints with Pydantic v2 validation
- ⚡ **Async/Sync APIs** - Identical interfaces for both paradigms
- 🔧 **Python DSL** - Intuitive query builder with Field API and Q objects
- 🔐 **Secure** - SecretStr for passwords, session caching, SSL verification
- 🔄 **Resilient** - Exponential backoff retry mechanism
- 📦 **Resource Managers** - High-level CRUD operations
- 🎯 **Context Managers** - Automatic connection management

## Installation

```bash
# Using pip
pip install iptvportal-client

# Using uv (recommended)
uv pip install iptvportal-client

# With CLI support
pip install iptvportal-client[cli]
```

## Quick Start

### Configuration

Create `.env` file:

```env
IPTVPORTAL_DOMAIN=adstat
IPTVPORTAL_USERNAME=your_username
IPTVPORTAL_PASSWORD=your_password
```

### Sync Client

```python
from iptvportal import IPTVPortalClient
from iptvportal.query import Field

with IPTVPortalClient() as client:
    # Using Query Builder
    query = client.query.select(
        data=["id", "name"],
        from_="tv_channel",
        limit=10
    )
    channels = client.execute(query)
    
    # Using Field API (Python-way)
    name = Field("name")
    disabled = Field("disabled")
    
    query = client.query.select(
        data=["id", "name"],
        from_="subscriber",
        where=(name.like("admin%")) & (disabled == False)
    )
    subscribers = client.execute(query)
```

### Async Client

```python
import asyncio
from iptvportal import AsyncIPTVPortalClient
from iptvportal.query import Q

async def main():
    async with AsyncIPTVPortalClient() as client:
        # Using Q Objects (Django-style)
        query = client.query.select(
            data=["id", "name"],
            from_="tv_channel",
            where=Q(name__like="%HD") & ~Q(disabled=True),
            limit=50
        )
        channels = await client.execute(query)
        
        # Parallel execution
        queries = [
            client.query.select(data=["id"], from_="subscriber"),
            client.query.select(data=["id"], from_="tv_channel"),
        ]
        results = await client.execute_many(queries)

asyncio.run(main())
```

## Query Building

Three ways to build queries:

### 1. Classic Query Builder

```python
from iptvportal.query import QueryBuilder, Q

qb = QueryBuilder()
query = qb.select(
    data=["id", "username", "email"],
    from_="subscriber",
    where=Q.and_(
        Q.eq("disabled", False),
        Q.gte("age", 18)
    ),
    limit=100
)
```

### 2. Field API (SQLAlchemy-style)

```python
from iptvportal.query import Field, QueryBuilder

username = Field("username")
age = Field("age")
email = Field("email")

qb = QueryBuilder()
query = qb.select(
    data=["id", "username", "email"],
    from_="subscriber",
    where=(
        (username.like("admin%") | email.contains("@gmail.com")) &
        (age >= 18) &
        ~(username.in_("blocked1", "blocked2"))
    )
)
```

### 3. Q Objects (Django-style)

```python
from iptvportal.query import Q, QueryBuilder

qb = QueryBuilder()
query = qb.select(
    data=["id", "username"],
    from_="subscriber",
    where=(
        Q(username="admin") |
        (Q(age__gte=18) & Q(disabled=False))
    )
)
```

## Architecture

```
iptvportal-client/
├── src/iptvportal/
│   ├── config.py          # Pydantic Settings
│   ├── exceptions.py      # Exception hierarchy
│   ├── auth.py            # Auth managers (sync/async)
│   ├── client.py          # Sync client
│   ├── async_client.py    # Async client
│   └── query/
│       ├── builder.py     # Query builder
│       ├── field.py       # Field API
│       └── q_objects.py   # Q Objects
```

## Development

```bash
# Clone repository
git clone https://github.com/pv-udpv/iptvportal-client.git
cd iptvportal-client

# Install with uv
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/iptvportal

# Linting
ruff check src/iptvportal
```

## License

MIT License - see LICENSE file for details.
