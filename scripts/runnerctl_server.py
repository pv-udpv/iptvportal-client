#!/usr/bin/env python3
"""
Lightweight RunnerCTL HTTP server (Typer/Pydantic Settings v2 ready).

Endpoints:
  - POST /api/v1/runners
      Body JSON: {"repo"|"org", "name", "labels", "ephemeral": bool, "version", "workdir", "daemonize": bool}
  - DELETE /api/v1/runners/{name}
      Body JSON: {"repo"|"org"}
  - GET /health

Auth:
  - Require header: Authorization: Bearer <API token>
    - Preferred env: GITHUB_WFA_RUNNER_SERVER__API_TOKEN (short: GHWFAX__SERVER__API_TOKEN)
    - Back-compat: RUNNERCTL_API_TOKEN

Settings (env, nested delimiter __):
  - GITHUB_WFA_RUNNER_SERVER__BIND (default 127.0.0.1:8080)
  - GITHUB_WFA_RUNNER_SERVER__SCRIPT (defaults to scripts/self-runner-ctl.sh)
  - Back-compat: RUNNERCTL_BIND
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Tuple

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


def _merge_short_prefix_env() -> None:
    # Map short prefix GHWFAX__* to full GITHUB_WFA_RUNNER_* for server settings
    alt = "GHWFAX__"
    full = "GITHUB_WFA_RUNNER_"
    for k, v in list(os.environ.items()):
        if k.startswith(alt):
            mapped = full + k[len(alt) :]
            os.environ.setdefault(mapped, v)


class ServerSettings(BaseSettings):
    api_token: str = Field(default="")
    bind: str = Field(default="127.0.0.1:8080")
    script: str = Field(default=os.path.join(os.path.dirname(__file__), "self-runner-ctl.sh"))

    model_config = SettingsConfigDict(
        env_prefix="GITHUB_WFA_RUNNER_SERVER_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    def with_back_compat(self) -> "ServerSettings":
        # Backwards compatibility fallbacks
        if not self.api_token:
            self.api_token = os.environ.get("RUNNERCTL_API_TOKEN", self.api_token)
        if self.bind == "127.0.0.1:8080":
            self.bind = os.environ.get("RUNNERCTL_BIND", self.bind)
        return self


_merge_short_prefix_env()
SETTINGS = ServerSettings().with_back_compat()


def _authz(headers) -> bool:
    if not SETTINGS.api_token:
        return False
    auth = headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    return auth.split(" ", 1)[1] == SETTINGS.api_token


def _json_body(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length == 0:
        return {}
    data = handler.rfile.read(length)
    try:
        return json.loads(data.decode("utf-8"))
    except Exception:
        return {}


def _ok(handler: BaseHTTPRequestHandler, obj: Dict[str, Any], status: int = 200):
    payload = json.dumps(obj).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def _err(handler: BaseHTTPRequestHandler, msg: str, status: int = 400):
    _ok(handler, {"error": msg}, status)


def _spawn(cmd: str, env: Dict[str, str]) -> Tuple[int, str]:
    proc = subprocess.Popen(cmd, shell=True, env={**os.environ, **env})
    return proc.pid, "started"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            self.send_response(HTTPStatus.OK)
            self.end_headers()
            self.wfile.write(b"ok")
            return
        _err(self, "Not found", 404)

    def do_POST(self):  # noqa: N802
        if not _authz(self.headers):
            _err(self, "Unauthorized", 401)
            return

        if self.path == "/api/v1/runners":
            data = _json_body(self)
            scope_repo = data.get("repo")
            scope_org = data.get("org")
            name = data.get("name")
            if not name:
                _err(self, "name is required", 422)
                return
            if not scope_repo and not scope_org:
                _err(self, "repo or org is required", 422)
                return

            labels = data.get("labels", "self-hosted,linux,x64")
            version = data.get("version", os.environ.get("RUNNER_VERSION", "latest"))
            workdir = data.get("workdir", os.environ.get("RUNNER_WORKDIR", "_work"))
            ephemeral = bool(data.get("ephemeral", True))
            daemonize = bool(data.get("daemonize", True))

            env = {
                "RUNNER_SCOPE": "org" if scope_org else "repo",
                "ORG": scope_org or "",
                "REPO": scope_repo or "",
                "RUNNER_NAME": str(name),
                "RUNNER_LABELS": str(labels),
                "RUNNER_VERSION": str(version),
                "RUNNER_WORKDIR": str(workdir),
                "EPHEMERAL": "true" if ephemeral else "false",
                "DAEMONIZE": "true" if daemonize else "false",
            }
            # Secrets for GitHub App / PAT are inherited from server environment.
            cmd = f"{shlex.quote(SETTINGS.script)} register"
            pid, state = _spawn(cmd, env)
            _ok(self, {"name": name, "pid": pid, "state": state})
            return

        _err(self, "Not found", 404)

    def do_DELETE(self):  # noqa: N802
        if not _authz(self.headers):
            _err(self, "Unauthorized", 401)
            return
        m = re.match(r"^/api/v1/runners/([^/]+)$", self.path)
        if not m:
            _err(self, "Not found", 404)
            return
        name = m.group(1)
        data = _json_body(self)
        scope_repo = (data or {}).get("repo")
        scope_org = (data or {}).get("org")
        if not scope_repo and not scope_org:
            _err(self, "repo or org is required in body", 422)
            return
        env = {
            "RUNNER_SCOPE": "org" if scope_org else "repo",
            "ORG": scope_org or "",
            "REPO": scope_repo or "",
            "RUNNER_NAME": str(name),
        }
        cmd = f"{shlex.quote(SETTINGS.script)} remove"
        pid, state = _spawn(cmd, env)
        _ok(self, {"name": name, "pid": pid, "state": state})


def main() -> None:
    if not SETTINGS.api_token:
        raise SystemExit("API token not configured. Set GITHUB_WFA_RUNNER_SERVER__API_TOKEN or RUNNERCTL_API_TOKEN")
    host, _, port = SETTINGS.bind.partition(":")
    if not port:
        port = "8080"
    server = HTTPServer((host, int(port)), Handler)
    print(f"RunnerCTL server listening on http://{SETTINGS.bind}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
