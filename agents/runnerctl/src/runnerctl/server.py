#!/usr/bin/env python3
"""RunnerCTL API Server - HTTP API for runner management."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import uvicorn

app = FastAPI(
    title="RunnerCTL API",
    description="GitHub Actions self-hosted runner management API",
    version="0.1.0",
)

# Global settings instance - created once at module level
SETTINGS: Optional["ServerSettings"] = None

class ServerSettings(BaseSettings):
    """Server configuration from environment."""

    api_token: str = Field(default="", validation_alias="GITHUB_WFA_RUNNER_SERVER__API_TOKEN")
    bind: str = Field(default="127.0.0.1:8080", validation_alias="GITHUB_WFA_RUNNER_SERVER__BIND")

    model_config = SettingsConfigDict(
        env_prefix="GITHUB_WFA_RUNNER_SERVER__",
        case_sensitive=False,
        extra="ignore",
    )

class RunnerRequest(BaseModel):
    """Runner creation request."""

    repo: str = Field(..., description="Repository in format owner/repo")
    name: str = Field(..., description="Runner name")
    labels: str = Field(default="self-hosted,linux,x64", description="Runner labels")
    ephemeral: bool = Field(default=True, description="Ephemeral runner")
    daemonize: bool = Field(default=True, description="Run as background process")

class RunnerRemovalRequest(BaseModel):
    """Runner removal request."""

    repo: str = Field(..., description="Repository in format owner/repo")

@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}

@app.post("/api/v1/runners")
async def create_runner(
    req: RunnerRequest,
    authorization: Optional[str] = Header(None),
) -> dict:
    """Create and register a new runner."""
    assert SETTINGS is not None, "Settings not initialized"
    
    # Verify API token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    
    token = authorization[7:]  # Remove "Bearer " prefix
    if token != SETTINGS.api_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")
    
    # Validate runner name to prevent path traversal
    if "/" in req.name or "\\" in req.name or req.name.startswith("."):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid runner name")
    
    # Prepare environment for runner script
    env = {
        **os.environ,
        "RUNNER_SCOPE": "repo",
        "REPO": req.repo,
        "RUNNER_NAME": req.name,
        "RUNNER_LABELS": req.labels.replace(" ", ""),
        "EPHEMERAL": "true" if req.ephemeral else "false",
        "DAEMONIZE": "true" if req.daemonize else "false",
        "RUNNER_HOME": f"/opt/runnerctl/runners/{req.name}",
    }
    
    # Call runner script
    script = os.path.join(os.path.dirname(__file__), "shell", "self-runner-ctl.sh")
    try:
        subprocess.Popen([script, "register"], env=env)
        return {"status": "started", "name": req.name}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.delete("/api/v1/runners/{runner_name}")
async def remove_runner(
    runner_name: str,
    req: RunnerRemovalRequest,
    authorization: Optional[str] = Header(None),
) -> dict:
    """Remove and deregister a runner."""
    assert SETTINGS is not None, "Settings not initialized"
    
    # Verify API token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    
    token = authorization[7:]  # Remove "Bearer " prefix
    if token != SETTINGS.api_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")
    
    # Validate runner_name to prevent path traversal
    if "/" in runner_name or "\\" in runner_name or runner_name.startswith("."):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid runner name")
    
    # Prepare environment
    env = {
        **os.environ,
        "RUNNER_SCOPE": "repo",
        "REPO": req.repo,
        "RUNNER_HOME": f"/opt/runnerctl/runners/{runner_name}",
    }
    
    # Call runner script
    script = os.path.join(os.path.dirname(__file__), "shell", "self-runner-ctl.sh")
    try:
        subprocess.Popen([script, "remove"], env=env)
        return {"status": "removed", "name": runner_name}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/api/v1/runners/{runner_name}/status")
async def runner_status(
    runner_name: str,
    authorization: Optional[str] = Header(None),
) -> dict:
    """Get runner status."""
    assert SETTINGS is not None, "Settings not initialized"
    
    # Verify API token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    
    token = authorization[7:]  # Remove "Bearer " prefix
    if token != SETTINGS.api_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")
    
    # Validate runner_name to prevent path traversal
    if "/" in runner_name or "\\" in runner_name or runner_name.startswith("."):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid runner name")
    
    runner_home = f"/opt/runnerctl/runners/{runner_name}"
    pid_file = f"{runner_home}/runner.pid"
    
    if not os.path.exists(runner_home):
        return {"status": "not_installed", "name": runner_name}
    
    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r", encoding="utf-8") as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return {"status": "running", "name": runner_name, "pid": pid}
        except Exception:
            pass
    
    return {"status": "installed_not_running", "name": runner_name}

def main() -> None:
    """Run the API server."""
    global SETTINGS
    SETTINGS = ServerSettings()
    
    if not SETTINGS.api_token:
        print("ERROR: GITHUB_WFA_RUNNER_SERVER__API_TOKEN environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    host, port = SETTINGS.bind.rsplit(":", 1)
    uvicorn.run(app, host=host, port=int(port), log_level="info")

if __name__ == "__main__":
    main()
