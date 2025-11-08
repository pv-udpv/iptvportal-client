#!/bin/bash
# IPTVPortal PR Creation Script
# Creates PRs with automatic issue linking and labeling

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MAIN_BRANCH="main"
REPO_URL="https://github.com/pv-udpv/iptvportal-client"

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

# Show usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Create a Pull Request with automatic issue linking and labeling"
    echo ""
    echo "OPTIONS:"
    echo "  -i, --issue NUMBER    Link PR to issue number"
    echo "  -t, --title TITLE     PR title (auto-generated if not provided)"
    echo "  -b, --body BODY       PR body (uses template if not provided)"
    echo "  -d, --draft           Create as draft PR"
    echo "  -l, --label LABEL     Add label (can be used multiple times)"
    echo "  --base BRANCH         Base branch (default: main)"
    echo "  -h, --help           Show this help"
    echo ""
    echo "EXAMPLES:"
    echo "  $0 --issue 123"
    echo "  $0 --title \"Add sync tests\" --draft"
    echo "  $0 --issue 456 --label enhancement --label testing"
}

# Parse arguments
ISSUE_NUM=""
PR_TITLE=""
PR_BODY=""
IS_DRAFT=false
LABELS=()
BASE_BRANCH="$MAIN_BRANCH"

while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--issue)
            ISSUE_NUM="$2"
            shift 2
            ;;
        -t|--title)
            PR_TITLE="$2"
            shift 2
            ;;
        -b|--body)
            PR_BODY="$2"
            shift 2
            ;;
        -d|--draft)
            IS_DRAFT=true
            shift
            ;;
        -l|--label)
            LABELS+=("$2")
            shift 2
            ;;
        --base)
            BASE_BRANCH="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Check if gh CLI is available
check_gh_cli() {
    if ! command -v gh &> /dev/null; then
        log_error "GitHub CLI (gh) is not installed"
        log_info "Install from: https://cli.github.com/"
        exit 1
    fi

    # Check if authenticated
    if ! gh auth status > /dev/null 2>&1; then
        log_error "Not authenticated with GitHub CLI"
        log_info "Run: gh auth login"
        exit 1
    fi
}

# Get current branch
get_current_branch() {
    current_branch=$(git branch --show-current)
    if [ -z "$current_branch" ]; then
        log_error "Could not determine current branch"
        exit 1
    fi

    if [ "$current_branch" = "$BASE_BRANCH" ]; then
        log_error "Cannot create PR from $BASE_BRANCH branch"
        exit 1
    fi

    echo "$current_branch"
}

# Auto-detect issue number from branch name
auto_detect_issue() {
    local branch="$1"

    # Check for issue-123 pattern
    if [[ $branch =~ issue-([0-9]+) ]]; then
        ISSUE_NUM="${BASH_REMATCH[1]}"
        log_info "Auto-detected issue #$ISSUE_NUM from branch name"
    fi
}

# Generate PR title from commit messages
generate_pr_title() {
    local branch="$1"

    if [ -n "$PR_TITLE" ]; then
        return
    fi

    # Get last commit message
    local last_commit=$(git log -1 --pretty=%B | head -n 1)

    # If it's a conventional commit, use it as title
    if [[ $last_commit =~ ^(feat|fix|docs|test|refactor|chore|perf|style|ci|revert)(\([^)]+\))?: ]]; then
        PR_TITLE="$last_commit"
        log_info "Using commit message as PR title: $PR_TITLE"
        return
    fi

    # Fallback to branch name
    PR_TITLE="${branch//-/ }"
    PR_TITLE="${PR_TITLE^}"  # Capitalize first letter
    log_info "Generated PR title: $PR_TITLE"
}

# Generate PR body
generate_pr_body() {
    if [ -n "$PR_BODY" ]; then
        return
    fi

    local body=""

    # Add issue reference
    if [ -n "$ISSUE_NUM" ]; then
        body+="Closes #$ISSUE_NUM"$'\n\n'
    fi

    # Add description
    body+="## Description"$'\n'
    body+="<!-- Describe the changes made in this PR -->"$'\n\n'

    # Add testing checklist
    body+="## Testing"$'\n'
    body+="- [ ] Tests pass locally"$'\n'
    body+="- [ ] Code follows project conventions"$'\n'
    body+="- [ ] Documentation updated if needed"$'\n\n'

    # Add type of change
    body+="## Type of Change"$'\n'
    body+="- [ ] Bug fix"$'\n'
    body+="- [ ] New feature"$'\n'
    body+="- [ ] Breaking change"$'\n'
    body+="- [ ] Documentation update"$'\n'
    body+="- [ ] Refactoring"$'\n'
    body+="- [ ] Performance improvement"$'\n'
    body+="- [ ] CI/CD changes"$'\n\n'

    PR_BODY="$body"
}

# Auto-generate labels based on changes
generate_labels() {
    local branch="$1"

    # Add labels from command line
    for label in "${LABELS[@]}"; do
        AUTO_LABELS+=("$label")
    done

    # Auto-detect labels from branch/commits
    if [[ $branch == *"fix"* ]] || [[ $branch == *"bug"* ]]; then
        AUTO_LABELS+=("bug")
    fi

    if [[ $branch == *"feat"* ]] || [[ $branch == *"feature"* ]]; then
        AUTO_LABELS+=("enhancement")
    fi

    if [[ $branch == *"test"* ]]; then
        AUTO_LABELS+=("testing")
    fi

    if [[ $branch == *"docs"* ]]; then
        AUTO_LABELS+=("documentation")
    fi

    # Remove duplicates
    AUTO_LABELS=($(printf "%s\n" "${AUTO_LABELS[@]}" | sort -u))
}

# Create PR
create_pr() {
    local branch="$1"

    log_info "Creating Pull Request..."
    log_info "Branch: $branch"
    log_info "Base: $BASE_BRANCH"
    log_info "Title: $PR_TITLE"

    # Build gh command
    local cmd="gh pr create"
    cmd="$cmd --title \"$PR_TITLE\""
    cmd="$cmd --body \"$PR_BODY\""
    cmd="$cmd --base \"$BASE_BRANCH\""
    cmd="$cmd --head \"$branch\""

    if $IS_DRAFT; then
        cmd="$cmd --draft"
    fi

    # Add labels
    for label in "${AUTO_LABELS[@]}"; do
        cmd="$cmd --label \"$label\""
    done

    log_info "Running: $cmd"

    # Execute command
    if eval "$cmd"; then
        log_success "Pull Request created successfully!"

        # Show PR URL
        local pr_url=$(gh pr view --json url -q .url)
        if [ -n "$pr_url" ]; then
            log_info "PR URL: $pr_url"
        fi
    else
        log_error "Failed to create Pull Request"
        exit 1
    fi
}

# Main function
main() {
    check_gh_cli

    local current_branch=$(get_current_branch)

    # Auto-detect issue if not provided
    if [ -z "$ISSUE_NUM" ]; then
        auto_detect_issue "$current_branch"
    fi

    generate_pr_title "$current_branch"
    generate_pr_body
    generate_labels "$current_branch"

    create_pr "$current_branch"
}

# Run main function
main "$@"
