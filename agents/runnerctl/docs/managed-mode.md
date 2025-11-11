# Managed Mode Guide

Managed Mode is a supervisor service that maintains your desired runner pool from a YAML configuration file. It continuously ensures that the declared runners are registered and online.

## Overview

Managed Mode is ideal for:
- Production deployments with static runner requirements
- On-premise infrastructure with persistent runners
- Organizations needing consistent runner availability
- Configuration-as-code approach to infrastructure

The manager service runs on a 10-second loop (configurable) and ensures:
1. Each declared runner is registered with GitHub
2. Runners stay online and healthy
3. Ephemeral runners are respawned after jobs complete
4. Persistent runners are restarted if they crash

## Architecture

```
┌─────────────────────────────────────────────────┐
│  /etc/runnerctl/runnerctl.yaml (Config)        │
│  defaults:                                      │
│    - labels, version, workdir, ephemeral, ...  │
│  runners:                                       │
│    - name: runner-1                             │
│    - name_prefix: pool- (count: 3)              │
└────────────────────┬────────────────────────────┘
                     │
        ┌────────────▼────────────┐
        │  runnerctl-manager      │
        │  (systemd service)      │
        │  Loop interval: 10s     │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────────────────┐
        │  For each runner in config:         │
        │  - Check if running (PID alive)     │
        │  - If not running: spawn it         │
        │  - Wait for completion              │
        │  - Log status                       │
        └────────────┬───────────────────────┘
                     │
    ┌────────────────┴─────────────────┐
    │                                  │
┌───▼──────────────┐     ┌────────────▼────┐
│ self-runner-ctl  │     │ Runner Process  │
│ register         │     │ (foreground or  │
│ (spawns runner)  │     │  background)    │
└──────────────────┘     └─────────────────┘
```

## Configuration

### Basic Structure

Create `/etc/runnerctl/runnerctl.yaml`:

```yaml
defaults:
  # Applied to all runners unless overridden
  labels: self-hosted,linux,x64
  version: latest
  workdir: _work
  ephemeral: true
  daemonize: true
  base_dir: /opt/runnerctl/runners

runners:
  # Single persistent runner
  - name: build-1
    scope: repo
    repo: owner/repo
    ephemeral: false

  # Pool of ephemeral runners
  - name_prefix: ci-pool
    scope: repo
    repo: owner/repo
    count: 3
    ephemeral: true

  # Organization-scoped runners
  - name_prefix: org-runners
    scope: org
    org: myorg
    count: 5
```

### Configuration Reference

#### Defaults Section

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `labels` | string | `self-hosted,linux,x64` | Comma-separated runner labels |
| `version` | string | `latest` | Actions runner version |
| `workdir` | string | `_work` | Working directory name |
| `ephemeral` | bool | `true` | Remove after each job |
| `daemonize` | bool | `true` | Run as background process |
| `base_dir` | string | `/opt/runnerctl/runners` | Base installation directory |

#### Runner Item

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `name` | string | If no `name_prefix` | Single runner name |
| `name_prefix` | string | If no `name` | Prefix for pool names |
| `count` | int | No (default: 1) | Number of runners in pool |
| `scope` | string | Yes | `repo` or `org` |
| `repo` | string | For repo scope | `owner/repo` |
| `org` | string | For org scope | Organization name |
| `labels` | string | No | Override default labels |
| `version` | string | No | Override default version |
| `workdir` | string | No | Override default workdir |
| `ephemeral` | bool | No | Override default ephemeral |
| `daemonize` | bool | No | Override default daemonize |

### Example Configurations

#### Example 1: Single Build Runner

```yaml
defaults:
  labels: self-hosted,linux,x64
  ephemeral: false
  daemonize: true

runners:
  - name: build-runner
    scope: repo
    repo: myorg/product
    labels: self-hosted,linux,x64,build
    ephemeral: false
```

#### Example 2: Ephemeral Pool for CI

```yaml
defaults:
  ephemeral: true
  daemonize: true

runners:
  - name_prefix: ci
    scope: repo
    repo: myorg/product
    count: 5
    labels: self-hosted,linux,x64,ci
```

#### Example 3: Multi-Repo Setup

```yaml
defaults:
  labels: self-hosted,linux,x64
  daemonize: true

runners:
  # Persistent runners for critical repos
  - name: prod-build-1
    scope: repo
    repo: myorg/production
    ephemeral: false
    labels: self-hosted,linux,x64,production

  # Ephemeral pool for dev repo
  - name_prefix: dev-ci
    scope: repo
    repo: myorg/development
    count: 3
    ephemeral: true
    labels: self-hosted,linux,x64,development

  # Org-wide shared runners
  - name_prefix: org-shared
    scope: org
    org: myorg
    count: 10
    ephemeral: true
    labels: self-hosted,linux,x64,shared
```

#### Example 4: Version-Specific Runners

```yaml
runners:
  - name: stable-runner
    scope: repo
    repo: myorg/product
    version: "2.314.0"  # Pinned version
    ephemeral: false

  - name_prefix: latest-pool
    scope: repo
    repo: myorg/product
    count: 3
    version: latest
    ephemeral: true
```

## Installation

### 1. Install Package

```bash
sudo pip3 install git+https://github.com/pv-udpv/iptvportal-client.git#subdirectory=agents/runnerctl
```

### 2. Create Configuration

```bash
# Copy example config
sudo install -m 0640 -o root -g runnerctl \
  /path/to/contrib/runnerctl.yaml.example \
  /etc/runnerctl/runnerctl.yaml

# Edit configuration
sudo nano /etc/runnerctl/runnerctl.yaml
```

### 3. Configure Environment

```bash
# Copy environment file
sudo install -m 0640 -o root -g runnerctl \
  /path/to/contrib/systemd/runnerctl.env.example \
  /etc/runnerctl/runnerctl.env

# Set GitHub App credentials
sudo nano /etc/runnerctl/runnerctl.env
```

### 4. Install Service

```bash
# Install systemd unit
sudo install -m 0644 -o root -g root \
  /path/to/contrib/systemd/runnerctl-manager.service \
  /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start
sudo systemctl enable runnerctl-manager
sudo systemctl start runnerctl-manager
```

### 5. Verify

```bash
# Check status
sudo systemctl status runnerctl-manager

# View logs
sudo journalctl -u runnerctl-manager -f

# Validate config
runnerctl-manager print-config --config /etc/runnerctl/runnerctl.yaml
```

## Environment Variable Overrides

Override defaults via environment variables (Pydantic Settings v2):

### Prefix: `GITHUB_WFA_RUNNER_DEFAULTS__`

```bash
# Set custom labels
export GITHUB_WFA_RUNNER_DEFAULTS__LABELS=self-hosted,linux,x64,custom

# Set runner version
export GITHUB_WFA_RUNNER_DEFAULTS__VERSION=2.314.0

# Change installation directory
export GITHUB_WFA_RUNNER_DEFAULTS__BASE_DIR=/data/runners

# Make all runners persistent by default
export GITHUB_WFA_RUNNER_DEFAULTS__EPHEMERAL=false
```

### Short Alias: `GHWFAX__DEFAULTS__`

```bash
# Shorter alias (auto-mapped to GITHUB_WFA_RUNNER_DEFAULTS__)
export GHWFAX__DEFAULTS__LABELS=self-hosted,linux,x64,custom
```

### Setting in Service File

Edit `/etc/systemd/system/runnerctl-manager.service`:

```ini
[Service]
Environment="GITHUB_WFA_RUNNER_DEFAULTS__LABELS=self-hosted,linux,x64,custom"
Environment="GITHUB_WFA_RUNNER_DEFAULTS__BASE_DIR=/data/runners"
EnvironmentFile=-/etc/runnerctl/runnerctl.env

ExecStart=/usr/bin/python3 -m runnerctl.manager --config /etc/runnerctl/runnerctl.yaml
```

Then restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart runnerctl-manager
```

## Operations

### View Status

```bash
# Service status
sudo systemctl status runnerctl-manager

# Real-time logs
sudo journalctl -u runnerctl-manager -f

# Show effective configuration
runnerctl-manager print-config

# List runner directories
ls -la /opt/runnerctl/runners/
```

### Monitor Runners

```bash
# Check individual runner status
cat /opt/runnerctl/runners/runner-1/runner.pid

# View runner logs
tail -f /opt/runnerctl/runners/runner-1/runner.log

# Watch runner process
watch -n 2 "ps aux | grep runner"
```

### Validate Configuration

```bash
# Check syntax
runnerctl-manager print-config --config /etc/runnerctl/runnerctl.yaml

# Run single pass (no loop)
runnerctl-manager once --config /etc/runnerctl/runnerctl.yaml
```

### Restart Runners

```bash
# Restart all runners
sudo systemctl restart runnerctl-manager

# Restart single runner
kill -9 $(cat /opt/runnerctl/runners/runner-1/runner.pid) || true
# Manager will respawn it within 10 seconds
```

### Scale Runner Pool

```bash
# Edit configuration
sudo nano /etc/runnerctl/runnerctl.yaml

# Update count in runner item
# runners:
#   - name_prefix: ci-pool
#     count: 10  # Increase from 5 to 10

# Reload (no service restart needed)
# Manager will detect new runners on next loop (10s)
```

### Remove Runner

```bash
# Option 1: Remove from YAML and manager will deregister
sudo nano /etc/runnerctl/runnerctl.yaml
# Remove the runner item, save

# Option 2: Manual cleanup
rm -rf /opt/runnerctl/runners/runner-name

# Manager will attempt to respawn, or you can:
sudo systemctl restart runnerctl-manager
```

## Troubleshooting

### Runner Not Registering

```bash
# Check manager logs
sudo journalctl -u runnerctl-manager -n 50 -f

# Verify runner directory
ls -la /opt/runnerctl/runners/runner-name/

# Check runner log
cat /opt/runnerctl/runners/runner-name/runner.log | tail -20

# Verify GitHub App permissions
# See: GitHub App Setup guide
```

### High CPU/Memory Usage

```bash
# Monitor resource usage
top -p $(pgrep -f "run.sh")

# Check if runners are stuck
ps aux | grep "run.sh"

# Kill stuck runner (will be respawned)
kill -9 <PID>
```

### Configuration Not Applied

```bash
# Verify config syntax
runnerctl-manager print-config --config /etc/runnerctl/runnerctl.yaml

# Check if service picked up changes
sudo systemctl restart runnerctl-manager

# Verify environment variables
cat /etc/runnerctl/runnerctl.env
```

### Runners Not Going Online

```bash
# Check GitHub connection
curl -I https://api.github.com

# Verify DNS resolution
nslookup github.com api.github.com

# Check firewall
sudo ufw status
sudo iptables -L | grep -i github
```

## Performance Tuning

### Adjust Loop Interval

Default is 10 seconds. To change:

```bash
# In service file
ExecStart=/usr/bin/python3 -m runnerctl.manager --config /etc/runnerctl/runnerctl.yaml --interval 30

# Then:
sudo systemctl daemon-reload
sudo systemctl restart runnerctl-manager
```

### Resource Limits

Set per-runner limits in systemd service:

```ini
[Service]
MemoryLimit=2G
CPUQuota=80%
```

### Disk Space

Monitor runner workspace usage:

```bash
# Check disk space
df -h /opt/runnerctl

# Monitor per-runner
du -sh /opt/runnerctl/runners/*
```

## See Also

- [Installation Guide](installation.md)
- [GitHub App Setup](github-app-setup.md)
- [API Mode](api-mode.md)
- [Troubleshooting](troubleshooting.md)
