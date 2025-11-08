#!/bin/bash
# IPTVPortal Cline Workflow Helper Library
# Common functions for Cline integration scripts

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
CLINE_PROGRESS_FILE=".cline-progress"
REPO_URL="https://github.com/pv-udpv/iptvportal-client"
MAIN_BRANCH="main"

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_debug() {
    echo -e "${PURPLE}🔍 $1${NC}"
}

log_progress() {
    echo -e "${CYAN}📊 $1${NC}"
}

# Check if we're in a git repository
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Not in a git repository"
        exit 1
    fi
}

# Get current branch
get_current_branch() {
    local branch=$(git branch --show-current)
    if [ -z "$branch" ]; then
        log_error "Could not determine current branch"
        exit 1
    fi
    echo "$branch"
}

# Get current timestamp in ISO 8601 format
get_timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# Extract issue number from branch name
extract_issue_from_branch() {
    local branch="$1"
    if [[ $branch =~ issue-([0-9]+) ]]; then
        echo "${BASH_REMATCH[1]}"
    fi
}

# Check if gh CLI is available
check_gh_cli() {
    if command -v gh &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Check if gh CLI is authenticated
check_gh_auth() {
    if check_gh_cli && gh auth status > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Initialize .cline-progress file
init_cline_progress() {
    local issue="$1"
    local branch="$2"

    if [ -z "$issue" ]; then
        issue="null"
    fi

    if [ -z "$branch" ]; then
        branch="null"
    fi

    cat > "$CLINE_PROGRESS_FILE" << EOF
{
  "version": "1.0",
  "issue": $issue,
  "branch": "$branch",
  "created": "$(get_timestamp)",
  "updated": "$(get_timestamp)",
  "items": [],
  "metadata": {
    "total_items": 0,
    "completed_items": 0,
    "in_progress_items": 0,
    "pending_items": 0,
    "completion_percentage": 0
  }
}
EOF

    log_success "Initialized .cline-progress file"
}

# Read .cline-progress file
read_cline_progress() {
    if [ ! -f "$CLINE_PROGRESS_FILE" ]; then
        log_error ".cline-progress file not found. Run './scripts/cline-init.sh --issue <number>' first"
        exit 1
    fi

    cat "$CLINE_PROGRESS_FILE"
}

# Update .cline-progress file
update_cline_progress() {
    local json_data="$1"

    # Update timestamp
    local updated_json=$(echo "$json_data" | jq --arg timestamp "$(get_timestamp)" '.updated = $timestamp')

    # Recalculate metadata
    local total_items=$(echo "$updated_json" | jq '.items | length')
    local completed_items=$(echo "$updated_json" | jq '[.items[] | select(.status == "completed")] | length')
    local in_progress_items=$(echo "$updated_json" | jq '[.items[] | select(.status == "in_progress")] | length')
    local pending_items=$(echo "$updated_json" | jq '[.items[] | select(.status == "pending")] | length')

    local completion_percentage=0
    if [ "$total_items" -gt 0 ]; then
        completion_percentage=$((completed_items * 100 / total_items))
    fi

    updated_json=$(echo "$updated_json" | jq --arg total "$total_items" --arg completed "$completed_items" --arg in_progress "$in_progress_items" --arg pending "$pending_items" --arg percentage "$completion_percentage" '.metadata = {
        total_items: ($total | tonumber),
        completed_items: ($completed | tonumber),
        in_progress_items: ($in_progress | tonumber),
        pending_items: ($pending | tonumber),
        completion_percentage: ($percentage | tonumber)
    }')

    echo "$updated_json" > "$CLINE_PROGRESS_FILE"
}

# Add item to .cline-progress
add_cline_item() {
    local text="$1"
    local status="${2:-pending}"
    local priority="${3:-medium}"

    local json_data=$(read_cline_progress)
    local new_id=$(echo "$json_data" | jq '.items | length + 1')

    local new_item=$(cat << EOF
{
  "id": $new_id,
  "text": "$text",
  "status": "$status",
  "priority": "$priority",
  "commit": null,
  "created": "$(get_timestamp)",
  "updated": "$(get_timestamp)"
}
EOF
)

    local updated_json=$(echo "$json_data" | jq --argjson item "$new_item" '.items += [$item]')
    update_cline_progress "$updated_json"

    log_success "Added checklist item: $text"
}

# Update item status in .cline-progress
update_cline_item() {
    local item_id="$1"
    local status="$2"
    local commit="${3:-null}"

    local json_data=$(read_cline_progress)

    # Check if item exists
    local item_exists=$(echo "$json_data" | jq --arg id "$item_id" '.items[] | select(.id == ($id | tonumber)) | .id')
    if [ -z "$item_exists" ]; then
        log_error "Checklist item #$item_id not found"
        exit 1
    fi

    # Update item
    local updated_json=$(echo "$json_data" | jq --arg id "$item_id" --arg status "$status" --arg commit "$commit" --arg timestamp "$(get_timestamp)" '
        .items |= map(
            if .id == ($id | tonumber) then
                .status = $status |
                .commit = (if $commit != "null" then $commit else .commit end) |
                .updated = $timestamp
            else
                .
            end
        )
    ')

    update_cline_progress "$updated_json"

    local item_text=$(echo "$updated_json" | jq -r --arg id "$item_id" '.items[] | select(.id == ($id | tonumber)) | .text')
    log_success "Updated checklist item #$item_id ($item_text) to $status"
}

# Get checklist items by status
get_cline_items_by_status() {
    local status="$1"
    local json_data=$(read_cline_progress)

    echo "$json_data" | jq -r --arg status "$status" '.items[] | select(.status == $status) | "\(.id): \(.text)"'
}

# Format checklist for display
format_checklist() {
    local json_data=$(read_cline_progress)

    echo "$json_data" | jq -r '.items[] | if .status == "completed" then
        "- [x] \(.text)" + (if .commit then " → `\(.commit[0:7])`" else "" end)
    elif .status == "in_progress" then
        "- [🚧] \(.text)"
    else
        "- [ ] \(.text)"
    end'
}

# Generate progress summary
get_progress_summary() {
    local json_data=$(read_cline_progress)

    local total=$(echo "$json_data" | jq '.metadata.total_items')
    local completed=$(echo "$json_data" | jq '.metadata.completed_items')
    local percentage=$(echo "$json_data" | jq '.metadata.completion_percentage')

    echo "${percentage}% complete (${completed}/${total} items)"
}

# Generate GitHub issue comment
generate_issue_comment() {
    local json_data=$(read_cline_progress)
    local branch=$(echo "$json_data" | jq -r '.branch')
    local issue=$(echo "$json_data" | jq -r '.issue')
    local percentage=$(echo "$json_data" | jq '.metadata.completion_percentage')

    cat << EOF
## 🤖 Cline Progress Update

**Branch:** \`$branch\`
**Last Updated:** $(get_timestamp)
**Completion:** ${percentage}% ●●●●●●○○○○

### ✅ Completed ($(echo "$json_data" | jq '.metadata.completed_items')/$(echo "$json_data" | jq '.metadata.total_items'))
$(echo "$json_data" | jq -r '.items[] | select(.status == "completed") | "- \(.text) - [`\(.commit[0:7])`](https://github.com/pv-udpv/iptvportal-client/commit/\(.commit)) - _\(.updated | strptime("%Y-%m-%dT%H:%M:%SZ") | strftime("%H:%M"))_"')

### 🚧 In Progress ($(echo "$json_data" | jq '.metadata.in_progress_items')/$(echo "$json_data" | jq '.metadata.total_items'))
$(echo "$json_data" | jq -r '.items[] | select(.status == "in_progress") | "- \(.text) - _Started \(.updated | strptime("%Y-%m-%dT%H:%M:%SZ") | strftime("%H:%M"))_"')

### 📋 Not Started ($(echo "$json_data" | jq '.metadata.pending_items')/$(echo "$json_data" | jq '.metadata.total_items'))
$(echo "$json_data" | jq -r '.items[] | select(.status == "pending") | "- \(.text)"')

---
_Auto-updated by Cline workflow integration_
EOF
}

# Post comment to GitHub issue
post_issue_comment() {
    local issue="$1"
    local comment="$2"

    if check_gh_auth; then
        echo "$comment" | gh issue comment "$issue" -F -
        log_success "Posted progress update to issue #$issue"
    else
        log_warning "GitHub CLI not authenticated. Cannot post issue comment."
        log_info "To enable automatic updates, run: gh auth login"
        return 1
    fi
}

# Generate PR description with checklist
generate_pr_description() {
    local json_data=$(read_cline_progress)
    local issue=$(echo "$json_data" | jq -r '.issue')
    local branch=$(echo "$json_data" | jq -r '.branch')
    local percentage=$(echo "$json_data" | jq '.metadata.completion_percentage')

    cat << EOF
## Description

<!-- Describe the changes made in this PR -->

## Cline Task Progress

### Completed Items ✅ ($(echo "$json_data" | jq '.metadata.completed_items')/$(echo "$json_data" | jq '.metadata.total_items'))
$(echo "$json_data" | jq -r '.items[] | select(.status == "completed") | "- [x] \(.text) → [`\(.commit[0:7])`](https://github.com/pv-udpv/iptvportal-client/commit/\(.commit))"')

### In Progress 🚧 ($(echo "$json_data" | jq '.metadata.in_progress_items')/$(echo "$json_data" | jq '.metadata.total_items'))
$(echo "$json_data" | jq -r '.items[] | select(.status == "in_progress") | "- [ ] \(.text)"')

### Not Started 📋 ($(echo "$json_data" | jq '.metadata.pending_items')/$(echo "$json_data" | jq '.metadata.total_items'))
$(echo "$json_data" | jq -r '.items[] | select(.status == "pending") | "- [ ] \(.text)"')

**Completion: ${percentage}%**
**Issue:** Closes #$issue
**Branch:** \`$branch\`

---
<!-- End Cline Task Progress -->
EOF
}

# Validate checklist consistency
validate_checklist() {
    local json_data=$(read_cline_progress)

    # Check for items without commits that are marked complete
    local invalid_items=$(echo "$json_data" | jq -r '.items[] | select(.status == "completed" and (.commit == null or .commit == "")) | "\(.id): \(.text)"')

    if [ -n "$invalid_items" ]; then
        log_warning "Found completed items without commit references:"
        echo "$invalid_items"
        return 1
    fi

    return 0
}

# Show usage for scripts that source this file
show_usage() {
    local script_name="$1"
    echo "Usage: $script_name [OPTIONS]"
    echo ""
    echo "Helper functions available:"
    echo "  check_git_repo          - Verify we're in a git repository"
    echo "  get_current_branch      - Get current git branch"
    echo "  init_cline_progress     - Initialize .cline-progress file"
    echo "  read_cline_progress     - Read current progress"
    echo "  update_cline_progress   - Update progress file"
    echo "  add_cline_item          - Add new checklist item"
    echo "  update_cline_item       - Update item status"
    echo "  format_checklist        - Format checklist for display"
    echo "  get_progress_summary    - Get completion summary"
    echo "  generate_issue_comment  - Generate GitHub issue comment"
    echo "  generate_pr_description - Generate PR description"
    echo "  validate_checklist      - Validate checklist consistency"
}

# Export functions for use in other scripts
export -f log_info log_success log_warning log_error log_debug log_progress
export -f check_git_repo get_current_branch get_timestamp
export -f extract_issue_from_branch check_gh_cli check_gh_auth
export -f init_cline_progress read_cline_progress update_cline_progress
export -f add_cline_item update_cline_item get_cline_items_by_status
export -f format_checklist get_progress_summary
export -f generate_issue_comment post_issue_comment
export -f generate_pr_description validate_checklist
export -f show_usage
