#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

try:
    import yaml  # type: ignore
except Exception:
    print("Missing dependency: pyyaml. Install with: sudo pip3 install pyyaml", file=sys.stderr)
    sys.exit(1)


@dataclass
class Defaults:
    labels: str = "self-hosted,linux,x64"
    version: str = os.environ.get("RUNNER_VERSION", "latest")
    workdir: str = os.environ.get("RUNNER_WORKDIR", "_work")
    ephemeral: bool = True
    daemonize: bool = True
    base_dir: str = "/opt/runnerctl/runners"


@dataclass
class RunnerDef:
    name: Optional[str]
    name_prefix: Optional[str]
    count: int
    scope: str  # repo|org
    repo: Optional[str]
    org: Optional[str]
    labels: str
    version: str
    workdir: str
    ephemeral: bool
    daemonize: bool


def load_config(path: str) -> tuple[Defaults, List[RunnerDef]]:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    dflt = cfg.get("defaults", {})
    defaults = Defaults(
        labels=str(dflt.get("labels", Defaults.labels)),
        version=str(dflt.get("version", Defaults.version)),
        workdir=str(dflt.get("workdir", Defaults.workdir)),
        ephemeral=bool(dflt.get("ephemeral", Defaults.ephemeral)),
        daemonize=bool(dflt.get("daemonize", Defaults.daemonize)),
        base_dir=str(dflt.get("base_dir", Defaults.base_dir)),
    )
    runners: List[RunnerDef] = []
    for item in cfg.get("runners", []) or []:
        name = item.get("name")
        name_prefix = item.get("name_prefix")
        count = int(item.get("count", 1))
        scope = item.get("scope", "repo")
        repo = item.get("repo")
        org = item.get("org")
        labels = ",".join(item.get("labels", defaults.labels).split(","))
        version = item.get("version", defaults.version)
        workdir = item.get("workdir", defaults.workdir)
        ephemeral = bool(item.get("ephemeral", defaults.ephemeral))
        daemonize = bool(item.get("daemonize", defaults.daemonize))
        runners.append(
            RunnerDef(
                name=name,
                name_prefix=name_prefix,
                count=count,
                scope=scope,
                repo=repo,
                org=org,
                labels=labels,
                version=version,
                workdir=workdir,
                ephemeral=ephemeral,
                daemonize=daemonize,
            )
        )
    return defaults, runners


def ensure_runner(defn: RunnerDef, defaults: Defaults, index: int) -> None:
    name = defn.name or f"{defn.name_prefix}-{index}" if defn.name_prefix else None
    if not name:
        raise SystemExit("Each runner requires either name or name_prefix")

    runner_home = os.path.join(defaults.base_dir, name)
    os.makedirs(runner_home, exist_ok=True)
    pid_file = os.path.join(runner_home, "runner.pid")
    pid = None
    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r", encoding="utf-8") as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            # process alive
            return
        except Exception:
            pid = None

    env = {
        "RUNNER_SCOPE": defn.scope,
        "REPO": defn.repo or "",
        "ORG": defn.org or "",
        "RUNNER_NAME": name,
        "RUNNER_LABELS": defn.labels,
        "RUNNER_VERSION": defn.version,
        "RUNNER_WORKDIR": defn.workdir,
        "EPHEMERAL": "true" if defn.ephemeral else "false",
        "DAEMONIZE": "true" if defn.daemonize else "false",
        "RUNNER_HOME": runner_home,
    }
    script = os.path.join(os.path.dirname(__file__), "self-runner-ctl.sh")
    cmd = f"{script} register"
    subprocess.Popen(cmd, shell=True, env={**os.environ, **env})


def main() -> None:
    parser = argparse.ArgumentParser(description="RunnerCTL manager: ensure desired runners are present")
    parser.add_argument("--config", default=os.environ.get("RUNNERCTL_CONFIG", "/etc/runnerctl/runnerctl.yaml"))
    parser.add_argument("--interval", type=int, default=int(os.environ.get("RUNNERCTL_INTERVAL", "10")))
    args = parser.parse_args()

    defaults, runners = load_config(args.config)
    while True:
        for defn in runners:
            total = defn.count if defn.count > 0 else 1
            for i in range(1, total + 1):
                try:
                    ensure_runner(defn, defaults, i)
                except Exception as e:
                    print(f"ensure_runner error: {e}", file=sys.stderr)
                    continue
        time.sleep(args.interval)


if __name__ == "__main__":
    main()

