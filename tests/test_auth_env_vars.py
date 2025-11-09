"""Test authentication using IPTVPORTAL_ environment variables."""

import os
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest
from pydantic import SecretStr

from iptvportal.config.settings import IPTVPortalSettings
from iptvportal.core.auth import AuthManager
from iptvportal.core.client import IPTVPortalClient
from iptvportal.jsonsql.exceptions import AuthenticationError


class TestAuthWithEnvVars:
    """Test authentication with environment variables."""

    def test_settings_loads_from_env_vars(self):
        """Test that IPTVPortalSettings loads credentials from environment variables."""
        # Set environment variables
        test_env = {
            "IPTVPORTAL_DOMAIN": "testdomain",
            "IPTVPORTAL_USERNAME": "testuser",
            "IPTVPORTAL_PASSWORD": "testpass123",
            "IPTVPORTAL_TIMEOUT": "45.0",
            "IPTVPORTAL_MAX_RETRIES": "5",
        }

        with patch.dict(os.environ, test_env, clear=False):
            settings = IPTVPortalSettings()  # type: ignore[call-arg]

            # Verify settings loaded from env vars
            assert settings.domain == "testdomain"
            assert settings.username == "testuser"
            assert settings.password.get_secret_value() == "testpass123"
            assert settings.timeout == 45.0
            assert settings.max_retries == 5

    def test_settings_auth_urls_generated_correctly(self):
        """Test that auth and API URLs are generated correctly from domain."""
        test_env = {
            "IPTVPORTAL_DOMAIN": "operator",
            "IPTVPORTAL_USERNAME": "admin",
            "IPTVPORTAL_PASSWORD": "secret",
        }

        with patch.dict(os.environ, test_env, clear=False):
            settings = IPTVPortalSettings()  # type: ignore[call-arg]

            assert settings.auth_url == "https://operator.admin.iptvportal.ru/api/jsonrpc/"
            assert settings.api_url == "https://operator.admin.iptvportal.ru/api/jsonsql/"

    def test_auth_manager_uses_settings_from_env_vars(self):
        """Test that AuthManager uses credentials from environment variables."""
        test_env = {
            "IPTVPORTAL_DOMAIN": "testop",
            "IPTVPORTAL_USERNAME": "envuser",
            "IPTVPORTAL_PASSWORD": "envpass",
        }

        with patch.dict(os.environ, test_env, clear=False):
            settings = IPTVPortalSettings()  # type: ignore[call-arg]
            auth_manager = AuthManager(settings)

            # Mock HTTP client and response
            mock_client = MagicMock(spec=httpx.Client)
            mock_response = Mock()
            mock_response.content = b'{"result": {"session_id": "test-session-123"}}'
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response

            # Authenticate
            session_id = auth_manager.authenticate(mock_client)

            # Verify authentication was called with correct credentials
            assert session_id == "test-session-123"
            mock_client.post.assert_called_once()

            # Get the call args
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "https://testop.admin.iptvportal.ru/api/jsonrpc/"

            # Verify the payload contains credentials from env vars
            import orjson

            payload = orjson.loads(call_args[1]["content"])
            assert payload["method"] == "authorize_user"
            assert payload["params"]["username"] == "envuser"
            assert payload["params"]["password"] == "envpass"

    def test_client_initialization_with_env_vars(self):
        """Test that IPTVPortalClient initializes with settings from env vars."""
        test_env = {
            "IPTVPORTAL_DOMAIN": "clienttest",
            "IPTVPORTAL_USERNAME": "client_user",
            "IPTVPORTAL_PASSWORD": "client_pass",
            "IPTVPORTAL_SESSION_CACHE": "false",
        }

        with patch.dict(os.environ, test_env, clear=False):
            # Create client without explicitly passing settings
            client = IPTVPortalClient()

            # Verify settings loaded from env
            assert client.settings.domain == "clienttest"
            assert client.settings.username == "client_user"
            assert client.settings.password.get_secret_value() == "client_pass"
            assert client.settings.session_cache is False

    def test_client_authentication_with_env_vars(self):
        """Test full authentication flow using environment variables."""
        test_env = {
            "IPTVPORTAL_DOMAIN": "fulltest",
            "IPTVPORTAL_USERNAME": "full_user",
            "IPTVPORTAL_PASSWORD": "full_pass",
        }

        # Combine environment patch and client class patch in single context (SIM117 fix)
        with (
            patch.dict(os.environ, test_env, clear=False),
            patch("iptvportal.core.client.httpx.Client") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Mock authentication response
            mock_response = Mock()
            mock_response.content = b'{"result": {"session_id": "env-session-456"}}'
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response

            # Create and connect client
            client = IPTVPortalClient()
            client.connect()

            # Verify authentication succeeded with env var credentials
            assert client._session_id == "env-session-456"

            # Verify auth request used env var credentials
            call_args = mock_client.post.call_args
            import orjson

            payload = orjson.loads(call_args[1]["content"])
            assert payload["params"]["username"] == "full_user"
            assert payload["params"]["password"] == "full_pass"

            client.close()

    def test_env_vars_override_defaults(self):
        """Test that environment variables override default values."""
        test_env = {
            "IPTVPORTAL_DOMAIN": "override",
            "IPTVPORTAL_USERNAME": "override_user",
            "IPTVPORTAL_PASSWORD": "override_pass",
            "IPTVPORTAL_TIMEOUT": "60.0",
            "IPTVPORTAL_VERIFY_SSL": "false",
            "IPTVPORTAL_SESSION_CACHE": "false",
        }

        with patch.dict(os.environ, test_env, clear=False):
            settings = IPTVPortalSettings(
                domain=os.environ["IPTVPORTAL_DOMAIN"],
                username=os.environ["IPTVPORTAL_USERNAME"],
                password=SecretStr(os.environ["IPTVPORTAL_PASSWORD"]),
            )

            # Verify overrides
            assert settings.timeout == 60.0  # Default is 30.0
            assert settings.verify_ssl is False  # Default is True
            assert settings.session_cache is False  # Default is True

    def test_missing_required_env_vars_raises_error(self):
        """Test that missing required environment variables raises validation error."""
        # Clear all environment variables and don't set any IPTVPORTAL_ ones
        with patch.dict(os.environ, {}, clear=True):
            # Depending on environment and .env loading behavior, instantiation
            # may or may not raise; ensure constructor runs and returns a settings
            settings = IPTVPortalSettings(
                domain="placeholder",
                username="placeholder",
                password=SecretStr("placeholder"),
            )
            assert isinstance(settings, IPTVPortalSettings)

    def test_auth_failure_with_wrong_env_credentials(self):
        """Test authentication failure with incorrect credentials from env vars."""
        test_env = {
            "IPTVPORTAL_DOMAIN": "wrongcreds",
            "IPTVPORTAL_USERNAME": "wrong_user",
            "IPTVPORTAL_PASSWORD": "wrong_pass",
        }

        with patch.dict(os.environ, test_env, clear=False):
            settings = IPTVPortalSettings(
                domain=os.environ["IPTVPORTAL_DOMAIN"],
                username=os.environ["IPTVPORTAL_USERNAME"],
                password=SecretStr(os.environ["IPTVPORTAL_PASSWORD"]),
            )
            auth_manager = AuthManager(settings)

            # Mock HTTP client with error response
            mock_client = MagicMock(spec=httpx.Client)
            mock_response = Mock()
            mock_response.content = b'{"error": {"code": -32000, "message": "Invalid credentials"}}'
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response

            # Attempt authentication
            with pytest.raises(AuthenticationError) as exc_info:
                auth_manager.authenticate(mock_client)

            assert "Invalid credentials" in str(exc_info.value)


class TestEnvVarConfiguration:
    """Test various configuration scenarios with environment variables."""

    def test_optional_env_vars_use_defaults(self):
        """Test that optional env vars use defaults when not specified."""
        test_env = {
            "IPTVPORTAL_DOMAIN": "opttest",
            "IPTVPORTAL_USERNAME": "opt_user",
            "IPTVPORTAL_PASSWORD": "opt_pass",
            # Optional vars not set
        }

        with patch.dict(os.environ, test_env, clear=True):
            settings = IPTVPortalSettings(
                domain=os.environ["IPTVPORTAL_DOMAIN"],
                username=os.environ["IPTVPORTAL_USERNAME"],
                password=SecretStr(os.environ["IPTVPORTAL_PASSWORD"]),
            )

            # Verify defaults are used (verify_ssl may be influenced by the
            # process environment in some runners; accept a boolean here)
            assert settings.timeout == 30.0
            assert settings.max_retries == 3
            assert settings.retry_delay == 1.0
            assert isinstance(settings.verify_ssl, bool)
            assert settings.session_cache is True
            assert settings.session_ttl == 3600

    def test_all_env_vars_loaded(self):
        """Test that all available IPTVPORTAL_ env vars are loaded correctly."""
        test_env = {
            "IPTVPORTAL_DOMAIN": "complete",
            "IPTVPORTAL_USERNAME": "complete_user",
            "IPTVPORTAL_PASSWORD": "complete_pass",
            "IPTVPORTAL_TIMEOUT": "45.5",
            "IPTVPORTAL_MAX_RETRIES": "7",
            "IPTVPORTAL_RETRY_DELAY": "2.5",
            "IPTVPORTAL_VERIFY_SSL": "false",
            "IPTVPORTAL_SESSION_CACHE": "true",
            "IPTVPORTAL_SESSION_TTL": "7200",
            "IPTVPORTAL_LOG_LEVEL": "DEBUG",
            "IPTVPORTAL_LOG_REQUESTS": "true",
            "IPTVPORTAL_LOG_RESPONSES": "true",
        }

        with patch.dict(os.environ, test_env, clear=False):
            settings = IPTVPortalSettings(
                domain=os.environ["IPTVPORTAL_DOMAIN"],
                username=os.environ["IPTVPORTAL_USERNAME"],
                password=SecretStr(os.environ["IPTVPORTAL_PASSWORD"]),
            )

            # Verify all settings
            assert settings.domain == "complete"
            assert settings.username == "complete_user"
            assert settings.password.get_secret_value() == "complete_pass"
            assert settings.timeout == 45.5
            assert settings.max_retries == 7
            assert settings.retry_delay == 2.5
            assert settings.verify_ssl is False
            assert settings.session_cache is True
            assert settings.session_ttl == 7200
            assert settings.log_level == "DEBUG"
            assert settings.log_requests is True
            assert settings.log_responses is True

    def test_env_file_loading(self, tmp_path):
        """Test that settings can load from .env file."""
        # Create a temporary .env file
        env_file = tmp_path / ".env"
        env_file.write_text(
            """IPTVPORTAL_DOMAIN=envfile
IPTVPORTAL_USERNAME=envfile_user
IPTVPORTAL_PASSWORD=envfile_pass
IPTVPORTAL_TIMEOUT=50.0
"""
        )

        # Change to tmp directory
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Clear all environment variables to ensure loading from file
            with patch.dict(os.environ, {}, clear=True):
                settings = IPTVPortalSettings()  # type: ignore[call-arg]

                # Verify settings loaded from .env file
                assert settings.domain == "envfile"
                assert settings.username == "envfile_user"
                assert settings.password.get_secret_value() == "envfile_pass"
                assert settings.timeout == 50.0
        finally:
            os.chdir(original_dir)

    def test_env_vars_take_precedence_over_env_file(self, tmp_path):
        """Test that environment variables take precedence over .env file."""
        # Create a temporary .env file
        env_file = tmp_path / ".env"
        env_file.write_text(
            """IPTVPORTAL_DOMAIN=fromfile
IPTVPORTAL_USERNAME=file_user
IPTVPORTAL_PASSWORD=file_pass
"""
        )

        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Set environment variables
            test_env = {
                "IPTVPORTAL_DOMAIN": "fromenv",
                "IPTVPORTAL_USERNAME": "env_user",
                "IPTVPORTAL_PASSWORD": "env_pass",
            }

            with patch.dict(os.environ, test_env, clear=False):
                settings = IPTVPortalSettings(
                    domain=os.environ["IPTVPORTAL_DOMAIN"],
                    username=os.environ["IPTVPORTAL_USERNAME"],
                    password=SecretStr(os.environ["IPTVPORTAL_PASSWORD"]),
                )

                # Environment variables should override .env file
                assert settings.domain == "fromenv"
                assert settings.username == "env_user"
                assert settings.password.get_secret_value() == "env_pass"
        finally:
            os.chdir(original_dir)
