"""Configuration management with Pydantic Settings."""

from typing import Optional
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class IPTVPortalSettings(BaseSettings):
    """IPTVPortal API client configuration.
    
    Configuration is loaded from:
    - Environment variables (IPTVPORTAL_ prefix)
    - .env file
    - Direct constructor arguments
    """

    model_config = SettingsConfigDict(
        env_prefix="IPTVPORTAL_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Connection parameters
    domain: str = Field(
        ...,
        description="Operator subdomain in IPTVPORTAL (e.g., 'operator' for operator.admin.iptvportal.ru)",
    )

    username: str = Field(
        ...,
        description="Admin username",
    )

    password: SecretStr = Field(
        ...,
        description="Admin password",
    )

    # Automatically generated URLs
    @property
    def auth_url(self) -> str:
        """Authorization endpoint URL."""
        return f"https://{self.domain}.admin.iptvportal.ru/api/jsonrpc/"

    @property
    def api_url(self) -> str:
        """API endpoint URL."""
        return f"https://{self.domain}.admin.iptvportal.ru/api/jsonsql/"

    # HTTP settings
    timeout: float = Field(
        default=30.0,
        description="Request timeout in seconds",
    )

    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts",
    )

    retry_delay: float = Field(
        default=1.0,
        description="Initial delay between retries in seconds (exponential backoff)",
    )

    # Client options
    verify_ssl: bool = Field(
        default=True,
        description="Verify SSL certificates",
    )

    session_cache: bool = Field(
        default=True,
        description="Cache session_id",
    )

    session_ttl: int = Field(
        default=3600,
        description="Session ID TTL in seconds (default 1 hour)",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )

    log_requests: bool = Field(
        default=False,
        description="Log HTTP requests",
    )

    log_responses: bool = Field(
        default=False,
        description="Log HTTP responses",
    )

    # Schema configuration
    schema_file: Optional[str] = Field(
        default=None,
        description="Path to schema configuration file (YAML or JSON)",
    )

    schema_format: str = Field(
        default="yaml",
        description="Schema file format: 'yaml' or 'json'",
    )

    auto_load_schemas: bool = Field(
        default=True,
        description="Automatically load schemas from schema_file on client initialization",
    )

    # Query caching
    enable_query_cache: bool = Field(
        default=True,
        description="Enable query result caching",
    )

    cache_ttl: int = Field(
        default=300,
        description="Default cache TTL in seconds (5 minutes)",
    )

    cache_max_size: int = Field(
        default=1000,
        description="Maximum number of cached query results",
    )

    # Query optimization
    auto_order_by_id: bool = Field(
        default=True,
        description="Automatically add ORDER BY id to SELECT queries without explicit ordering",
    )
