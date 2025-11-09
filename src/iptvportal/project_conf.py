# ruff: noqa: I001
"""Backward-compatible project configuration module.

This module re-exports the public configuration API implemented in
``iptvportal.config.project`` to preserve imports used in legacy code
and tests (e.g. ``from iptvportal.project_conf import get_conf`` or
``from iptvportal import project_conf``).
"""

from __future__ import annotations

from iptvportal.config.project import (
    get_conf,
    reload_conf,
    get_value,
    set_value,
    list_settings,
    get_config_files,
    settings,
)

__all__ = [
    "get_conf",
    "reload_conf",
    "get_value",
    "set_value",
    "list_settings",
    "get_config_files",
    "settings",
]
