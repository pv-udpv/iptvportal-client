"""Query result caching for IPTVPortal client."""

import hashlib
import json
import time
from collections import OrderedDict
from threading import RLock
from typing import Any


class QueryCache:
    """
    LRU cache for query results with TTL support.

    Features:
    - Hash-based cache keys from query dictionaries
    - LRU eviction policy
    - Configurable TTL per entry
    - Thread-safe operations
    - Cache statistics tracking
    """

    def __init__(self, max_size: int = 1000, default_ttl: int | None = 300):
        """
        Initialize query cache.

        Args:
            max_size: Maximum number of entries to cache
            default_ttl: Default time-to-live in seconds (None = no expiration)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._lock = RLock()

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def compute_query_hash(self, query: dict[str, Any]) -> str:
        """
        Compute hash for a query dictionary.

        Args:
            query: Query dictionary (JSON-RPC request)

        Returns:
            SHA256 hash string
        """
        # Extract only the relevant parts for hashing
        # Ignore 'id' and 'jsonrpc' fields from JSON-RPC wrapper
        hashable_parts = {"method": query.get("method"), "params": query.get("params", {})}

        # Convert to canonical JSON string (sorted keys for consistency)
        json_str = json.dumps(hashable_parts, sort_keys=True, ensure_ascii=True)

        # Compute SHA256 hash
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    def get(self, query_hash: str) -> Any | None:
        """
        Get cached result by query hash.

        Args:
            query_hash: Query hash string

        Returns:
            Cached result or None if not found/expired
        """
        with self._lock:
            if query_hash not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[query_hash]

            # Check if entry has expired
            if entry["expires_at"] is not None and time.time() > entry["expires_at"]:
                # Remove expired entry
                del self._cache[query_hash]
                self._misses += 1
                return None

            # Move to end (mark as recently used)
            self._cache.move_to_end(query_hash)

            self._hits += 1
            return entry["result"]

    def set(
        self, query_hash: str, result: Any, ttl: int | None = None, query: dict[str, Any] | None = None
    ) -> None:
        """
        Cache a query result.

        Args:
            query_hash: Query hash string
            result: Result to cache
            ttl: Time-to-live in seconds (None = use default, 0 = no expiration)
            query: Optional query dictionary for metadata extraction
        """
        with self._lock:
            # Determine TTL
            if ttl is None:
                ttl = self.default_ttl

            # Calculate expiration time
            expires_at = None
            if ttl is not None and ttl > 0:
                expires_at = time.time() + ttl

            # Extract table name from query if provided
            table_name = None
            if query:
                table_name = self._extract_table_name(query)

            # If at capacity, evict least recently used
            if query_hash not in self._cache and len(self._cache) >= self.max_size:
                # Remove oldest (first) entry
                self._cache.popitem(last=False)
                self._evictions += 1

            # Store entry
            self._cache[query_hash] = {
                "result": result,
                "cached_at": time.time(),
                "expires_at": expires_at,
                "table_name": table_name,
            }

            # Move to end (mark as recently used)
            self._cache.move_to_end(query_hash)

    def clear(self, table_name: str | None = None) -> int:
        """
        Clear cache entries.

        Args:
            table_name: Optional table name to clear entries for specific table

        Returns:
            Number of entries removed
        """
        with self._lock:
            if table_name is None:
                # Clear all entries
                count = len(self._cache)
                self._cache.clear()
                return count

            # Clear entries for specific table
            keys_to_remove = [
                key
                for key, entry in self._cache.items()
                if entry.get("table_name") == table_name
            ]

            for key in keys_to_remove:
                del self._cache[key]

            return len(keys_to_remove)

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_rate": round(hit_rate, 2),
                "total_requests": total_requests,
            }

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._evictions = 0

    def _extract_table_name(self, query: dict[str, Any]) -> str | None:
        """
        Extract table name from query dictionary.

        Args:
            query: Query dictionary

        Returns:
            Table name if found, None otherwise
        """
        params = query.get("params", {})
        if isinstance(params, dict):
            # Direct table name in params
            if "from" in params:
                return params["from"]
            # Table name in nested structure
            if "table" in params:
                return params["table"]
        return None

    def is_read_query(self, query: dict[str, Any]) -> bool:
        """
        Check if query is a read operation (cacheable).

        Args:
            query: Query dictionary

        Returns:
            True if query is cacheable (SELECT operation)
        """
        method = query.get("method", "").lower()

        # Cache only SELECT queries
        return method in ("select", "query", "get")

    def extract_table_name(self, query: dict[str, Any]) -> str | None:
        """
        Extract table name from a query dictionary.

        Args:
            query: Query dictionary (JSON-RPC request)

        Returns:
            Table name if found, None otherwise
        """
        params = query.get("params", {})

        # Try to extract from different possible locations
        if isinstance(params, dict):
            # Direct 'from' field
            if "from" in params:
                return params["from"]

            # Inside a 'query' object (JSONSQL format)
            if "query" in params and isinstance(params["query"], dict):
                return params["query"].get("from")

            # Inside a 'table' field
            if "table" in params:
                return params["table"]

        return None
