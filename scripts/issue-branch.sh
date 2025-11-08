#!/bin/bash
# IPTVPortal Issue Branch Creation Script
# Creates a branch from an issue with proper naming

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
    echo "Usage: $0 ISSUE_NUMBER [BRANCH_SUFFIX]"
    echo ""
    echo "Create a branch from an issue with proper naming convention"
    echo ""
    echo "ARGUMENTS:"
    echo "  ISSUE_NUMBER    GitHub issue number"
    echo "  BRANCH_SUFFIX   Optional suffix for branch name (default: auto-generated)"
    echo ""
    echo "EXAMPLES:"
    echo "  $0 123"
    echo "  $0 456 add-validation"
    echo ""
    echo "BRANCH NAMING:"
    echo "  issue-123-fix-database-connection"
    echo "  issue-456-add-user-validation"
}

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

# Get issue details
get_issue_details() {
    local issue_num="$1"

    log_info "Fetching issue #$issue_num details..."

    # Get issue title
    local issue_title=$(gh issue view "$issue_num" --json title --jq .title 2>/dev/null)

    if [ -z "$issue_title" ]; then
        log_error "Issue #$issue_num not found or not accessible"
        exit 1
    fi

    # Get issue labels
    local issue_labels=$(gh issue view "$issue_num" --json labels --jq '.labels[].name' 2>/dev/null || echo "")

    log_success "Issue found: $issue_title"

    # Return values
    echo "$issue_title"
    echo "$issue_labels"
}

# Generate branch name
generate_branch_name() {
    local issue_num="$1"
    local issue_title="$2"
    local suffix="$3"

    # Clean up title for branch name
    local clean_title=$(echo "$issue_title" | \
        tr '[:upper:]' '[:lower:]' | \
        sed 's/[^a-z0-9]/-/g' | \
        sed 's/--*/-/g' | \
        sed 's/^-//' | \
        sed 's/-$//')

    # Determine action from title
    local action=""
    if [[ $clean_title =~ ^(add|create|implement|build) ]]; then
        action="add"
    elif [[ $clean_title =~ ^(fix|resolve|solve|correct) ]]; then
        action="fix"
    elif [[ $clean_title =~ ^(update|change|modify|improve) ]]; then
        action="update"
    elif [[ $clean_title =~ ^(remove|delete|drop) ]]; then
        action="remove"
    elif [[ $clean_title =~ ^(refactor|restructure) ]]; then
        action="refactor"
    else
        action="add"  # default
    fi

    # Use provided suffix or generate from title
    if [ -n "$suffix" ]; then
        local branch_name="issue-$issue_num-$suffix"
    else
        # Take first 3-4 words from title
        local short_title=$(echo "$clean_title" | cut -d'-' -f1-4)
        local branch_name="issue-$issue_num-$action-$short_title"
    fi

    # Ensure branch name is not too long (GitHub limit is 255 chars, but keep reasonable)
    if [ ${#branch_name} -gt 50 ]; then
        branch_name="${branch_name:0:47}..."
    fi

    echo "$branch_name"
}

# Check if branch already exists
check_branch_exists() {
    local branch_name="$1"

    if git show-ref --verify --quiet "refs/heads/$branch_name"; then
        log_warning "Branch '$branch_name' already exists locally"
        echo "Do you want to switch to it? (y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            git checkout "$branch_name"
            log_success "Switched to existing branch '$branch_name'"
            exit 0
        else
            log_info "Please choose a different issue number or suffix"
            exit 1
        fi
    fi

    # Check remote branch
    if git ls-remote --heads origin "$branch_name" > /dev/null 2>&1; then
        log_warning "Branch '$branch_name' exists on remote"
        log_info "Consider using a different suffix"
    fi
}

# Create and switch to branch
create_branch() {
    local branch_name="$1"
    local base_branch="main"

    log_info "Creating branch '$branch_name' from '$base_branch'..."

    # Create and switch to new branch
    git checkout -b "$branch_name" "$base_branch"

    log_success "Created and switched to branch '$branch_name'"
}

# Show next steps
show_next_steps() {
    local branch_name="$1"
    local issue_num="$2"

    echo ""
    log_success "Branch '$branch_name' created successfully!"
    echo ""
    log_info "Next steps:"
    echo "  1. Make your changes"
    echo "  2. Use conventional commits: ./scripts/commit-helper.sh"
    echo "  3. Push and create PR: ./scripts/git-workflow.sh"
    echo "  4. Or create PR manually: ./scripts/create-pr.sh --issue $issue_num"
    echo ""
    log_info "Current status:"
    git status --short
}

# Main function
main() {
    local issue_num="$1"
    local suffix="$2"

    if [ -z "$issue_num" ]; then
        log_error "Issue number is required"
        usage
        exit 1
    fi

    # Validate issue number is numeric
    if ! [[ "$issue_num" =~ ^[0-9]+$ ]]; then
        log_error "Issue number must be numeric"
        exit 1
    fi

    check_gh_cli

    # Get issue details
    local issue_details=($(get_issue_details "$issue_num"))
    local issue_title="${issue_details[0]}"
    local issue_labels="${issue_details[@]:1}"

    # Generate branch name
    local branch_name=$(generate_branch_name "$issue_num" "$issue_title" "$suffix")

    log_info "Proposed branch name: $branch_name"
    echo "Do you want to use this name? (Y/n)"
    read -r response
    if [[ "$response" =~ ^[Nn]$ ]]; then
        echo "Enter custom branch name (without issue- prefix):"
        read -r custom_name
        branch_name="issue-$issue_num-$custom_name"
    fi

    # Check if branch exists
    check_branch_exists "$branch_name"

    # Create branch
    create_branch "$branch_name"

    # Show next steps
    show_next_steps "$branch_name" "$issue_num"
}

# Run main function
main "$@"
