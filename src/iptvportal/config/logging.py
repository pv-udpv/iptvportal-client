"""Logging configuration integrated with Dynaconf for IPTVPortal (config package).

This module is a refactor of the previous :mod:`iptvportal.logging_setup`.
It provides:
- building logging.dictConfig from a dynaconf `logging` section
- setup_logging(conf) to apply configuration
- reconfigure_logging() to reload from current dynaconf config
- set_module_log_level(module, level) to change levels at runtime
- get_logger(name=None) helper
"""

from __future__ import annotations

import inspect
import logging
import logging.config
from contextlib import suppress
from pathlib import Path
from typing import Any

from dynaconf import Dynaconf

from iptvportal.config.project import (
    get_conf,
    set_value,
)  # imported lazily by callers in some codepaths


def _ensure_log_dir(path: str | Path) -> None:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Best-effort: do not fail app startup because of logging dir issues
        pass


def _build_formatters(cfg: dict[str, Any]) -> dict[str, Any]:
    formatters: dict[str, Any] = {}
    fmt = cfg.get("format") or "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"
    formatters["default"] = {"format": fmt, "datefmt": "%Y-%m-%d %H:%M:%S"}

    # colored formatter (optional)
    colorize = cfg.get("handlers", {}).get("console", {}).get("colorize", True)
    if colorize:
        with suppress(Exception):
            formatters["colored"] = {
                "()": "colorlog.ColoredFormatter",
                "format": "%(log_color)s" + fmt,
                "datefmt": "%Y-%m-%d %H:%M:%S",
                "log_colors": {
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "red,bg_white",
                },
            }

    # json formatter (optional)
    file_json = cfg.get("handlers", {}).get("file", {}).get("json_format", False)
    if file_json:
        with suppress(Exception):
            formatters["json"] = {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(funcName)s %(message)s",
            }

    return formatters


def _build_handlers(
    cfg: dict[str, Any], formatters: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    handlers: dict[str, Any] = {}
    handler_names: list[str] = []

    # Console handler
    console_cfg = cfg.get("handlers", {}).get("console", {})
    if console_cfg.get("enabled", True):
        formatter = "colored" if "colored" in formatters else "default"
        handlers["console"] = {
            "class": "logging.StreamHandler",
            "level": console_cfg.get("level", "DEBUG"),
            "formatter": formatter,
            "stream": "ext://sys.stdout",
        }
        handler_names.append("console")

    # File handler
    file_cfg = cfg.get("handlers", {}).get("file", {})
    if file_cfg.get("enabled", False):
        path = file_cfg.get("path", "logs/iptvportal.log")
        _ensure_log_dir(path)
        formatter = (
            "json" if ("json" in formatters and file_cfg.get("json_format", False)) else "default"
        )
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": file_cfg.get("level", "INFO"),
            "formatter": formatter,
            "filename": str(path),
            "maxBytes": file_cfg.get("max_bytes", 10_485_760),
            "backupCount": file_cfg.get("backup_count", 5),
            "encoding": "utf-8",
        }
        handler_names.append("file")

    return handlers, handler_names


def _build_loggers(cfg: dict[str, Any], handler_names: list[str]) -> dict[str, Any]:
    """
    Build logger mappings.

    Supports several logger-name formats:
    - Dot notation (recommended): "iptvportal.client.sync"
    - Underscore shorthand (env vars): "iptvportal_client_sync" -> "iptvportal.client.sync"
    - Triple underscore as explicit boundary: "iptvportal___client___sync" -> "iptvportal.client.sync"
    """

    # Optional registry for known snake_case module names to disambiguate
    KNOWN_MODULES: dict[str, str] = {
        # Auto-generated mapping of snake_case keys -> dotted module paths
        # Keys are suitable for environment variable forms (underscored)
        "exceptions": "iptvportal.exceptions",
        "logging_setup": "iptvportal.logging_setup",
        "validation": "iptvportal.validation",
        "project_conf": "iptvportal.project_conf",
        "sync_exceptions": "iptvportal.sync.exceptions",
        "sync_manager": "iptvportal.sync.manager",
        "sync_database": "iptvportal.sync.database",
        "config_settings": "iptvportal.config.settings",
        "config_project": "iptvportal.config.project",
        "config_logging": "iptvportal.config.logging",
        "schema_codegen": "iptvportal.schema.codegen",
        "schema_table": "iptvportal.schema.table",
        "schema_introspector": "iptvportal.schema.introspector",
        "core_client": "iptvportal.core.client",
        "core_auth": "iptvportal.core.auth",
        "core_cache": "iptvportal.core.cache",
        "core_async_client": "iptvportal.core.async_client",
        "models_requests": "iptvportal.models.requests",
        "models_responses": "iptvportal.models.responses",
        "service_query": "iptvportal.service.query",
        "cli_debug": "iptvportal.cli.debug",
        "cli_introspection": "iptvportal.cli.introspection",
        "cli_utils": "iptvportal.cli.utils",
        "cli_formatters": "iptvportal.cli.formatters",
        "cli_commands_sql": "iptvportal.cli.commands.sql",
        "cli_commands_sync": "iptvportal.cli.commands.sync",
        "cli_commands_schema": "iptvportal.cli.commands.schema",
        "cli_commands_transpile": "iptvportal.cli.commands.transpile",
        "cli_commands_jsonsql": "iptvportal.cli.commands.jsonsql",
        "cli_commands_auth": "iptvportal.cli.commands.auth",
        "cli_commands_cache": "iptvportal.cli.commands.cache",
        "cli_commands_config": "iptvportal.cli.commands.config",
        "cli_core_editor": "iptvportal.cli.core.editor",
        "jsonsql_functions": "iptvportal.jsonsql.functions",
        "jsonsql_exceptions": "iptvportal.jsonsql.exceptions",
        "jsonsql_operators": "iptvportal.jsonsql.operators",
        "jsonsql_builder": "iptvportal.jsonsql.builder",
        "jsonsql_transpiler": "iptvportal.jsonsql.transpiler",
    }

    def resolve_logger_name(raw: str) -> str:
        """Resolve env/config key to Python logger dotted path."""
        # If already dot notation, return as-is
        if "." in raw:
            return raw

        # Triple underscore marks explicit boundaries
        if "___" in raw:
            return raw.replace("___", ".")

        # Try registry-based substitution
        for key, replacement in KNOWN_MODULES.items():
            if key in raw:
                return raw.replace(key, replacement).replace("_", ".").strip(".")

        # Fallback heuristic:
        # Convert first underscore after package name to dot, then remaining underscores to dots.
        # e.g., iptvportal_client_sync -> iptvportal.client.sync
        if raw.startswith("iptvportal_"):
            remainder = raw[len("iptvportal_") :]
            return "iptvportal." + remainder.replace("_", ".")
        # Generic fallback: replace all underscores with dots
        return raw.replace("_", ".")

    # Base package logger
    loggers: dict[str, Any] = {}
    base_level = cfg.get("level", "INFO")
    loggers["iptvportal"] = {"level": base_level, "handlers": handler_names, "propagate": False}

    # Custom loggers, expect a mapping under "loggers"
    custom = cfg.get("loggers", {}) or {}
    for name, val in custom.items():
        actual_name = resolve_logger_name(name)
        if isinstance(val, dict):
            level = val.get("level", base_level)
            handlers = val.get("handlers", handler_names)
            propagate = val.get("propagate", False)
        else:
            # shorthand: string => level
            level = str(val).upper()
            handlers = handler_names
            propagate = False
        loggers[actual_name] = {"level": level, "handlers": handlers, "propagate": propagate}

    # Third-party libs defaults
    lib_level = cfg.get("library_level", "WARNING")
    for lib in ("httpx", "urllib3", "requests", "httpcore"):
        if lib not in loggers:
            loggers[lib] = {"level": lib_level, "handlers": handler_names, "propagate": False}

    return loggers


def _build_dict_config(cfg: dict[str, Any]) -> dict[str, Any]:
    formatters = _build_formatters(cfg)
    handlers, handler_names = _build_handlers(cfg, formatters)
    loggers = _build_loggers(cfg, handler_names)
    lib_level = cfg.get("library_level", "WARNING")

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "loggers": loggers,
        "root": {"level": lib_level, "handlers": handler_names},
    }


def setup_logging(dynaconf_conf: Dynaconf | dict | None = None) -> None:
    """
    Configure logging from a dynaconf configuration object or plain dict.

    Accepts either a Dynaconf instance or a dict with a "logging" key.
    If dynaconf_conf is None, tries to use project.get_conf() to obtain current config.
    """
    try:
        if dynaconf_conf is None:
            try:
                dynaconf_conf = get_conf()
            except Exception:
                dynaconf_conf = None

        if dynaconf_conf is None:
            cfg: dict[str, Any] = {}
        elif isinstance(dynaconf_conf, (Dynaconf, dict)):
            cfg = dynaconf_conf.get("logging", {}) or {}
        else:
            # Fallback: try to read .as_dict if available
            try:
                cfg = dynaconf_conf.as_dict()
                cfg = cfg.get("logging", {}) or {}
            except Exception:
                cfg = {}

        dict_config = _build_dict_config(cfg)
        logging.config.dictConfig(dict_config)
        logger = logging.getLogger("iptvportal")
        logger.info(
            "Logging configured",
            extra={"configured_handlers": list(dict_config["handlers"].keys())},
        )
    except Exception:
        # Don't fail the application startup due to logging config errors.
        logging.basicConfig(level=logging.INFO)
        logging.getLogger("iptvportal").warning(
            "Failed to apply advanced logging config; using basicConfig"
        )


def reconfigure_logging() -> None:
    """Reload logging configuration from the active dynaconf configuration."""
    try:
        cfg = get_conf()
    except Exception:
        cfg = None
    setup_logging(cfg)


def set_module_log_level(module: str, level: str) -> None:
    """Set the logging level for a module at runtime and persist to Dynaconf.

    Args:
        module: Module name, dot or underscore notation accepted.
        level: String log level name (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    level_name = str(level).upper()
    valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if level_name not in valid:
        raise ValueError(f"Invalid log level: {level}")

    # Normalize module name (convert underscores to dots)
    name = module if "." in module else module.replace("_", ".")
    logging.getLogger(name).setLevel(level_name)

    # Persist to dynaconf so reconfigure_logging can pick it up later
    try:
        # store under logging.loggers.<module_key>.level using underscores to be safe for env mapping
        module_key = name.replace(".", "_")
        set_value(f"logging.loggers.{module_key}.level", level_name)
    except Exception:
        # best-effort: don't fail on persistence
        pass


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a configured logger instance.

    If name is None, infer module name from caller frame.
    """
    if name:
        return logging.getLogger(name)

    # Infer caller module safely (guard against None f_back)
    frame = inspect.currentframe()
    if frame is None:
        return logging.getLogger()

    prev = getattr(frame, "f_back", None)
    caller = getattr(prev, "f_back", None) if prev is not None else None

    # If we couldn't reach the caller two frames up, try one frame up or fallback
    target_frame = caller or prev or frame
    module_name = ""
    try:
        module_name = getattr(target_frame, "f_globals", {}).get("__name__", "")  # type: ignore[arg-type]
    except Exception:
        module_name = ""

    return logging.getLogger(module_name or "")
