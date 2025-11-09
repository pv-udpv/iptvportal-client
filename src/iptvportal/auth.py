"""Auth module (backward compatibility)."""

from iptvportal.core.auth import AsyncAuthManager, AuthManager

__all__ = ["AuthManager", "AsyncAuthManager"]
