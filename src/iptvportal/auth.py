"""Authentication managers for sync and async clients."""

import time

import httpx
import orjson

from iptvportal.config import IPTVPortalSettings
from iptvportal.exceptions import AuthenticationError


class AuthManager:
    """Synchronous authentication manager with session caching."""

    def __init__(self, settings: IPTVPortalSettings) -> None:
        self.settings = settings
        self._session_id: str | None = None
        self._session_timestamp: float | None = None

    @property
    def session_id(self) -> str | None:
        """Get cached session ID if still valid."""
        if not self.settings.session_cache:
            return self._session_id

        if self._session_id and self._session_timestamp:
            elapsed = time.time() - self._session_timestamp
            if elapsed < self.settings.session_ttl:
                return self._session_id

        return None

    def authenticate(self, http_client: httpx.Client) -> str:
        """Authenticate and return session_id.
        
        Args:
            http_client: HTTP client instance
            
        Returns:
            Session ID string
            
        Raises:
            AuthenticationError: If authentication fails
        """
        # Check cache first
        if cached_session := self.session_id:
            return cached_session

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "authorize_user",
            "params": {
                "username": self.settings.username,
                "password": self.settings.password.get_secret_value(),
            },
        }

        try:
            response = http_client.post(
                self.settings.auth_url,
                content=orjson.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = orjson.loads(response.content)

            if "error" in data:
                raise AuthenticationError(
                    data["error"].get("message", "Authentication failed"),
                    details=data["error"],
                )

            result = data.get("result", {})
            session_id = result.get("session_id")

            if not session_id:
                raise AuthenticationError("No session_id in response")

            # Cache session
            self._session_id = session_id
            self._session_timestamp = time.time()

            return session_id

        except httpx.HTTPError as e:
            raise AuthenticationError(f"HTTP error during authentication: {e}") from e


class AsyncAuthManager:
    """Asynchronous authentication manager with session caching."""

    def __init__(self, settings: IPTVPortalSettings) -> None:
        self.settings = settings
        self._session_id: str | None = None
        self._session_timestamp: float | None = None

    @property
    def session_id(self) -> str | None:
        """Get cached session ID if still valid."""
        if not self.settings.session_cache:
            return self._session_id

        if self._session_id and self._session_timestamp:
            elapsed = time.time() - self._session_timestamp
            if elapsed < self.settings.session_ttl:
                return self._session_id

        return None

    async def authenticate(self, http_client: httpx.AsyncClient) -> str:
        """Authenticate and return session_id (async).
        
        Args:
            http_client: Async HTTP client instance
            
        Returns:
            Session ID string
            
        Raises:
            AuthenticationError: If authentication fails
        """
        # Check cache first
        if cached_session := self.session_id:
            return cached_session

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "authorize_user",
            "params": {
                "username": self.settings.username,
                "password": self.settings.password.get_secret_value(),
            },
        }

        try:
            response = await http_client.post(
                self.settings.auth_url,
                content=orjson.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = orjson.loads(response.content)

            if "error" in data:
                raise AuthenticationError(
                    data["error"].get("message", "Authentication failed"),
                    details=data["error"],
                )

            result = data.get("result", {})
            session_id = result.get("session_id")

            if not session_id:
                raise AuthenticationError("No session_id in response")

            # Cache session
            self._session_id = session_id
            self._session_timestamp = time.time()

            return session_id

        except httpx.HTTPError as e:
            raise AuthenticationError(f"HTTP error during authentication: {e}") from e
