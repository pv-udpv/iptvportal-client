#!/bin/bash
# IPTVPortal Commit Message Validator
# Standalone tool to validate commit messages against conventional commit format

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
    echo "Usage: $0 [OPTIONS] [COMMIT_REF]"
    echo ""
    echo "Validate commit messages against conventional commit format"
    echo ""
    echo "ARGUMENTS:"
    echo "  COMMIT_REF    Git reference (commit hash, branch, etc.) - defaults to HEAD"
    echo ""
    echo "OPTIONS:"
    echo "  -a, --all         Validate all commits in current branch"
    echo "  -r, --range REF   Validate commits from REF to HEAD"
    echo "  -f, --fix         Attempt to fix simple formatting issues"
    echo "  -v, --verbose     Show detailed validation results"
    echo "  -h, --help        Show this help"
    echo ""
    echo "EXAMPLES:"
    echo "  $0                    # Validate last commit"
    echo "  $0 --all             # Validate all commits in branch"
    echo "  $0 --range main      # Validate commits since main"
    echo "  $0 abc123            # Validate specific commit"
}

# Parse arguments
VALIDATE_ALL=false
VALIDATE_RANGE=""
FIX_MODE=false
VERBOSE=false
COMMIT_REF="HEAD"

while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--all)
            VALIDATE_ALL=true
            shift
            ;;
        -r|--range)
            VALIDATE_RANGE="$2"
            shift 2
            ;;
        -f|--fix)
            FIX_MODE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            if [ -z "$COMMIT_REF" ] || [ "$COMMIT_REF" = "HEAD" ]; then
                COMMIT_REF="$1"
            else
                log_error "Unexpected argument: $1"
                usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Valid types and scopes
VALID_TYPES="feat|fix|docs|test|refactor|chore|perf|style|ci|revert|build"
VALID_SCOPES="sync|cli|transpiler|schema|cache|config|docs|test|ci|deps"

# Validate single commit message
validate_commit_message() {
    local commit_hash="$1"
    local message="$2"
    local errors=()
    local warnings=()

    # Skip merge commits
    if [[ $message =~ ^Merge ]]; then
        $VERBOSE && log_info "Skipping merge commit $commit_hash"
        return 0
    fi

    # Skip revert commits
    if [[ $message =~ ^Revert ]]; then
        $VERBOSE && log_info "Skipping revert commit $commit_hash"
        return 0
    fi

    # Check basic format: type(scope): description
    if [[ ! $message =~ ^($VALID_TYPES)(\(($VALID_SCOPES)\))?:[[:space:]] ]]; then
        errors+=("Invalid format. Expected: type(scope): description")
        errors+=("Valid types: feat, fix, docs, test, refactor, chore, perf, style, ci, revert, build")
        errors+=("Valid scopes: sync, cli, transpiler, schema, cache, config, docs, test, ci, deps")
    fi

    # Check length
    local first_line=$(echo "$message" | head -n 1)
    if [ ${#first_line} -gt 72 ]; then
        errors+=("First line too long (${#first_line} chars). Maximum 72 characters.")
    fi

    if [ ${#first_line} -lt 10 ]; then
        warnings+=("First line very short (${#first_line} chars). Consider being more descriptive.")
    fi

    # Check for trailing punctuation
    if [[ $first_line =~ [.!?]$ ]]; then
        warnings+=("First line ends with punctuation. Consider removing it.")
    fi

    # Check for all caps
    if [[ $first_line =~ ^[A-Z[:space:]]+$ ]] && [ ${#first_line} -gt 10 ]; then
        warnings+=("First line is all caps. Consider using sentence case.")
    fi

    # Report results
    if [ ${#errors[@]} -gt 0 ]; then
        log_error "Commit $commit_hash has validation errors:"
        for error in "${errors[@]}"; do
            echo "  ❌ $error"
        done
        return 1
    fi

    if [ ${#warnings[@]} -gt 0 ] && $VERBOSE; then
        log_warning "Commit $commit_hash has warnings:"
        for warning in "${warnings[@]}"; do
            echo "  ⚠️  $warning"
        done
    fi

    $VERBOSE && log_success "Commit $commit_hash is valid"
    return 0
}

# Attempt to fix simple formatting issues
fix_commit_message() {
    local commit_hash="$1"
    local message="$2"

    local fixed_message="$message"

    # Remove trailing punctuation from first line
    local first_line=$(echo "$message" | head -n 1)
    local rest=$(echo "$message" | tail -n +2)

    first_line=$(echo "$first_line" | sed 's/[.!?]$//')

    if [ -n "$rest" ]; then
        fixed_message="$first_line
$rest"
    else
        fixed_message="$first_line"
    fi

    # Check if message changed
    if [ "$fixed_message" != "$message" ]; then
        log_info "Fixed commit $commit_hash:"
        log_info "  Original: $(echo "$message" | head -n 1)"
        log_info "  Fixed:    $first_line"

        # Amend commit with fixed message
        echo "$fixed_message" | git commit --amend -F -
        log_success "Commit $commit_hash amended with fixes"
        return 0
    else
        log_info "No fixes needed for commit $commit_hash"
        return 1
    fi
}

# Get commits to validate
get_commits_to_validate() {
    if $VALIDATE_ALL; then
        # All commits in current branch not in main
        git rev-list --not --remotes origin/main --remotes 2>/dev/null || git rev-list HEAD
    elif [ -n "$VALIDATE_RANGE" ]; then
        # Commits from range to HEAD
        git rev-list "$VALIDATE_RANGE..HEAD" 2>/dev/null || echo ""
    else
        # Single commit
        echo "$COMMIT_REF"
    fi
}

# Main validation function
validate_commits() {
    local commits=$(get_commits_to_validate)
    local total_commits=$(echo "$commits" | wc -l)
    local valid_count=0
    local invalid_count=0
    local fixed_count=0

    if [ -z "$commits" ]; then
        log_warning "No commits found to validate"
        return 0
    fi

    log_info "Validating $total_commits commit(s)..."

    while IFS= read -r commit_hash; do
        if [ -z "$commit_hash" ]; then
            continue
        fi

        # Get commit message
        local message=$(git log -1 --pretty=%B "$commit_hash" 2>/dev/null)

        if [ -z "$message" ]; then
            log_error "Could not get message for commit $commit_hash"
            continue
        fi

        if validate_commit_message "$commit_hash" "$message"; then
            ((valid_count++))
        else
            ((invalid_count++))

            if $FIX_MODE; then
                if fix_commit_message "$commit_hash" "$message"; then
                    ((fixed_count++))
                    ((valid_count++))
                    ((invalid_count--))
                fi
            fi
        fi
    done <<< "$commits"

    # Show summary
    echo ""
    log_info "Validation Summary:"
    echo "  Total commits: $total_commits"
    echo "  Valid: $valid_count"
    echo "  Invalid: $invalid_count"
    if $FIX_MODE; then
        echo "  Fixed: $fixed_count"
    fi

    if [ $invalid_count -gt 0 ]; then
        log_error "Found $invalid_count invalid commit(s)"
        return 1
    else
        log_success "All commits are valid!"
        return 0
    fi
}

# Main function
main() {
    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Not in a git repository"
        exit 1
    fi

    validate_commits
}

# Run main function
main "$@"
