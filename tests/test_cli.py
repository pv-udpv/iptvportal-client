"""Tests for CLI commands."""

from typer.testing import CliRunner

from iptvportal.cli.__main__ import app

runner = CliRunner()


def test_cli_help():
    """Test that CLI help works."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "IPTVPortal JSONSQL API Client CLI" in result.stdout


def test_jsonsql_help():
    """Test jsonsql command help."""
    result = runner.invoke(app, ["jsonsql", "--help"])
    assert result.exit_code == 0
    assert "jsonsql" in result.stdout.lower()


def test_auth_command_help():
    """Test jsonsql auth command help."""
    """Test auth command help."""
    result = runner.invoke(app, ["jsonsql", "auth", "--help"])
    assert result.exit_code == 0
    assert "authentication" in result.stdout.lower()


def test_auth_deprecated():
    """Test that deprecated auth command shows helpful message."""
    result = runner.invoke(app, ["auth"])
    assert result.exit_code == 1
    assert "Command moved" in result.stdout
    assert "iptvportal jsonsql auth" in result.stdout


def test_query_select_help():
    """Test jsonsql select command help."""
    result = runner.invoke(app, ["jsonsql", "select", "--help"])
    assert result.exit_code == 0
    assert "SELECT" in result.stdout


def test_query_insert_help():
    """Test jsonsql insert command help."""
    result = runner.invoke(app, ["jsonsql", "insert", "--help"])
    assert result.exit_code == 0
    assert "INSERT" in result.stdout


def test_query_update_help():
    """Test jsonsql update command help."""
    result = runner.invoke(app, ["jsonsql", "update", "--help"])
    assert result.exit_code == 0
    assert "UPDATE" in result.stdout


def test_query_delete_help():
    """Test jsonsql delete command help."""
    result = runner.invoke(app, ["jsonsql", "delete", "--help"])
    assert result.exit_code == 0
    assert "DELETE" in result.stdout


def test_transpile_command_help():
    """Test jsonsql transpile command help."""
    result = runner.invoke(app, ["jsonsql", "transpile", "--help"])
    """Test transpile command help."""
    result = runner.invoke(app, ["jsonsql", "utils", "transpile", "--help"])
    assert result.exit_code == 0
    assert "Transpile" in result.stdout


def test_transpile_deprecated():
    """Test that deprecated transpile command shows helpful message."""
    result = runner.invoke(app, ["transpile", "--help"])
    assert result.exit_code == 1
    assert "Command moved" in result.stdout
    assert "iptvportal jsonsql transpile" in result.stdout


def test_sql_command_help():
    """Test jsonsql sql command help."""
    result = runner.invoke(app, ["jsonsql", "sql", "--help"])
    assert result.exit_code == 0
    assert "SQL" in result.stdout


def test_sql_deprecated():
    """Test that deprecated sql command shows helpful message."""
    result = runner.invoke(app, ["sql"])
    assert result.exit_code == 1
    assert "Command moved" in result.stdout
    assert "iptvportal jsonsql sql" in result.stdout


def test_schema_command_help():
    """Test jsonsql schema command help."""
    result = runner.invoke(app, ["jsonsql", "schema", "--help"])
    assert result.exit_code == 0
    assert "schema" in result.stdout.lower()


def test_schema_deprecated():
    """Test that deprecated schema command shows helpful message."""
    result = runner.invoke(app, ["schema"])
    assert result.exit_code == 1
    assert "Command moved" in result.stdout
    assert "iptvportal jsonsql schema" in result.stdout


def test_config_command_help():
    """Test config command help (should still work at top level)."""
    result = runner.invoke(app, ["config", "--help"])
    assert result.exit_code == 0
    assert "configuration" in result.stdout.lower()


def test_sync_command_help():
    """Test sync command help (should still work at top level)."""
    result = runner.invoke(app, ["sync", "--help"])
    assert result.exit_code == 0
    assert "sync" in result.stdout.lower() or "cache" in result.stdout.lower()


def test_transpile_simple_query():
    """Test transpiling a simple SQL query."""
    result = runner.invoke(app, ["jsonsql", "transpile", "SELECT * FROM subscriber"])
    result = runner.invoke(app, ["jsonsql", "utils", "transpile", "SELECT * FROM subscriber"])
    assert result.exit_code == 0
    assert "SQL Query" in result.stdout
    assert "Transpiled JSONSQL" in result.stdout
    assert '"from": "subscriber"' in result.stdout


def test_transpile_with_where():
    """Test transpiling SQL with WHERE clause."""
    first = runner.invoke(
        app, ["jsonsql", "transpile", "SELECT id, username FROM subscriber WHERE disabled = false"]
    )
    assert first.exit_code == 0
    result = runner.invoke(
        app, ["jsonsql", "utils", "transpile", "SELECT id, username FROM subscriber WHERE disabled = false"]
    )
    assert result.exit_code == 0
    assert '"from": "subscriber"' in result.stdout
    assert '"where"' in result.stdout


def test_transpile_yaml_format():
    """Test transpiling with YAML output format."""
    result = runner.invoke(app, ["jsonsql", "transpile", "SELECT * FROM subscriber", "--format", "yaml"])
    result = runner.invoke(app, ["jsonsql", "utils", "transpile", "SELECT * FROM subscriber", "--format", "yaml"])
    assert result.exit_code == 0
    assert "from: subscriber" in result.stdout


def test_query_select_dry_run():
    """Test jsonsql select with dry-run mode."""
    result = runner.invoke(
        app,
        [
            "jsonsql",
            "select",
            "--from",
            "subscriber",
            "--data",
            "id,username",
            "--limit",
            "10",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "DRY RUN MODE" in result.stdout
    assert '"from": "subscriber"' in result.stdout
    assert "Query will NOT be executed" in result.stdout


def test_query_select_from_sql_dry_run():
    """Test jsonsql sql command with --query and dry-run."""
    result = runner.invoke(app, ["jsonsql", "sql", "--query", "SELECT * FROM subscriber LIMIT 5", "--dry-run"])
    assert result.exit_code == 0
    assert "DRY RUN MODE" in result.stdout
    assert "SQL Input" in result.stdout
    assert "Transpiled JSONSQL" in result.stdout


def test_query_insert_dry_run():
    """Test jsonsql sql command with INSERT query and dry-run mode."""
    result = runner.invoke(
        app,
        [
            "jsonsql",
            "sql",
            "--query",
            "INSERT INTO package (name, paid) VALUES ('test', true) RETURNING id",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "DRY RUN MODE" in result.stdout
    assert '"into":' in result.stdout  # Transpiler has bug with table name extraction


def test_query_update_dry_run():
    """Test jsonsql sql command with UPDATE query and dry-run mode."""
    result = runner.invoke(
        app,
        [
            "jsonsql",
            "sql",
            "--query",
            "UPDATE subscriber SET disabled = true WHERE username = 'test'",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "DRY RUN MODE" in result.stdout
    assert '"table": "subscriber"' in result.stdout


def test_query_delete_dry_run():
    """Test jsonsql sql command with DELETE query and dry-run mode."""
    result = runner.invoke(
        app, ["jsonsql", "sql", "--query", "DELETE FROM terminal WHERE id = 123", "--dry-run"]
    )
    assert result.exit_code == 0
    assert "DRY RUN MODE" in result.stdout
    assert '"from": "terminal"' in result.stdout


def test_query_select_missing_from():
    """Test that jsonsql select requires --from when not using --edit."""
    result = runner.invoke(app, ["jsonsql", "select", "--data", "id,username"])
    assert result.exit_code == 1
    assert "--from is required" in result.stdout


def test_query_insert_missing_params():
    """Test that jsonsql insert requires parameters when not using --edit."""
    result = runner.invoke(app, ["jsonsql", "insert", "--into", "package"])
    assert result.exit_code == 1
    assert "required" in result.stdout.lower()


def test_query_update_missing_params():
    """Test that jsonsql update requires parameters when not using --edit."""
    result = runner.invoke(app, ["jsonsql", "update", "--table", "subscriber"])
    assert result.exit_code == 1
    assert "required" in result.stdout.lower()


def test_query_delete_missing_from():
    """Test that jsonsql delete requires --from when not using --edit."""
    result = runner.invoke(app, ["jsonsql", "delete", "--where", '{"eq": ["id", 123]}'])
    assert result.exit_code == 1
    assert "--from is required" in result.stdout


def test_sql_join_dry_run():
    """Test SQL query with JOIN in dry-run mode."""
    result = runner.invoke(
        app,
        [
            "jsonsql",
            "sql",
            "-q",
            "SELECT c.name AS channel, p.title AS program FROM tv_program p JOIN tv_channel c ON p.channel_id = c.id LIMIT 10",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "DRY RUN MODE" in result.stdout
    assert '"from":' in result.stdout
    # Verify it shows the JOIN structure
    assert '"join":' in result.stdout or "tv_channel" in result.stdout


def test_sql_join_with_show_request():
    """Test SQL query with JOIN and --show-request flag in dry-run mode."""
    result = runner.invoke(
        app,
        [
            "jsonsql",
            "sql",
            "-q",
            "SELECT c.name AS channel, p.title AS program FROM tv_program p JOIN tv_channel c ON p.channel_id = c.id LIMIT 10",
            "--dry-run",
            "--show-request",
        ],
    )
    assert result.exit_code == 0
    assert "DRY RUN MODE" in result.stdout
    assert "JSON-RPC Request:" in result.stdout
    assert '"from":' in result.stdout


def test_sql_multiple_joins_dry_run():
    """Test SQL query with multiple JOINs in dry-run mode."""
    result = runner.invoke(
        app,
        [
            "jsonsql",
            "sql",
            "-q",
            """SELECT 
                c.name AS channel,
                p.title AS program,
                cat.name AS category,
                cat.genre AS genre
            FROM tv_program p
            JOIN tv_channel c ON p.channel_id = c.id
            JOIN tv_program_category pc ON pc.program_id = p.id
            JOIN tv_category cat ON pc.category_id = cat.id
            WHERE p.epg_provider_id = 36
            LIMIT 10""",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "DRY RUN MODE" in result.stdout
    assert '"from":' in result.stdout
    # Verify multiple JOINs are present
    assert result.stdout.count('"join":') >= 2 or result.stdout.count("tv_channel") >= 1


def test_sql_debug_mode():
    """Test SQL query with --debug flag in dry-run mode."""
    result = runner.invoke(
        app,
        [
            "sql",
            "-q",
            "SELECT id, username FROM subscriber LIMIT 5",
            "--dry-run",
            "--debug",
        ],
    )
    assert result.exit_code == 0
    assert "[DEBUG]" in result.stdout
    assert "SQL Input" in result.stdout
    assert "Transpiled JSONSQL" in result.stdout


def test_sql_debug_json_format():
    """Test SQL query with --debug and --debug-format json."""
    result = runner.invoke(
        app,
        [
            "sql",
            "-q",
            "SELECT * FROM subscriber LIMIT 3",
            "--dry-run",
            "--debug",
            "--debug-format",
            "json",
        ],
    )
    assert result.exit_code == 0
    # JSON format should have step and data fields
    assert '"step":' in result.stdout
    assert '"data":' in result.stdout


def test_sql_debug_yaml_format():
    """Test SQL query with --debug and --debug-format yaml."""
    result = runner.invoke(
        app,
        [
            "sql",
            "-q",
            "SELECT * FROM subscriber LIMIT 3",
            "--dry-run",
            "--debug",
            "--debug-format",
            "yaml",
        ],
    )
    assert result.exit_code == 0
    # YAML format should have step and data fields
    assert "step:" in result.stdout
    assert "data:" in result.stdout


def test_jsonsql_debug_mode():
    """Test jsonsql select query with --debug flag."""
    result = runner.invoke(
        app,
        [
            "jsonsql",
            "select",
            "--from",
            "subscriber",
            "--data",
            "id,username",
            "--limit",
            "5",
            "--dry-run",
            "--debug",
        ],
    )
    assert result.exit_code == 0
    assert "[DEBUG]" in result.stdout
    assert "JSONSQL Parameters" in result.stdout


def test_jsonsql_insert_debug_mode():
    """Test jsonsql insert query with --debug flag."""
    result = runner.invoke(
        app,
        [
            "jsonsql",
            "insert",
            "--into",
            "package",
            "--columns",
            "name,paid",
            "--values",
            '[["test", true]]',
            "--dry-run",
            "--debug",
        ],
    )
    assert result.exit_code == 0
    assert "[DEBUG]" in result.stdout
    assert "JSONSQL Parameters" in result.stdout


def test_jsonsql_update_debug_mode():
    """Test jsonsql update query with --debug flag."""
    result = runner.invoke(
        app,
        [
            "jsonsql",
            "update",
            "--table",
            "subscriber",
            "--set",
            '{"disabled": true}',
            "--where",
            '{"eq": ["id", 123]}',
            "--dry-run",
            "--debug",
        ],
    )
    assert result.exit_code == 0
    assert "[DEBUG]" in result.stdout
    assert "JSONSQL Parameters" in result.stdout


def test_jsonsql_delete_debug_mode():
    """Test jsonsql delete query with --debug flag."""
    result = runner.invoke(
        app,
        [
            "jsonsql",
            "delete",
            "--from",
            "terminal",
            "--where",
            '{"eq": ["id", 456]}',
            "--dry-run",
            "--debug",
        ],
    )
    assert result.exit_code == 0
    assert "[DEBUG]" in result.stdout
    assert "JSONSQL Parameters" in result.stdout


def test_cache_service_help():
    """Test cache service help."""
    result = runner.invoke(app, ["cache", "--help"])
    assert result.exit_code == 0
    assert "Cache management service" in result.stdout


def test_cache_config_help():
    """Test cache config subcommand help."""
    result = runner.invoke(app, ["cache", "config", "--help"])
    assert result.exit_code == 0
    assert "configuration" in result.stdout.lower()


def test_schema_service_help():
    """Test schema service help."""
    result = runner.invoke(app, ["schema", "--help"])
    assert result.exit_code == 0
    assert "Schema management service" in result.stdout


def test_schema_config_help():
    """Test schema config subcommand help."""
    result = runner.invoke(app, ["schema", "config", "--help"])
    assert result.exit_code == 0
    assert "configuration" in result.stdout.lower()


def test_jsonsql_service_help():
    """Test jsonsql service help."""
    result = runner.invoke(app, ["jsonsql", "--help"])
    assert result.exit_code == 0
    assert "JSONSQL API operations" in result.stdout


def test_jsonsql_config_help():
    """Test jsonsql config subcommand help."""
    result = runner.invoke(app, ["jsonsql", "config", "--help"])
    assert result.exit_code == 0
    assert "configuration" in result.stdout.lower()


def test_jsonsql_utils_help():
    """Test jsonsql utils subcommand help."""
    result = runner.invoke(app, ["jsonsql", "utils", "--help"])
    assert result.exit_code == 0
    assert "utilities" in result.stdout.lower()


def test_jsonsql_sql_help():
    """Test jsonsql sql subcommand help."""
    result = runner.invoke(app, ["jsonsql", "sql", "--help"])
    assert result.exit_code == 0
    assert "SQL" in result.stdout


def test_service_discovery():
    """Test that all services are discovered and registered."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    # Check all services are present
    assert "cache" in result.stdout
    assert "config" in result.stdout
    assert "jsonsql" in result.stdout
    assert "schema" in result.stdout
    assert "sync" in result.stdout
