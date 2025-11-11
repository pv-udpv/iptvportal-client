# API Mode Guide

API Mode provides an HTTP REST API server for dynamic runner provisioning. It allows programmatic creation and removal of runners on-demand, ideal for ephemeral workloads and integration with CI/CD platforms.

## Overview

API Mode is ideal for:
- Dynamic runner provisioning from workflows
- Integration with external automation systems
- Ephemeral runners with per-job lifecycles
- Scaling runner pools based on demand
- Multi-tenant runner management

The API server exposes RESTful endpoints secured with bearer token authentication and integrates with your GitHub App for runner registration.

## Architecture

```
┌──────────────────────────────────────────────────┐
│  GitHub Actions Workflow / External System      │
│  POST /api/v1/runners                           │
│  DELETE /api/v1/runners/{name}                  │
└────────────────────┬─────────────────────────────┘
                     │
         ┌───────────▼────────────┐
         │  Cloudflare Tunnel     │
         │  (Optional - Secure)   │
         └───────────┬────────────┘
                     │
    ┌────────────────▼─────────────┐
    │  runnerctl-server            │
    │  (FastAPI + Uvicorn)         │
    │  Listen: 127.0.0.1:8080     │
    └────────────────┬─────────────┘
                     │
    ┌────────────────▼──────────────────────┐
    │  Bearer Token Authentication          │
    │  (GITHUB_WFA_RUNNER_SERVER__API_TOKEN)│
    └────────────────┬──────────────────────┘
                     │
    ┌────────────────▼──────────────────────┐
    │  self-runner-ctl.sh                   │
    │  (Register / Remove / Status)         │
    └────────────────┬──────────────────────┘
                     │
         ┌───────────▼────────────┐
         │ GitHub API             │
         │ (Registration Token)   │
         └────────────────────────┘
```

## Installation

### 1. Install Package

```bash
sudo pip3 install git+https://github.com/pv-udpv/iptvportal-client.git#subdirectory=agents/runnerctl
```

### 2. Configure Environment

```bash
# Create/edit environment file
sudo nano /etc/runnerctl/runnerctl.env
```

**Required Variables:**

```bash
# GitHub App credentials (see GitHub App Setup)
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY_B64=LS0tLS1CRUdJTi...

# API token (generate a secure random string)
GITHUB_WFA_RUNNER_SERVER__API_TOKEN=your-very-long-random-secret-token-here

# Server binding (optional)
GITHUB_WFA_RUNNER_SERVER__BIND=127.0.0.1:8080
```

Generate a secure API token:

```bash
# Option 1: Using openssl
openssl rand -hex 32

# Option 2: Using Python
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Option 3: Using dd
dd if=/dev/urandom bs=1 count=32 2>/dev/null | xxd -p
```

### 3. Set File Permissions

```bash
# Secure the environment file
sudo chmod 0640 /etc/runnerctl/runnerctl.env
sudo chown root:runnerctl /etc/runnerctl/runnerctl.env

# Verify permissions
stat /etc/runnerctl/runnerctl.env
```

### 4. Install Systemd Service

```bash
# Copy service file (if available)
sudo install -m 0644 -o root -g root \
  /path/to/contrib/systemd/runnerctl.service \
  /etc/systemd/system/

# Or create manually:
sudo tee /etc/systemd/system/runnerctl-server.service > /dev/null << 'EOF'
[Unit]
Description=RunnerCTL API Server (dynamic runner provisioning)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=runnerctl
Group=runnerctl
WorkingDirectory=/opt/runnerctl
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=-/etc/runnerctl/runnerctl.env
ExecStart=/usr/bin/python3 -m runnerctl.server
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

# Reload and start
sudo systemctl daemon-reload
sudo systemctl enable runnerctl-server
sudo systemctl start runnerctl-server
```

### 5. Verify Service

```bash
# Check status
sudo systemctl status runnerctl-server

# View logs
sudo journalctl -u runnerctl-server -f

# Test API
curl -H "Authorization: Bearer $API_TOKEN" \
  http://127.0.0.1:8080/health
```

## API Reference

### Health Check

**Endpoint**: `GET /health`  
**Authentication**: None  
**Description**: Service health check

**Response**:
```json
{
  "status": "ok"
}
```

**Example**:
```bash
curl http://127.0.0.1:8080/health
```

### Create Runner

**Endpoint**: `POST /api/v1/runners`  
**Authentication**: Bearer token required  
**Description**: Create and register a new runner

**Request**:
```json
{
  "repo": "owner/repo",
  "name": "runner-1",
  "labels": "self-hosted,linux,x64",
  "ephemeral": true,
  "daemonize": true
}
```

**Response**:
```json
{
  "status": "started",
  "name": "runner-1"
}
```

**Fields**:
- `repo` (string, required): Repository in format `owner/repo`
- `name` (string, required): Runner name
- `labels` (string, optional): Comma-separated labels (default: `self-hosted,linux,x64`)
- `ephemeral` (bool, optional): Remove after each job (default: `true`)
- `daemonize` (bool, optional): Run as background process (default: `true`)

**Example**:
```bash
API_TOKEN="your-api-token"
curl -X POST \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "myorg/product",
    "name": "ci-runner-1",
    "labels": "self-hosted,linux,x64,ci",
    "ephemeral": true,
    "daemonize": true
  }' \
  http://127.0.0.1:8080/api/v1/runners
```

### Remove Runner

**Endpoint**: `DELETE /api/v1/runners/{runner_name}`  
**Authentication**: Bearer token required  
**Description**: Remove and deregister a runner

**Request Body**:
```json
{
  "repo": "owner/repo"
}
```

**Response**:
```json
{
  "status": "removed",
  "name": "runner-1"
}
```

**Example**:
```bash
API_TOKEN="your-api-token"
curl -X DELETE \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"repo": "myorg/product"}' \
  http://127.0.0.1:8080/api/v1/runners/ci-runner-1
```

### Get Runner Status

**Endpoint**: `GET /api/v1/runners/{runner_name}/status`  
**Authentication**: Bearer token required  
**Description**: Get runner status

**Response**:
```json
{
  "status": "running",
  "name": "runner-1",
  "pid": 12345
}
```

**Status Values**:
- `running` - Runner process is active
- `installed_not_running` - Runner configured but process down
- `not_installed` - Runner not found

**Example**:
```bash
API_TOKEN="your-api-token"
curl -H "Authorization: Bearer $API_TOKEN" \
  http://127.0.0.1:8080/api/v1/runners/ci-runner-1/status
```

## Securing the API

### Option 1: Loopback Only (Default)

Bind to localhost only (most secure for single-host):

```bash
GITHUB_WFA_RUNNER_SERVER__BIND=127.0.0.1:8080
```

Access from the same host only:
```bash
curl http://127.0.0.1:8080/health
```

### Option 2: Cloudflare Tunnel (Recommended)

Use Cloudflare Tunnel for secure public access:

**Install cloudflared**:
```bash
# On Ubuntu/Debian
curl https://pkg.cloudflare.com/cloudflare-release.key | sudo gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-mainline.gpg
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-mainline.gpg] https://pkg.cloudflare.com/linux focal main' | sudo tee /etc/apt/sources.list.d/cloudflare-main.list
sudo apt-get update && sudo apt-get install cloudflared
```

**Create tunnel**:
```bash
# Authenticate
cloudflared tunnel login

# Create named tunnel
cloudflared tunnel create runnerctl

# Get tunnel ID
TUNNEL_ID=$(cloudflared tunnel list | awk '/runnerctl/ {print $1; exit}')

# Create DNS route
cloudflared tunnel route dns runnerctl runnerctl.example.com
```

**Configure ingress** (`/etc/cloudflared/config.yml`):
```yaml
tunnel: ${TUNNEL_ID}
credentials-file: /etc/cloudflared/${TUNNEL_ID}.json

ingress:
  - hostname: runnerctl.example.com
    service: http://127.0.0.1:8080
  - service: http_status:404
```

**Run as service**:
```bash
sudo systemctl enable --now cloudflared
sudo systemctl status cloudflared
```

**Access via tunnel**:
```bash
curl -H "Authorization: Bearer $API_TOKEN" \
  https://runnerctl.example.com/health
```

### Option 3: Firewall Rules

Restrict access by IP:

```bash
# Allow only specific IPs
sudo ufw allow from 203.0.113.0/24 to any port 8080

# Or with iptables
sudo iptables -A INPUT -p tcp --dport 8080 -s 203.0.113.0/24 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8080 -j DROP
```

## Integration with GitHub Actions

### Setup

Store secrets in your repository:

```bash
RUNNERCTL_BASE_URL=https://runnerctl.example.com  # or http://127.0.0.1:8080
API_TOKEN=your-very-long-secret-token
```

### Workflow Example

```yaml
name: CI with RunnerCTL

on: [push]

jobs:
  provision:
    runs-on: ubuntu-latest
    outputs:
      runner-name: ${{ steps.create.outputs.runner-name }}
    steps:
      - name: Create ephemeral runner
        id: create
        run: |
          RUNNER_NAME="runner-${{ github.run_id }}"
          echo "runner-name=$RUNNER_NAME" >> $GITHUB_OUTPUT
          
          curl -X POST \
            -H "Authorization: Bearer ${{ secrets.API_TOKEN }}" \
            -H "Content-Type: application/json" \
            -d "{
              \"repo\": \"${{ github.repository }}\",
              \"name\": \"$RUNNER_NAME\",
              \"labels\": \"self-hosted,linux,x64\",
              \"ephemeral\": true,
              \"daemonize\": true
            }" \
            ${{ secrets.RUNNERCTL_BASE_URL }}/api/v1/runners
          
          # Wait for runner to come online
          for i in {1..60}; do
            STATUS=$(curl -s \
              -H "Authorization: Bearer ${{ secrets.API_TOKEN }}" \
              ${{ secrets.RUNNERCTL_BASE_URL }}/api/v1/runners/$RUNNER_NAME/status \
              | jq -r .status)
            
            if [ "$STATUS" = "running" ]; then
              echo "Runner online"
              exit 0
            fi
            
            echo "Waiting for runner... ($i/60)"
            sleep 1
          done
          
          echo "Timeout waiting for runner"
          exit 1

  build:
    needs: provision
    runs-on: ${{ needs.provision.outputs.runner-name }}
    steps:
      - uses: actions/checkout@v4
      - name: Build
        run: make build

  cleanup:
    if: always()
    needs: [provision, build]
    runs-on: ubuntu-latest
    steps:
      - name: Remove runner
        run: |
          curl -X DELETE \
            -H "Authorization: Bearer ${{ secrets.API_TOKEN }}" \
            -H "Content-Type: application/json" \
            -d '{"repo": "${{ github.repository }}"}' \
            ${{ secrets.RUNNERCTL_BASE_URL }}/api/v1/runners/${{ needs.provision.outputs.runner-name }}
```

## Operations

### Monitor Server

```bash
# Check status
sudo systemctl status runnerctl-server

# View logs
sudo journalctl -u runnerctl-server -f

# Check bound port
netstat -tlnp | grep python
```

### Restart Server

```bash
sudo systemctl restart runnerctl-server
```

### Check API Token

```bash
# View current token (careful - exposes secrets!)
grep API_TOKEN /etc/runnerctl/runnerctl.env | cut -d= -f2

# Rotate token (requires service restart)
sudo nano /etc/runnerctl/runnerctl.env
# Update GITHUB_WFA_RUNNER_SERVER__API_TOKEN
sudo systemctl restart runnerctl-server
```

## Troubleshooting

### Connection Refused

```bash
# Verify server is running
systemctl status runnerctl-server

# Check binding
netstat -tlnp | grep python

# Verify environment variables
cat /etc/runnerctl/runnerctl.env
```

### Authentication Failed

```bash
# Verify API token
echo $API_TOKEN
echo "Check against: grep API_TOKEN /etc/runnerctl/runnerctl.env"

# Bearer token format (with space)
curl -H "Authorization: Bearer $API_TOKEN" \
  http://127.0.0.1:8080/health
```

### Runner Not Starting

```bash
# Check runner logs
tail -f /opt/runnerctl/runners/runner-name/runner.log

# Verify GitHub App credentials
cat /etc/runnerctl/runnerctl.env | grep GITHUB_APP

# Check API server logs
journalctl -u runnerctl-server -n 50 -f
```

### Cloudflare Tunnel Issues

```bash
# Check tunnel status
cloudflared tunnel list
cloudflared tunnel ingress validate

# View tunnel logs
journalctl -u cloudflared -f

# Test tunnel connectivity
curl https://runnerctl.example.com/health
```

## Performance Considerations

### Connection Pooling

API server handles concurrent requests. For high throughput:

```bash
# Monitor resource usage
top -p $(pgrep -f "uvicorn")

# Increase file descriptors if needed
ulimit -n 4096
```

### Request Rate Limiting

Implement rate limiting upstream:

```bash
# With Cloudflare Tunnel
# Enable Cloudflare DDoS protection and rate limiting

# With firewall
sudo ufw limit 8080
```

### Timeout Handling

Runners typically take 30-60 seconds to come online:

```bash
# Increase workflow timeout
jobs:
  build:
    timeout-minutes: 10  # Allow 10 minutes for provisioning + build
```

## See Also

- [Installation Guide](installation.md)
- [GitHub App Setup](github-app-setup.md)
- [Managed Mode](managed-mode.md)
- [Troubleshooting](troubleshooting.md)
