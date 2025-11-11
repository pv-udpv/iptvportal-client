#!/usr/bin/env bash
set -euo pipefail

# Self-hosted runner controller (server-side)
# - Generates a GitHub App installation token
# - Requests a short-lived runner registration token
# - Downloads and configures the Actions runner
# - Starts the runner (foreground) or installs as a service (optional)
#
# Requirements on the host:
# - bash, curl, openssl, tar, gzip
# - jq (for JSON parsing)
#
# Inputs via env vars:
# - RUNNER_SCOPE:    repo|org (default: repo)
# - REPO:            owner/repo (required for repo scope)
# - ORG:             org name (required for org scope)
# - RUNNER_NAME:     name of the runner (default: hostname)
# - RUNNER_LABELS:   comma-separated labels (default: self-hosted,linux,x64)
# - RUNNER_WORKDIR:  work directory (default: _work)
# - RUNNER_VERSION:  actions runner version (default: latest)
# - EPHEMERAL:       true|false (default: false)
# - DISABLE_UPDATE:  true|false (default: true)
#
# GitHub App auth (preferred):
# - GITHUB_APP_ID:               App ID (required)
# - GITHUB_APP_PRIVATE_KEY_FILE: Path to PEM file (or)
# - GITHUB_APP_PRIVATE_KEY:      PEM content (multiline) (or)
# - GITHUB_APP_PRIVATE_KEY_B64:  PEM content base64-encoded (single line)
#
# PAT fallback (not recommended):
# - GITHUB_PAT: Personal access token with repo admin permissions

API_ROOT="https://api.github.com"

# Track temporary files for cleanup
TEMP_FILES=()

cleanup() {
  for f in "${TEMP_FILES[@]}"; do
    [[ -f "$f" ]] && rm -f "$f"
  done
}

trap cleanup EXIT

log() { echo "[$(date -Is)] $*"; }
err() { echo "[$(date -Is)] ERROR: $*" >&2; }

need() {
  command -v "$1" >/dev/null 2>&1 || { err "Missing dependency: $1"; exit 1; }
}

need curl; need openssl; need tar; need gzip; need sed; need grep; need jq

RUNNER_SCOPE="${RUNNER_SCOPE:-repo}"
REPO="${REPO:-}"            # owner/repo
ORG="${ORG:-}"              # org name
RUNNER_NAME="${RUNNER_NAME:-$(hostname)}"
RUNNER_LABELS="${RUNNER_LABELS:-self-hosted,linux,x64}"
RUNNER_WORKDIR="${RUNNER_WORKDIR:-_work}"
RUNNER_VERSION="${RUNNER_VERSION:-latest}"
EPHEMERAL="${EPHEMERAL:-false}"
DISABLE_UPDATE="${DISABLE_UPDATE:-true}"
# Runner installation directory (per instance). Defaults to 'actions-runner'.
# For multi-runner hosts, set RUNNER_HOME to a unique path per runner
# e.g., /opt/runnerctl/runners/$RUNNER_NAME
RUNNER_HOME="${RUNNER_HOME:-actions-runner}"
# If true, do not exec run.sh; start in background and write PID
DAEMONIZE="${DAEMONIZE:-false}"

AUTH_MODE=""

if [[ -n "${GITHUB_APP_ID:-}" ]]; then
  AUTH_MODE="app"
elif [[ -n "${GITHUB_PAT:-}" ]]; then
  AUTH_MODE="pat"
else
  err "Provide either GitHub App credentials (GITHUB_APP_ID + private key) or GITHUB_PAT"
  exit 1
fi

if [[ "$RUNNER_SCOPE" == "repo" && -z "$REPO" ]]; then
  err "RUNNER_SCOPE=repo requires REPO=owner/repo"
  exit 1
fi
if [[ "$RUNNER_SCOPE" == "org" && -z "$ORG" ]]; then
  err "RUNNER_SCOPE=org requires ORG=name"
  exit 1
fi

github_api() {
  local method="$1" path="$2" token="$3" data="${4:-}"
  if [[ -n "$data" ]]; then
    curl -fsS -X "$method" \
      -H "Accept: application/vnd.github+json" \
      -H "Authorization: Bearer $token" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      "$API_ROOT$path" \
      -d "$data"
  else
    curl -fsS -X "$method" \
      -H "Accept: application/vnd.github+json" \
      -H "Authorization: Bearer $token" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      "$API_ROOT$path"
  fi
}

make_app_jwt() {
  local key_file="${GITHUB_APP_PRIVATE_KEY_FILE:-}"
  if [[ -z "$key_file" ]]; then
    if [[ -n "${GITHUB_APP_PRIVATE_KEY_B64:-}" ]]; then
      key_file="$(mktemp)"
      TEMP_FILES+=("$key_file")
      printf '%s' "$GITHUB_APP_PRIVATE_KEY_B64" | base64 -d > "$key_file"
    elif [[ -n "${GITHUB_APP_PRIVATE_KEY:-}" ]]; then
      key_file="$(mktemp)"
      TEMP_FILES+=("$key_file")
      printf '%s' "$GITHUB_APP_PRIVATE_KEY" > "$key_file"
    fi
  fi
  [[ -f "$key_file" ]] || { err "GitHub App private key not provided"; exit 1; }

  local now exp header payload header_b64 payload_b64 sig_b64 unsigned
  now=$(date +%s)
  exp=$((now + 540)) # 9 minutes
  header='{"alg":"RS256","typ":"JWT"}'
  payload="{\"iat\":$((now-60)),\"exp\":$exp,\"iss\":$GITHUB_APP_ID}"
  header_b64=$(printf '%s' "$header" | openssl base64 -A | tr '+/' '-_' | tr -d '=')
  payload_b64=$(printf '%s' "$payload" | openssl base64 -A | tr '+/' '-_' | tr -d '=')
  unsigned="$header_b64.$payload_b64"
  sig_b64=$(printf '%s' "$unsigned" | openssl dgst -binary -sha256 -sign "$key_file" | openssl base64 -A | tr '+/' '-_' | tr -d '=')
  echo "$unsigned.$sig_b64"
}

get_installation_token() {
  local app_jwt="$1" inst_id
  if [[ "$RUNNER_SCOPE" == "repo" ]]; then
    local owner repo
    owner="${REPO%%/*}"; repo="${REPO##*/}"
    inst_id=$(github_api GET "/repos/$owner/$repo/installation" "$app_jwt" | jq -r '.id')
  else
    inst_id=$(github_api GET "/orgs/$ORG/installation" "$app_jwt" | jq -r '.id')
  fi
  [[ -n "$inst_id" && "$inst_id" != null ]] || { err "Failed to get installation id"; exit 1; }
  github_api POST "/app/installations/$inst_id/access_tokens" "$app_jwt" | jq -r '.token'
}

get_runner_registration_token() {
  local install_token="$1" owner repo
  if [[ "$RUNNER_SCOPE" == "repo" ]]; then
    owner="${REPO%%/*}"; repo="${REPO##*/}"
    github_api POST "/repos/$owner/$repo/actions/runners/registration-token" "$install_token" | jq -r '.token'
  else
    github_api POST "/orgs/$ORG/actions/runners/registration-token" "$install_token" | jq -r '.token'
  fi
}

get_runner_version() {
  if [[ "$RUNNER_VERSION" == "latest" ]]; then
    curl -fsS "$API_ROOT/repos/actions/runner/releases/latest" | jq -r '.tag_name' | sed 's/^v//'
  else
    echo "$RUNNER_VERSION"
  fi
}

download_runner() {
  local version="$1"
  if [[ ! -d "$RUNNER_HOME" ]]; then
    mkdir -p "$RUNNER_HOME"
  fi
  cd "$RUNNER_HOME"
  if [[ ! -f ".runner.${version}" ]]; then
    rm -f actions-runner-linux-x64-*.tar.gz || true
    curl -fsS -L -o actions-runner-linux-x64-${version}.tar.gz \
      https://github.com/actions/runner/releases/download/v${version}/actions-runner-linux-x64-${version}.tar.gz
    tar xzf actions-runner-linux-x64-${version}.tar.gz
    rm -f .runner.* || true
    touch ".runner.${version}"
  fi
}

configure_and_run() {
  local token="$1" version="$2"
  local url
  if [[ "$RUNNER_SCOPE" == "repo" ]]; then
    url="https://github.com/$REPO"
  else
    url="https://github.com/$ORG"
  fi
  local args=("--url" "$url" "--token" "$token" "--name" "$RUNNER_NAME" "--labels" "$RUNNER_LABELS" "--work" "$RUNNER_WORKDIR" "--unattended" "--replace")
  [[ "$EPHEMERAL" == "true" ]] && args+=("--ephemeral")
  [[ "$DISABLE_UPDATE" == "true" ]] && args+=("--disableupdate")

  ( cd "$RUNNER_HOME" && ./config.sh "${args[@]}" )
  log "Runner configured. Starting..."
  if [[ "$DAEMONIZE" == "true" ]]; then
    ( cd "$RUNNER_HOME" && nohup ./run.sh > runner.log 2>&1 & echo $! > runner.pid && echo "pid=$!" )
    if [[ -f "$RUNNER_HOME/runner.pid" ]]; then
      log "Runner started in background (pid $(cat "$RUNNER_HOME/runner.pid"))."
    else
      log "Runner started in background."
    fi
  else
    exec "$RUNNER_HOME"/run.sh
  fi
}

# Removal token endpoint helper
get_runner_removal_token() {
  local token_source="$1"
  if [[ "$RUNNER_SCOPE" == "repo" ]]; then
    local owner repo
    owner="${REPO%%/*}"; repo="${REPO##*/}"
    github_api POST "/repos/$owner/$repo/actions/runners/remove-token" "$token_source" | jq -r '.token'
  else
    github_api POST "/orgs/$ORG/actions/runners/remove-token" "$token_source" | jq -r '.token'
  fi
}

cmd_register() {
  local token app_jwt install_token version
  if [[ "$AUTH_MODE" == "app" ]]; then
    log "Using GitHub App authentication"
    app_jwt=$(make_app_jwt)
    install_token=$(get_installation_token "$app_jwt")
    token=$(get_runner_registration_token "$install_token")
  else
    log "Using PAT authentication"
    if [[ "$RUNNER_SCOPE" == "repo" ]]; then
      token=$(github_api POST "/repos/${REPO}/actions/runners/registration-token" "$GITHUB_PAT" | jq -r '.token')
    else
      token=$(github_api POST "/orgs/${ORG}/actions/runners/registration-token" "$GITHUB_PAT" | jq -r '.token')
    fi
  fi

  [[ -n "$token" && "$token" != null ]] || { err "Failed to obtain runner registration token"; exit 1; }
  version=$(get_runner_version)
  log "Using actions runner version: $version"
  download_runner "$version"
  configure_and_run "$token" "$version"
}

cmd_remove() {
  cd "$RUNNER_HOME" || { err "Runner directory not found: $RUNNER_HOME"; exit 1; }
  local token app_jwt install_token removal_token
  if [[ "$AUTH_MODE" == "app" ]]; then
    app_jwt=$(make_app_jwt)
    install_token=$(get_installation_token "$app_jwt")
    removal_token=$(get_runner_removal_token "$install_token")
  else
    # PAT mode uses PAT to get removal token
    removal_token=$(get_runner_removal_token "$GITHUB_PAT")
  fi
  [[ -n "$removal_token" && "$removal_token" != null ]] || { err "Failed to obtain runner removal token"; exit 1; }
  if [[ -f runner.pid ]]; then
    if kill -0 "$(cat runner.pid)" 2>/dev/null; then
      log "Stopping background runner pid $(cat runner.pid)"
      kill "$(cat runner.pid)" || true
      sleep 2 || true
    fi
  fi
  ./config.sh remove --token "$removal_token"
  log "Runner removed."
}

cmd_status() {
  if [[ -d "$RUNNER_HOME" ]]; then
    cd "$RUNNER_HOME"
    if [[ -f runner.pid ]] && kill -0 "$(cat runner.pid)" 2>/dev/null; then
      echo "running (pid $(cat runner.pid))"
    else
      echo "installed (not running)"
    fi
  else
    echo "not installed"
  fi
}

main() {
  local cmd="${1:-register}"
  case "$cmd" in
    register) shift || true; cmd_register "$@" ;;
    remove) shift || true; cmd_remove "$@" ;;
    status) shift || true; cmd_status "$@" ;;
    *) err "Unknown command: $cmd (expected: register|remove|status)"; exit 1 ;;
  esac
}

main "$@"
