# RunnerCTL Managed Mode (Config-Driven Runners)

RunnerCTL can maintain a pool of self-hosted runners declared in a YAML config. The manager keeps the desired set online by registering/starting runners and re-provisioning ephemeral ones after they finish.

Use cases:
- Private repos where users cannot add runners via the API.


## Config Schema

Path: `/etc/runnerctl/runnerctl.yaml` (see `contrib/runnerctl.yaml.example`)

```yaml
defaults:
  labels: self-hosted,linux,x64
  version: latest
  workdir: _work
  ephemeral: true
  daemonize: true
  base_dir: /opt/runnerctl/runners

runners:
  - name: repo-build-1
    scope: repo        # or org
    repo: owner/repo   # or org: my-org
    labels: self-hosted,linux,x64,build
    ephemeral: false   # persistent

  - name_prefix: repo-two-ephem
    scope: repo
    repo: owner/repo-two
    count: 3           # maintain 3 ephemeral instances
    labels: self-hosted,linux,x64,ephemeral
    ephemeral: true
```

Notes:
- Each runner entry uses either `name` (single) or `name_prefix` + `count` (pool) to generate names (`<prefix>-1..count`).
- `scope: repo|org` chooses registration scope. For org scope, the GitHub App must be installed at org level with appropriate permissions.
- Runners install under `base_dir/<name>`; this isolates multiple instances.

## Manager Service

Install the manager as a service alongside the API server:

```bash
sudo install -m 0644 contrib/systemd/runnerctl-manager.service /etc/systemd/system/
sudo install -m 0644 contrib/runnerctl.yaml.example /etc/runnerctl/runnerctl.yaml
sudo systemctl daemon-reload
sudo systemctl enable --now runnerctl-manager
```

Manager reads env from `/etc/runnerctl/runnerctl.env` (same as the API service), including GitHub App or PAT credentials. It loops every 10s and ensures each runner (or pool) is present and running.

### Environment Overrides for Defaults

You can override `defaults` via environment variables (Pydantic Settings v2):

- Prefix: `GITHUB_WFA_RUNNER_DEFAULTS__` (short alias also supported: `GHWFAX__DEFAULTS__`)
- Examples:
  - `GITHUB_WFA_RUNNER_DEFAULTS__LABELS=self-hosted,linux,x64,build`
  - `GITHUB_WFA_RUNNER_DEFAULTS__VERSION=latest`
  - `GITHUB_WFA_RUNNER_DEFAULTS__WORKDIR=_work`
  - `GITHUB_WFA_RUNNER_DEFAULTS__EPHEMERAL=false`
  - `GITHUB_WFA_RUNNER_DEFAULTS__DAEMONIZE=true`
  - `GITHUB_WFA_RUNNER_DEFAULTS__BASE_DIR=/opt/runnerctl/runners`

These apply after the YAML is loaded, so env values take precedence over file defaults.

## How It Works

- For each defined runner name, the manager sets `RUNNER_HOME` to a unique directory and shells out to `scripts/self-runner-ctl.sh register` with `DAEMONIZE=true`.
- Ephemeral runners are created and will exit after serving one job. The manager respawns them to keep the pool size.
- Persistent runners remain running; the manager restarts them if the process exits.

## Caveats

- Ensure sufficient CPU/RAM on the host for the number of runner instances.
- Outbound HTTPS to GitHub is required. For org scope, ensure App permissions include self-hosted runner admin.
- The manager is a simple supervisor; it does not scale on demand from webhook events (planned for a future autoscaler component).

## Troubleshooting

- Status per runner directory: `cat /opt/runnerctl/runners/<name>/runner.pid` and `tail -f /opt/runnerctl/runners/<name>/runner.log`
- Logs: `journalctl -u runnerctl-manager -f` and `journalctl -u runnerctl -f`
- Re-register a broken runner: stop/remove its directory and let the manager recreate it.
