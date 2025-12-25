# Testing Guide for Logging and Rich Table Fixes

This guide helps verify the fixes for issues #70 (duplicate logging warnings) and #71 (Rich table ellipsis).

## Prerequisites

```bash
# Checkout the fix branch
git checkout fix/logging-and-rich-table-issues

# Create/activate virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install in development mode
uv pip install -e ".[cli,dev]"
```

## Test 1: Logging Configuration

### 1.1 Verify No Duplicate Warnings

**Expected**: Single `INFO:iptvportal:Logging configured` or no logging setup messages

```bash
# Basic query - should see ONE logging message or none
iptvportal jsonsql sql -q "SELECT * FROM tv_channel LIMIT 10"

# With debug logging
iptvportal --log-level DEBUG jsonsql sql -q "SELECT * FROM subscriber LIMIT 5"

# With verbose flag
iptvportal -v iptvportal jsonsql sql -q "SELECT * FROM media LIMIT 3"
```

### 1.2 Test Silent Mode

**Expected**: No logging configuration messages at all

```bash
# Enable silent mode
export IPTVPORTAL_LOGGING_SILENT=1
iptvportal jsonsql sql -q "SELECT * FROM terminal LIMIT 5"

# Clean up
unset IPTVPORTAL_LOGGING_SILENT
```

### 1.3 Test CLI Logging Options

**Expected**: CLI flags override default config without duplicate warnings

```bash
# Global log level
iptvportal --log-level WARNING jsonsql sql -q "SELECT * FROM subscriber LIMIT 5"

# Per-module verbose
iptvportal -v httpx jsonsql sql -q "SELECT * FROM media LIMIT 3"

# Per-module quiet
iptvportal -q iptvportal.core jsonsql sql -q "SELECT * FROM terminal LIMIT 5"

# Multiple module overrides
iptvportal -v httpx -q iptvportal.cli jsonsql sql -q "SELECT * FROM media LIMIT 5"
```

### 1.4 Test Reconfiguration

**Expected**: Explicit reconfiguration works without duplicate messages

```python
# In Python REPL
import logging
from iptvportal.config import setup_logging, reconfigure_logging

# First setup (should configure)
setup_logging()

# Second setup (should skip - idempotent)
setup_logging()

# Force reconfiguration
setup_logging(force=True)

# Reconfigure from active config
reconfigure_logging()
```

## Test 2: Rich Table Display

### 2.1 Verify Full Data Display

**Expected**: Tables show full data without ellipsis (`…`), with text wrapping

```bash
# Basic table output
iptvportal jsonsql sql -q "SELECT * FROM tv_channel LIMIT 10"

# With show-request flag
iptvportal jsonsql sql -e --show-request

# Specific columns
iptvportal jsonsql sql -q "SELECT id, username, created_at FROM subscriber LIMIT 10"
```

### 2.2 Test Terminal Width Detection

**Expected**: Tables adapt to terminal width, show warning if too narrow

```bash
# Check detected width
python3 -c "from rich.console import Console; c=Console(); print(f'Terminal: {c.width}x{c.height}')"

# Normal width (should work well)
iptvportal jsonsql sql -q "SELECT * FROM media LIMIT 10"

# Force narrow terminal (should show warning)
export COLUMNS=80
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 10"
unset COLUMNS

# Force very narrow (should suggest JSON/YAML)
export COLUMNS=60
iptvportal jsonsql sql -q "SELECT * FROM tv_channel LIMIT 10"
unset COLUMNS
```

### 2.3 Test Different Output Formats

**Expected**: JSON and YAML formats work as expected

```bash
# JSON format
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 5" --format json

# YAML format
iptvportal jsonsql sql -q "SELECT * FROM terminal LIMIT 5" --format yaml

# Table format (default)
iptvportal jsonsql sql -q "SELECT * FROM media LIMIT 5" --format table
```

### 2.4 Test Wide Tables

**Expected**: Many columns wrap gracefully, no ellipsis truncation

```bash
# Select all columns from a wide table
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 5"

# Many columns with long text
iptvportal jsonsql sql -q "SELECT id, username, email, description, created_at, updated_at FROM media LIMIT 5"
```

## Test 3: Edge Cases

### 3.1 Empty Results

**Expected**: Shows "No results" message in yellow

```bash
iptvportal jsonsql sql -q "SELECT * FROM subscriber WHERE id = 999999"
```

### 3.2 Large Result Sets

**Expected**: Tables render smoothly without hanging

```bash
# 100 rows
iptvportal jsonsql sql -q "SELECT * FROM tv_channel LIMIT 100"

# With pagination (if supported)
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 50 OFFSET 100"
```

### 3.3 Special Characters

**Expected**: Unicode and special chars display correctly

```bash
# UTF-8 content
iptvportal jsonsql sql -q "SELECT id, name FROM tv_channel WHERE name LIKE '%Россия%' LIMIT 10"
```

### 3.4 NULL Values

**Expected**: NULLs render as empty string or "None"

```bash
iptvportal jsonsql sql -q "SELECT id, username, email FROM subscriber WHERE email IS NULL LIMIT 10"
```

## Test 4: Integration Tests

### 4.1 Full CLI Workflow

```bash
# 1. Start with editor mode
iptvportal jsonsql sql -e
# Enter: SELECT * FROM tv_channel LIMIT 5
# Save and exit

# 2. Check with show-request
iptvportal jsonsql sql -q "SELECT * FROM media LIMIT 10" --show-request

# 3. Try different formats
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 10" -f json
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 10" -f yaml
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 10" -f table

# 4. Test with debug mode
iptvportal jsonsql sql -q "SELECT * FROM terminal LIMIT 5" --debug
```

### 4.2 Python API Usage

```python
# Test programmatic usage
from iptvportal import IPTVPortalClient
from iptvportal.cli.formatters import format_table

# Create client
client = IPTVPortalClient.from_config()

# Execute query
result = client.select(
    data=["id", "username"],
    from_="subscriber",
    limit=10
)

# Display with formatter
format_table(result.data, title="Subscribers")
```

## Diagnostic Commands

### Check Logging State

```python
import logging
from iptvportal.config.logging import _LOGGING_CONFIGURED

print(f"Logging configured: {_LOGGING_CONFIGURED}")
print(f"Root logger handlers: {logging.getLogger().handlers}")
print(f"iptvportal logger: {logging.getLogger('iptvportal').level}")
```

### Check Console Properties

```python
from rich.console import Console
import os

console = Console()
print(f"Width: {console.width}")
print(f"Height: {console.height}")
print(f"COLUMNS env: {os.environ.get('COLUMNS', 'not set')}")
print(f"Is terminal: {console.is_terminal}")
```

### Check Table Rendering

```python
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

# Test data
data = [
    {"id": 1, "name": "Test 1", "description": "A" * 50},
    {"id": 2, "name": "Test 2", "description": "B" * 50},
]

table = Table(expand=True, box=box.SIMPLE)
for col in data[0].keys():
    table.add_column(col, overflow="fold", no_wrap=False, max_width=30)

for row in data:
    table.add_row(*[str(v) for v in row.values()])

console.print(table)
```

## Expected Results Summary

### ✅ Pass Criteria

1. **Logging**:
   - ✅ No duplicate warning messages
   - ✅ Single "Logging configured" info or silence with env var
   - ✅ CLI flags work without triggering re-init warnings
   - ✅ Explicit `force=True` reconfiguration works

2. **Rich Tables**:
   - ✅ Full data visible without `…` ellipsis
   - ✅ Tables expand to terminal width
   - ✅ Long text wraps instead of truncating
   - ✅ Narrow terminals show helpful warning
   - ✅ JSON/YAML formats unaffected

### ❌ Fail Indicators

1. **Logging**:
   - ❌ Multiple identical warning messages
   - ❌ Warnings on every CLI invocation
   - ❌ `basicConfig()` failures with handlers already present

2. **Rich Tables**:
   - ❌ Ellipsis (`…`) in table cells
   - ❌ Data truncation without wrapping
   - ❌ Tables not expanding to terminal width
   - ❌ Hard crash on narrow terminals

## Troubleshooting

### Issue: Still seeing duplicate warnings

```bash
# Check if old .pyc files cached
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

# Reinstall
pip uninstall iptvportal-client -y
pip install -e ".[cli,dev]"
```

### Issue: Tables still showing ellipsis

```bash
# Check terminal width
echo "COLUMNS: $COLUMNS"
tput cols

# Force remove COLUMNS
unset COLUMNS
export TERM=xterm-256color

# Test again
iptvportal jsonsql sql -q "SELECT * FROM tv_channel LIMIT 10"
```

### Issue: Import errors

```bash
# Check rich installation
pip show rich

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## Reporting Issues

If tests fail, report with:

1. Python version: `python --version`
2. Terminal: `echo $TERM`
3. Terminal size: `tput cols && tput lines`
4. OS: `uname -a`
5. Full command and output
6. Logs with `--debug` flag

## Success Checklist

- [ ] No duplicate logging warnings in any command
- [ ] Tables display full data without ellipsis
- [ ] Terminal width detected correctly
- [ ] Text wraps in table cells
- [ ] Narrow terminal shows warning
- [ ] Silent mode works (`IPTVPORTAL_LOGGING_SILENT=1`)
- [ ] CLI logging flags work without side effects
- [ ] JSON/YAML formats unaffected
- [ ] Editor mode works
- [ ] Debug mode works
- [ ] No new errors or crashes
