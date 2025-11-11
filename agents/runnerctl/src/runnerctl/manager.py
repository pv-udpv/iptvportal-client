#!/usr/bin/env python3
"""RunnerCTL Manager - Maintains a pool of self-hosted runners from config."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import List, Optional, Tuple

import typer
import yaml  # type: ignore
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

APP = typer.Typer(
    add_completion=False,
    help="RunnerCTL manager: maintain a pool of self-hosted runners from config",
)


def _merge_short_prefix_env() -> None:
    """Support alternate short env prefix GHWFAX__ by mapping it to GITHUB_WFA_RUNNER_."""
    alt = "GHWFAX__"
    full = "GITHUB_WFA_RUNNER_"
    for k, v in list(os.environ.items()):
        if k.startswith(alt):
            mapped = full + k[len(alt) :]
            os.environ.setdefault(mapped, v)


class DefaultsModel(BaseModel):
    """Default configuration for runners."""

    labels: str = Field(default="self-hosted,linux,x64")
    version: str = Field(default=os.environ.get("RUNNER_VERSION", "latest"))
    workdir: str = Field(default=os.environ.get("RUNNER_WORKDIR", "_work"))
    ephemeral: bool = Field(default=True)
    daemonize: bool = Field(default=True)
    base_dir: str = Field(default="/opt/runnerctl/runners")


class RunnerItem(BaseModel):
    """Individual runner configuration."""

    name: Optional[str] = None
    name_prefix: Optional[str] = None
    count: int = 1
    scope: str = Field(default="repo")  # repo|org
    repo: Optional[str] = None
    org: Optional[str] = None
    labels: Optional[str] = None
    version: Optional[str] = None
    workdir: Optional[str] = None
    ephemeral: Optional[bool] = None
    daemonize: Optional[bool] = None

    def resolve(self, defaults: DefaultsModel) -> Tuple[str, str, str, str, bool, bool]:
        """Resolve runner configuration with defaults."""
        labels = (self.labels or defaults.labels).replace(" ", "")
        version = self.version or defaults.version
        workdir = self.workdir or defaults.workdir
        ephemeral = defaults.ephemeral if self.ephemeral is None else self.ephemeral
        daemonize = defaults.daemonize if self.daemonize is None else self.daemonize
        scope = self.scope
        if scope not in ("repo", "org"):
            raise ValueError(f"Invalid scope: {scope}")
        return scope, labels, version, workdir, ephemeral, daemonize


class FileConfig(BaseModel):
    """File-based configuration structure."""

    defaults: DefaultsModel = Field(default_factory=DefaultsModel)
    runners: List[RunnerItem] = Field(default_factory=list)


class ManagerSettings(BaseSettings):
    """Manager settings from environment."""

    config: str = "/etc/runnerctl/runnerctl.yaml"
    interval: int = 10

    model_config = SettingsConfigDict(
        env_prefix="GITHUB_WFA_RUNNER_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )


class DefaultsEnvOverrides(BaseSettings):
    """Environment-driven overrides for defaults section.

    Prefix: GITHUB_WFA_RUNNER_DEFAULTS__ (short: GHWFAX__DEFAULTS__)
    Examples:
      - GITHUB_WFA_RUNNER_DEFAULTS__LABELS="self-hosted,linux,x64,build"
      - GITHUB_WFA_RUNNER_DEFAULTS__BASE_DIR="/opt/runnerctl/runners"
      - GITHUB_WFA_RUNNER_DEFAULTS__EPHEMERAL=false
    """

    labels: Optional[str] = None
    version: Optional[str] = None
    workdir: Optional[str] = None
    ephemeral: Optional[bool] = None
    daemonize: Optional[bool] = None
    base_dir: Optional[str] = None

    model_config = SettingsConfigDict(
        env_prefix="GITHUB_WFA_RUNNER_DEFAULTS_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )


def load_config(path: str) -> FileConfig:
    """Load and validate configuration from YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    cfg = FileConfig.model_validate(raw)
    # Apply env overrides to defaults (pydantic-settings v2)
    _merge_short_prefix_env()
    env_over = DefaultsEnvOverrides()
    for field_name in ("labels", "version", "workdir", "ephemeral", "daemonize", "base_dir"):
        val = getattr(env_over, field_name)
        if val is not None:
            if field_name == "labels" and isinstance(val, str):
                val = val.replace(" ", "")
            setattr(cfg.defaults, field_name, val)
    return cfg


def ensure_runner(item: RunnerItem, defaults: DefaultsModel, index: int, base_dir: str) -> None:
    """Ensure a runner is running, starting it if necessary."""
    name: Optional[str] = item.name or (f"{item.name_prefix}-{index}" if item.name_prefix else None)
    if not name:
        raise RuntimeError("Each runner requires either 'name' or 'name_prefix'")

    runner_home = os.path.join(base_dir, name)
    os.makedirs(runner_home, exist_ok=True)
    pid_file = os.path.join(runner_home, "runner.pid")
    if os.path.exists(pid_file):
        try:
            pid = int(open(pid_file, "r", encoding="utf-8").read().strip())
            os.kill(pid, 0)
            return  # still running
        except Exception:
            pass

    scope, labels, version, workdir, ephemeral, daemonize = item.resolve(defaults)
    env = {
        "RUNNER_SCOPE": scope,
        "REPO": item.repo or "",
        "ORG": item.org or "",
        "RUNNER_NAME": name,
        "RUNNER_LABELS": labels,
        "RUNNER_VERSION": version,
        "RUNNER_WORKDIR": workdir,
        "EPHEMERAL": "true" if ephemeral else "false",
        "DAEMONIZE": "true" if daemonize else "false",
        "RUNNER_HOME": runner_home,
    }
    script = os.path.join(os.path.dirname(__file__), "shell", "self-runner-ctl.sh")
    cmd = f"{script} register"
    subprocess.Popen(cmd, shell=True, env={**os.environ, **env})


def _run_loop(settings: ManagerSettings) -> None:
    """Main manager loop ensuring desired runner state."""
    config = load_config(settings.config)
    while True:
        for item in config.runners:
            total = item.count if item.count > 0 else 1
            for i in range(1, total + 1):
                try:
                    ensure_runner(item, config.defaults, i, config.defaults.base_dir)
                except Exception as exc:
                    print(f"ensure_runner error: {exc}", file=sys.stderr)
                    continue
        time.sleep(settings.interval)


@APP.command()
def run(
    config: Optional[str] = typer.Option(None, help="Path to runnerctl YAML config"),
    interval: Optional[int] = typer.Option(None, help="Loop interval seconds"),
) -> None:
    """Run the manager loop, ensuring declared runners are present and online."""
    _merge_short_prefix_env()
    settings = ManagerSettings()
    if config:
        settings.config = config
    if interval is not None:
        settings.interval = interval
    _run_loop(settings)


@APP.command()
def once(
    config: Optional[str] = typer.Option(None, help="Path to runnerctl YAML config"),
) -> None:
    """Perform a single ensure pass and exit."""
    _merge_short_prefix_env()
    settings = ManagerSettings()
    if config:
        settings.config = config
    cfg = load_config(settings.config)
    for item in cfg.runners:
        total = item.count if item.count > 0 else 1
        for i in range(1, total + 1):
            ensure_runner(item, cfg.defaults, i, cfg.defaults.base_dir)


@APP.command()
def print_config(
    config: Optional[str] = typer.Option(None, help="Path to runnerctl YAML config"),
) -> None:
    """Validate and print the effective config with defaults applied (structure only)."""
    _merge_short_prefix_env()
    settings = ManagerSettings()
    if config:
        settings.config = config
    cfg = load_config(settings.config)
    # Print minimal info without secrets
    data = {
        "defaults": cfg.defaults.model_dump(),
        "runners": [item.model_dump() for item in cfg.runners],
    }
    import json as _json

    print(_json.dumps(data, indent=2))


def main() -> None:
    """CLI entrypoint."""
    # Back-compat: treat bare options as 'run' command
    if len(sys.argv) > 1 and sys.argv[1].startswith("-"):
        sys.argv.insert(1, "run")
    APP()


if __name__ == "__main__":
    main()
