# Troubleshooting Guide

Common issues and solutions for RunnerCTL installation, configuration, and operation.

## Installation Issues

### ModuleNotFoundError: No module named 'typer'

**Symptom**: Import error when running RunnerCTL  
**Cause**: Dependencies not installed

**Solution**:
```bash
# Reinstall with all dependencies
sudo pip3 install --force-reinstall \
  git+https://github.com/pv-udpv/iptvportal-client.git#subdirectory=agents/runnerctl

# Or from local:
cd agents/runnerctl
sudo pip3 install -e .

# Verify installation
python3 -c "import runnerctl; print('OK')"
```

### Permission denied: /opt/runnerctl

**Symptom**: Cannot create runner directories  
**Cause**: Incorrect directory ownership

**Solution**:
```bash
# Fix ownership
sudo chown -R runnerctl:runnerctl /opt/runnerctl
sudo chmod 755 /opt/runnerctl

# Verify
ls -la /opt/runnerctl
# Should show: runnerctl runnerctl

# Reset runner directories if corrupted
sudo rm -rf /opt/runnerctl/runners/*
sudo systemctl restart runnerctl-manager
```

### self-runner-ctl.sh: No such file or directory

**Symptom**: Shell script not found when running manager  
**Cause**: Package not installed correctly with data files

**Solution**:
```bash
# Verify package installation
pip show -f runnerctl | head -20

# Should include: .../shell/self-runner-ctl.sh

# Reinstall with explicit data files
sudo pip3 install --force-reinstall --no-cache-dir \
  git+https://github.com/pv-udpv/iptvportal-client.git#subdirectory=agents/runnerctl
```

### Configuration file not found

**Symptom**: `/etc/runnerctl/runnerctl.yaml` not found  
**Cause**: File not created

**Solution**:
```bash
# Create directory
sudo mkdir -p /etc/runnerctl
sudo chown root:runnerctl /etc/runnerctl
sudo chmod 755 /etc/runnerctl

# Copy example config
sudo cp contrib/runnerctl.yaml.example /etc/runnerctl/runnerctl.yaml
sudo chmod 640 /etc/runnerctl/runnerctl.yaml
sudo chown root:runnerctl /etc/runnerctl/runnerctl.yaml

# Verify
stat /etc/runnerctl/runnerctl.yaml
```

## Configuration Issues

### Invalid YAML syntax

**Symptom**: `yaml.scanner.ScannerError` or `yaml.parser.ParserError`  
**Cause**: YAML syntax error

**Solution**:
```bash
# Validate YAML syntax
runnerctl-manager print-config --config /etc/runnerctl/runnerctl.yaml

# Common issues:
# - Incorrect indentation (must use spaces, not tabs)
# - Missing colons after keys
# - Unquoted special characters

# Example valid YAML:
cat > /tmp/test.yaml << 'EOF'
defaults:
  labels: "self-hosted,linux,x64"
  
runners:
  - name: test-runner
    scope: repo
    repo: owner/repo
EOF

# Test parsing
python3 << 'EOF'
import yaml
with open('/tmp/test.yaml') as f:
    data = yaml.safe_load(f)
    print(data)
EOF
```

### Missing required fields

**Symptom**: `ValueError: Each runner requires either 'name' or 'name_prefix'`  
**Cause**: Runner item missing name configuration

**Solution**:
```yaml
# Either use 'name' for single runner
runners:
  - name: runner-1
    scope: repo
    repo: owner/repo

# Or use 'name_prefix' with 'count' for pool
runners:
  - name_prefix: runner
    scope: repo
    repo: owner/repo
    count: 3
```

### Incorrect scope

**Symptom**: `ValueError: Invalid scope: repo_org`  
**Cause**: Typo in scope value

**Solution**:
```yaml
# Valid values are exactly:
scope: repo    # for repository scope
scope: org     # for organization scope

# NOT:
scope: repo_org  # Invalid
scope: organization  # Invalid
```

## GitHub App Issues

### Failed to get installation id

**Symptom**: `Failed to get installation id` error  
**Cause**: App not installed or credentials invalid

**Solution**:
```bash
# 1. Verify GitHub App ID and private key
grep GITHUB_APP /etc/runnerctl/runnerctl.env

# 2. Check app installation
# Go to: https://github.com/settings/apps/YOUR_APP_NAME/installations
# Verify the app is installed on the target repo/org

# 3. Reinstall app:
# - Go to app settings
# - Click "Install App"
# - Select repositories/organizations
# - Confirm installation

# 4. Test with curl
export GITHUB_APP_ID=123456
export GITHUB_APP_PRIVATE_KEY_B64=...
export REPO=owner/repo

# This should return the installation ID:
# curl -H "Authorization: Bearer <JWT>" \
#   https://api.github.com/repos/$REPO/installation | jq .id
```

### Invalid JWT

**Symptom**: `Unauthorized` or `401` responses from GitHub API  
**Cause**: Bad private key or App ID

**Solution**:
```bash
# Verify values match GitHub App page
# https://github.com/settings/apps/YOUR_APP_NAME

# Check App ID
grep GITHUB_APP_ID /etc/runnerctl/runnerctl.env

# Verify private key is base64-encoded correctly
grep GITHUB_APP_PRIVATE_KEY_B64 /etc/runnerctl/runnerctl.env | \
  cut -d= -f2 | base64 -d | head -1
# Should output: -----BEGIN PRIVATE KEY-----

# If using file-based key:
grep GITHUB_APP_PRIVATE_KEY_FILE /etc/runnerctl/runnerctl.env
head -1 /etc/runnerctl/private-key.pem
# Should output: -----BEGIN PRIVATE KEY-----
```

### Insufficient permissions

**Symptom**: `403 Forbidden` when managing runners  
**Cause**: GitHub App lacks required permissions

**Solution**:
```bash
# 1. Go to GitHub App settings:
# https://github.com/settings/apps/YOUR_APP_NAME/permissions

# 2. For repo scope, add permissions:
# - Actions: Read & write
# - Administration: Read & write

# 3. For org scope, add permissions:
# - Self-hosted runners: Read & write
# - Administration: Read & write

# 4. Click "Save changes"

# 5. Reinstall on repositories/organizations:
# https://github.com/settings/apps/YOUR_APP_NAME/installations

# 6. Test again:
runnerctl-manager once --config /etc/runnerctl/runnerctl.yaml
```

## Environment Variable Issues

### GITHUB_APP_PRIVATE_KEY_B64 not recognized

**Symptom**: `No suitable authentication available` error  
**Cause**: Environment variable not loaded

**Solution**:
```bash
# Verify env file location
stat /etc/runnerctl/runnerctl.env

# Check systemd service reads it:
grep EnvironmentFile /etc/systemd/system/runnerctl-manager.service

# Manually source and test:
source /etc/runnerctl/runnerctl.env
echo $GITHUB_APP_ID
echo $GITHUB_APP_PRIVATE_KEY_B64 | head -c 50

# If not set, update service:
sudo systemctl edit runnerctl-manager
# Add: EnvironmentFile=/etc/runnerctl/runnerctl.env

sudo systemctl daemon-reload
sudo systemctl restart runnerctl-manager
```

### Defaults environment overrides not applied

**Symptom**: Default labels/version not changed despite env vars  
**Cause**: Environment variables not set correctly

**Solution**:
```bash
# Check both supported prefixes:
echo "Full prefix:"
grep "GITHUB_WFA_RUNNER_DEFAULTS__" /etc/runnerctl/runnerctl.env
echo "Short prefix:"
grep "GHWFAX__DEFAULTS__" /etc/runnerctl/runnerctl.env

# Verify they're set:
env | grep GITHUB_WFA_RUNNER_DEFAULTS

# Or set directly for testing:
export GITHUB_WFA_RUNNER_DEFAULTS__LABELS=custom,labels,here
runnerctl-manager once --config /etc/runnerctl/runnerctl.yaml

# Check effective config:
runnerctl-manager print-config | grep labels
```

## Managed Mode Issues

### Runner not registering

**Symptom**: Runner directory exists but runner.pid is empty  
**Cause**: Registration failed, check logs

**Solution**:
```bash
# 1. Check manager logs
sudo journalctl -u runnerctl-manager -n 50 -f

# 2. Check runner registration log
tail -f /opt/runnerctl/runners/runner-name/runner.log

# 3. Verify runner directory was created
ls -la /opt/runnerctl/runners/

# 4. Check if shell script exists
ls -la /opt/runnerctl/runners/runner-name/

# 5. Manual test with verbose output
export GITHUB_APP_ID=123456
export GITHUB_APP_PRIVATE_KEY_B64=...
export RUNNER_NAME=test-1
export REPO=owner/repo
export RUNNER_HOME=/tmp/test-runner
export EPHEMERAL=true
export DAEMONIZE=false

bash -x scripts/self-runner-ctl.sh register
```

### Runners go offline after job

**Symptom**: Runner process exits after completing a job  
**Cause**: Ephemeral runner doing its job (expected)

**Solution**:
```bash
# This is normal for ephemeral runners:
# 1. Runner registers
# 2. Job executes
# 3. Runner exits (ephemeral behavior)
# 4. Manager respawns within 10 seconds

# To prevent this, make runner persistent:
nano /etc/runnerctl/runnerctl.yaml
# Set: ephemeral: false

sudo systemctl restart runnerctl-manager
```

### High CPU/Memory usage

**Symptom**: CPU or memory usage spikes  
**Cause**: Runner process consuming resources

**Solution**:
```bash
# 1. Monitor resource usage
top -p $(pgrep -f "run.sh")

# 2. Identify resource-heavy runner
ps aux | grep "run.sh" | sort -k3,3 -rn

# 3. Reduce runner count
nano /etc/runnerctl/runnerctl.yaml
# Decrease 'count' for runner pools

# 4. Or limit resources in systemd:
sudo systemctl edit runnerctl-manager
# Add:
# [Service]
# MemoryLimit=2G
# CPUQuota=80%

sudo systemctl daemon-reload
sudo systemctl restart runnerctl-manager

# 5. Check disk space (runners use workspace)
df -h /opt/runnerctl

# Clean old runner directories:
sudo rm -rf /opt/runnerctl/runners/*/work/
```

### Config changes not applied

**Symptom**: YAML changes don't take effect  
**Cause**: Manager not reloading config

**Solution**:
```bash
# The manager only loads config at startup
# Changes are NOT picked up without restart

# Option 1: Restart service (downtime)
sudo systemctl restart runnerctl-manager

# Option 2: Single pass mode (no restart needed)
runnerctl-manager once --config /etc/runnerctl/runnerctl.yaml

# Option 3: Verify changes took effect
runnerctl-manager print-config --config /etc/runnerctl/runnerctl.yaml
```

## API Mode Issues

### API server won't start

**Symptom**: `systemctl start runnerctl-server` fails  
**Cause**: Port already in use or permission issue

**Solution**:
```bash
# Check what's using the port
sudo lsof -i :8080
# or
sudo netstat -tlnp | grep 8080

# Kill conflicting process
sudo kill -9 <PID>

# Check permissions
stat /etc/runnerctl/runnerctl.env
# Should be readable by runnerctl user

# Start service
sudo systemctl start runnerctl-server
sudo systemctl status runnerctl-server
```

### Authentication failed on API calls

**Symptom**: `403 Forbidden` on API requests  
**Cause**: Invalid or missing API token

**Solution**:
```bash
# 1. Get the API token
API_TOKEN=$(grep API_TOKEN /etc/runnerctl/runnerctl.env | cut -d= -f2)

# 2. Test with correct format
curl -H "Authorization: Bearer $API_TOKEN" \
  http://127.0.0.1:8080/health

# Common mistakes:
# - Missing "Bearer " prefix
# - Token typo
# - Old token after rotation

# 3. Verify token in environment
echo $API_TOKEN

# 4. If still fails, rotate token:
sudo nano /etc/runnerctl/runnerctl.env
# Generate new token: openssl rand -hex 32
# Update GITHUB_WFA_RUNNER_SERVER__API_TOKEN
# Save and restart:
sudo systemctl restart runnerctl-server
```

### Cloudflare Tunnel connection issues

**Symptom**: `curl: (60) SSL certificate problem` or timeout  
**Cause**: Tunnel not properly configured or running

**Solution**:
```bash
# 1. Verify tunnel is running
sudo systemctl status cloudflared

# 2. Check tunnel status
cloudflared tunnel list
# Should show: NAME    UUID    NAME    CNAME    ACCOUNT    ACTIVE CONN STATUS

# 3. Validate ingress configuration
cloudflared tunnel ingress validate

# 4. Check tunnel logs
sudo journalctl -u cloudflared -f

# 5. Test local connection first
curl -H "Authorization: Bearer $API_TOKEN" \
  http://127.0.0.1:8080/health

# 6. Then test via tunnel
curl -H "Authorization: Bearer $API_TOKEN" \
  https://runnerctl.example.com/health

# 7. If still broken, recreate tunnel
cloudflared tunnel delete runnerctl
cloudflared tunnel create runnerctl
# Reconfigure ingress in /etc/cloudflared/config.yml
```

## Network Issues

### Cannot reach GitHub API

**Symptom**: `curl: (7) Failed to connect to api.github.com`  
**Cause**: Network connectivity problem

**Solution**:
```bash
# 1. Test basic connectivity
ping github.com
curl -I https://api.github.com

# 2. Check DNS resolution
nslookup api.github.com
dig api.github.com

# 3. Check firewall rules
sudo ufw status
sudo iptables -L -n | grep HTTPS

# 4. Check proxy settings
env | grep -i proxy
# If using proxy, configure:
export https_proxy=http://proxy.example.com:8080

# 5. Test from runner directory
cd /opt/runnerctl/runners/runner-name
curl -I https://api.github.com
```

### Port not accessible from outside

**Symptom**: Cannot reach API from remote machine  
**Cause**: Server only binding to localhost

**Solution**:
```bash
# Default binding is localhost (secure):
GITHUB_WFA_RUNNER_SERVER__BIND=127.0.0.1:8080

# To make accessible:
# 1. Use Cloudflare Tunnel (recommended)
# See: docs/api-mode.md - Securing the API

# 2. Or change binding (less secure):
sudo nano /etc/runnerctl/runnerctl.env
# Change to: GITHUB_WFA_RUNNER_SERVER__BIND=0.0.0.0:8080

# 3. Configure firewall
sudo ufw allow from 203.0.113.0/24 to any port 8080

# 4. Restart service
sudo systemctl restart runnerctl-server
```

## Logs and Debugging

### View comprehensive logs

```bash
# Manager service logs
sudo journalctl -u runnerctl-manager -f

# API server logs
sudo journalctl -u runnerctl-server -f

# Both services
sudo journalctl -u runnerctl-manager -u runnerctl-server -f

# All runner logs
tail -f /opt/runnerctl/runners/*/runner.log

# Historical logs (last 100 lines)
journalctl -u runnerctl-manager -n 100
```

### Enable debug logging

```bash
# Increase verbosity with environment variables
export PYTHONUNBUFFERED=1

# Run manager in foreground with output
runnerctl-manager run --config /etc/runnerctl/runnerctl.yaml

# Or edit service for debug:
sudo systemctl edit runnerctl-manager
# Change: ExecStart=/usr/bin/python3 -u -m runnerctl.manager ...
```

### Collect diagnostic information

```bash
# Create diagnostic bundle for support
(
  echo "=== Environment ==="
  echo "OS: $(uname -a)"
  echo "Python: $(python3 --version)"
  echo "Disk: $(df -h /opt/runnerctl)"
  
  echo -e "\n=== Service Status ==="
  systemctl status runnerctl-manager 2>&1
  
  echo -e "\n=== Configuration ==="
  runnerctl-manager print-config 2>&1
  
  echo -e "\n=== Recent Logs ==="
  journalctl -u runnerctl-manager -n 50 2>&1
  
  echo -e "\n=== Runner Directories ==="
  ls -la /opt/runnerctl/runners/ 2>&1
  
  echo -e "\n=== Network ==="
  netstat -tlnp | grep python 2>&1
  
  echo -e "\n=== Connectivity Test ==="
  curl -I https://api.github.com 2>&1
) | tee /tmp/runnerctl-diag.txt

# Share /tmp/runnerctl-diag.txt with support
```

## Getting Help

If you still need help:

1. **Check documentation**: Review [Installation](installation.md), [Managed Mode](managed-mode.md), or [API Mode](api-mode.md)
2. **Review logs**: Check systemd logs and runner logs for error messages
3. **Test connectivity**: Verify network access to GitHub
4. **Verify credentials**: Double-check GitHub App ID and private key
5. **Create issue**: Report to [GitHub Issues](https://github.com/pv-udpv/iptvportal-client/issues)

Include diagnostic bundle and relevant logs when reporting issues.
