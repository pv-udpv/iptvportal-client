# GitHub Copilot Workspace Instructions (iptvportal-client)

Short, project-specific rules to make AI agents productive and consistent here.

## Big picture
- Python 3.12+ client and CLI for IPTVPORTAL JSONSQL over JSON-RPC; sync and async APIs.
- Major modules: `auth.py` (session), `client.py`/`async_client.py` (HTTP via httpx), `query/` (builder, Field, Q), `transpiler/` (SQL→JSONSQL using sqlglot), `schema.py` (table schemas + mapping), `sync/` (SQLite cache), `cli/` (Typer app).
- Entry point: `iptvportal` → `iptvportal.cli.__main__:main`.

## CLI surface (current, Nov 2025)
- Commands: `iptvportal config …`, `iptvportal auth [--renew]`, `iptvportal sql …`, `iptvportal jsonsql <select|insert|update|delete> …`, `iptvportal transpile …`.
- Deprecated (don’t use in docs/tests): `iptvportal query select|insert|update|delete`.
- Helpful modes: `--dry-run` (print transpiled JSONSQL & request, don’t execute) and `--show-request` (execute + print JSON-RPC request).
- Schema-aware output is ON by default; disable with `--no-map-schema` to see raw field positions.

## Transpiler behaviors to preserve
- Auto ORDER BY id: `SQLTranspiler(auto_order_by_id=True)` adds `order_by: "id"` for simple SELECTs without joins/group/aggregates when `id` is selected.
- COUNT rules (see tests/docs):
   - `COUNT(*)` → `{function: count, args: ["*"]}`
   - `COUNT(col)` → `{function: count, args: "col"}`
   - `COUNT(DISTINCT col)` → `{function: count, args: {function: distinct, args: "col"}}`
- FROM with JOINs returns list of table refs with `on` expressed via logical ops.

## Integration details
- Auth via JSON-RPC `authorize_user`; subsequent calls require header `Iptvportal-Authorization: sessionid={sid}`.
- DML endpoint is JSONSQL; clients handle retries, timeouts, and rich error bodies (see `exceptions.py`).

## Dev workflow (uv + Makefile)
- Bootstrap: `make dev` (creates venv and installs dev deps). Run: `make test`, `make test-cov`, `make lint`, `make type-check`, or `make ci`.
- Quick CLI runs: `make cli ARGS="sql -q 'SELECT …' --dry-run"`.
- User/system CLI install helpers: `make install-user` or `make install-system` (copies schema templates and creates default config).

## Where to implement changes
- CLI: add/edit commands in `src/iptvportal/cli/commands/*.py` and wire in `cli/__main__.py`.
- Transpiler: `src/iptvportal/transpiler/transpiler.py` (+ helpers in `operators.py`, `functions.py`).
- Client behavior (auth, errors, caching, schema mapping): `client.py`, `async_client.py`, `cache.py`, `schema.py`.

## Tests you must touch
- CLI behavior and modes: `tests/test_cli.py` (asserts help text, dry-run/show-request markers, and key snippets like `"from": "subscriber"`).
- Transpiler coverage/regressions: `tests/test_transpiler.py` (add SQL→JSONSQL cases, especially aggregates/joins).
- Sync/cache/database: `tests/test_sync_*.py` when touching `sync/`.

## Documentation sync (same-commit rule)
- Update all affected docs alongside code:
   - `README.md` (Quick Start, CLI usage, Supported Features, Error Handling examples)
   - `docs/cli.md` (command syntax, modes, examples; note schema mapping and deprecations)
   - `docs/jsonsql.md` (spec nuances you changed, e.g., function args or join shapes)

## Examples (project-specific)
- SQL auto-transpile: `iptvportal sql -q "SELECT COUNT(DISTINCT mac_addr) FROM terminal" --dry-run` → prints nested `distinct` per rules above.
- Native JSONSQL: `iptvportal jsonsql select --from subscriber --data id,username --limit 5 --show-request`.

When in doubt, mirror existing patterns and update docs/tests in the same commit.
