# GitHub App Setup Guide

RunnerCTL requires a GitHub App for secure authentication and runner management. This guide walks through creating, configuring, and securing your GitHub App.

## Why GitHub App?

GitHub Apps provide:
- **Finer permissions** - Only the permissions you need
- **Better security** - Private keys, no personal tokens
- **Token rotation** - Easy credential refresh
- **Audit trail** - Clear integration logs
- **Scope flexibility** - Repository or organization level

## Creating a GitHub App

### Step 1: Navigate to GitHub App Settings

1. Go to your GitHub account settings: https://github.com/settings/apps
2. Click **New GitHub App** button
3. Or for organization apps: https://github.com/organizations/{org}/settings/apps

### Step 2: Register New Application

Fill in the following fields:

| Field | Value | Notes |
|-------|-------|-------|
| **GitHub App name** | `runnerctl` (or similar) | Must be unique within scope |
| **Homepage URL** | `https://github.com` | Can be your org website |
| **Webhook URL** | Leave blank | RunnerCTL doesn't need webhooks |
| **Webhook active** | ☐ Unchecked | Not required |
| **Permissions** | See below | **Critical** - see permissions section |

### Step 3: Set Permissions

#### For Repository Scope

Set these permissions to **Read & write**:

- **Actions**: Read & write (for runner management)
- **Administration**: Read & write (for runner access)
- **Contents**: Read-only (optional, for downloading scripts)

Repository permissions apply to individual repos where the app is installed.

#### For Organization Scope

Set these permissions to **Read & write**:

- **Self-hosted runners**: Read & write (for org-level runner management)
- **Administration**: Read & write (for org settings access)

Organization scope allows managing runners across all repos in the org.

### Step 4: Save App

Click **Create GitHub App**. You'll be redirected to the app details page.

## Configuring the App

### Step 1: Generate Private Key

1. On the GitHub App page, scroll to **Private keys** section
2. Click **Generate a private key**
3. A `.pem` file will be downloaded automatically
4. **Keep this file secure** - anyone with it can act as your app

### Step 2: Note App ID

1. On the GitHub App page, find **App ID** (near the top)
2. Example: `123456`
3. Save this for configuration

### Step 3: Encode Private Key

Convert the PEM file to base64 (single-line format):

```bash
# Option 1: From downloaded file
cat ~/Downloads/runnerctl.2024-11-11.private-key.pem | base64 -w 0 > private-key-b64.txt
cat private-key-b64.txt

# Option 2: From PEM content (copy-paste)
echo "-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA...
...
-----END RSA PRIVATE KEY-----" | base64 -w 0
```

Output will be a single long line like:
```
LS0tLS1CRUdJTiBSU0EgUFJJVkFURSBLRVktLS0tLQpNSUlFb3dJQkFBS0NBUkVBNGVxdEk1VDNM...
```

## Installing the App on Repositories

### Install on Specific Repository (Repo Scope)

1. Go back to your GitHub App page
2. Click **Install App** (left sidebar)
3. Select the user/organization where the repo lives
4. Choose **Only select repositories**
5. Select repositories you want to manage runners for
6. Click **Install**

### Install on Organization (Org Scope)

1. Go back to your GitHub App page
2. Click **Install App** (left sidebar)
3. Select your organization
4. Choose **All repositories** or **Only select repositories**
5. Click **Install**

### Verify Installation

Check installation by listing installations:

```bash
# For repo scope
curl -s \
  -H "Authorization: Bearer GITHUB_APP_JWT" \
  https://api.github.com/repos/owner/repo/installation | jq .

# For org scope
curl -s \
  -H "Authorization: Bearer GITHUB_APP_JWT" \
  https://api.github.com/orgs/myorg/installation | jq .
```

## Configuring RunnerCTL

### Environment Variables

Set these in `/etc/runnerctl/runnerctl.env`:

```bash
# GitHub App ID (from app details page)
GITHUB_APP_ID=123456

# Private key (base64-encoded, single line)
GITHUB_APP_PRIVATE_KEY_B64=LS0tLS1CRUdJTi...

# Alternative: Path to PEM file
# GITHUB_APP_PRIVATE_KEY_FILE=/etc/runnerctl/private-key.pem

# Alternative: PEM content directly (multiline, enclosed in quotes)
# GITHUB_APP_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----
# MIIEvAI...
# -----END PRIVATE KEY-----"
```

### Secure File Permissions

```bash
# If using file-based key
sudo install -m 0600 -o runnerctl -g runnerctl \
  /path/to/private-key.pem \
  /etc/runnerctl/private-key.pem

# Verify permissions
stat /etc/runnerctl/private-key.pem
# Access: (0600/-rw-------)  Uid: ( 1234/ runnerctl)

# Lock down env file
sudo chmod 0640 /etc/runnerctl/runnerctl.env
sudo chown root:runnerctl /etc/runnerctl/runnerctl.env
```

## YAML Configuration

In `/etc/runnerctl/runnerctl.yaml`, specify the scope (repo or org):

```yaml
runners:
  # Repository-scoped runner
  - name: build-1
    scope: repo
    repo: owner/repo-name
    ephemeral: false
    labels: self-hosted,linux,x64,build

  # Organization-scoped runners (requires org-level app install)
  - name_prefix: org-pool
    scope: org
    org: my-org
    count: 5
    ephemeral: true
    labels: self-hosted,linux,x64,org
```

## Testing the Configuration

### 1. Validate App JWT

```bash
export GITHUB_APP_ID=123456
export GITHUB_APP_PRIVATE_KEY_B64=LS0tLS1CRUdJTi...

# This will create a JWT (expires in 9 minutes)
python3 << 'EOF'
import os, json, base64, time
from datetime import datetime

# Generate JWT manually (for testing)
app_id = os.environ.get('GITHUB_APP_ID')
key_b64 = os.environ.get('GITHUB_APP_PRIVATE_KEY_B64')

key_pem = base64.b64decode(key_b64).decode()
print("Private Key loaded successfully")
print(f"App ID: {app_id}")
EOF
```

### 2. Check Installation ID

```bash
source /etc/runnerctl/runnerctl.env

# For repo scope
curl -s \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer <APP_JWT>" \
  https://api.github.com/repos/owner/repo/installation | jq -r '.id'

# For org scope
curl -s \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer <APP_JWT>" \
  https://api.github.com/orgs/my-org/installation | jq -r '.id'
```

### 3. Test Runner Registration

```bash
# One-time registration test
export REPO=owner/repo-name
export RUNNER_NAME=test-runner
export RUNNER_HOME=/tmp/test-runner
export EPHEMERAL=true
export DAEMONIZE=false

runnerctl-manager once --config /etc/runnerctl/runnerctl.yaml
```

## Troubleshooting

### "Failed to get installation id"

**Cause**: App not installed on the repository/org  
**Solution**:
```bash
# Verify app installation
https://github.com/settings/apps/runnerctl/installations

# Reinstall the app on the target repo/org
```

### "Invalid JWT"

**Cause**: Incorrect private key or App ID  
**Solution**:
```bash
# Verify values match your GitHub App page
echo $GITHUB_APP_ID
echo $GITHUB_APP_PRIVATE_KEY_B64 | head -c 50

# Check file permissions if using GITHUB_APP_PRIVATE_KEY_FILE
stat /etc/runnerctl/private-key.pem
```

### "Insufficient permissions"

**Cause**: GitHub App doesn't have required permissions  
**Solution**:
1. Go to your GitHub App settings
2. Click **Permissions & events**
3. Ensure "Self-hosted runners" and "Administration" are set to "Read & write"
4. Click **Save changes**
5. Reinstall on repositories/organization

### "No suitable authentication available"

**Cause**: None of the three auth methods are set  
**Solution**: Ensure at least one of these is set in environment:
- `GITHUB_APP_PRIVATE_KEY_FILE` - path to PEM file
- `GITHUB_APP_PRIVATE_KEY` - PEM content (multiline)
- `GITHUB_APP_PRIVATE_KEY_B64` - base64-encoded PEM

## Security Best Practices

1. **Rotate Keys Regularly**
   ```bash
   # On GitHub App page, regenerate private key every 90 days
   # Update /etc/runnerctl/runnerctl.env with new key
   ```

2. **Restrict App Permissions**
   - Only grant "Self-hosted runners" permissions (avoid broad "repo" access)
   - Use specific repos instead of "All repositories"

3. **Limit Runner Scope**
   - Prefer organization scope over repository scope
   - Use labels to restrict where runners are used

4. **Monitor App Usage**
   ```bash
   # View GitHub App logs
   https://github.com/settings/apps/runnerctl/installations
   ```

5. **Audit Runner Actions**
   ```bash
   # Check systemd logs
   sudo journalctl -u runnerctl-manager -f

   # Check runner logs
   tail -f /opt/runnerctl/runners/*/runner.log
   ```

## Reference

- [GitHub App Documentation](https://docs.github.com/en/developers/apps)
- [Self-hosted runners API](https://docs.github.com/en/rest/actions/self-hosted-runners)
- [GitHub App Permissions](https://docs.github.com/en/developers/apps/building-github-apps/permissions-for-github-apps)
