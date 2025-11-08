"""Tests for SyncConfig validation and behavior.

Run with:
    uv run pytest tests/test_sync_config.py
    uv run pytest tests/test_sync_config.py -v
"""

from iptvportal.schema import SyncConfig


class TestSyncConfigValidation:
    """Test SyncConfig validation logic."""

    def test_valid_config(self):
        """Test that valid config passes validation."""
        config = SyncConfig(
            where="deleted_at IS NULL",
            limit=1000,
            order_by="id",
            chunk_size=100,
            enable_chunking=True,
            ttl=3600,
            cache_strategy="full",
            auto_sync=True,
            sync_interval=1800,
            disabled=False,
            include_fields=["id", "name"],
            exclude_fields=["password"],
            incremental_field="updated_at",
            incremental_mode=True,
            prefetch_relationships=False,
            max_concurrent_chunks=3,
        )

        errors = config.validate()
        assert len(errors) == 0

    def test_invalid_chunk_size(self):
        """Test validation of chunk_size."""
        config = SyncConfig(chunk_size=0)
        errors = config.validate()
        assert "chunk_size must be positive" in errors

        config = SyncConfig(chunk_size=-1)
        errors = config.validate()
        assert "chunk_size must be positive" in errors

    def test_invalid_limit_chunk_size_relationship(self):
        """Test that limit must be >= chunk_size."""
        config = SyncConfig(limit=50, chunk_size=100)
        errors = config.validate()
        assert "limit should be >= chunk_size" in errors

    def test_invalid_cache_strategy(self):
        """Test validation of cache_strategy."""
        config = SyncConfig(cache_strategy="invalid")
        errors = config.validate()
        assert "Invalid cache_strategy: invalid" in errors

    def test_incremental_mode_requires_field(self):
        """Test that incremental_mode requires incremental_field."""
        config = SyncConfig(incremental_mode=True, incremental_field=None)
        errors = config.validate()
        assert "incremental_field required when incremental_mode=True" in errors

    def test_negative_ttl(self):
        """Test validation of TTL."""
        config = SyncConfig(ttl=-1)
        errors = config.validate()
        assert "ttl must be non-negative" in errors

    def test_valid_incremental_config(self):
        """Test valid incremental sync configuration."""
        config = SyncConfig(
            incremental_mode=True, incremental_field="updated_at", cache_strategy="incremental"
        )
        errors = config.validate()
        assert len(errors) == 0


class TestSyncConfigToDict:
    """Test SyncConfig.to_dict() export functionality."""

    def test_to_dict_with_defaults(self):
        """Test to_dict with default values (should be minimal)."""
        config = SyncConfig()
        result = config.to_dict()
        assert result == {}

    def test_to_dict_with_custom_values(self):
        """Test to_dict with custom values."""
        config = SyncConfig(
            where="deleted_at IS NULL",
            limit=1000,
            order_by="name",
            chunk_size=500,
            enable_chunking=False,
            ttl=7200,
            cache_strategy="incremental",
            auto_sync=True,
            sync_interval=3600,
            include_fields=["id", "name"],
            exclude_fields=["password"],
            incremental_field="updated_at",
            incremental_mode=True,
            prefetch_relationships=True,
            max_concurrent_chunks=5,
            disabled=True,
        )

        result = config.to_dict()
        expected = {
            "where": "deleted_at IS NULL",
            "limit": 1000,
            "order_by": "name",
            "chunk_size": 500,
            "enable_chunking": False,
            "ttl": 7200,
            "cache_strategy": "incremental",
            "auto_sync": True,
            "sync_interval": 3600,
            "include_fields": ["id", "name"],
            "exclude_fields": ["password"],
            "incremental_field": "updated_at",
            "incremental_mode": True,
            "prefetch_relationships": True,
            "max_concurrent_chunks": 5,
            "disabled": True,
        }

        assert result == expected

    def test_to_dict_excludes_defaults(self):
        """Test that default values are excluded from to_dict."""
        config = SyncConfig(
            order_by="id",  # This is the default
            chunk_size=1000,  # This is the default
            cache_strategy="full",  # This is the default
            max_concurrent_chunks=3,  # This is the default
        )

        result = config.to_dict()
        assert result == {}


class TestSyncConfigStrategies:
    """Test different sync strategy configurations."""

    def test_full_sync_config(self):
        """Test configuration optimized for full sync."""
        config = SyncConfig(cache_strategy="full", chunk_size=1000, ttl=3600, auto_sync=True)

        errors = config.validate()
        assert len(errors) == 0
        assert config.cache_strategy == "full"

    def test_incremental_sync_config(self):
        """Test configuration optimized for incremental sync."""
        config = SyncConfig(
            cache_strategy="incremental",
            incremental_mode=True,
            incremental_field="updated_at",
            chunk_size=5000,
            ttl=1800,
        )

        errors = config.validate()
        assert len(errors) == 0
        assert config.incremental_mode is True
        assert config.incremental_field == "updated_at"

    def test_on_demand_sync_config(self):
        """Test configuration for on-demand sync."""
        config = SyncConfig(cache_strategy="on-demand", ttl=600, auto_sync=False)

        errors = config.validate()
        assert len(errors) == 0
        assert config.cache_strategy == "on-demand"
        assert config.auto_sync is False


class TestSyncConfigEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_where_clause(self):
        """Test empty where clause."""
        config = SyncConfig(where="")
        result = config.to_dict()
        # Empty string should not be included
        assert "where" not in result

    def test_none_values(self):
        """Test None values are handled correctly."""
        config = SyncConfig(
            where=None,
            limit=None,
            ttl=None,
            sync_interval=None,
            include_fields=None,
            exclude_fields=None,
            incremental_field=None,
        )

        result = config.to_dict()
        assert result == {}

    def test_large_values(self):
        """Test large but valid values."""
        config = SyncConfig(
            limit=1000000,
            chunk_size=50000,
            ttl=86400 * 30,  # 30 days
            sync_interval=3600 * 24,  # 24 hours
        )

        errors = config.validate()
        assert len(errors) == 0

    def test_zero_values(self):
        """Test zero values where allowed."""
        config = SyncConfig(
            limit=0,  # No limit
            ttl=0,  # No TTL
            sync_interval=0,  # No interval
        )

        errors = config.validate()
        assert len(errors) == 0
