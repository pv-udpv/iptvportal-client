#!/bin/bash
# Quick test script for logging fix verification

set -e

echo "=========================================="
echo "Quick Logging Fix Test"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_passed=0
test_failed=0

run_test() {
    local test_name="$1"
    local command="$2"
    
    echo -e "${YELLOW}Running:${NC} $test_name"
    echo "Command: $command"
    
    if eval "$command" 2>&1 | tee /tmp/test_output.log | grep -q "WARNING.*Failed to apply advanced logging"; then
        echo -e "${RED}✗ FAILED${NC} - Found duplicate warnings\n"
        ((test_failed++))
    else
        echo -e "${GREEN}✓ PASSED${NC} - No duplicate warnings\n"
        ((test_passed++))
    fi
}

# Test 1: Basic SQL query
run_test "Test 1: Basic SQL" \
    "uv run iptvportal jsonsql sql -q 'SELECT * FROM subscriber LIMIT 1'"

# Test 2: Schema list
run_test "Test 2: Schema list" \
    "uv run iptvportal jsonsql schema list"

# Test 3: With log level flag
run_test "Test 3: --log-level flag" \
    "uv run iptvportal --log-level INFO jsonsql sql -q 'SELECT * FROM subscriber LIMIT 1'"

# Test 4: Library usage
run_test "Test 4: Library usage" \
    "uv run python test_logging_fix.py"

echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $test_passed${NC}"
echo -e "${RED}Failed: $test_failed${NC}"
echo ""

if [ $test_failed -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Review PR #73: https://github.com/pv-udpv/iptvportal-client/pull/73"
    echo "2. Merge the PR"
    echo "3. Close issue #70"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    echo "Please review the output above."
    exit 1
fi
