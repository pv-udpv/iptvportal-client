"""Configuration management with Pydantic Settings."""

from typing import Optional, Literal
from pathlib import Path
from pydantic import Field, SecretStr, field_validator, model_validator
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

    # ==================== SQLite Cache Settings ====================

    cache_db_path: str = Field(
        default="~/.iptvportal/cache.db",
        description="Path to SQLite cache database"
    )

    enable_persistent_cache: bool = Field(
        default=True,
        description="Enable SQLite persistent cache (vs in-memory only)"
    )

    cache_db_journal_mode: Literal["DELETE", "WAL", "MEMORY"] = Field(
        default="WAL",
        description="SQLite journal mode (WAL recommended for concurrency)"
    )

    cache_db_page_size: int = Field(
        default=4096,
        description="SQLite page size in bytes"
    )

    cache_db_cache_size: int = Field(
        default=-64000,
        description="SQLite cache size (negative = KB, positive = pages)"
    )

    # ==================== Sync Behavior ====================

    default_sync_strategy: Literal["full", "incremental", "on_demand"] = Field(
        default="full",
        description="Default sync strategy for tables without explicit config"
    )

    default_sync_ttl: int = Field(
        default=3600,
        description="Default cache TTL in seconds (1 hour)"
    )

    default_chunk_size: int = Field(
        default=1000,
        description="Default chunk size for bulk sync operations"
    )

    auto_sync_on_startup: bool = Field(
        default=False,
        description="Automatically sync all tables on client startup"
    )

    auto_sync_stale_tables: bool = Field(
        default=True,
        description="Automatically sync stale tables on first access"
    )

    max_concurrent_syncs: int = Field(
        default=3,
        description="Maximum number of tables to sync concurrently"
    )

    # ==================== Maintenance ====================

    auto_vacuum_enabled: bool = Field(
        default=True,
        description="Automatically vacuum database on maintenance"
    )

    vacuum_threshold_mb: int = Field(
        default=100,
        description="Trigger vacuum when wasted space exceeds this (MB)"
    )

    auto_analyze_enabled: bool = Field(
        default=True,
        description="Automatically run ANALYZE for query optimization"
    )

    analyze_interval_hours: int = Field(
        default=24,
        description="Run ANALYZE every N hours"
    )


class CLISettings(BaseSettings):
    """CLI-specific configuration with defaults and guardrails.

    These settings control CLI behavior, defaults, and safety features.
    Configuration loaded from:
    - ~/.iptvportal/cli-config.yaml or ~/.iptvportal/cli-config.json
    - Environment variables (IPTVPORTAL_CLI_ prefix)
    - Command-line overrides
    """

    model_config = SettingsConfigDict(
        env_prefix="IPTVPORTAL_CLI_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==================== Output Defaults ====================
    default_format: Literal["table", "json", "yaml", "csv"] = Field(
        default="table",
        description="Default output format for query results",
    )

    default_table_style: Literal[
        "default", "simple", "github", "grid", "fancy_grid", "pipe", "orgtbl", "rst", "mediawiki"
    ] = Field(
        default="default",
        description="Default table rendering style (uses rich/tabulate styles)",
    )

    max_table_width: int | None = Field(
        default=None,
        description="Maximum table width in characters (None = terminal width)",
    )

    truncate_strings: bool = Field(
        default=True,
        description="Truncate long string values in table output",
    )

    max_string_length: int = Field(
        default=50,
        ge=10,
        le=500,
        description="Maximum string length before truncation (10-500 chars)",
    )

    show_row_numbers: bool = Field(
        default=False,
        description="Show row numbers in table output",
    )

    colorize_output: bool = Field(
        default=True,
        description="Use colors in terminal output (auto-detects TTY)",
    )

    # ==================== Query Safety & Guardrails ====================
    enable_guardrails: bool = Field(
        default=True,
        description="Enable safety checks and warnings for potentially dangerous queries",
    )

    require_limit_on_select: bool = Field(
        default=False,
        description="Require LIMIT clause on SELECT queries (prevents accidental full table scans)",
    )

    default_limit: int | None = Field(
        default=None,
        ge=1,
        le=100000,
        description="Auto-add LIMIT if not specified (None = no auto-limit, 1-100000)",
    )

    max_limit: int = Field(
        default=10000,
        ge=1,
        le=1000000,
        description="Maximum allowed LIMIT value (safety check, 1-1000000)",
    )

    warn_large_limit: int = Field(
        default=1000,
        ge=100,
        le=100000,
        description="Warn when LIMIT exceeds this threshold (100-100000)",
    )

    confirm_destructive_queries: bool = Field(
        default=True,
        description="Require confirmation for UPDATE/DELETE without WHERE clause",
    )

    confirm_large_updates: bool = Field(
        default=True,
        description="Require confirmation for UPDATE/DELETE with large affected row counts",
    )

    large_update_threshold: int = Field(
        default=100,
        ge=1,
        le=100000,
        description="Row count threshold for 'large update' confirmation (1-100000)",
    )

    dry_run_first: bool = Field(
        default=False,
        description="Always show dry-run preview before executing queries",
    )

    # ==================== Performance & Caching ====================
    enable_query_cache: bool = Field(
        default=True,
        description="Enable client-side caching of query results",
    )

    cache_ttl_seconds: int = Field(
        default=300,
        ge=0,
        le=86400,
        description="Cache TTL in seconds (0=disabled, max 24 hours)",
    )

    cache_max_size_mb: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Maximum cache size in megabytes (1-10000 MB)",
    )

    cache_location: str = Field(
        default="~/.iptvportal/cache",
        description="Directory for query result cache",
    )

    enable_schema_cache: bool = Field(
        default=True,
        description="Cache table schemas after introspection",
    )

    schema_cache_ttl_seconds: int = Field(
        default=3600,
        ge=60,
        le=604800,
        description="Schema cache TTL in seconds (1 hour - 1 week)",
    )

    # ==================== Editor & Input ====================
    default_editor: str | None = Field(
        default=None,
        description="Preferred text editor for --edit mode (None = $EDITOR env var)",
    )

    editor_syntax_highlighting: bool = Field(
        default=True,
        description="Enable syntax highlighting in editor (when supported)",
    )

    save_query_history: bool = Field(
        default=True,
        description="Save command history for --edit mode",
    )

    query_history_size: int = Field(
        default=1000,
        ge=0,
        le=100000,
        description="Maximum number of queries in history (0=unlimited, max 100k)",
    )

    query_history_location: str = Field(
        default="~/.iptvportal/query-history.txt",
        description="Path to query history file",
    )

    # ==================== Transpiler Behavior ====================
    transpiler_dialect: Literal["postgres", "mysql", "sqlite", "tsql", "oracle"] = Field(
        default="postgres",
        description="SQL dialect for transpiler",
    )

    auto_order_by_id: bool = Field(
        default=True,
        description="Auto-add ORDER BY id to SELECT queries without ordering",
    )

    preserve_sql_comments: bool = Field(
        default=False,
        description="Preserve SQL comments in transpiled queries",
    )

    validate_jsonsql: bool = Field(
        default=True,
        description="Validate transpiled JSONSQL before execution",
    )

    # ==================== Schema Mapping ====================
    auto_detect_schema: bool = Field(
        default=True,
        description="Auto-detect and load schemas for result mapping",
    )

    schema_directory: str = Field(
        default="~/.iptvportal/schemas",
        description="Directory for schema YAML/JSON files",
    )

    prefer_mapped_results: bool = Field(
        default=False,
        description="Use schema mapping for results by default (without --map-schema flag)",
    )

    # ==================== Logging & Debug ====================
    verbose: bool = Field(
        default=False,
        description="Enable verbose output for debugging",
    )

    log_queries: bool = Field(
        default=False,
        description="Log all executed queries to file",
    )

    query_log_location: str = Field(
        default="~/.iptvportal/query.log",
        description="Path to query log file",
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level for CLI operations",
    )

    show_execution_time: bool = Field(
        default=True,
        description="Show query execution time in output",
    )

    show_row_count: bool = Field(
        default=True,
        description="Show total row count in query results",
    )

    # ==================== Session & Auth ====================
    session_cache_enabled: bool = Field(
        default=True,
        description="Cache authentication session ID",
    )

    session_cache_location: str = Field(
        default="~/.iptvportal/session-cache",
        description="Directory for session cache files",
    )

    auto_renew_session: bool = Field(
        default=True,
        description="Automatically renew expired sessions",
    )

    # ==================== Advanced Features ====================
    enable_autocomplete: bool = Field(
        default=True,
        description="Enable shell autocomplete for table/column names",
    )

    autocomplete_cache_ttl: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Autocomplete cache TTL in seconds (1 hour - 24 hours)",
    )

    enable_query_explain: bool = Field(
        default=False,
        description="Automatically run EXPLAIN for SELECT queries",
    )

    parallel_query_threshold: int = Field(
        default=5,
        ge=2,
        le=100,
        description="Minimum queries for parallel execution (2-100)",
    )

    max_parallel_queries: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum concurrent queries in parallel mode (1-50)",
    )

    # ==================== Export Settings ====================
    export_directory: str = Field(
        default="./exports",
        description="Default directory for exported results (CSV, JSON, etc.)",
    )

    export_timestamp_format: str = Field(
        default="%Y%m%d_%H%M%S",
        description="Timestamp format for auto-generated export filenames",
    )

    compress_exports: bool = Field(
        default=False,
        description="Automatically compress large exports (gzip)",
    )

    compress_threshold_mb: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Size threshold in MB for automatic compression (1-1000)",
    )

    # ==================== Notifications ====================
    enable_notifications: bool = Field(
        default=False,
        description="Enable desktop notifications for long-running queries",
    )

    notification_threshold_seconds: int = Field(
        default=30,
        ge=5,
        le=3600,
        description="Minimum execution time for notification (5 seconds - 1 hour)",
    )

    play_sound_on_complete: bool = Field(
        default=False,
        description="Play sound when long-running query completes",
    )

    # ==================== Pager Settings ====================
    use_pager: bool = Field(
        default=False,
        description="Use pager (less/more) for large outputs",
    )

    pager_threshold_lines: int = Field(
        default=100,
        ge=10,
        le=10000,
        description="Minimum lines to trigger pager (10-10000)",
    )

    pager_command: str | None = Field(
        default=None,
        description="Custom pager command (None = $PAGER env var or 'less -R')",
    )


# ==================== Config File Management ====================


def load_cli_config(config_path: str | None = None) -> CLISettings:
    """
    Load CLI configuration from file with fallback chain.

    Priority:
    1. Explicit config_path argument
    2. IPTVPORTAL_CLI_CONFIG environment variable
    3. ~/.iptvportal/cli-config.yaml
    4. ~/.iptvportal/cli-config.json
    5. Defaults from CLISettings

    Args:
        config_path: Optional explicit path to config file

    Returns:
        CLISettings instance with loaded configuration

    Example:
        >>> config = load_cli_config()
        >>> config = load_cli_config("./my-config.yaml")
    """
    import os
    from pathlib import Path

    # Try explicit path first
    if config_path:
        path = Path(config_path).expanduser()
        if path.exists():
            return _load_config_from_file(path)
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Try environment variable
    env_config = os.getenv("IPTVPORTAL_CLI_CONFIG")
    if env_config:
        path = Path(env_config).expanduser()
        if path.exists():
            return _load_config_from_file(path)

    # Try default locations
    config_dir = Path.home() / ".iptvportal"
    for filename in ["cli-config.yaml", "cli-config.yml", "cli-config.json"]:
        path = config_dir / filename
        if path.exists():
            return _load_config_from_file(path)

    # Return defaults
    return CLISettings()


def _load_config_from_file(path: Path) -> CLISettings:
    """Load configuration from YAML or JSON file."""
    import json
    import yaml

    content = path.read_text()

    if path.suffix in [".yaml", ".yml"]:
        data = yaml.safe_load(content)
    elif path.suffix == ".json":
        data = json.loads(content)
    else:
        raise ValueError(f"Unsupported config file format: {path.suffix}")

    return CLISettings(**data)


def save_cli_config(config: CLISettings, path: str | None = None, format: str = "yaml") -> None:
    """
    Save CLI configuration to file.

    Args:
        config: CLISettings instance to save
        path: Output path (default: ~/.iptvportal/cli-config.yaml)
        format: Output format ('yaml' or 'json')

    Example:
        >>> config = CLISettings(default_format="json", max_limit=5000)
        >>> save_cli_config(config)
        >>> save_cli_config(config, "my-config.yaml", "yaml")
    """
    from pathlib import Path
    import json
    import yaml

    if path is None:
        config_dir = Path.home() / ".iptvportal"
        config_dir.mkdir(parents=True, exist_ok=True)
        path = str(config_dir / f"cli-config.{format}")

    output_path = Path(path).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Export config as dict, excluding unset values
    data = config.model_dump(exclude_unset=False)

    if format == "yaml":
        content = yaml.dump(data, default_flow_style=False, sort_keys=False)
    else:
        content = json.dumps(data, indent=2)

    output_path.write_text(content)


def create_default_cli_config() -> None:
    """
    Create default CLI configuration file with comments.

    Creates ~/.iptvportal/cli-config.yaml with all available options
    and documentation comments.

    Example:
        >>> from iptvportal.config import create_default_cli_config
        >>> create_default_cli_config()
    """
    from pathlib import Path

    config_dir = Path.home() / ".iptvportal"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "cli-config.yaml"

    # Generate commented YAML with all defaults
    config = CLISettings()

    template = """# IPTVPortal CLI Configuration
# Auto-generated configuration file with all available options
#
# Edit this file to customize CLI behavior, defaults, and safety features.
# See documentation: https://github.com/pv-udpv/iptvportal-client

# ==================== Output Defaults ====================
# Control how query results are displayed

default_format: {default_format}  # Output format: table, json, yaml, csv
default_table_style: {default_table_style}  # Table style for rich output
max_table_width: {max_table_width}  # Max table width (null = terminal width)
truncate_strings: {truncate_strings}  # Truncate long strings in tables
max_string_length: {max_string_length}  # Max string length before truncation
show_row_numbers: {show_row_numbers}  # Show row numbers in tables
colorize_output: {colorize_output}  # Use colors in terminal

# ==================== Query Safety & Guardrails ====================
# Protect against dangerous queries and mistakes

enable_guardrails: {enable_guardrails}  # Enable all safety checks
require_limit_on_select: {require_limit_on_select}  # Force LIMIT on SELECT
default_limit: {default_limit}  # Auto-add LIMIT (null = no limit)
max_limit: {max_limit}  # Maximum allowed LIMIT value
warn_large_limit: {warn_large_limit}  # Warn when LIMIT exceeds this
confirm_destructive_queries: {confirm_destructive_queries}  # Confirm UPDATE/DELETE without WHERE
confirm_large_updates: {confirm_large_updates}  # Confirm large UPDATE/DELETE
large_update_threshold: {large_update_threshold}  # Row threshold for confirmation
dry_run_first: {dry_run_first}  # Always preview before execution

# ==================== Performance & Caching ====================

enable_query_cache: {enable_query_cache}  # Cache query results
cache_ttl_seconds: {cache_ttl_seconds}  # Cache TTL (0 = disabled)
cache_max_size_mb: {cache_max_size_mb}  # Max cache size in MB
cache_location: {cache_location}  # Cache directory
enable_schema_cache: {enable_schema_cache}  # Cache table schemas
schema_cache_ttl_seconds: {schema_cache_ttl_seconds}  # Schema cache TTL

# ==================== Editor & Input ====================

default_editor: {default_editor}  # Text editor (null = $EDITOR)
editor_syntax_highlighting: {editor_syntax_highlighting}  # Syntax highlighting
save_query_history: {save_query_history}  # Save query history
query_history_size: {query_history_size}  # Max history entries
query_history_location: {query_history_location}  # History file path

# ==================== Transpiler Behavior ====================

transpiler_dialect: {transpiler_dialect}  # SQL dialect
auto_order_by_id: {auto_order_by_id}  # Auto-add ORDER BY id
preserve_sql_comments: {preserve_sql_comments}  # Keep SQL comments
validate_jsonsql: {validate_jsonsql}  # Validate transpiled queries

# ==================== Schema Mapping ====================

auto_detect_schema: {auto_detect_schema}  # Auto-load schemas
schema_directory: {schema_directory}  # Schema files location
prefer_mapped_results: {prefer_mapped_results}  # Use mapping by default

# ==================== Logging & Debug ====================

verbose: {verbose}  # Verbose output
log_queries: {log_queries}  # Log queries to file
query_log_location: {query_log_location}  # Query log path
log_level: {log_level}  # Logging level
show_execution_time: {show_execution_time}  # Show query time
show_row_count: {show_row_count}  # Show row count

# ==================== Session & Auth ====================

session_cache_enabled: {session_cache_enabled}  # Cache session ID
session_cache_location: {session_cache_location}  # Session cache dir
auto_renew_session: {auto_renew_session}  # Auto-renew expired sessions

# ==================== Advanced Features ====================

enable_autocomplete: {enable_autocomplete}  # Shell autocomplete
autocomplete_cache_ttl: {autocomplete_cache_ttl}  # Autocomplete cache TTL
enable_query_explain: {enable_query_explain}  # Auto EXPLAIN queries
parallel_query_threshold: {parallel_query_threshold}  # Min queries for parallel
max_parallel_queries: {max_parallel_queries}  # Max concurrent queries

# ==================== Export Settings ====================

export_directory: {export_directory}  # Export output directory
export_timestamp_format: {export_timestamp_format}  # Filename timestamp format
compress_exports: {compress_exports}  # Auto-compress exports
compress_threshold_mb: {compress_threshold_mb}  # Compression threshold

# ==================== Notifications ====================

enable_notifications: {enable_notifications}  # Desktop notifications
notification_threshold_seconds: {notification_threshold_seconds}  # Notify after N seconds
play_sound_on_complete: {play_sound_on_complete}  # Play sound on completion

# ==================== Pager Settings ====================

use_pager: {use_pager}  # Use pager for large outputs
pager_threshold_lines: {pager_threshold_lines}  # Lines threshold for pager
pager_command: {pager_command}  # Custom pager (null = $PAGER or less)
""".format(**config.model_dump())

    config_path.write_text(template)
    print(f"Created default CLI configuration: {config_path}")
