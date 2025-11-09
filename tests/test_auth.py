"""Tests for authentication module."""

import time
from unittest.mock import Mock, patch

import httpx
import orjson
import pytest
from pydantic import SecretStr

from iptvportal.config.settings import IPTVPortalSettings
from iptvportal.core.auth import AsyncAuthManager, AuthManager
from iptvportal.exceptions import AuthenticationError


@pytest.fixture
def test_settings():
    """Create test settings for authentication."""
    return IPTVPortalSettings(
        domain="test",
        username="test_user",
        password=SecretStr("test_password"),
        session_cache=True,
        session_ttl=3600,
    )


@pytest.fixture
def auth_manager(test_settings):
    """Create AuthManager instance."""
    return AuthManager(test_settings)


@pytest.fixture
def async_auth_manager(test_settings):
    """Create AsyncAuthManager instance."""
    return AsyncAuthManager(test_settings)


class TestAuthManager:
    """Tests for synchronous AuthManager."""

    def test_init(self, auth_manager, test_settings):
        """Test AuthManager initialization."""
        assert auth_manager.settings == test_settings
        assert auth_manager._session_id is None
        assert auth_manager._session_timestamp is None

    def test_session_id_cache_enabled(self, auth_manager):
        """Test session_id property with caching enabled."""
        # No cached session initially
        assert auth_manager.session_id is None

        # Set session
        auth_manager._session_id = "test_session_123"
        auth_manager._session_timestamp = time.time()

        # Should return cached session
        assert auth_manager.session_id == "test_session_123"

    def test_session_id_cache_expired(self, auth_manager):
        """Test session_id property with expired cache."""
        auth_manager._session_id = "test_session_123"
        auth_manager._session_timestamp = time.time() - 4000  # Expired (> 3600s)

        # Should return None for expired session
        assert auth_manager.session_id is None

    def test_session_id_cache_disabled(self, test_settings):
        """Test session_id property with caching disabled."""
        test_settings.session_cache = False
        auth_manager = AuthManager(test_settings)

        auth_manager._session_id = "test_session_123"
        auth_manager._session_timestamp = time.time()

        # Should still return session even though cache is disabled (for same instance)
        assert auth_manager.session_id == "test_session_123"

    def test_authenticate_success(self, auth_manager):
        """Test successful authentication."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = orjson.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"session_id": "new_session_456"},
            }
        )

        mock_client = Mock(spec=httpx.Client)
        mock_client.post.return_value = mock_response

        session_id = auth_manager.authenticate(mock_client)

        assert session_id == "new_session_456"
        assert auth_manager._session_id == "new_session_456"
        assert auth_manager._session_timestamp is not None

        # Verify the request was made correctly
        call_args = mock_client.post.call_args
        assert call_args[0][0] == auth_manager.settings.auth_url
        payload = orjson.loads(call_args[1]["content"])
        assert payload["method"] == "authorize_user"
        assert payload["params"]["username"] == "test_user"
        assert payload["params"]["password"] == "test_password"

    def test_authenticate_uses_cached_session(self, auth_manager):
        """Test that authenticate uses cached session if available."""
        # Set cached session
        auth_manager._session_id = "cached_session_789"
        auth_manager._session_timestamp = time.time()

        mock_client = Mock(spec=httpx.Client)

        session_id = auth_manager.authenticate(mock_client)

        # Should return cached session without making HTTP request
        assert session_id == "cached_session_789"
        mock_client.post.assert_not_called()

    def test_authenticate_error_in_response(self, auth_manager):
        """Test authentication with error in API response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = orjson.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "error": {
                    "code": -32001,
                    "message": "Invalid credentials",
                },
            }
        )

        mock_client = Mock(spec=httpx.Client)
        mock_client.post.return_value = mock_response

        with pytest.raises(AuthenticationError) as exc_info:
            auth_manager.authenticate(mock_client)

        assert "Invalid credentials" in str(exc_info.value)
        assert exc_info.value.details["code"] == -32001

    def test_authenticate_missing_session_id(self, auth_manager):
        """Test authentication with missing session_id in response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = orjson.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {},  # No session_id
            }
        )

        mock_client = Mock(spec=httpx.Client)
        mock_client.post.return_value = mock_response

        with pytest.raises(AuthenticationError) as exc_info:
            auth_manager.authenticate(mock_client)

        assert "No session_id in response" in str(exc_info.value)

    def test_authenticate_http_error(self, auth_manager):
        """Test authentication with HTTP error."""
        mock_client = Mock(spec=httpx.Client)
        mock_client.post.side_effect = httpx.HTTPError("Connection refused")

        with pytest.raises(AuthenticationError) as exc_info:
            auth_manager.authenticate(mock_client)

        assert "HTTP error during authentication" in str(exc_info.value)

    def test_authenticate_network_timeout(self, auth_manager):
        """Test authentication with network timeout."""
        mock_client = Mock(spec=httpx.Client)
        mock_client.post.side_effect = httpx.TimeoutException("Request timeout")

        with pytest.raises(AuthenticationError) as exc_info:
            auth_manager.authenticate(mock_client)

        assert "HTTP error during authentication" in str(exc_info.value)


class TestAsyncAuthManager:
    """Tests for asynchronous AsyncAuthManager."""

    def test_init(self, async_auth_manager, test_settings):
        """Test AsyncAuthManager initialization."""
        assert async_auth_manager.settings == test_settings
        assert async_auth_manager._session_id is None
        assert async_auth_manager._session_timestamp is None

    def test_session_id_cache_enabled(self, async_auth_manager):
        """Test session_id property with caching enabled."""
        # No cached session initially
        assert async_auth_manager.session_id is None

        # Set session
        async_auth_manager._session_id = "test_session_123"
        async_auth_manager._session_timestamp = time.time()

        # Should return cached session
        assert async_auth_manager.session_id == "test_session_123"

    def test_session_id_cache_expired(self, async_auth_manager):
        """Test session_id property with expired cache."""
        async_auth_manager._session_id = "test_session_123"
        async_auth_manager._session_timestamp = time.time() - 4000  # Expired

        # Should return None for expired session
        assert async_auth_manager.session_id is None

    @pytest.mark.asyncio
    async def test_authenticate_success(self, async_auth_manager):
        """Test successful async authentication."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = orjson.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"session_id": "async_session_456"},
            }
        )

        mock_client = Mock(spec=httpx.AsyncClient)
        mock_client.post = Mock(return_value=mock_response)

        # Mock async context

        async def mock_post(*args, **kwargs):
            return mock_response

        mock_client.post = mock_post

        session_id = await async_auth_manager.authenticate(mock_client)

        assert session_id == "async_session_456"
        assert async_auth_manager._session_id == "async_session_456"
        assert async_auth_manager._session_timestamp is not None

    @pytest.mark.asyncio
    async def test_authenticate_uses_cached_session(self, async_auth_manager):
        """Test that async authenticate uses cached session if available."""
        # Set cached session
        async_auth_manager._session_id = "cached_async_session_789"
        async_auth_manager._session_timestamp = time.time()

        mock_client = Mock(spec=httpx.AsyncClient)
        mock_client.post = Mock()

        session_id = await async_auth_manager.authenticate(mock_client)

        # Should return cached session without making HTTP request
        assert session_id == "cached_async_session_789"
        mock_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_authenticate_error_in_response(self, async_auth_manager):
        """Test async authentication with error in API response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = orjson.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "error": {
                    "code": -32001,
                    "message": "Invalid credentials",
                },
            }
        )

        async def mock_post(*args, **kwargs):
            return mock_response

        mock_client = Mock(spec=httpx.AsyncClient)
        mock_client.post = mock_post

        with pytest.raises(AuthenticationError) as exc_info:
            await async_auth_manager.authenticate(mock_client)

        assert "Invalid credentials" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authenticate_http_error(self, async_auth_manager):
        """Test async authentication with HTTP error."""

        async def mock_post(*args, **kwargs):
            raise httpx.HTTPError("Connection refused")

        mock_client = Mock(spec=httpx.AsyncClient)
        mock_client.post = mock_post

        with pytest.raises(AuthenticationError) as exc_info:
            await async_auth_manager.authenticate(mock_client)

        assert "HTTP error during authentication" in str(exc_info.value)


class TestSessionCaching:
    """Tests for session caching behavior."""

    def test_cache_ttl_respected(self, test_settings):
        """Test that session cache respects TTL."""
        test_settings.session_ttl = 1  # 1 second TTL
        auth_manager = AuthManager(test_settings)

        # Set session
        auth_manager._session_id = "test_session"
        auth_manager._session_timestamp = time.time()

        # Immediately should be valid
        assert auth_manager.session_id == "test_session"

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired now
        assert auth_manager.session_id is None

    def test_cache_disabled_behavior(self, test_settings):
        """Test behavior when cache is disabled."""
        test_settings.session_cache = False
        auth_manager = AuthManager(test_settings)

        # Set session
        auth_manager._session_id = "test_session"
        auth_manager._session_timestamp = time.time()

        # Should still return the session (not checking TTL when disabled)
        assert auth_manager.session_id == "test_session"


class TestAuthenticationIntegration:
    """Integration tests for authentication with settings."""

    def test_auth_url_generation(self, test_settings):
        """Test that auth URL is correctly generated from settings."""
        assert test_settings.auth_url == "https://test.admin.iptvportal.ru/api/jsonrpc/"

    def test_api_url_generation(self, test_settings):
        """Test that API URL is correctly generated from settings."""
        assert test_settings.api_url == "https://test.admin.iptvportal.ru/api/jsonsql/"

    def test_password_security(self, test_settings):
        """Test that password is stored securely."""
        # Password should be SecretStr
        assert isinstance(test_settings.password, SecretStr)

        # Should require explicit access to get value
        assert test_settings.password.get_secret_value() == "test_password"

        # String representation should not reveal password
        assert "test_password" not in str(test_settings.password)
        assert "test_password" not in repr(test_settings.password)

    def test_settings_from_env_vars(self):
        """Test loading settings from environment variables."""
        with patch.dict(
            "os.environ",
            {
                "IPTVPORTAL_DOMAIN": "env_test",
                "IPTVPORTAL_USERNAME": "env_user",
                "IPTVPORTAL_PASSWORD": "env_pass",
            },
        ):
            # Create new settings instance that will load from env
            settings = IPTVPortalSettings()
            assert settings.domain == "env_test"
            assert settings.username == "env_user"
            assert settings.password.get_secret_value() == "env_pass"
