# CLI Command Reorganization

## Overview

The IPTVPortal CLI has been reorganized to provide a clearer logical structure by grouping all API operations under the `jsonsql` namespace, while keeping infrastructure commands at the top level.

## Rationale

**Before:** Commands were mixed at the top level, making it unclear which commands interact with the API vs manage local client state.

**After:** Clear separation:
- **API operations** → under `iptvportal jsonsql` (auth, sql, transpile, schema, select/insert/update/delete)
- **Infrastructure** → top-level `iptvportal` (config, sync, cache)

This makes the CLI more intuitive and aligns the command structure with the logical separation of concerns.

## Command Changes

### API Operations (moved under jsonsql)

| Old Command | New Command | Status |
|------------|-------------|---------|
| `iptvportal auth` | `iptvportal jsonsql auth` | ✅ Deprecated with helpful message |
| `iptvportal sql` | `iptvportal jsonsql sql` | ✅ Deprecated with helpful message |
| `iptvportal transpile` | `iptvportal jsonsql transpile` | ✅ Deprecated with helpful message |
| `iptvportal schema` | `iptvportal jsonsql schema` | ✅ Deprecated with helpful message |
| `iptvportal jsonsql select` | `iptvportal jsonsql select` | ✅ No change (already under jsonsql) |
| `iptvportal jsonsql insert` | `iptvportal jsonsql insert` | ✅ No change (already under jsonsql) |
| `iptvportal jsonsql update` | `iptvportal jsonsql update` | ✅ No change (already under jsonsql) |
| `iptvportal jsonsql delete` | `iptvportal jsonsql delete` | ✅ No change (already under jsonsql) |

### Infrastructure Commands (unchanged)

| Command | Status |
|---------|--------|
| `iptvportal config` | ✅ No change |
| `iptvportal sync` | ✅ No change |
| `iptvportal cache` | ✅ No change |

### Schema Command Simplification

The `schema list` and `schema show` commands have been merged:

| Old Command | New Command | Description |
|------------|-------------|-------------|
| `iptvportal schema list` | `iptvportal jsonsql schema show` | List all schemas (no argument) |
| `iptvportal schema show TABLE` | `iptvportal jsonsql schema show TABLE` | Show specific table schema |

The old `schema list` command still works but shows a deprecation message.

## Migration Examples

### Authentication

**Old:**
```bash
iptvportal auth
iptvportal auth --renew
```

**New:**
```bash
iptvportal jsonsql auth
iptvportal jsonsql auth --renew
```

### SQL Queries

**Old:**
```bash
iptvportal sql -q "SELECT * FROM subscriber LIMIT 10"
iptvportal sql --edit
iptvportal sql -q "SELECT * FROM subscriber" --dry-run
```

**New:**
```bash
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 10"
iptvportal jsonsql sql --edit
iptvportal jsonsql sql -q "SELECT * FROM subscriber" --dry-run
```

### Transpilation

**Old:**
```bash
iptvportal transpile "SELECT * FROM subscriber"
iptvportal transpile "SELECT * FROM subscriber" --format yaml
```

**New:**
```bash
iptvportal jsonsql transpile "SELECT * FROM subscriber"
iptvportal jsonsql transpile "SELECT * FROM subscriber" --format yaml
```

### Schema Management

**Old:**
```bash
iptvportal schema list
iptvportal schema show subscriber
iptvportal schema introspect tv_channel
```

**New:**
```bash
iptvportal jsonsql schema show              # list all schemas
iptvportal jsonsql schema show subscriber   # show specific table
iptvportal jsonsql schema introspect tv_channel
```

### Infrastructure Commands (no change)

```bash
# These remain unchanged
iptvportal config init
iptvportal config show
iptvportal sync init
iptvportal sync status
```

## Backwards Compatibility

Old commands are deprecated but still work with helpful migration messages:

```bash
$ iptvportal auth
Command moved: iptvportal auth → iptvportal jsonsql auth
Run: iptvportal jsonsql auth
```

```bash
$ iptvportal sql -q "SELECT * FROM subscriber"
Command moved: iptvportal sql → iptvportal jsonsql sql
Run: iptvportal jsonsql sql --query 'SELECT ...'
```

```bash
$ iptvportal transpile "SELECT * FROM subscriber"
Command moved: iptvportal transpile → iptvportal jsonsql transpile
Run: iptvportal jsonsql transpile <sql>
```

```bash
$ iptvportal schema list
Command moved: iptvportal schema → iptvportal jsonsql schema
Run: iptvportal jsonsql schema show
```

## New Command Hierarchy

```
iptvportal
├── config                    # Configuration management
│   ├── init
│   ├── show
│   └── conf
├── sync                      # Cache management
│   ├── init
│   ├── status
│   ├── tables
│   ├── clear
│   └── stats
├── cache                     # Cache utilities
│   └── clear
└── jsonsql                   # API operations
    ├── auth                  # Authentication (moved from top-level)
    ├── sql                   # SQL queries (moved from top-level)
    │   ├── --query/-q
    │   ├── --edit/-e
    │   ├── --dry-run
    │   └── --show-request
    ├── transpile            # SQL → JSONSQL (moved from top-level)
    ├── schema               # Schema management (moved from top-level)
    │   ├── show            # Merged list + show
    │   ├── introspect
    │   ├── from-sql
    │   ├── export
    │   ├── import
    │   ├── validate
    │   ├── validate-mapping
    │   ├── generate-models
    │   └── clear
    ├── select               # Native JSONSQL (no change)
    ├── insert               # Native JSONSQL (no change)
    ├── update               # Native JSONSQL (no change)
    └── delete               # Native JSONSQL (no change)
```

## Benefits

1. **Clearer Organization**: API operations are clearly separated from infrastructure commands
2. **Logical Grouping**: All JSONSQL-related commands are in one place
3. **Consistency**: Native JSONSQL commands (select/insert/update/delete) are now siblings with SQL and transpile commands
4. **Maintainability**: Easier to add new API operations under the jsonsql namespace
5. **Backwards Compatible**: Old commands still work with helpful migration messages

## Implementation Details

### Code Changes

1. **`src/iptvportal/cli/__main__.py`**:
   - Removed direct registration of auth, sql, transpile, schema commands
   - Now only registers config, sync, cache, and jsonsql at top level
   - Added hidden deprecated command stubs with helpful error messages

2. **`src/iptvportal/cli/commands/jsonsql.py`**:
   - Added `_register_subcommands()` function to register auth, sql, transpile, schema as subcommands
   - Updated help text to reflect broader scope

3. **`src/iptvportal/cli/commands/schema.py`**:
   - Merged `list` and `show` commands into a single `show` command with optional table argument
   - Added hidden deprecated `list` command for backwards compatibility

4. **Documentation**:
   - Updated all command examples in README.md
   - Updated docs/cli.md with new hierarchy overview
   - Updated docs/authentication.md, docs/ENV_VAR_AUTH.md, docs/schema.md
   - All command examples now use new paths

5. **Tests**:
   - Updated all test cases to use new command paths
   - Added tests for deprecation warnings
   - Verified all commands work with new hierarchy

## Testing

All existing functionality is preserved. Tests have been updated to reflect the new command structure:

- ✅ Authentication commands work under jsonsql
- ✅ SQL commands work under jsonsql  
- ✅ Transpile commands work under jsonsql
- ✅ Schema commands work under jsonsql
- ✅ Native JSONSQL commands (select/insert/update/delete) continue to work
- ✅ Config commands remain at top level
- ✅ Sync commands remain at top level
- ✅ Deprecated commands show helpful migration messages
- ✅ Schema show/list merge works correctly

## Questions?

If you have questions about the reorganization or need help migrating your scripts, please:
1. Check the migration examples above
2. Run the old command to see the migration message
3. Refer to the updated documentation in README.md and docs/cli.md
4. Open an issue if you encounter any problems
