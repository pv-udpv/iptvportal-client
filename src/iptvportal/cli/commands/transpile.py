"""Transpile command - SQL to JSONSQL conversion."""

from typing import Optional

import typer
from rich.console import Console

from iptvportal.transpiler import SQLTranspiler
from iptvportal.cli.formatters import format_json, format_yaml
from iptvportal.transpiler.exceptions import TranspilerError

console = Console()

def transpile_command(
    sql: str = typer.Argument(..., help="SQL query to transpile"),
    format: str = typer.Option("json", "--format", help="Output format: json, yaml"),
    file: Optional[str] = typer.Option(None, "--file", help="Read SQL from file instead"),
) -> None:
    """
    Transpile SQL query to JSONSQL format (without executing).
    
    Examples:
        iptvportal transpile "SELECT * FROM subscriber"
        iptvportal transpile "SELECT * FROM subscriber WHERE disabled = false" --format yaml
        iptvportal transpile --file query.sql
    """
    try:
        # Read from file if specified
        if file:
            with open(file, "r") as f:
                sql = f.read()
        
        # Transpile SQL to JSONSQL
        transpiler = SQLTranspiler()
        jsonsql = transpiler.transpile(sql)
        
        console.print("\n[bold cyan]SQL Query:[/bold cyan]")
        console.print(sql)
        console.print()
        
        console.print("[bold cyan]Transpiled JSONSQL:[/bold cyan]")
        if format == "yaml":
            format_yaml(jsonsql)
        else:
            format_json(jsonsql)
        
    except FileNotFoundError:
        console.print(f"[bold red]Error:[/bold red] File not found: {file}")
        raise typer.Exit(1)
    except TranspilerError as e:
        console.print(f"[bold red]Transpilation failed:[/bold red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        raise typer.Exit(1)
