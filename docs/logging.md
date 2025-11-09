# Logging design and configuration notes (generated)

This document summarizes the implemented logging integration for IPTVPortal.

## Overview

- Added `src/iptvportal/logging_setup.py` to build and apply logging configuration from Dynaconf.
- Logging config lives under the `logging` key in `config/settings.yaml` and supports:
  - Console & rotating file handlers
  - Colored console output (via colorlog)
  - JSON file output (via python-json-logger)
  - Per-module loggers under `logging.loggers`
  - Third-party library log level defaults

## Envvar Overrides

Dynaconf supports nested envvars with `__` delimiter. Example overrides:

```bash
# Root logging level
export IPTVPORTAL_LOGGING__LEVEL=DEBUG

# Enable file handler and set path
export IPTVPORTAL_LOGGING__HANDLERS__FILE__ENABLED=true
export IPTVPORTAL_LOGGING__HANDLERS__FILE__PATH=/tmp/iptv.log

# Per-module logger level
export IPTVPORTAL_LOGGING__LOGGERS__iptvportal_client__LEVEL=DEBUG
```

Notes:
- Triple underscore `___` is reserved by Dynaconf for list indexing; do not use it for module boundaries.
- For ambiguous snake_case module names, prefer using dot notation in YAML or the triple-underscore convention if needed (see section below).

## Snake_case Module Name Disambiguation

Two recommended approaches:

1. Use explicit dot-notation in YAML (recommended):
   ```yaml
   logging:
     loggers:
       "iptvportal.query_builder.select":
         level: DEBUG
   ```

2. Use triple-underscore in environment vars to mark module boundaries:
   ```bash
   export IPTVPORTAL_LOGGING__LOGGERS__iptvportal___query_builder___select__LEVEL=DEBUG
   ```

Also consider maintaining a `KNOWN_MODULES` registry in `logging_setup.py` for smart name resolution.

## Integration

- `src/iptvportal/config/project.py` now calls `setup_logging` after loading dynaconf.
- `reload_conf()` reconfigures logging to apply changes dynamically.

## Testing

Suggested tests:
- Validate dictConfig is generated for default config
- Validate env var overrides apply to handlers and per-module loggers
- Ensure logging setup does not crash when optional deps missing (colorlog / python-json-logger)
- Integration tests for CLI flags that change logging level at runtime

## Next steps / Improvements

- Add unit tests for `logging_setup.py`
- Add `KNOWN_MODULES` registry and implement smart matching resolver
- Optionally implement Pydantic wrapper for validated config (hybrid approach)


