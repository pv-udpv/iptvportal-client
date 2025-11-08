#!/bin/bash
# IPTVPortal Commit Message Helper
# Interactive tool for creating conventional commit messages

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
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Interactive conventional commit message builder"
    echo ""
    echo "OPTIONS:"
    echo "  -t, --type TYPE       Commit type (feat, fix, docs, etc.)"
    echo "  -s, --scope SCOPE     Commit scope (sync, cli, transpiler, etc.)"
    echo "  -m, --message MSG     Commit message"
    echo "  -b, --breaking        Mark as breaking change"
    echo "  --no-add             Don't add files automatically"
    echo "  -h, --help           Show this help"
    echo ""
    echo "EXAMPLES:"
    echo "  $0"
    echo "  $0 --type feat --scope sync --message \"Add incremental sync\""
    echo "  $0 --breaking --message \"Remove deprecated API\""
}

# Parse arguments
COMMIT_TYPE=""
COMMIT_SCOPE=""
COMMIT_MESSAGE=""
IS_BREAKING=false
AUTO_ADD=true

while [[ $# -gt 0 ]]; do
    case $1 in
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
        -b|--breaking)
            IS_BREAKING=true
            shift
            ;;
        --no-add)
            AUTO_ADD=false
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

# Interactive type selection
select_commit_type() {
    if [ -n "$COMMIT_TYPE" ]; then
        return
    fi

    echo "Select commit type:"
    echo "1) feat      - New feature"
    echo "2) fix       - Bug fix"
    echo "3) docs      - Documentation"
    echo "4) test      - Testing"
    echo "5) refactor  - Code refactoring"
    echo "6) chore     - Maintenance"
    echo "7) perf      - Performance improvement"
    echo "8) style     - Code style changes"
    echo "9) ci        - CI/CD changes"
    echo "10) revert   - Revert changes"
    echo "11) build    - Build system changes"

    while true; do
        read -r -p "Enter type number (1-11): " type_num
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
            11) COMMIT_TYPE="build" ;;
            *) continue ;;
        esac
        break
    done
}

# Interactive scope selection
select_commit_scope() {
    if [ -n "$COMMIT_SCOPE" ]; then
        return
    fi

    echo "Select commit scope:"
    echo "1) sync       - Sync system"
    echo "2) cli        - CLI commands"
    echo "3) transpiler - Transpiler"
    echo "4) schema     - Schema handling"
    echo "5) cache      - Caching system"
    echo "6) config     - Configuration"
    echo "7) docs       - Documentation"
    echo "8) test       - Testing"
    echo "9) ci         - CI/CD"
    echo "10) deps      - Dependencies"
    echo "11) none      - No scope"

    while true; do
        read -r -p "Enter scope number (1-11): " scope_num
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
            10) COMMIT_SCOPE="deps" ;;
            11) COMMIT_SCOPE="" ;;
            *) continue ;;
        esac
        break
    done
}

# Get commit message
get_commit_message() {
    if [ -n "$COMMIT_MESSAGE" ]; then
        return
    fi

    while true; do
        read -r -p "Enter commit message (max 72 chars): " message
        if [ ${#message} -gt 72 ]; then
            log_warning "Message too long (${#message} chars). Max 72 chars."
            continue
        fi
        if [ -z "$message" ]; then
            log_warning "Message cannot be empty"
            continue
        fi
        COMMIT_MESSAGE="$message"
        break
    done
}

# Build final commit message
build_commit_message() {
    local message="$COMMIT_TYPE"

    if [ -n "$COMMIT_SCOPE" ]; then
        message="$message($COMMIT_SCOPE)"
    fi

    message="$message: $COMMIT_MESSAGE"

    if $IS_BREAKING; then
        message="$message\n\nBREAKING CHANGE: This change breaks backward compatibility"
    fi

    echo "$message"
}

# Validate commit message format
validate_commit_message() {
    local message="$1"

    # Check basic format
    if [[ ! $message =~ ^(feat|fix|docs|test|refactor|chore|perf|style|ci|revert|build)(\([^)]+\))?: ]]; then
        log_error "Invalid commit message format"
        log_info "Expected: type(scope): description"
        return 1
    fi

    # Check length
    local first_line=$(echo "$message" | head -n 1)
    if [ ${#first_line} -gt 72 ]; then
        log_error "First line too long (${#first_line} chars). Max 72 chars."
        return 1
    fi

    return 0
}

# Check for uncommitted changes
check_changes() {
    if git diff --quiet && git diff --staged --quiet; then
        log_warning "No uncommitted changes found"
        echo "Do you want to continue anyway? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            exit 0
        fi
    fi
}

# Main function
main() {
    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Not in a git repository"
        exit 1
    fi

    check_changes

    select_commit_type
    select_commit_scope
    get_commit_message

    local final_message=$(build_commit_message)

    echo ""
    log_info "Commit message preview:"
    echo "$final_message"
    echo ""

    read -r -p "Is this correct? (Y/n): " confirm
    if [[ "$confirm" =~ ^[Nn]$ ]]; then
        log_info "Starting over..."
        COMMIT_TYPE=""
        COMMIT_SCOPE=""
        COMMIT_MESSAGE=""
        main
        return
    fi

    if ! validate_commit_message "$final_message"; then
        exit 1
    fi

    # Add files if requested
    if $AUTO_ADD; then
        log_info "Adding files..."
        git add .
    fi

    # Create commit
    log_info "Creating commit..."
    echo "$final_message" | git commit -F -

    log_success "Commit created successfully!"
    log_info "Use 'git log --oneline -1' to see the commit"
}

# Run main function
main "$@"
