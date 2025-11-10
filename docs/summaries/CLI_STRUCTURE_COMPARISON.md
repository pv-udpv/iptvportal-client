CLI COMMAND STRUCTURE - BEFORE vs AFTER
========================================

BEFORE (Flat Structure):
------------------------
iptvportal/
├── auth                    ← Mixed at top level
├── transpile              ← Mixed at top level
├── sql                    ← Mixed at top level
├── schema                 ← Mixed at top level
├── config                 ← Infrastructure
├── sync                   ← Infrastructure
├── cache                  ← Infrastructure
└── jsonsql                ← Only native JSONSQL operations
    ├── select
    ├── insert
    ├── update
    └── delete

Issues:
- Unclear which commands interact with API vs manage local state
- Inconsistent grouping (some API ops at top, others under jsonsql)
- Hard to discover related commands


AFTER (Hierarchical Structure):
--------------------------------
iptvportal/
├── config                      [INFRASTRUCTURE - Top Level]
│   ├── init
│   ├── show
│   └── conf
├── sync                        [INFRASTRUCTURE - Top Level]
│   ├── init
│   ├── status
│   ├── tables
│   ├── clear
│   └── stats
├── cache                       [INFRASTRUCTURE - Top Level]
│   └── clear
└── jsonsql                     [API OPERATIONS - Grouped]
    ├── auth                    ← Moved from top level
    ├── sql                     ← Moved from top level
    │   ├── --query/-q
    │   ├── --edit/-e
    │   ├── --dry-run
    │   └── --show-request
    ├── transpile              ← Moved from top level
    ├── schema                 ← Moved from top level
    │   ├── show (merged list + show)
    │   ├── introspect
    │   ├── from-sql
    │   ├── export
    │   ├── import
    │   ├── validate
    │   ├── validate-mapping
    │   ├── generate-models
    │   └── clear
    ├── select                 ← Already here (no change)
    ├── insert                 ← Already here (no change)
    ├── update                 ← Already here (no change)
    └── delete                 ← Already here (no change)

Benefits:
✓ Clear separation: API operations vs infrastructure
✓ Logical grouping: All JSONSQL operations together
✓ Consistent: SQL, transpile, schema alongside select/insert/update/delete
✓ Discoverable: Related commands are grouped
✓ Maintainable: Easy to add new API operations


MIGRATION EXAMPLES:
===================

Authentication:
OLD: iptvportal auth
NEW: iptvportal jsonsql auth

SQL Queries:
OLD: iptvportal sql -q "SELECT * FROM subscriber"
NEW: iptvportal jsonsql sql -q "SELECT * FROM subscriber"

Transpilation:
OLD: iptvportal transpile "SELECT * FROM subscriber"
NEW: iptvportal jsonsql transpile "SELECT * FROM subscriber"

Schema Management:
OLD: iptvportal schema list
OLD: iptvportal schema show subscriber
NEW: iptvportal jsonsql schema show              (list all)
NEW: iptvportal jsonsql schema show subscriber   (show specific)

Infrastructure (No Change):
iptvportal config init        ← Same
iptvportal sync status        ← Same


BACKWARDS COMPATIBILITY:
========================

All old commands still work but show helpful messages:

$ iptvportal auth
Command moved: iptvportal auth → iptvportal jsonsql auth
Run: iptvportal jsonsql auth

$ iptvportal sql -q "SELECT ..."
Command moved: iptvportal sql → iptvportal jsonsql sql
Run: iptvportal jsonsql sql --query 'SELECT ...'

$ iptvportal transpile "SELECT ..."
Command moved: iptvportal transpile → iptvportal jsonsql transpile
Run: iptvportal jsonsql transpile <sql>

$ iptvportal schema list
Command moved: iptvportal schema → iptvportal jsonsql schema
Run: iptvportal jsonsql schema show
