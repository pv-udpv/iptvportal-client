"""Project configuration (backward compatibility).

This module provides backward compatibility for code importing from iptvportal.project_conf.
"""

# Re-export everything from the new location
from iptvportal.config.project import (
    get_conf,
    get_config_files,
    get_value,
    list_settings,
    reload_conf,
    set_value,
)

# Re-export the settings instance
settings = get_conf()

__all__ = [
    "get_conf",
    "get_value",
    "set_value",
    "reload_conf",
    "list_settings",
    "get_config_files",
    "settings",
]
