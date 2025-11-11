# RunnerCTL Installation Guide

This guide walks through installing RunnerCTL on an on-premise Linux host for managing self-hosted GitHub Actions runners.

## Prerequisites

### System Requirements

- **OS**: Linux (Ubuntu 20.04 LTS or later recommended)
- **Python**: 3.9 or later
- **Disk Space**: Minimum 5GB for runner installations
- **Network**: Outbound HTTPS to `api.github.com` and `github.com`

### System Packages

Install required dependencies:

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv curl openssl tar gzip jq
```

### GitHub App

You need a GitHub App with appropriate permissions. See [GitHub App Setup](github-app-setup.md) for detailed instructions.

## Installation Steps

### 1. Create Service User and Directories

```bash
# Create unprivileged system user
sudo useradd --system --home /opt/runnerctl --shell /usr/sbin/nologin runnerctl || true

# Create directories
sudo mkdir -p /opt/runnerctl /etc/runnerctl
sudo chown -R runnerctl:runnerctl /opt/runnerctl
sudo chmod 755 /opt/runnerctl
```

### 2. Install RunnerCTL Package

#### From GitHub (Recommended)

```bash
sudo pip3 install git+https://github.com/pv-udpv/iptvportal-client.git#subdirectory=agents/runnerctl
```

#### From Local Clone

```bash
cd agents/runnerctl
sudo pip3 install -e .
```

#### Development Installation

```bash
cd agents/runnerctl
sudo pip3 install -e ".[dev]"
```

### 3. Verify Installation

```bash
# Check CLI availability
runnerctl --help
runnerctl-manager --help
runnerctl-server --help

# Check Python package
python3 -c "import runnerctl; print(runnerctl.__version__)"
```

### 4. Configure Environment

Copy and edit the environment file:

```bash
sudo install -m 0640 -o root -g runnerctl \
  /path/to/contrib/systemd/runnerctl.env.example \
  /etc/runnerctl/runnerctl.env

sudo nano /etc/runnerctl/runnerctl.env
```

**Required Variables:**

```bash
# GitHub App credentials (see GitHub App Setup guide)
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY_B64=LS0tLS1CRUdJTi... # base64-encoded PEM

# API token for HTTP API mode (generate random string)
GITHUB_WFA_RUNNER_SERVER__API_TOKEN=your-very-long-random-secret-token

# Optional: Override runner defaults
GITHUB_WFA_RUNNER_DEFAULTS__BASE_DIR=/opt/runnerctl/runners
GITHUB_WFA_RUNNER_DEFAULTS__LABELS=self-hosted,linux,x64
GITHUB_WFA_RUNNER_DEFAULTS__EPHEMERAL=true
GITHUB_WFA_RUNNER_DEFAULTS__DAEMONIZE=true
```

### 5. Configure Managed Mode (Optional)

For managed mode, create `/etc/runnerctl/runnerctl.yaml`:

```bash
sudo install -m 0640 -o root -g runnerctl \
  /path/to/contrib/runnerctl.yaml.example \
  /etc/runnerctl/runnerctl.yaml

sudo nano /etc/runnerctl/runnerctl.yaml
```

Example configuration:

```yaml
defaults:
  labels: self-hosted,linux,x64
  version: latest
  workdir: _work
  ephemeral: true
  daemonize: true
  base_dir: /opt/runnerctl/runners

runners:
  - name: build-1
    scope: repo
    repo: owner/repo
    ephemeral: false
    labels: self-hosted,linux,x64,build

  - name_prefix: ci-pool
    scope: repo
    repo: owner/repo
    count: 3
    ephemeral: true
    labels: self-hosted,linux,x64,ci
```

## Running Modes

### Managed Mode (Recommended for Production)

Supervisor service that maintains runner pool from YAML config:

```bash
# Start immediately
sudo systemctl start runnerctl-manager

# Enable on boot
sudo systemctl enable runnerctl-manager

# View logs
sudo journalctl -u runnerctl-manager -f

# Check config
runnerctl-manager print-config --config /etc/runnerctl/runnerctl.yaml
```

See [Managed Mode Guide](managed-mode.md) for details.

### API Mode

HTTP API server for dynamic runner provisioning:

```bash
# Start immediately
sudo systemctl start runnerctl-server

# Enable on boot
sudo systemctl enable runnerctl-server

# View logs
sudo journalctl -u runnerctl-server -f

# Test API
curl -H "Authorization: Bearer $API_TOKEN" http://127.0.0.1:8080/health
```

See [API Mode Guide](api-mode.md) for details.

### Manual Mode

Run commands directly:

```bash
# Register a single runner
export GITHUB_APP_ID=123456
export GITHUB_APP_PRIVATE_KEY_B64=...
export RUNNER_NAME=manual-1
export REPO=owner/repo
export EPHEMERAL=false
export DAEMONIZE=true
export RUNNER_HOME=/opt/runnerctl/runners/manual-1

runnerctl-manager once --config /etc/runnerctl/runnerctl.yaml
```

## Systemd Service Files

### Managed Mode Service

Install the manager service:

```bash
sudo install -m 0644 -o root -g root \
  /path/to/contrib/systemd/runnerctl-manager.service \
  /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable runnerctl-manager
```

### Verify Services

```bash
# List all runnerctl services
systemctl list-units | grep runnerctl

# Check status
systemctl status runnerctl-manager
systemctl status runnerctl-server

# View real-time logs
journalctl -u runnerctl-manager -u runnerctl-server -f
```

## Post-Installation Checks

### 1. Verify Permissions

```bash
# Check directory ownership
ls -la /opt/runnerctl
ls -la /etc/runnerctl

# Check file permissions
stat /etc/runnerctl/runnerctl.env
```

### 2. Test GitHub App Access

```bash
# Export GitHub App credentials
source /etc/runnerctl/runnerctl.env

# Test runner registration (dry-run)
export RUNNER_NAME=test-1
export REPO=owner/repo
export EPHEMERAL=true
export RUNNER_HOME=/tmp/test-runner

# This should fail gracefully if credentials are wrong
runnerctl-manager once
```

### 3. Check Network Connectivity

```bash
# Test GitHub API access
curl -I https://api.github.com

# Test DNS resolution
nslookup github.com
nslookup api.github.com
```

### 4. Monitor First Runner Registration

```bash
# Watch service logs
sudo journalctl -u runnerctl-manager -f

# In another terminal, check runner directory
watch -n 2 "ls -la /opt/runnerctl/runners/"

# Monitor runner process
watch -n 2 "ps aux | grep runner"
```

## Troubleshooting Installation

### Import Errors

```bash
# Error: ModuleNotFoundError: No module named 'typer'
# Solution: Reinstall with dependencies
pip install --force-reinstall git+https://github.com/pv-udpv/iptvportal-client.git#subdirectory=agents/runnerctl
```

### Permission Denied

```bash
# Error: Permission denied to create /opt/runnerctl/runners/runner-1
# Solution: Fix directory ownership
sudo chown -R runnerctl:runnerctl /opt/runnerctl
sudo chmod 755 /opt/runnerctl
```

### Shell Script Not Found

```bash
# Error: self-runner-ctl.sh: No such file or directory
# Solution: Verify package installation includes shell scripts
pip show -f runnerctl | grep shell
```

### GitHub API Errors

```bash
# Error: Failed to get installation id
# Solution: Check GitHub App credentials and permissions
# See: GitHub App Setup guide
```

## Next Steps

1. **[GitHub App Setup](github-app-setup.md)** - Create and configure GitHub App
2. **[Managed Mode](managed-mode.md)** - Configure and run managed mode
3. **[API Mode](api-mode.md)** - Setup HTTP API server
4. **[Troubleshooting](troubleshooting.md)** - Common issues and solutions

## Uninstallation

To completely remove RunnerCTL:

```bash
# Stop services
sudo systemctl stop runnerctl-manager runnerctl-server
sudo systemctl disable runnerctl-manager runnerctl-server

# Remove systemd files
sudo rm -f /etc/systemd/system/runnerctl*.service
sudo systemctl daemon-reload

# Remove package
sudo pip3 uninstall -y runnerctl

# Remove configuration
sudo rm -rf /etc/runnerctl

# Remove user and home directory
sudo userdel -r runnerctl || true
