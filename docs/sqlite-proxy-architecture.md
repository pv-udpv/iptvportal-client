# SQLite Proxy Layer Architecture

## Overview

Create a transparent caching layer that stores IPTVPortal data in local SQLite with metadata tracking, providing fast local access with lazy loading from remote JSONSQL source when needed.

## Architecture

```
┌─────────────────┐
│  Application    │
│  (User Code)    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Proxy Layer (ORM-style)       │
│  - SQLModel/SQLAlchemy models   │
│  - Transparent data access      │
│  - Lazy loading strategy        │
└────────┬─────────────┬──────────┘
         │             │
    ┌────▼────┐   ┌───▼─────────┐
    │ SQLite  │   │  IPTVPortal │
    │  Cache  │   │  JSONSQL    │
    │ + Meta  │   │   Remote    │
    └─────────┘   └─────────────┘
```

## Components

### 1. SQLite Cache Layer (`cache_db.py`)

```python
from sqlmodel import SQLModel, Field, Session, create_engine, select
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

# Base metadata table for tracking cache state
class CacheMetadata(SQLModel, table=True):
    __tablename__ = "cache_metadata"
    
    table_name: str = Field(primary_key=True)
    last_sync: datetime
    last_sync_id: Optional[int] = None  # For incremental sync
    row_count: int
    strategy: str  # "full", "incremental", "on_demand"
    ttl: int  # seconds
    schema_hash: str  # Detect schema changes
    
    def is_stale(self) -> bool:
        """Check if cache is expired"""
        age = (datetime.now() - self.last_sync).total_seconds()
        return age > self.ttl


# Dynamic table generation from schema
class TableFactory:
    """Generate SQLModel classes from TableSchema"""
    
    @staticmethod
    def create_model(schema: TableSchema) -> type[SQLModel]:
        """
        Create SQLModel class dynamically based on schema
        
        Example:
            schema = introspector.introspect_table("subscriber")
            SubscriberModel = TableFactory.create_model(schema)
            
            # Now can use as normal SQLModel
            with Session(engine) as session:
                users = session.exec(
                    select(SubscriberModel).where(SubscriberModel.disabled == False)
                ).all()
        """
        # Build field definitions
        fields = {}
        for pos, field_def in schema.fields.items():
            python_type = field_def.get_python_type()
            fields[field_def.name] = (
                python_type,
                Field(default=None, description=field_def.description)
            )
        
        # Create model class dynamically
        model = type(
            schema.table_name.title(),
            (SQLModel,),
            {
                "__tablename__": schema.table_name,
                "__annotations__": {k: v[0] for k, v in fields.items()},
                **{k: v[1] for k, v in fields.items()}
            }
        )
        
        return model
```

### 2. Proxy Manager (`proxy.py`)

```python
from typing import TypeVar, Generic, Optional, List
from sqlmodel import Session, select
from datetime import datetime

T = TypeVar('T', bound=SQLModel)

class ProxyManager(Generic[T]):
    """
    Transparent proxy between local SQLite cache and remote JSONSQL
    
    Usage:
        # Setup
        schema = await introspector.introspect_table("subscriber")
        SubscriberModel = TableFactory.create_model(schema)
        proxy = ProxyManager(
            model=SubscriberModel,
            client=client,
            schema=schema,
            engine=sqlite_engine
        )
        
        # Query (auto-syncs if stale)
        users = proxy.query().where(SubscriberModel.disabled == False).all()
        
        # Lazy loading for single record
        user = proxy.get(id=123)  # Fetches from remote if not in cache
        
        # Force refresh
        proxy.sync(force=True)
    """
    
    def __init__(
        self,
        model: type[T],
        client: AsyncIPTVPortalClient,
        schema: TableSchema,
        engine: Engine
    ):
        self.model = model
        self.client = client
        self.schema = schema
        self.engine = engine
        self.table_name = schema.table_name
    
    def _get_metadata(self, session: Session) -> Optional[CacheMetadata]:
        """Get cache metadata for table"""
        return session.exec(
            select(CacheMetadata).where(
                CacheMetadata.table_name == self.table_name
            )
        ).first()
    
    def _is_stale(self, session: Session) -> bool:
        """Check if cache needs refresh"""
        meta = self._get_metadata(session)
        if not meta:
            return True  # No cache yet
        return meta.is_stale()
    
    async def _sync_full(self, session: Session) -> int:
        """Full table synchronization"""
        # Clear existing data
        session.exec(f"DELETE FROM {self.table_name}")
        
        # Fetch from remote
        sync_config = self.schema.sync_config
        offset = 0
        total_synced = 0
        
        while True:
            query = {
                "data": ["*"],
                "from": self.table_name,
                "limit": sync_config.chunk_size,
                "offset": offset,
                "order_by": sync_config.order_by or "id"
            }
            
            if sync_config.where:
                query["where"] = sync_config.where
            
            rows = await self.client.execute({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "select",
                "params": query
            })
            
            if not rows:
                break
            
            # Map and insert
            for row in rows:
                mapped = self.schema.map_row_to_dict(row)
                record = self.model(**mapped)
                session.add(record)
            
            total_synced += len(rows)
            offset += sync_config.chunk_size
            
            if len(rows) < sync_config.chunk_size:
                break  # Last page
        
        # Update metadata
        meta = self._get_metadata(session) or CacheMetadata(
            table_name=self.table_name
        )
        meta.last_sync = datetime.now()
        meta.row_count = total_synced
        meta.strategy = sync_config.cache_strategy
        meta.ttl = sync_config.ttl
        meta.schema_hash = self.schema.get_hash()
        
        session.add(meta)
        session.commit()
        
        return total_synced
    
    async def _sync_incremental(self, session: Session) -> int:
        """Incremental sync using updated_at field"""
        meta = self._get_metadata(session)
        if not meta:
            return await self._sync_full(session)
        
        sync_config = self.schema.sync_config
        last_sync = meta.last_sync
        
        # Fetch only updated records
        query = {
            "data": ["*"],
            "from": self.table_name,
            "where": {
                "gt": [sync_config.incremental_field, last_sync.isoformat()]
            },
            "order_by": sync_config.order_by or "id"
        }
        
        rows = await self.client.execute({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "select",
            "params": query
        })
        
        if not rows:
            return 0
        
        # Upsert records
        total_synced = 0
        for row in rows:
            mapped = self.schema.map_row_to_dict(row)
            # Check if exists
            existing = session.get(self.model, mapped["id"])
            if existing:
                # Update
                for key, value in mapped.items():
                    setattr(existing, key, value)
            else:
                # Insert
                record = self.model(**mapped)
                session.add(record)
            total_synced += 1
        
        # Update metadata
        meta.last_sync = datetime.now()
        meta.row_count += total_synced
        session.add(meta)
        session.commit()
        
        return total_synced
    
    async def sync(self, force: bool = False) -> int:
        """Synchronize cache with remote"""
        with Session(self.engine) as session:
            if not force and not self._is_stale(session):
                return 0  # Cache is fresh
            
            sync_config = self.schema.sync_config
            if sync_config.incremental_mode and not force:
                return await self._sync_incremental(session)
            else:
                return await self._sync_full(session)
    
    def query(self) -> Select[T]:
        """
        Get SQLModel select statement (auto-syncs if stale)
        
        Usage:
            stmt = proxy.query().where(Model.disabled == False)
            with Session(engine) as session:
                results = session.exec(stmt).all()
        """
        # Check and sync in background if needed
        with Session(self.engine) as session:
            if self._is_stale(session):
                # Trigger async sync
                import asyncio
                asyncio.create_task(self.sync())
        
        return select(self.model)
    
    async def get(self, **filters) -> Optional[T]:
        """
        Get single record (lazy load from remote if not in cache)
        
        Usage:
            user = await proxy.get(id=123)
            user = await proxy.get(username="admin")
        """
        with Session(self.engine) as session:
            # Try local cache first
            stmt = select(self.model)
            for key, value in filters.items():
                stmt = stmt.where(getattr(self.model, key) == value)
            
            result = session.exec(stmt).first()
            
            if result:
                return result
            
            # Not in cache, fetch from remote
            where_conditions = [
                {"eq": [key, value]} for key, value in filters.items()
            ]
            where = {"and": where_conditions} if len(where_conditions) > 1 else where_conditions[0]
            
            query = {
                "data": ["*"],
                "from": self.table_name,
                "where": where,
                "limit": 1
            }
            
            rows = await self.client.execute({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "select",
                "params": query
            })
            
            if not rows:
                return None
            
            # Cache and return
            mapped = self.schema.map_row_to_dict(rows[0])
            record = self.model(**mapped)
            session.add(record)
            session.commit()
            session.refresh(record)
            
            return record
```

### 3. High-Level API (`proxy_client.py`)

```python
class ProxyClient:
    """
    High-level client with automatic proxy setup
    
    Usage:
        async with ProxyClient() as client:
            # Auto-introspect and setup proxy
            Subscriber = await client.table("subscriber")
            
            # Query like normal SQLModel
            with client.session() as session:
                users = session.exec(
                    select(Subscriber).where(Subscriber.disabled == False)
                ).all()
            
            # Or use proxy manager
            user = await client.subscribers.get(id=123)
            await client.subscribers.sync(force=True)
    """
    
    def __init__(
        self,
        settings: Optional[IPTVPortalSettings] = None,
        cache_db: str = "~/.iptvportal/cache.db"
    ):
        self.settings = settings or IPTVPortalSettings()
        self.client = AsyncIPTVPortalClient(self.settings)
        self.introspector = SchemaIntrospector(self.client)
        
        # SQLite setup
        cache_path = Path(cache_db).expanduser()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{cache_path}")
        
        self._models = {}
        self._proxies = {}
    
    async def __aenter__(self):
        await self.client.connect()
        return self
    
    async def __aexit__(self, *args):
        await self.client.close()
    
    async def table(self, table_name: str, force_introspect: bool = False) -> type[SQLModel]:
        """Get or create SQLModel for table"""
        if table_name in self._models and not force_introspect:
            return self._models[table_name]
        
        # Introspect schema
        schema = await self.introspector.introspect_table(table_name)
        
        # Create model
        model = TableFactory.create_model(schema)
        
        # Create table in SQLite
        SQLModel.metadata.create_all(self.engine)
        
        # Setup proxy
        proxy = ProxyManager(
            model=model,
            client=self.client,
            schema=schema,
            engine=self.engine
        )
        
        self._models[table_name] = model
        self._proxies[table_name] = proxy
        
        # Add as attribute for convenience
        setattr(self, table_name, proxy)
        
        return model
    
    def session(self) -> Session:
        """Get SQLite session"""
        return Session(self.engine)
```

## Usage Examples

### Example 1: Basic Query with Auto-Sync

```python
async with ProxyClient() as client:
    # First access: introspects, creates model, syncs data
    Subscriber = await client.table("subscriber")
    
    # Query from local SQLite (fast!)
    with client.session() as session:
        active_users = session.exec(
            select(Subscriber)
            .where(Subscriber.disabled == False)
            .where(Subscriber.balance > 0)
        ).all()
        
        for user in active_users:
            print(f"{user.username}: {user.balance}")
```

### Example 2: Lazy Loading Single Record

```python
async with ProxyClient() as client:
    await client.table("subscriber")
    
    # Fetch specific user (from cache if exists, remote if not)
    user = await client.subscriber.get(username="admin")
    print(user.email)
```

### Example 3: Force Refresh

```python
async with ProxyClient() as client:
    await client.table("tv_channel")
    
    # Force refresh from remote
    synced = await client.tv_channel.sync(force=True)
    print(f"Synced {synced} channels")
    
    # Now query fresh data
    with client.session() as session:
        channels = session.exec(
            select(client._models["tv_channel"])
            .order_by("name")
        ).all()
```

### Example 4: JOINs with Multiple Tables

```python
async with ProxyClient() as client:
    # Setup multiple tables
    Subscriber = await client.table("subscriber")
    Terminal = await client.table("terminal")
    
    # JOIN in SQLite (blazing fast!)
    with client.session() as session:
        results = session.exec(
            select(Subscriber, Terminal)
            .join(Terminal, Subscriber.id == Terminal.subscriber_id)
            .where(Terminal.active == True)
        ).all()
```

## Benefits

1. **Performance**: Local SQLite queries are 100x+ faster than remote API calls
2. **Offline Support**: Can work with cached data when network is unavailable
3. **Rich Querying**: Full SQL power (JOINs, CTEs, aggregates) without JSONSQL limitations
4. **Transparent**: Use familiar SQLModel/SQLAlchemy API
5. **Smart Caching**: Automatic staleness detection and incremental sync
6. **Type Safety**: Full typing support through SQLModel

## Implementation Plan

1. ✅ Schema introspection (already done)
2. ⬜ Create `TableFactory` for dynamic model generation
3. ⬜ Implement `CacheMetadata` tracking
4. ⬜ Build `ProxyManager` with sync strategies
5. ⬜ Create `ProxyClient` high-level API
6. ⬜ Add CLI commands for cache management
7. ⬜ Write comprehensive tests
8. ⬜ Document usage patterns
