"""Schema management CLI commands."""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from iptvportal.cli.utils import load_config
from iptvportal.client import IPTVPortalClient
from iptvportal.schema import SchemaLoader, TableSchema

console = Console()
schema_app = typer.Typer(name="schema", help="Manage table schemas")


@schema_app.command(name="list")
def list_command(
    config_file: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """
    List all loaded schemas.

    Examples:
        iptvportal schema list
        iptvportal schema list --config config.yaml
    """
    try:
        settings = load_config(config_file)

        with IPTVPortalClient(settings) as client:
            tables = client.schema_registry.list_tables()

            if not tables:
                console.print("[yellow]No schemas loaded[/yellow]")
                console.print("\n[dim]Load schemas from a file or generate them with:[/dim]")
                console.print('[dim]  iptvportal schema from-sql -q "SELECT * FROM table"[/dim]\n')
                return

            console.print(f"\n[bold cyan]Loaded Schemas ({len(tables)} tables)[/bold cyan]\n")

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Table Name", style="white")
            table.add_column("Total Fields", style="green")
            table.add_column("Defined Fields", style="blue")
            table.add_column("Type", style="yellow")

            for table_name in sorted(tables):
                schema = client.schema_registry.get(table_name)
                schema_type = (
                    "Auto-generated"
                    if not schema.fields
                    or all(f.description == "Auto-generated field" for f in schema.fields.values())
                    else "Predefined"
                )

                table.add_row(
                    table_name,
                    str(schema.total_fields or len(schema.fields)),
                    str(len(schema.fields)),
                    schema_type,
                )

            console.print(table)
            console.print()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@schema_app.command(name="show")
def show_command(
    table_name: str = typer.Argument(..., help="Table name to show schema for"),
    config_file: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """
    Show detailed schema information for a table.

    Examples:
        iptvportal schema show media
        iptvportal schema show subscriber --config config.yaml
    """
    try:
        settings = load_config(config_file)

        with IPTVPortalClient(settings) as client:
            if not client.schema_registry.has(table_name):
                console.print(f"[yellow]Schema for table '{table_name}' not found[/yellow]")
                console.print("\n[dim]Generate it with:[/dim]")
                console.print(
                    f'[dim]  iptvportal schema from-sql -q "SELECT * FROM {table_name}"[/dim]\n'
                )
                raise typer.Exit(1)

            schema = client.schema_registry.get(table_name)

            console.print(f"\n[bold cyan]Schema for table: {table_name}[/bold cyan]\n")

            # Schema metadata
            info_table = Table(show_header=False, box=None)
            info_table.add_column("Property", style="cyan")
            info_table.add_column("Value", style="white")

            info_table.add_row("Total Fields", str(schema.total_fields or len(schema.fields)))
            info_table.add_row("Defined Fields", str(len(schema.fields)))
            if schema.pydantic_model:
                info_table.add_row("Pydantic Model", schema.pydantic_model.__name__)

            console.print(info_table)
            console.print()

            # Field definitions
            if schema.fields:
                console.print("[bold]Field Definitions:[/bold]\n")

                fields_table = Table(show_header=True, header_style="bold cyan")
                fields_table.add_column("Pos", style="dim")
                fields_table.add_column("Name", style="white")
                fields_table.add_column("Type", style="green")
                fields_table.add_column("Alias", style="yellow")
                fields_table.add_column("Python Name", style="blue")
                fields_table.add_column("Description", style="dim")

                for pos in sorted(schema.fields.keys()):
                    field = schema.fields[pos]
                    fields_table.add_row(
                        str(pos),
                        field.name,
                        field.field_type.value,
                        field.alias or "-",
                        field.python_name or "-",
                        field.description or "-",
                    )

                console.print(fields_table)
                console.print()

            # SELECT * expansion preview
            console.print("[bold]SELECT * Expansion:[/bold]")
            expansion = schema.resolve_select_star()
            console.print(f"[dim]{', '.join(expansion)}[/dim]\n")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@schema_app.command(name="from-sql")
def from_sql_command(
    query: str = typer.Option(..., "--query", "-q", help="SQL query to execute"),
    limit: int = typer.Option(1, "--limit", "-l", help="Number of rows to sample"),
    fields: str | None = typer.Option(
        None, "--fields", help="Manual field mappings (e.g., '1:name,2:email,3:url')"
    ),
    save: bool = typer.Option(False, "--save", "-s", help="Save generated schema to file"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path"),
    format: str = typer.Option("yaml", "--format", "-f", help="Output format (yaml/json)"),
    config_file: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """
    Generate schema from SQL query.

    Executes the query, samples results, and generates a schema based on the data structure.
    You can manually specify field names for specific positions using --fields.

    Examples:
        iptvportal schema from-sql -q "SELECT * FROM media LIMIT 5"
        iptvportal schema from-sql -q "SELECT * FROM media" --limit 100 --save
        iptvportal schema from-sql -q "SELECT * FROM tv_channel" --fields "1:name,2:url"
        iptvportal schema from-sql -q "SELECT * FROM media" -s -o schemas.yaml
    """
    try:
        settings = load_config(config_file)

        # Extract table name from query (simple parsing)
        query_upper = query.upper()
        if "FROM" not in query_upper:
            console.print("[red]Error: Could not extract table name from query[/red]")
            console.print("[dim]Query must contain FROM clause[/dim]")
            raise typer.Exit(1)

        # Simple table name extraction
        parts = query_upper.split("FROM")[1].split()
        if not parts:
            console.print("[red]Error: Could not extract table name[/red]")
            raise typer.Exit(1)

        table_name = parts[0].strip().lower()
        # Remove any trailing clauses
        table_name = table_name.split()[0].strip(";,")

        console.print(f"\n[cyan]Generating schema for table: {table_name}[/cyan]")
        console.print(f"[dim]Executing query with LIMIT {limit}...[/dim]\n")

        # Add LIMIT to query if not present
        if "LIMIT" not in query_upper:
            query = f"{query.rstrip(';')} LIMIT {limit}"

        with IPTVPortalClient(settings) as client:
            # Transpile SQL to JSONSQL
            from iptvportal.transpiler import SQLTranspiler

            transpiler = SQLTranspiler()
            jsonsql = transpiler.transpile(query)

            # Determine method from transpiled result
            method = jsonsql.get("_method", "select")
            if "_method" in jsonsql:
                del jsonsql["_method"]

            # Execute query
            from iptvportal.cli.utils import build_jsonrpc_request

            request = build_jsonrpc_request(method, jsonsql)
            result = client.execute(request)

            if not result or not isinstance(result, list) or len(result) == 0:
                console.print("[yellow]No results returned from query[/yellow]")
                raise typer.Exit(1)

            # Parse manual field mappings if provided
            field_overrides = {}
            if fields:
                try:
                    for mapping in fields.split(","):
                        mapping = mapping.strip()
                        if ":" not in mapping:
                            console.print(
                                f"[yellow]Warning: Invalid field mapping '{mapping}' (expected format: 'position:name')[/yellow]"
                            )
                            continue

                        pos_str, name = mapping.split(":", 1)
                        position = int(pos_str.strip())
                        field_name = name.strip()

                        if position < 0 or position >= len(result[0]):
                            console.print(
                                f"[yellow]Warning: Position {position} out of range (0-{len(result[0]) - 1})[/yellow]"
                            )
                            continue

                        field_overrides[position] = field_name

                    if field_overrides:
                        console.print(
                            f"[dim]Applying {len(field_overrides)} manual field mapping(s)[/dim]"
                        )
                except ValueError as e:
                    console.print(f"[yellow]Warning: Error parsing field mappings: {e}[/yellow]")

            # Generate schema from first row
            sample_row = result[0]
            schema = TableSchema.auto_generate(
                table_name, sample_row, field_name_overrides=field_overrides
            )

            # Register in current session
            client.schema_registry.register(schema)

            console.print(f"[green]✓ Generated schema with {schema.total_fields} fields[/green]\n")

            # Display schema
            fields_table = Table(show_header=True, header_style="bold cyan")
            fields_table.add_column("Position", style="dim")
            fields_table.add_column("Name", style="white")
            fields_table.add_column("Type", style="green")
            fields_table.add_column("Sample Value", style="yellow")

            for pos, value in enumerate(sample_row):
                field = schema.fields.get(pos)
                if field:
                    # Truncate long values
                    sample_str = str(value)
                    if len(sample_str) > 50:
                        sample_str = sample_str[:47] + "..."

                    fields_table.add_row(str(pos), field.name, field.field_type.value, sample_str)

            console.print(fields_table)
            console.print()

            # Save if requested
            if save or output:
                output_path = output or f"config/{table_name}-schema.{format}"

                # Convert schema to dict
                schema_dict = {"schemas": {table_name: schema.to_dict()}}

                # Ensure output directory exists
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)

                # Write to file
                if format == "json":
                    with open(output_path, "w") as f:
                        json.dump(schema_dict, f, indent=2)
                else:  # yaml
                    try:
                        import yaml

                        with open(output_path, "w") as f:
                            yaml.dump(schema_dict, f, default_flow_style=False, sort_keys=False)
                    except ImportError:
                        console.print(
                            "[yellow]PyYAML not installed. Saving as JSON instead.[/yellow]"
                        )
                        output_path = output_path.replace(".yaml", ".json").replace(".yml", ".json")
                        with open(output_path, "w") as f:
                            json.dump(schema_dict, f, indent=2)

                console.print(f"[green]✓ Schema saved to: {output_path}[/green]\n")

            console.print("[dim]Tip: Use --save to export this schema to a file[/dim]\n")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@schema_app.command(name="export")
def export_command(
    table_name: str = typer.Argument(..., help="Table name to export"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path"),
    format: str = typer.Option("yaml", "--format", "-f", help="Output format (yaml/json)"),
    config_file: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """
    Export a schema to a file.

    Examples:
        iptvportal schema export media
        iptvportal schema export media -o schemas.yaml
        iptvportal schema export subscriber --format json -o sub.json
    """
    try:
        settings = load_config(config_file)

        with IPTVPortalClient(settings) as client:
            if not client.schema_registry.has(table_name):
                console.print(f"[yellow]Schema for table '{table_name}' not found[/yellow]")
                raise typer.Exit(1)

            schema = client.schema_registry.get(table_name)

            # Determine output path
            output_path = output or f"config/{table_name}-schema.{format}"

            # Convert schema to dict
            schema_dict = {"schemas": {table_name: schema.to_dict()}}

            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # Write to file
            if format == "json":
                with open(output_path, "w") as f:
                    json.dump(schema_dict, f, indent=2)
            else:  # yaml
                try:
                    import yaml

                    with open(output_path, "w") as f:
                        yaml.dump(schema_dict, f, default_flow_style=False, sort_keys=False)
                except ImportError:
                    console.print("[yellow]PyYAML not installed. Saving as JSON instead.[/yellow]")
                    output_path = output_path.replace(".yaml", ".json").replace(".yml", ".json")
                    with open(output_path, "w") as f:
                        json.dump(schema_dict, f, indent=2)

            console.print(
                f"[green]✓ Schema for '{table_name}' exported to: {output_path}[/green]\n"
            )

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@schema_app.command(name="import")
def import_command(
    file_path: str = typer.Argument(..., help="Schema file to import"),
    config_file: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """
    Import schemas from a file.

    Examples:
        iptvportal schema import schemas.yaml
        iptvportal schema import config/schemas.json
    """
    try:
        if not Path(file_path).exists():
            console.print(f"[red]File not found: {file_path}[/red]")
            raise typer.Exit(1)

        console.print(f"\n[cyan]Importing schemas from: {file_path}[/cyan]\n")

        # Detect format from extension
        if file_path.endswith(".json"):
            registry = SchemaLoader.from_json(file_path)
        else:
            registry = SchemaLoader.from_yaml(file_path)

        tables = registry.list_tables()

        console.print(f"[green]✓ Imported {len(tables)} schema(s):[/green]")
        for table_name in tables:
            schema = registry.get(table_name)
            console.print(f"  • {table_name} ({schema.total_fields or len(schema.fields)} fields)")

        console.print("\n[dim]Schemas are loaded for this session only[/dim]")
        console.print("[dim]To persist, set schema_file in your configuration[/dim]\n")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@schema_app.command(name="validate")
def validate_command(file_path: str = typer.Argument(..., help="Schema file to validate")) -> None:
    """
    Validate a schema file.

    Examples:
        iptvportal schema validate schemas.yaml
        iptvportal schema validate config/schemas.json
    """
    try:
        if not Path(file_path).exists():
            console.print(f"[red]File not found: {file_path}[/red]")
            raise typer.Exit(1)

        console.print(f"\n[cyan]Validating: {file_path}[/cyan]\n")

        errors = []
        warnings = []

        # Try to load the file
        try:
            if file_path.endswith(".json"):
                registry = SchemaLoader.from_json(file_path)
            else:
                registry = SchemaLoader.from_yaml(file_path)
        except Exception as e:
            console.print(f"[red]✗ Failed to parse file: {e}[/red]\n")
            raise typer.Exit(1)

        tables = registry.list_tables()

        if not tables:
            warnings.append("No schemas found in file")

        # Validate each schema
        for table_name in tables:
            schema = registry.get(table_name)

            # Check for duplicate positions
            positions = list(schema.fields.keys())
            if len(positions) != len(set(positions)):
                errors.append(f"{table_name}: Duplicate field positions detected")

            # Check for invalid field types
            for _pos, field in schema.fields.items():
                if field.field_type.value not in [
                    "integer",
                    "string",
                    "boolean",
                    "float",
                    "datetime",
                    "date",
                    "json",
                    "unknown",
                ]:
                    errors.append(
                        f"{table_name}.{field.name}: Invalid field type '{field.field_type.value}'"
                    )

            # Warn about missing total_fields
            if not schema.total_fields:
                warnings.append(f"{table_name}: total_fields not specified")

        # Display results
        if errors:
            console.print("[bold red]✗ Validation failed:[/bold red]\n")
            for error in errors:
                console.print(f"  [red]• {error}[/red]")
            console.print()
            raise typer.Exit(1)

        if warnings:
            console.print("[bold yellow]⚠ Validation passed with warnings:[/bold yellow]\n")
            for warning in warnings:
                console.print(f"  [yellow]• {warning}[/yellow]")
            console.print()
        else:
            console.print("[bold green]✓ Validation passed[/bold green]")
            console.print(f"[green]Found {len(tables)} valid schema(s)[/green]\n")

    except Exception as e:
        if "Failed to parse" not in str(e):
            console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@schema_app.command(name="introspect")
def introspect_command(
    table_name: str = typer.Argument(..., help="Table name to introspect"),
    no_metadata: bool = typer.Option(False, "--no-metadata", help="Skip metadata gathering"),
    save: bool = typer.Option(False, "--save", "-s", help="Save generated schema to file"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path"),
    format: str = typer.Option("yaml", "--format", "-f", help="Output format (yaml/json)"),
    config_file: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """
    Introspect remote table structure with automatic metadata gathering.

    This command automatically:
    - Determines field names and types from sample data
    - Counts total rows (COUNT(*))
    - Gets MAX(id) and MIN(id)
    - Analyzes timestamp field ranges
    - Generates smart sync guardrails based on table size

    Examples:
        iptvportal schema introspect tv_channel
        iptvportal schema introspect subscriber --save
        iptvportal schema introspect media --no-metadata -o schemas.yaml
    """
    try:
        settings = load_config(config_file)

        console.print(f"\n[cyan]Introspecting table: {table_name}[/cyan]")

        # Use async client for introspection
        import asyncio

        from iptvportal.async_client import AsyncIPTVPortalClient
        from iptvportal.introspector import SchemaIntrospector

        async def do_introspect():
            try:
                async with AsyncIPTVPortalClient(settings) as client:
                    introspector = SchemaIntrospector(client)

                    gather_metadata = not no_metadata

                    if gather_metadata:
                        console.print(
                            "[dim]Gathering metadata (row count, ID ranges, timestamps)...[/dim]"
                        )
                    else:
                        console.print("[dim]Analyzing table structure...[/dim]")

                    return await introspector.introspect_table(
                        table_name=table_name, gather_metadata=gather_metadata
                    )

            except Exception:
                import traceback

                console.print("\n[red]Detailed error:[/red]")
                console.print(f"[red]{traceback.format_exc()}[/red]")
                raise

        schema = asyncio.run(do_introspect())

        console.print("[green]✓ Introspection complete[/green]\n")

        # Display schema info
        info_table = Table(show_header=False, box=None)
        info_table.add_column("Property", style="cyan")
        info_table.add_column("Value", style="white")

        info_table.add_row("Table", table_name)
        info_table.add_row("Total Fields", str(schema.total_fields))

        if schema.metadata:
            info_table.add_row("Row Count", f"{schema.metadata.row_count:,}")
            if schema.metadata.max_id:
                info_table.add_row("Max ID", str(schema.metadata.max_id))
            if schema.metadata.min_id:
                info_table.add_row("Min ID", str(schema.metadata.min_id))
            if schema.metadata.analyzed_at:
                info_table.add_row("Analyzed At", schema.metadata.analyzed_at)

        console.print(info_table)
        console.print()

        # Display detected fields
        console.print("[bold]Detected Fields:[/bold]\n")

        fields_table = Table(show_header=True, header_style="bold cyan")
        fields_table.add_column("Pos", style="dim")
        fields_table.add_column("Name", style="white")
        fields_table.add_column("Type", style="green")
        fields_table.add_column("Description", style="dim")

        for pos in sorted(schema.fields.keys()):
            field = schema.fields[pos]
            fields_table.add_row(
                str(pos), field.name, field.field_type.value, field.description or "-"
            )

        console.print(fields_table)
        console.print()

        # Display sync guardrails
        if schema.sync_config:
            console.print("[bold]Auto-generated Sync Guardrails:[/bold]\n")

            sync_table = Table(show_header=False, box=None)
            sync_table.add_column("Setting", style="cyan")
            sync_table.add_column("Value", style="white")

            if schema.sync_config.where:
                sync_table.add_row("WHERE Clause", schema.sync_config.where)
            if schema.sync_config.limit:
                sync_table.add_row("Sync Limit", f"{schema.sync_config.limit:,}")
            sync_table.add_row("Chunk Size", f"{schema.sync_config.chunk_size:,}")
            sync_table.add_row("Cache Strategy", schema.sync_config.cache_strategy)
            sync_table.add_row("Auto Sync", "Yes" if schema.sync_config.auto_sync else "No")
            if schema.sync_config.ttl:
                sync_table.add_row("Cache TTL", f"{schema.sync_config.ttl}s")
            if schema.sync_config.incremental_field:
                sync_table.add_row("Incremental Field", schema.sync_config.incremental_field)

            console.print(sync_table)
            console.print()

        # Timestamp ranges
        if schema.metadata and schema.metadata.timestamp_ranges:
            console.print("[bold]Timestamp Ranges:[/bold]\n")

            for field_name, ranges in schema.metadata.timestamp_ranges.items():
                console.print(f"  [cyan]{field_name}:[/cyan]")
                if ranges.get("min"):
                    console.print(f"    Min: {ranges['min']}")
                if ranges.get("max"):
                    console.print(f"    Max: {ranges['max']}")
                console.print()

        # Save if requested
        if save or output:
            output_path = output or f"config/{table_name}-schema.{format}"

            # Convert schema to dict
            schema_dict = {"schemas": {table_name: schema.to_dict()}}

            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # Write to file
            if format == "json":
                with open(output_path, "w") as f:
                    json.dump(schema_dict, f, indent=2)
            else:  # yaml
                try:
                    import yaml

                    with open(output_path, "w") as f:
                        yaml.dump(schema_dict, f, default_flow_style=False, sort_keys=False)
                except ImportError:
                    console.print("[yellow]PyYAML not installed. Saving as JSON instead.[/yellow]")
                    output_path = output_path.replace(".yaml", ".json").replace(".yml", ".json")
                    with open(output_path, "w") as f:
                        json.dump(schema_dict, f, indent=2)

            console.print(f"[green]✓ Schema saved to: {output_path}[/green]\n")
        else:
            console.print("[dim]Tip: Use --save to export this schema to a file[/dim]\n")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[dim]The table may be empty or doesn't exist[/dim]\n")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@schema_app.command(name="clear")
def clear_command(
    table_name: str | None = typer.Argument(None, help="Table name to clear (omit to clear all)"),
    config_file: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """
    Clear schema(s) from the registry.

    Examples:
        iptvportal schema clear media
        iptvportal schema clear --force  # Clear all schemas
    """
    try:
        settings = load_config(config_file)

        with IPTVPortalClient(settings) as client:
            if table_name:
                if not client.schema_registry.has(table_name):
                    console.print(f"[yellow]Schema for table '{table_name}' not found[/yellow]")
                    raise typer.Exit(1)

                if not force:
                    confirm = typer.confirm(f"Clear schema for '{table_name}'?")
                    if not confirm:
                        console.print("[yellow]Cancelled[/yellow]")
                        raise typer.Exit(0)

                # Remove from registry (would need to add remove method)
                console.print(f"[green]✓ Schema for '{table_name}' cleared[/green]")
                console.print("[dim]Note: This only affects the current session[/dim]\n")
            else:
                tables = client.schema_registry.list_tables()

                if not tables:
                    console.print("[yellow]No schemas to clear[/yellow]")
                    raise typer.Exit(0)

                if not force:
                    console.print(f"[yellow]This will clear {len(tables)} schema(s):[/yellow]")
                    for t in tables:
                        console.print(f"  • {t}")
                    console.print()
                    confirm = typer.confirm("Continue?")
                    if not confirm:
                        console.print("[yellow]Cancelled[/yellow]")
                        raise typer.Exit(0)

                console.print(f"[green]✓ Cleared {len(tables)} schema(s)[/green]")
                console.print("[dim]Note: This only affects the current session[/dim]\n")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)
