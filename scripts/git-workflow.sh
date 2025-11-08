#!/bin/bash
# IPTVPortal Git Workflow Automation Script
# Provides interactive commit → test → push → PR workflow

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="iptvportal-client"
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

# Check if we're in a git repository
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Not in a git repository"
        exit 1
    fi
}

# Check for uncommitted changes
check_uncommitted_changes() {
    if git diff --quiet && git diff --staged --quiet; then
        log_warning "No uncommitted changes found"
        echo "Do you want to continue anyway? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            exit 0
        fi
    fi
}

# Run tests
run_tests() {
    log_info "Running tests..."
    if uv run pytest --tb=short -q; then
        log_success "Tests passed"
        return 0
    else
        log_error "Tests failed"
        echo "Do you want to continue anyway? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Format code
format_code() {
    log_info "Formatting code..."
    uv run ruff format .
    uv run ruff check . --fix
    log_success "Code formatted"
}

# Interactive commit message builder
build_commit_message() {
    echo "Select commit type:"
    echo "1) feat     - New feature"
    echo "2) fix      - Bug fix"
    echo "3) docs     - Documentation"
    echo "4) test     - Testing"
    echo "5) refactor - Code refactoring"
    echo "6) chore    - Maintenance"
    echo "7) perf     - Performance improvement"
    echo "8) style    - Code style changes"
    echo "9) ci       - CI/CD changes"
    echo "10) revert  - Revert changes"

    while true; do
        read -r -p "Enter type number (1-10): " type_num
        case $type_num in
            1) TYPE="feat" ;;
            2) TYPE="fix" ;;
            3) TYPE="docs" ;;
            4) TYPE="test" ;;
            5) TYPE="refactor" ;;
            6) TYPE="chore" ;;
            7) TYPE="perf" ;;
            8) TYPE="style" ;;
            9) TYPE="ci" ;;
            10) TYPE="revert" ;;
            *) continue ;;
        esac
        break
    done

    echo "Available scopes:"
    echo "1) sync      - Sync system"
    echo "2) cli       - CLI commands"
    echo "3) transpiler - Transpiler"
    echo "4) schema    - Schema handling"
    echo "5) cache     - Caching system"
    echo "6) config    - Configuration"
    echo "7) docs      - Documentation"
    echo "8) test      - Testing"
    echo "9) ci        - CI/CD"
    echo "10) none     - No scope"

    while true; do
        read -r -p "Enter scope number (1-10): " scope_num
        case $scope_num in
            1) SCOPE="sync" ;;
            2) SCOPE="cli" ;;
            3) SCOPE="transpiler" ;;
            4) SCOPE="schema" ;;
            5) SCOPE="cache" ;;
            6) SCOPE="config" ;;
            7) SCOPE="docs" ;;
            8) SCOPE="test" ;;
            9) SCOPE="ci" ;;
            10) SCOPE="" ;;
            *) continue ;;
        esac
        break
    done

    read -r -p "Enter description (max 72 chars): " DESCRIPTION

    # Build commit message
    if [ -n "$SCOPE" ]; then
        COMMIT_MSG="$TYPE($SCOPE): $DESCRIPTION"
    else
        COMMIT_MSG="$TYPE: $DESCRIPTION"
    fi

    echo "Commit message: $COMMIT_MSG"
    read -r -p "Is this correct? (Y/n): " confirm
    if [[ "$confirm" =~ ^[Nn]$ ]]; then
        build_commit_message
        return
    fi
}

# Create commit
create_commit() {
    build_commit_message

    log_info "Creating commit..."
    git add .
    git commit -m "$COMMIT_MSG"
    log_success "Commit created: $COMMIT_MSG"
}

# Push changes
push_changes() {
    current_branch=$(git branch --show-current)
    log_info "Pushing to branch: $current_branch"

    if git push origin "$current_branch"; then
        log_success "Changes pushed to $current_branch"
    else
        log_error "Failed to push changes"
        exit 1
    fi
}

# Offer PR creation
offer_pr_creation() {
    current_branch=$(git branch --show-current)

    if [ "$current_branch" = "$MAIN_BRANCH" ]; then
        log_warning "On main branch, skipping PR creation"
        return
    fi

    echo "Do you want to create a Pull Request? (Y/n)"
    read -r response
    if [[ "$response" =~ ^[Nn]$ ]]; then
        return
    fi

    # Check if gh CLI is available
    if ! command -v gh &> /dev/null; then
        log_warning "GitHub CLI not found. Install it to create PRs automatically."
        log_info "Manual PR creation: https://github.com/pv-udpv/iptvportal-client/compare/$MAIN_BRANCH...$current_branch"
        return
    fi

    # Extract issue number from branch name
    issue_num=""
    if [[ $current_branch =~ issue-([0-9]+) ]]; then
        issue_num="${BASH_REMATCH[1]}"
    fi

    # Create PR
    pr_args="--title \"$COMMIT_MSG\" --base $MAIN_BRANCH"

    if [ -n "$issue_num" ]; then
        pr_args="$pr_args --body \"Closes #$issue_num\""
    fi

    log_info "Creating Pull Request..."
    if eval "gh pr create $pr_args"; then
        log_success "Pull Request created"
    else
        log_error "Failed to create Pull Request"
    fi
}

# Main workflow
main() {
    log_info "Starting IPTVPortal Git Workflow"

    check_git_repo
    check_uncommitted_changes
    run_tests
    format_code
    create_commit
    push_changes
    offer_pr_creation

    log_success "Workflow completed successfully!"
    log_info "Don't forget to check your PR and request reviews if needed."
}

# Run main function
main "$@"
