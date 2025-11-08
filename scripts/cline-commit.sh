#!/bin/bash
# IPTVPortal Cline Commit Script
# Creates commits with checklist item references

set -e

# Source helper functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/cline-helpers.sh"

# Show usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Create a commit with checklist item references"
    echo ""
    echo "OPTIONS:"
    echo "  -i, --items IDS       Checklist item IDs to mark complete (comma-separated)"
    echo "  -t, --type TYPE       Commit type (feat, fix, docs, test, refactor, chore, perf, style, ci, revert, build)"
    echo "  -s, --scope SCOPE     Commit scope (sync, cli, transpiler, schema, cache, config, docs, test, ci, deps)"
    echo "  -m, --message MSG     Commit message"
    echo "  -l, --list            List available checklist items"
    echo "  -h, --help           Show this help"
    echo ""
    echo "EXAMPLES:"
    echo "  $0 --items 1,3 --type feat --scope sync --message \"Add incremental sync\""
    echo "  $0 --list"
    echo "  $0 --type fix --scope cli --message \"Handle invalid args\""
}

# Parse arguments
ITEM_IDS=""
COMMIT_TYPE=""
COMMIT_SCOPE=""
COMMIT_MESSAGE=""
LIST_ITEMS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--items)
            ITEM_IDS="$2"
            shift 2
            ;;
        -t|--type)
            COMMIT_TYPE="$2"
            shift 2
            ;;
        -s|--scope)
            COMMIT_SCOPE="$2"
            shift 2
            ;;
        -m|--message)
            COMMIT_MESSAGE="$2"
            shift 2
            ;;
        -l|--list)
            LIST_ITEMS=true
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

# Check if we're in a git repository
check_git_repo

# List items if requested
if [ "$LIST_ITEMS" = true ]; then
    if [ ! -f ".cline-progress" ]; then
        log_error ".cline-progress file not found. Run './scripts/cline-init.sh --issue <number>' first"
        exit 1
    fi

    echo "Available checklist items:"
    echo ""
    format_checklist
    echo ""
    log_info "Use --items to specify which items to mark complete (comma-separated IDs)"
    exit 0
fi

# Validate that we have a .cline-progress file
if [ ! -f ".cline-progress" ]; then
    log_error ".cline-progress file not found. Run './scripts/cline-init.sh --issue <number>' first"
    exit 1
fi

# Interactive mode if no arguments provided
if [ -z "$COMMIT_TYPE" ] && [ -z "$COMMIT_MESSAGE" ]; then
    log_info "Interactive commit mode"

    # Show current checklist
    echo "Current checklist status:"
    echo ""
    format_checklist
    echo ""

    # Get commit type
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
            1) COMMIT_TYPE="feat" ;;
            2) COMMIT_TYPE="fix" ;;
            3) COMMIT_TYPE="docs" ;;
            4) COMMIT_TYPE="test" ;;
            5) COMMIT_TYPE="refactor" ;;
            6) COMMIT_TYPE="chore" ;;
            7) COMMIT_TYPE="perf" ;;
            8) COMMIT_TYPE="style" ;;
            9) COMMIT_TYPE="ci" ;;
            10) COMMIT_TYPE="revert" ;;
            *) continue ;;
        esac
        break
    done

    # Get commit scope
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
            1) COMMIT_SCOPE="sync" ;;
            2) COMMIT_SCOPE="cli" ;;
            3) COMMIT_SCOPE="transpiler" ;;
            4) COMMIT_SCOPE="schema" ;;
            5) COMMIT_SCOPE="cache" ;;
            6) COMMIT_SCOPE="config" ;;
            7) COMMIT_SCOPE="docs" ;;
            8) COMMIT_SCOPE="test" ;;
            9) COMMIT_SCOPE="ci" ;;
            10) COMMIT_SCOPE="" ;;
            *) continue ;;
        esac
        break
    done

    # Get checklist items to complete
    if [ -z "$ITEM_IDS" ]; then
        echo ""
        echo "Enter checklist item IDs to mark complete (comma-separated, or empty for none):"
        read -r ITEM_IDS
    fi

    # Get commit message
    read -r -p "Enter commit message: " COMMIT_MESSAGE
fi

# Validate required fields
if [ -z "$COMMIT_TYPE" ]; then
    log_error "Commit type is required"
    exit 1
fi

if [ -z "$COMMIT_MESSAGE" ]; then
    log_error "Commit message is required"
    exit 1
fi

# Build commit message
if [ -n "$COMMIT_SCOPE" ]; then
    FULL_MESSAGE="$COMMIT_TYPE($COMMIT_SCOPE): $COMMIT_MESSAGE"
else
    FULL_MESSAGE="$COMMIT_TYPE: $COMMIT_MESSAGE"
fi

# Add checklist references if items specified
if [ -n "$ITEM_IDS" ]; then
    # Validate item IDs exist
    json_data=$(read_cline_progress)
    for item_id in $(echo "$ITEM_IDS" | tr ',' ' '); do
        item_exists=$(echo "$json_data" | jq --arg id "$item_id" '.items[] | select(.id == ($id | tonumber)) | .id')
        if [ -z "$item_exists" ]; then
            log_error "Checklist item #$item_id not found"
            exit 1
        fi
    done

    FULL_MESSAGE="$FULL_MESSAGE

Completes: #$ITEM_IDS (from .cline-progress)"
fi

# Show what will be committed
echo ""
log_info "Files to be committed:"
git status --porcelain
echo ""

log_info "Commit message:"
echo "$FULL_MESSAGE"
echo ""

read -r -p "Proceed with commit? (Y/n): " confirm
if [[ "$confirm" =~ ^[Nn]$ ]]; then
    log_info "Commit cancelled"
    exit 0
fi

# Stage all changes if nothing is staged
if git diff --cached --quiet; then
    log_info "Staging all changes..."
    git add .
fi

# Create the commit
log_info "Creating commit..."
git commit -m "$FULL_MESSAGE"

log_success "Commit created successfully!"

# The post-commit hook will automatically update checklist items
log_info "Checklist items will be updated automatically by the post-commit hook"
