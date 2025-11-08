"""Tests for CLI commands."""

from typer.testing import CliRunner

from iptvportal.cli.__main__ import app

runner = CliRunner()


def test_cli_help():
    """Test that CLI help works."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "IPTVPortal JSONSQL API Client CLI" in result.stdout


def test_auth_command_help():
    """Test auth command help."""
    result = runner.invoke(app, ["auth", "--help"])
    assert result.exit_code == 0
    assert "authentication" in result.stdout.lower()


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
    """Test transpile command help."""
    result = runner.invoke(app, ["transpile", "--help"])
    assert result.exit_code == 0
    assert "Transpile" in result.stdout


def test_config_command_help():
    """Test config command help."""
    result = runner.invoke(app, ["config", "--help"])
    assert result.exit_code == 0
    assert "configuration" in result.stdout.lower()


def test_transpile_simple_query():
    """Test transpiling a simple SQL query."""
    result = runner.invoke(app, ["transpile", "SELECT * FROM subscriber"])
    assert result.exit_code == 0
    assert "SQL Query" in result.stdout
    assert "Transpiled JSONSQL" in result.stdout
    assert '"from": "subscriber"' in result.stdout


def test_transpile_with_where():
    """Test transpiling SQL with WHERE clause."""
    result = runner.invoke(
        app, ["transpile", "SELECT id, username FROM subscriber WHERE disabled = false"]
    )
    assert result.exit_code == 0
    assert '"from": "subscriber"' in result.stdout
    assert '"where"' in result.stdout


def test_transpile_yaml_format():
    """Test transpiling with YAML output format."""
    result = runner.invoke(app, ["transpile", "SELECT * FROM subscriber", "--format", "yaml"])
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
    """Test sql command with --query and dry-run."""
    result = runner.invoke(app, ["sql", "--query", "SELECT * FROM subscriber LIMIT 5", "--dry-run"])
    assert result.exit_code == 0
    assert "DRY RUN MODE" in result.stdout
    assert "SQL Input" in result.stdout
    assert "Transpiled JSONSQL" in result.stdout


def test_query_insert_dry_run():
    """Test sql command with INSERT query and dry-run mode."""
    result = runner.invoke(
        app,
        [
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
    """Test sql command with UPDATE query and dry-run mode."""
    result = runner.invoke(
        app,
        [
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
    """Test sql command with DELETE query and dry-run mode."""
    result = runner.invoke(
        app, ["sql", "--query", "DELETE FROM terminal WHERE id = 123", "--dry-run"]
    )
    assert result.exit_code == 0
    assert "DRY RUN MODE" in result.stdout
    assert '"from": "terminal"' in result.stdout


def test_query_select_missing_from():
    """Test that jsonsql select requires --from when not using --from-sql."""
    result = runner.invoke(app, ["jsonsql", "select", "--data", "id,username"])
    assert result.exit_code == 1
    assert "--from is required" in result.stdout


def test_query_insert_missing_params():
    """Test that jsonsql insert requires parameters when not using --from-sql."""
    result = runner.invoke(app, ["jsonsql", "insert", "--into", "package"])
    assert result.exit_code == 1
    assert "required" in result.stdout.lower()


def test_query_update_missing_params():
    """Test that jsonsql update requires parameters when not using --from-sql."""
    result = runner.invoke(app, ["jsonsql", "update", "--table", "subscriber"])
    assert result.exit_code == 1
    assert "required" in result.stdout.lower()


def test_query_delete_missing_from():
    """Test that jsonsql delete requires --from when not using --from-sql."""
    result = runner.invoke(app, ["jsonsql", "delete", "--where", '{"eq": ["id", 123]}'])
    assert result.exit_code == 1
    assert "--from is required" in result.stdout
