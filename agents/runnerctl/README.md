# RunnerCTL - GitHub Actions Self-Hosted Runner Management

RunnerCTL is a comprehensive tool for deploying, managing, and maintaining pools of GitHub Actions self-hosted runners on-premise. It supports two modes of operation:

- **Managed Mode**: Configuration-driven runner pool supervisor (YAML-based, systemd service)
- **API Mode**: HTTP API server for dynamic runner provisioning (REST endpoints)

## Features

✅ **GitHub App Integration** - Secure authentication with GitHub (supports org and repo scopes)  
✅ **Runner Pools** - Maintain persistent and ephemeral runner pools from config  
✅ **Environment Overrides** - Flexible configuration via environment variables (Pydantic Settings v2)  
✅ **Daemonization** - Run runners as background processes with automatic monitoring  
✅ **Multi-Instance** - Support multiple runners per host with isolated directories  
✅ **HTTP API** - REST API for programmatic runner management  
✅ **Systemd Integration** - Production-ready service files with security hardening  

## Quick Start

### Installation

Install directly from GitHub:

```bash
pip install git+https://github.com/pv-udpv/iptvportal-client.git#subdirectory=agents/runnerctl
```

Or from local clone:

```bash
cd agents/runnerctl
pip install -e .
```

### Verify Installation

```bash
runnerctl --help
runnerctl-manager --help
runnerctl-server --help
```

## Documentation

- **[Installation Guide](docs/installation.md)** - System setup and package installation
- **[GitHub App Setup](docs/github-app-setup.md)** - Creating and configuring GitHub Apps
- **[Managed Mode](docs/managed-mode.md)** - Configuration-driven runner pools
- **[API Mode](docs/api-mode.md)** - HTTP API server and dynamic provisioning
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions

## Use Cases

### 1. Private Repository Builds

Keep runners private for sensitive repositories where GitHub-hosted runners aren't suitable:

```yaml
runners:
  - name: private-build-1
    scope: repo
    repo: myorg/private-repo
    ephemeral: false
    labels: self-hosted,linux,x64,build
```

### 2. Ephemeral CI/CD Pipeline

Maintain a pool of temporary runners for short-lived CI jobs:

```yaml
runners:
  - name_prefix: ci-pool
    scope: repo
    repo: myorg/product
    count: 5
    ephemeral: true
    labels: self-hosted,linux,x64,ci
```

### 3. Organization-Wide Runners

Provide shared runners across multiple repositories:

```yaml
runners:
  - name_prefix: org-runners
    scope: org
    org: myorg
    count: 10
    ephemeral: true
    labels: self-hosted,linux,x64,shared
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub (api.github.com)                  │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
                ┌─────────────┼─────────────┐
                │             │             │
        ┌───────▼──────┐  ┌──▼────────┐  ┌─▼────────────┐
        │ App Auth JWT │  │ Reg Token │  │ Remove Token │
        └──────────────┘  └───────────┘  └──────────────┘
                              ▲               ▲
                              │               │
                    ┌─────────┴───────────────┴──────┐
                    │                                │
            ┌───────▼────────────────┐      ┌────────▼──────────┐
            │ runnerctl-manager      │      │ runnerctl-server  │
            │ (Managed Mode)         │      │ (API Mode)        │
            └───────────────────────┬┘      └──┬─────────────────┘
                    │               │          │
            ┌───────▼───────────────▼──────────▼───────┐
            │   self-runner-ctl.sh                      │
            │   - Download actions/runner               │
            │   - Configure runner                      │
            │   - Start (foreground or daemon)          │
            └───────────────────────┬────────────────────┘
                                    │
                    ┌───────────────▼──────────────┐
                    │ /opt/runnerctl/runners/      │
                    │ ├── runner-1/                │
                    │ │   ├── config/              │
                    │ │   ├── _work/               │
                    │ │   ├── run.sh               │
                    │ │   ├── runner.pid           │
                    │ │   └── runner.log           │
                    │ ├── runner-2/                │
                    │ └── ...                      │
                    └───────────────────────────────┘
```

## Configuration

### Managed Mode (runnerctl-manager)

YAML configuration at `/etc/runnerctl/runnerctl.yaml`:

```yaml
defaults:
  labels: self-hosted,linux,x64
  version: latest
  workdir: _work
  ephemeral: true
  daemonize: true
  base_dir: /opt/runnerctl/runners

runners:
  - name: build-runner-1
    scope: repo
    repo: owner/repo
    ephemeral: false
    
  - name_prefix: ephem-pool
    scope: repo
    repo: owner/repo
    count: 3
    ephemeral: true
```

### API Mode (runnerctl-server)

Environment variables:

```bash
GITHUB_WFA_RUNNER_SERVER__API_TOKEN=your-secret-token
GITHUB_WFA_RUNNER_SERVER__BIND=127.0.0.1:8080
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY_B64=<base64-pem>
```

## Requirements

- Linux host with outbound HTTPS access to GitHub
- Python 3.9+
- System packages: `curl`, `openssl`, `tar`, `gzip`, `jq`
- GitHub App with appropriate permissions

## License

MIT

## Contributing

Issues and pull requests welcome at [GitHub](https://github.com/pv-udpv/iptvportal-client).
