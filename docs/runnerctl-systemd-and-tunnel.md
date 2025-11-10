# RunnerCTL Systemd Service and Cloudflare Tunnel Quickstart

This guide shows how to run the RunnerCTL API server as a systemd service on a Linux host and (optionally) expose it safely over the internet using Cloudflare Tunnel. RunnerCTL drives GitHub self‑hosted runner registration/removal using a GitHub App (preferred) or PAT fallback.

## Prerequisites

- Linux host with outbound HTTPS access to `github.com` / `api.github.com`
- Packages: `python3`, `curl`, `openssl`, `tar`, `gzip`, `jq`
- GitHub App credentials (App ID + private key PEM) or a PAT (fallback)

## Install RunnerCTL on host

1) Create service user and directories

```bash
sudo useradd --system --home /opt/runnerctl --shell /usr/sbin/nologin runnerctl || true
sudo mkdir -p /opt/runnerctl /etc/runnerctl
sudo chown -R runnerctl:runnerctl /opt/runnerctl
```

2) Copy RunnerCTL files

From this repo, copy the controller and server to the host (adjust path if needed):

```bash
sudo cp scripts/self-runner-ctl.sh /opt/runnerctl/
sudo cp scripts/runnerctl_server.py /opt/runnerctl/
sudo chown runnerctl:runnerctl /opt/runnerctl/*
sudo chmod +x /opt/runnerctl/self-runner-ctl.sh
```

3) Create environment file with secrets and defaults

```bash
sudo install -m 0640 -o root -g runnerctl contrib/systemd/runnerctl.env.example /etc/runnerctl/runnerctl.env
sudo editor /etc/runnerctl/runnerctl.env  # fill values
```

Required variables:
- `RUNNERCTL_API_TOKEN`: long random token used by the HTTP API (bearer auth)
- GitHub App (preferred): `GITHUB_APP_ID` and one of `GITHUB_APP_PRIVATE_KEY_B64`, `GITHUB_APP_PRIVATE_KEY_FILE`, or `GITHUB_APP_PRIVATE_KEY`
- Optional PAT fallback: `GITHUB_PAT`

4) Install systemd unit

```bash
sudo install -m 0644 -o root -g root contrib/systemd/runnerctl.service /etc/systemd/system/runnerctl.service
sudo systemctl daemon-reload
sudo systemctl enable --now runnerctl
```

5) Verify service

```bash
systemctl status runnerctl
journalctl -u runnerctl -f
curl -sS http://127.0.0.1:8080/health
```

## Cloudflare Tunnel (recommended)

RunnerCTL binds to loopback by default. Use Cloudflare Tunnel to expose it without opening inbound firewall ports.

### Quick test (ephemeral URL)

```bash
# Install cloudflared (see vendor docs). Then:
cloudflared tunnel --url http://127.0.0.1:8080
# Output shows a https://*.trycloudflare.com URL
```

Test API (from anywhere):

```bash
curl -H "Authorization: Bearer $RUNNERCTL_API_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST "https://<random>.trycloudflare.com/api/v1/runners" \
     -d '{"repo":"owner/repo","name":"ephem-1","labels":"self-hosted,linux,x64","ephemeral":true,"daemonize":true}'
```

### Permanent named tunnel

1) Authenticate cloudflared

```bash
cloudflared tunnel login
```

2) Create a tunnel and DNS route

```bash
cloudflared tunnel create runnerctl
TUNNEL_ID=$(cloudflared tunnel list | awk '/runnerctl/ {print $1; exit}')
cloudflared tunnel route dns runnerctl runnerctl.example.com
```

3) Configure ingress

Create `/etc/cloudflared/config.yml`:

```yaml
tunnel: ${TUNNEL_ID}
credentials-file: /etc/cloudflared/${TUNNEL_ID}.json
ingress:
  - hostname: runnerctl.example.com
    service: http://127.0.0.1:8080
  - service: http_status:404
```

4) Start tunnel as a service

```bash
sudo systemctl enable --now cloudflared
sudo systemctl status cloudflared
```

5) Secure access (recommended)

- Keep RunnerCTL bound to `127.0.0.1` (default)
- Require `RUNNERCTL_API_TOKEN` in all requests
- Optionally enable Cloudflare Access with an allow‑list policy

## Using from GitHub Actions (API mode)

Set repo secrets:
- `RUNNERCTL_BASE_URL`: e.g., `https://runnerctl.example.com`
- `RUNNERCTL_API_TOKEN`: same value as on the host

Sample job step:

```yaml
- name: Provision ephemeral runner
  run: |
    curl -H "Authorization: Bearer ${{ secrets.RUNNERCTL_API_TOKEN }}" \
         -H "Content-Type: application/json" \
         -X POST "${{ secrets.RUNNERCTL_BASE_URL }}/api/v1/runners" \
         -d '{"repo":"${{ github.repository }}","name":"ephem-${{ github.run_id }}","labels":"self-hosted,linux,x64","ephemeral":true,"daemonize":true}'
```

To remove:

```yaml
- name: Remove runner
  run: |
    curl -H "Authorization: Bearer ${{ secrets.RUNNERCTL_API_TOKEN }}" \
         -H "Content-Type: application/json" \
         -X DELETE "${{ secrets.RUNNERCTL_BASE_URL }}/api/v1/runners/ephem-${{ github.run_id }}" \
         -d '{"repo":"${{ github.repository }}"}'
```

## Notes

- Ensure outbound connectivity to GitHub from the host; otherwise the runner cannot register or go online.
- Prefer GitHub App credentials over PAT for better security and rotation.
- Logs are in journald: `journalctl -u runnerctl -f`.

