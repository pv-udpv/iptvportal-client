"""Exceptions for sync system."""


class SyncError(Exception):
    """Base exception for sync operations."""

    pass


class DatabaseError(SyncError):
    """Database operation failed."""

    pass


class SyncStrategyError(SyncError):
    """Invalid or unsupported sync strategy."""

    pass


class SchemaVersionError(SyncError):
    """Schema version mismatch detected."""

    pass


class TableNotFoundError(SyncError):
    """Table not registered in cache."""

    pass


class SyncInProgressError(SyncError):
    """Sync operation already in progress for this table."""

    pass


class ConfigurationError(SyncError):
    """Invalid sync configuration."""

    pass


class ConnectionError(SyncError):
    """Failed to connect to remote API."""

    pass
