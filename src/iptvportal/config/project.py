"""Project configuration loader using dynaconf.

This module provides a unified configuration system with:
- Modular YAML-based configuration tree
- Auto-discovery of *.settings.yaml files
- Deep merging of configuration layers
- Environment variable overrides
- Runtime configuration access API
"""

from pathlib import Path
from typing import Any

from dynaconf import Dynaconf, Validator


# Discover base directory (either package root or working directory)
def _find_config_base() -> Path:
    """Find the base directory for configuration files.

    Returns:
        Path to config directory (either in package or current working dir)
    """
    # Try package-relative config directory first
    package_dir = Path(__file__).parent.parent.parent
    config_dir = package_dir / "config"
    if config_dir.exists():
        return config_dir

    # Fall back to current working directory
    cwd_config = Path.cwd() / "config"
    if cwd_config.exists():
        return cwd_config

    # If neither exists, use package location (will be created on demand)
    return config_dir


def _discover_settings_files(base_path: Path) -> list[Path]:
    """Recursively discover all *.settings.yaml files.

    Args:
        base_path: Base directory to search from

    Returns:
        List of discovered settings file paths, sorted by name
    """
    if not base_path.exists():
        return []

    settings_files = []

    # Find all *.settings.yaml files recursively
    for yaml_file in base_path.rglob("*.settings.yaml"):
        settings_files.append(yaml_file)

    # Sort for consistent loading order
    return sorted(settings_files)


def _init_dynaconf() -> Dynaconf:
    """Initialize dynaconf with auto-discovered settings files.

    Returns:
        Configured Dynaconf instance
    """
    config_base = _find_config_base()

    # Start with main settings.yaml
    settings_files = [str(config_base / "settings.yaml")]

    # Auto-discover and add schema-specific settings
    discovered_files = _discover_settings_files(config_base / "schemas")
    settings_files.extend([str(f) for f in discovered_files])

    # Initialize dynaconf with merged settings
    return Dynaconf(
        envvar_prefix="IPTVPORTAL",
        settings_files=settings_files,
        environments=False,  # Single environment mode
        load_dotenv=True,  # Load from .env files
        merge_enabled=True,  # Enable deep merging
        lowercase_read=True,  # Enable lowercase access (e.g., conf.core.timeout)
        validators=[
            # Core validators - ensure required fields are set (can be empty for init)
            Validator("core.timeout", gte=0, default=30.0),
            Validator("core.max_retries", gte=0, default=3),
            Validator("core.session_ttl", gte=0, default=3600),
            # CLI validators
            Validator("cli.max_limit", gte=1, lte=1000000, default=10000),
            Validator("cli.warn_large_limit", gte=100, lte=100000, default=1000),
            # Sync validators
            Validator("sync.default_chunk_size", gte=1, default=1000),
            Validator("sync.max_concurrent_syncs", gte=1, default=3),
        ],
    )


# Global settings instance
_settings: Dynaconf | None = None


def get_conf() -> Dynaconf:
    """Get the global configuration instance.

    Returns:
        Dynaconf configuration object with all merged settings

    Example:
        >>> from iptvportal.project_conf import get_conf
        >>> conf = get_conf()
        >>> conf.core.timeout  # -> 30.0
        >>> conf.sync.subscriber.strategy  # -> incremental
    """
    global _settings
    if _settings is None:
        _settings = _init_dynaconf()
        # Initialize logging after config is loaded; keep best-effort to avoid import cycles
        try:
            from iptvportal.logging_setup import setup_logging

            setup_logging(_settings)
        except Exception:
            # Do not fail configuration loading if logging setup fails
            pass
    return _settings


def reload_conf() -> Dynaconf:
    """Reload configuration from disk.

    Useful after modifying settings files or environment variables.

    Returns:
        Reloaded Dynaconf instance

    Example:
        >>> from iptvportal.project_conf import reload_conf
        >>> conf = reload_conf()
    """
    global _settings
    _settings = _init_dynaconf()
    # Reconfigure logging to pick up any changed logging settings
    try:
        from iptvportal.logging_setup import setup_logging

        setup_logging(_settings)
    except Exception:
        # Best-effort: don't raise on logging failures
        pass
    return _settings


def get_value(key: str, default: Any = None) -> Any:
    """Get a configuration value by dot-notation key.

    Args:
        key: Configuration key in dot notation (e.g., 'core.timeout', 'sync.subscriber.ttl')
        default: Default value if key not found

    Returns:
        Configuration value or default

    Example:
        >>> from iptvportal.project_conf import get_value
        >>> timeout = get_value('core.timeout', 30.0)
        >>> subscriber_ttl = get_value('sync.subscriber.ttl', 1800)
    """
    conf = get_conf()
    try:
        # Navigate through nested keys
        value = conf
        for part in key.split("."):
            value = getattr(value, part)
        return value
    except (AttributeError, KeyError):
        return default


def set_value(key: str, value: Any) -> None:
    """Set a configuration value at runtime.

    Note: Changes are not persisted to disk, only in memory.

    Args:
        key: Configuration key in dot notation
        value: Value to set

    Example:
        >>> from iptvportal.project_conf import set_value
        >>> set_value('core.timeout', 60.0)
        >>> set_value('cli.verbose', True)
    """
    conf = get_conf()
    conf.set(key, value)


def list_settings(prefix: str = "") -> dict[str, Any]:
    """List all settings under a given prefix.

    Args:
        prefix: Optional prefix to filter settings (e.g., 'core', 'sync')

    Returns:
        Dictionary of settings matching the prefix

    Example:
        >>> from iptvportal.project_conf import list_settings
        >>> core_settings = list_settings('core')
        >>> sync_settings = list_settings('sync')
        >>> all_settings = list_settings()  # Get everything
    """
    conf = get_conf()

    if not prefix:
        # Return all settings as dict
        return conf.as_dict()

    # Get settings under prefix
    try:
        value = conf
        for part in prefix.split("."):
            value = getattr(value, part)

        # Convert to dict if it's a Box/DynaBox
        if hasattr(value, "to_dict"):
            return value.to_dict()
        if isinstance(value, dict):
            return value
        # Single value, return as dict with the key
        return {prefix: value}
    except (AttributeError, KeyError):
        return {}


def get_config_files() -> list[str]:
    """Get list of all configuration files being loaded.

    Returns:
        List of configuration file paths

    Example:
        >>> from iptvportal.project_conf import get_config_files
        >>> files = get_config_files()
        >>> for f in files:
        ...     f  # iterate over configuration file paths
    """
    config_base = _find_config_base()

    settings_files = [str(config_base / "settings.yaml")]
    discovered_files = _discover_settings_files(config_base / "schemas")
    settings_files.extend([str(f) for f in discovered_files])

    return settings_files


# Convenience exports for backward compatibility
settings = get_conf()


__all__ = [
    "get_conf",
    "reload_conf",
    "get_value",
    "set_value",
    "list_settings",
    "get_config_files",
    "settings",
]
