#!/bin/bash
# IPTVPortal Git Hooks Setup Script
# Configures git to use the custom hooks in .githooks directory

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

# Check if we're in a git repository
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Not in a git repository"
        exit 1
    fi
}

# Check if .githooks directory exists
check_hooks_directory() {
    if [ ! -d ".githooks" ]; then
        log_error ".githooks directory not found"
        log_info "Make sure you're in the project root directory"
        exit 1
    fi
}

# Make hooks executable
make_hooks_executable() {
    log_info "Making git hooks executable..."

    local hooks=(pre-commit commit-msg post-commit pre-push)

    for hook in "${hooks[@]}"; do
        local hook_path=".githooks/$hook"
        if [ -f "$hook_path" ]; then
            chmod +x "$hook_path"
            log_success "Made $hook executable"
        else
            log_warning "Hook $hook not found at $hook_path"
        fi
    done
}

# Configure git to use .githooks directory
configure_git_hooks_path() {
    log_info "Configuring git hooks path..."

    # Set the hooks path to .githooks
    git config core.hooksPath .githooks

    log_success "Git hooks path configured to .githooks"
}

# Test hooks are working
test_hooks() {
    log_info "Testing git hooks configuration..."

    # Check if hooks are properly configured
    local configured_path=$(git config core.hooksPath)

    if [ "$configured_path" = ".githooks" ]; then
        log_success "Git hooks path is correctly configured"
    else
        log_error "Git hooks path configuration failed"
        log_info "Expected: .githooks, Got: $configured_path"
        exit 1
    fi

    # Check if hooks are executable
    local hooks=(pre-commit commit-msg post-commit pre-push)

    for hook in "${hooks[@]}"; do
        local hook_path=".githooks/$hook"
        if [ -f "$hook_path" ] && [ -x "$hook_path" ]; then
            log_success "Hook $hook is executable"
        else
            log_warning "Hook $hook is not executable or missing"
        fi
    done
}

# Show setup summary
show_setup_summary() {
    echo ""
    log_success "Git hooks setup completed successfully! 🎉"
    echo ""
    log_info "What was configured:"
    echo "  • Git hooks path set to .githooks/"
    echo "  • All hooks made executable"
    echo "  • Hooks will run automatically on git operations"
    echo ""
    log_info "Available hooks:"
    echo "  • pre-commit: Quality checks before commits"
    echo "  • commit-msg: Message format validation"
    echo "  • post-commit: Helpful suggestions after commits"
    echo "  • pre-push: Comprehensive checks before pushing"
    echo ""
    log_info "To skip hooks, use --no-verify flag:"
    echo "  git commit --no-verify"
    echo "  git push --no-verify"
    echo ""
    log_info "To test hooks manually:"
    echo "  .githooks/pre-commit"
    echo "  .githooks/commit-msg <commit-msg-file>"
}

# Show workflow scripts
show_workflow_scripts() {
    echo ""
    log_info "Available workflow scripts:"
    echo "  • ./scripts/git-workflow.sh     - Full commit → test → push → PR workflow"
    echo "  • ./scripts/create-pr.sh        - Create PR with issue linking"
    echo "  • ./scripts/commit-helper.sh    - Interactive commit message builder"
    echo ""
    log_info "Make sure scripts are executable:"
    echo "  chmod +x scripts/*.sh"
}

# Main function
main() {
    log_info "Setting up IPTVPortal Git Hooks..."

    check_git_repo
    check_hooks_directory
    make_hooks_executable
    configure_git_hooks_path
    test_hooks
    show_setup_summary
    show_workflow_scripts

    log_success "Setup complete! Happy coding! 🚀"
}

# Run main function
main "$@"
