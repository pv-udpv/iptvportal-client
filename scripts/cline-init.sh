#!/bin/bash
# IPTVPortal Cline Initialization Script
# Initializes Cline tracking for an issue

set -e

# Source helper functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/cline-helpers.sh"

# Show usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Initialize Cline tracking for an issue"
    echo ""
    echo "OPTIONS:"
    echo "  -i, --issue NUMBER    Issue number to track"
    echo "  -b, --branch NAME     Branch name (auto-detected if not provided)"
    echo "  -f, --force           Overwrite existing .cline-progress file"
    echo "  -h, --help           Show this help"
    echo ""
    echo "EXAMPLES:"
    echo "  $0 --issue 123"
    echo "  $0 --issue 456 --branch issue-456-feature"
    echo "  $0 --issue 789 --force"
}

# Parse arguments
ISSUE_NUM=""
BRANCH_NAME=""
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--issue)
            ISSUE_NUM="$2"
            shift 2
            ;;
        -b|--branch)
            BRANCH_NAME="$2"
            shift 2
            ;;
        -f|--force)
            FORCE=true
            shift
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

# Validate arguments
if [ -z "$ISSUE_NUM" ]; then
    log_error "Issue number is required"
    log_info "Use --issue to specify the issue number"
    exit 1
fi

# Check if we're in a git repository
check_git_repo

# Auto-detect branch if not provided
if [ -z "$BRANCH_NAME" ]; then
    BRANCH_NAME=$(get_current_branch)
    log_info "Auto-detected branch: $BRANCH_NAME"
fi

# Check if .cline-progress already exists
if [ -f ".cline-progress" ] && [ "$FORCE" = false ]; then
    log_warning ".cline-progress file already exists"
    log_info "Use --force to overwrite existing file"
    exit 1
fi

# Initialize the progress file
init_cline_progress "$ISSUE_NUM" "$BRANCH_NAME"

log_success "Cline tracking initialized for issue #$ISSUE_NUM on branch '$BRANCH_NAME'"
log_info "Next steps:"
echo "  1. Add checklist items: Use Cline to create task_progress checklists"
echo "  2. Make commits: Use './scripts/cline-commit.sh' for checklist-aware commits"
echo "  3. Create PR: Use './scripts/cline-pr.sh' when ready to create PR"
echo "  4. Check status: Use './scripts/cline-status.sh' to view progress"

# Show current status
echo ""
log_info "Current status:"
format_checklist
