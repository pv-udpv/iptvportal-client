"""CLI interface for SQL to JSONSQL transpiler."""

import argparse
import json
import sys
from pathlib import Path

from .exceptions import TranspilerError
from .transpiler import SQLTranspiler


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Transpile SQL queries to JSONSQL format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Transpile SQL string
  python -m iptvportal.transpiler "SELECT id, name FROM users WHERE age > 18"
  
  # Transpile from file
  python -m iptvportal.transpiler -f query.sql
  
  # Pretty print output
  python -m iptvportal.transpiler -p "SELECT * FROM users LIMIT 10"
  
  # Specify dialect
  python -m iptvportal.transpiler -d mysql "SELECT * FROM users"
        """
    )

    parser.add_argument(
        "query",
        nargs="?",
        help="SQL query to transpile"
    )

    parser.add_argument(
        "-f", "--file",
        type=Path,
        help="Read SQL from file"
    )

    parser.add_argument(
        "-d", "--dialect",
        default="postgres",
        help="SQL dialect (default: postgres)"
    )

    parser.add_argument(
        "-p", "--pretty",
        action="store_true",
        help="Pretty-print JSON output"
    )

    parser.add_argument(
        "-i", "--indent",
        type=int,
        default=2,
        help="Indentation level for pretty-print (default: 2)"
    )

    args = parser.parse_args()

    # Get SQL query
    if args.file:
        try:
            sql = args.file.read_text()
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.query:
        sql = args.query
    else:
        parser.print_help()
        sys.exit(1)

    # Transpile
    try:
        transpiler = SQLTranspiler(dialect=args.dialect)
        result = transpiler.transpile(sql)

        # Output
        if args.pretty:
            print(json.dumps(result, indent=args.indent))
        else:
            print(json.dumps(result))

    except TranspilerError as e:
        print(f"Transpilation error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
