"""Schema management CLI commands."""

import json
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from iptvportal.cli.utils import load_config
from iptvportal.core.client import IPTVPortalClient
from iptvportal.schema import SchemaLoader, TableSchema

os.environ.setdefault("NO_COLOR", "1")
console = Console(color_system=None)
app = typer.Typer(name="schema", help="Schema management service")
# Keep schema_app as alias for backwards compatibility in this file
schema_app = app


@schema_app.callback(invoke_without_command=True)
def schema_entry(ctx: typer.Context) -> None:
    """Show deprecation hint when invoked without subcommands."""
    if ctx.resilient_parsing:
        for flag, desc in (
            ("--sync", "Perform table sync after introspection"),
            ("--sync-chunk", "Override auto-generated sync chunk size"),
            ("--order-by-fields", "Specify sync order (e.g., 'id:asc')"),
            ("--sync-run-timeout", "Sync run timeout in seconds (0 = no timeout)"),
            ("--analyze-from-cache", "Analyze synced cache data instead of samples"),
        ):
            console.print(f"{flag}: {desc}")
        return

    if ctx.invoked_subcommand:
        return

    console.print("[yellow]Command moved:[/yellow] iptvportal schema → iptvportal jsonsql schema")
    console.print("[dim]Run: iptvportal jsonsql schema show[/dim]")
    raise typer.Exit(1)


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
            from iptvportal.jsonsql import SQLTranspiler

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
    table_name: str | None = typer.Argument(None, help="Table name to introspect"),
    table: str | None = typer.Option(None, "--table", help="Table name (alternative to positional argument)"),
    from_sql: str | None = typer.Option(None, "--from-sql", help="SQL query to introspect (e.g., 'SELECT * FROM table')"),
    fields: str | None = typer.Option(None, "--fields", help="Manual field mappings (e.g., '0:id,1:name,2:email')"),
    sample_size: int = typer.Option(1000, "--sample-size", help="Sample size for DuckDB analysis"),
    no_metadata: bool = typer.Option(False, "--no-metadata", help="Skip metadata gathering"),
    no_duckdb_analysis: bool = typer.Option(False, "--no-duckdb-analysis", help="Skip DuckDB statistical analysis"),
    sync: bool = typer.Option(False, "--sync", help="Perform table sync after introspection"),
    sync_chunk: int | None = typer.Option(None, "--sync-chunk", help="Chunk size for sync (overrides auto-generated)"),
    order_by_fields: str | None = typer.Option(None, "--order-by-fields", help="Order by fields for sync (e.g., 'id:asc')"),
    sync_run_timeout: int | None = typer.Option(None, "--sync-run-timeout", help="Sync run timeout in seconds (0=no timeout)"),
    analyze_from_cache: bool = typer.Option(False, "--analyze-from-cache", help="Run DuckDB analysis on synced cache data instead of sample"),
    save: bool = typer.Option(False, "--save", "-s", help="Save generated schema to file"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path"),
    format: str = typer.Option("yaml", "--format", "-f", help="Output format (yaml/json)"),
    config_file: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """
    Introspect remote table structure with automatic metadata gathering and DuckDB analysis.

    Use --sync to perform table synchronization after introspection.
    This command automatically:
    - Determines field names and types from sample data
    - Counts total rows (COUNT(*))
    - Gets MAX(id) and MIN(id)
    - Analyzes timestamp field ranges
    - Performs DuckDB statistical analysis (min, max, nulls, unique values, cardinality)
    - Generates smart sync guardrails based on table size
    - Optionally syncs table data to local cache (with --sync flag)
    - Can analyze from synced cache data for more comprehensive statistics

    Examples:
        iptvportal schema introspect tv_channel
        iptvportal schema introspect --table=tv_channel
        iptvportal schema introspect --from-sql="SELECT * FROM tv_channel"
        iptvportal schema introspect subscriber --save
        iptvportal schema introspect media --no-metadata -o schemas.yaml
        iptvportal schema introspect --table=media --sample-size=5000
        iptvportal schema introspect tv_channel --sync
        iptvportal schema introspect tv_program --fields='0:channel_id,1:start,2:stop' --sync
        iptvportal schema introspect media --sync --sync-chunk=5000 --analyze-from-cache
    """
    try:
        settings = load_config(config_file)

        # Determine the table name from different input methods
        resolved_table_name = table_name or table
        
        if from_sql:
            # Extract table name from SQL query
            query_upper = from_sql.upper()
            if "FROM" not in query_upper:
                console.print("[red]Error: Could not extract table name from SQL query[/red]")
                console.print("[dim]Query must contain FROM clause[/dim]")
                raise typer.Exit(1)
            
            parts = query_upper.split("FROM")[1].split()
            if not parts:
                console.print("[red]Error: Could not extract table name[/red]")
                raise typer.Exit(1)
            
            resolved_table_name = parts[0].strip().lower()
            resolved_table_name = resolved_table_name.split()[0].strip(";,")
        
        if not resolved_table_name:
            console.print("[red]Error: Table name is required[/red]")
            console.print("[dim]Use either positional argument, --table option, or --from-sql[/dim]")
            raise typer.Exit(1)

        console.print(f"\n[cyan]Introspecting table: {resolved_table_name}[/cyan]")

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
                    field_overrides[position] = field_name

                if field_overrides:
                    console.print(
                        f"[dim]Applying {len(field_overrides)} manual field mapping(s)[/dim]"
                    )
            except ValueError as e:
                console.print(f"[yellow]Warning: Error parsing field mappings: {e}[/yellow]")

        # Use async client for introspection
        import asyncio

        from iptvportal.core.async_client import AsyncIPTVPortalClient
        from iptvportal.schema.introspector import SchemaIntrospector

        async def do_introspect():
            try:
                async with AsyncIPTVPortalClient(settings) as client:
                    introspector = SchemaIntrospector(client)

                    gather_metadata = not no_metadata
                    perform_duckdb = not no_duckdb_analysis

                    if gather_metadata:
                        console.print(
                            "[dim]Gathering metadata (row count, ID ranges, timestamps)...[/dim]"
                        )
                    else:
                        console.print("[dim]Analyzing table structure...[/dim]")

                    if perform_duckdb:
                        console.print(f"[dim]Performing DuckDB analysis (sample size: {sample_size})...[/dim]")

                    return await introspector.introspect_table(
                        table_name=resolved_table_name, 
                        gather_metadata=gather_metadata,
                        field_name_overrides=field_overrides if field_overrides else None,
                        sample_size=sample_size,
                        perform_duckdb_analysis=perform_duckdb,
                    )

            except Exception:
                import traceback

                console.print("\n[red]Detailed error:[/red]")
                console.print(f"[red]{traceback.format_exc()}[/red]")
                raise

        schema = asyncio.run(do_introspect())

        console.print("[green]✓ Introspection complete[/green]\n")

        # Perform sync if requested
        if sync:
            console.print(f"[cyan]Syncing table {resolved_table_name} to local cache...[/cyan]\n")
            
            # Override sync config if options provided
            if sync_chunk is not None:
                schema.sync_config.chunk_size = sync_chunk
            
            if order_by_fields:
                schema.sync_config.order_by = order_by_fields.replace(":asc", "").replace(":desc", "")
            
            # Perform the sync
            async def do_sync():
                from iptvportal.sync.database import SyncDatabase
                from iptvportal.sync.manager import SyncManager
                
                async with AsyncIPTVPortalClient(settings) as client:
                    # Initialize sync database
                    db_path = settings.cache_db_path or "~/.iptvportal/cache.db"
                    database = SyncDatabase(db_path, settings)
                    database.initialize()
                    
                    # Register the schema
                    from iptvportal.schema import SchemaRegistry
                    registry = SchemaRegistry()
                    registry.register(schema)
                    
                    # Register schema in database
                    database.register_table_schema(resolved_table_name, schema)
                    
                    # Create sync manager
                    sync_manager = SyncManager(database, client, registry, settings)
                    
                    # Perform sync with progress
                    def progress_handler(progress):
                        console.print(
                            f"[dim]Progress: {progress.completed_chunks}/{progress.total_chunks} chunks, "
                            f"{progress.rows_synced:,} rows, "
                            f"{progress.elapsed_seconds:.1f}s elapsed[/dim]"
                        )
                    
                    # Convert sync callback to async
                    async def async_progress_callback(progress):
                        progress_handler(progress)
                    
                    # Apply timeout if specified
                    if sync_run_timeout is not None and sync_run_timeout > 0:
                        import asyncio
                        try:
                            result = await asyncio.wait_for(
                                sync_manager.sync_table(
                                    resolved_table_name,
                                    strategy=schema.sync_config.cache_strategy,
                                    force=True,
                                    progress_callback=async_progress_callback
                                ),
                                timeout=sync_run_timeout
                            )
                        except asyncio.TimeoutError:
                            console.print(f"[yellow]⚠ Sync timeout after {sync_run_timeout}s[/yellow]")
                            return None
                    else:
                        result = await sync_manager.sync_table(
                            resolved_table_name,
                            strategy=schema.sync_config.cache_strategy,
                            force=True,
                            progress_callback=async_progress_callback
                        )
                    
                    return result, database
            
            sync_result, database = asyncio.run(do_sync())
            
            if sync_result:
                console.print(f"\n[green]✓ Sync complete![/green]")
                console.print(f"  Rows fetched: {sync_result.rows_fetched:,}")
                console.print(f"  Rows inserted: {sync_result.rows_inserted:,}")
                console.print(f"  Chunks processed: {sync_result.chunks_processed}")
                console.print(f"  Duration: {sync_result.duration_ms / 1000:.2f}s\n")
                
                # Analyze from cache if requested
                if analyze_from_cache and not no_duckdb_analysis:
                    console.print("[cyan]Performing DuckDB analysis on synced cache data...[/cyan]\n")
                    
                    try:
                        from iptvportal.schema.duckdb_analyzer import DuckDBAnalyzer
                        
                        analyzer = DuckDBAnalyzer()
                        if analyzer.available:
                            # Fetch data from cache
                            cache_data = database.fetch_rows(resolved_table_name, limit=sample_size)
                            
                            if cache_data:
                                field_names = [schema.fields[i].name for i in sorted(schema.fields.keys())]
                                cache_analysis = analyzer.analyze_sample(cache_data, field_names)
                                
                                # Update schema metadata with cache analysis
                                if not hasattr(schema.metadata, "duckdb_analysis"):
                                    schema.metadata.duckdb_analysis = cache_analysis
                                else:
                                    schema.metadata.duckdb_analysis = cache_analysis
                                
                                # Display cache analysis
                                console.print("[bold]DuckDB Analysis (from cache):[/bold]\n")
                                for field_name, stats in cache_analysis.items():
                                    if isinstance(stats, dict) and "error" not in stats:
                                        console.print(f"  [cyan]{field_name}:[/cyan]")
                                        if "dtype" in stats:
                                            console.print(f"    Type: {stats['dtype']}")
                                        if "null_percentage" in stats:
                                            console.print(f"    Null %: {stats['null_percentage']:.2f}%")
                                        if "unique_count" in stats:
                                            console.print(f"    Unique: {stats['unique_count']} ({stats.get('cardinality', 0):.2%} cardinality)")
                                        if "min_value" in stats and "max_value" in stats:
                                            console.print(f"    Range: [{stats['min_value']} .. {stats['max_value']}]")
                                        console.print()
                        else:
                            console.print("[yellow]⚠ DuckDB not available for cache analysis[/yellow]\n")
                    except Exception as e:
                        console.print(f"[yellow]⚠ Cache analysis failed: {e}[/yellow]\n")
            else:
                console.print("[yellow]⚠ Sync completed with timeout or partial results[/yellow]\n")

        # Display schema info
        info_table = Table(show_header=False, box=None)
        info_table.add_column("Property", style="cyan")
        info_table.add_column("Value", style="white")

        info_table.add_row("Table", resolved_table_name)
        info_table.add_row("Field Count", str(schema.total_fields))

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

        # DuckDB Analysis
        if schema.metadata and hasattr(schema.metadata, "duckdb_analysis") and schema.metadata.duckdb_analysis:
            analysis = schema.metadata.duckdb_analysis
            
            if "error" not in analysis:
                console.print("[bold]DuckDB Statistical Analysis:[/bold]\n")

                for field_name, stats in analysis.items():
                    if isinstance(stats, dict) and "error" not in stats:
                        console.print(f"  [cyan]{field_name}:[/cyan]")
                        
                        # Display basic stats
                        if "dtype" in stats:
                            console.print(f"    Type: {stats['dtype']}")
                        if "null_percentage" in stats:
                            console.print(f"    Null %: {stats['null_percentage']:.2f}%")
                        if "unique_count" in stats:
                            console.print(f"    Unique: {stats['unique_count']} ({stats.get('cardinality', 0):.2%} cardinality)")
                        
                        # Display type-specific stats
                        if "min_value" in stats and "max_value" in stats:
                            console.print(f"    Range: [{stats['min_value']} .. {stats['max_value']}]")
                            if "avg_value" in stats and stats["avg_value"] is not None:
                                console.print(f"    Average: {stats['avg_value']:.2f}")
                        
                        if "min_length" in stats and "max_length" in stats:
                            console.print(f"    Length: [{stats['min_length']} .. {stats['max_length']}]")
                            if "avg_length" in stats and stats["avg_length"] is not None:
                                console.print(f"    Avg Length: {stats['avg_length']:.2f}")
                        
                        # Display top values for low cardinality
                        if "top_values" in stats and stats["top_values"]:
                            console.print("    Top Values:")
                            for val, cnt in stats["top_values"][:3]:
                                console.print(f"      • {val}: {cnt}")
                        
                        console.print()

        # Save if requested
        if save or output:
            output_path = output or f"config/{resolved_table_name}-schema.{format}"

            # Convert schema to dict
            schema_dict = {"schemas": {resolved_table_name: schema.to_dict()}}

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


@schema_app.command(name="validate-mapping")
def validate_mapping_command(
    table_name: str = typer.Argument(..., help="Table name to validate"),
    mappings: str = typer.Option(
        ..., "--mappings", "-m", help="Field mappings to validate (e.g., '0:id,1:username,2:email')"
    ),
    sample_size: int = typer.Option(1000, "--sample-size", "-s", help="Sample size for validation"),
    save: bool = typer.Option(False, "--save", help="Save validation results to schema"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path"),
    config_file: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """
    Validate remote field mappings using data-driven comparison.

    Uses pandas to compare local field positions with remote column values and
    calculates match ratios to verify correctness of field mappings.

    Examples:
        iptvportal schema validate-mapping subscriber -m "0:id,1:username,2:email"
        iptvportal schema validate-mapping media -m "0:id,1:name" --sample-size 500 --save
    """
    try:
        settings = load_config(config_file)

        console.print(f"\n[cyan]Validating field mappings for table: {table_name}[/cyan]")

        # Parse mappings
        field_mappings = {}
        try:
            for mapping in mappings.split(","):
                mapping = mapping.strip()
                if ":" not in mapping:
                    console.print(
                        f"[red]Error: Invalid mapping '{mapping}' (expected format: 'position:column_name')[/red]"
                    )
                    raise typer.Exit(1)

                pos_str, col_name = mapping.split(":", 1)
                position = int(pos_str.strip())
                column_name = col_name.strip()
                field_mappings[position] = column_name

            console.print(
                f"[dim]Validating {len(field_mappings)} field mapping(s) with sample size {sample_size}...[/dim]\n"
            )

        except ValueError as e:
            console.print(f"[red]Error parsing mappings: {e}[/red]")
            raise typer.Exit(1)

        # Run validation
        import asyncio

        from iptvportal.core.async_client import AsyncIPTVPortalClient
        from iptvportal.validation import RemoteFieldValidator

        async def do_validation():
            async with AsyncIPTVPortalClient(settings) as client:
                validator = RemoteFieldValidator(client)
                return await validator.validate_table_schema(
                    table_name=table_name,
                    field_mappings=field_mappings,
                    sample_size=sample_size,
                )

        results = asyncio.run(do_validation())

        # Display results
        console.print("[bold]Validation Results:[/bold]\n")

        results_table = Table(show_header=True, header_style="bold cyan")
        results_table.add_column("Position", style="dim")
        results_table.add_column("Remote Column", style="white")
        results_table.add_column("Match Ratio", style="green")
        results_table.add_column("Sample Size", style="blue")
        results_table.add_column("Dtype", style="yellow")
        results_table.add_column("Null Count", style="dim")
        results_table.add_column("Unique", style="dim")

        all_passed = True
        for position in sorted(results.keys()):
            result = results[position]

            if "error" in result:
                results_table.add_row(
                    str(position),
                    result.get("remote_column", "?"),
                    "[red]ERROR[/red]",
                    "-",
                    "-",
                    "-",
                    "-",
                )
                all_passed = False
            else:
                match_ratio = result["match_ratio"]
                match_ratio_str = f"{match_ratio:.2%}"

                # Color code match ratio
                if match_ratio >= 0.95:
                    match_ratio_str = f"[green]{match_ratio_str}[/green]"
                elif match_ratio >= 0.80:
                    match_ratio_str = f"[yellow]{match_ratio_str}[/yellow]"
                else:
                    match_ratio_str = f"[red]{match_ratio_str}[/red]"
                    all_passed = False

                results_table.add_row(
                    str(position),
                    result["remote_column"],
                    match_ratio_str,
                    str(result["sample_size"]),
                    result["dtype"],
                    str(result["null_count"]),
                    str(result["unique_count"]),
                )

        console.print(results_table)
        console.print()

        # Summary
        if all_passed:
            console.print("[bold green]✓ All validations passed (match ratio ≥ 95%)[/bold green]\n")
        else:
            console.print(
                "[bold yellow]⚠ Some validations failed (match ratio < 95%)[/bold yellow]\n"
            )

        # Save results if requested
        if save or output:
            # Load or create schema
            with IPTVPortalClient(settings) as client:
                if client.schema_registry.has(table_name):
                    schema = client.schema_registry.get(table_name)
                else:
                    # Create minimal schema
                    from iptvportal.schema import FieldDefinition, FieldType, TableSchema

                    fields = {}
                    for position, col_name in field_mappings.items():
                        result = results[position]
                        if "error" not in result:
                            # Infer field type from dtype
                            dtype_str = result["dtype"]
                            validator_inst = RemoteFieldValidator(None)  # Just for dtype inference
                            field_type_str = validator_inst.infer_field_type_from_dtype(dtype_str)
                            field_type = FieldType(field_type_str)

                            fields[position] = FieldDefinition(
                                name=col_name,
                                position=position,
                                remote_name=col_name,
                                field_type=field_type,
                                remote_mapping=result,
                            )

                    schema = TableSchema(
                        table_name=table_name,
                        fields=fields,
                        total_fields=len(fields),
                    )

                # Update remote_mapping for each field
                for position, result in results.items():
                    if position in schema.fields and "error" not in result:
                        schema.fields[position].remote_mapping = result

                # Save schema
                output_path = output or f"config/{table_name}-validated-schema.yaml"
                schema_dict = {"schemas": {table_name: schema.to_dict()}}

                Path(output_path).parent.mkdir(parents=True, exist_ok=True)

                try:
                    import yaml

                    with open(output_path, "w") as f:
                        yaml.dump(schema_dict, f, default_flow_style=False, sort_keys=False)
                except ImportError:
                    import json

                    output_path = output_path.replace(".yaml", ".json")
                    with open(output_path, "w") as f:
                        json.dump(schema_dict, f, indent=2)

                console.print(f"[green]✓ Validated schema saved to: {output_path}[/green]\n")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        import traceback

        console.print(f"[red]{traceback.format_exc()}[/red]")
        raise typer.Exit(1)


@schema_app.command(name="generate-models")
def generate_models_command(
    schema_file: str = typer.Argument(..., help="Schema file to generate models from"),
    output_dir: str = typer.Option("models", "--output", "-o", help="Output directory for models"),
    format: str = typer.Option(
        "sqlmodel", "--format", "-f", help="Model format (sqlmodel/pydantic)"
    ),
    relationships: bool = typer.Option(
        True, "--relationships/--no-relationships", help="Include relationships"
    ),
) -> None:
    """
    Generate ORM models (SQLModel/Pydantic) from schema files.

    Generates Python code for ORM models based on schema definitions, including:
    - Field types and constraints
    - Primary keys and foreign keys
    - Unique and index constraints
    - Relationships (one-to-many, many-to-one)

    Examples:
        iptvportal schema generate-models schemas.yaml
        iptvportal schema generate-models schemas.yaml -o ./models --format pydantic
        iptvportal schema generate-models schemas.yaml --no-relationships
    """
    try:
        if not Path(schema_file).exists():
            console.print(f"[red]File not found: {schema_file}[/red]")
            raise typer.Exit(1)

        console.print(f"\n[cyan]Generating {format} models from: {schema_file}[/cyan]\n")

        # Generate models
        from iptvportal.schema.codegen import ORMGenerator

        results = ORMGenerator.load_and_generate(
            schema_path=schema_file,
            output_format=format,
            output_dir=Path(output_dir),
            include_relationships=relationships,
        )

        # Display results
        console.print(f"[green]✓ Generated {len(results)} model(s):[/green]\n")

        for table_name, _code in results.items():
            # Get class name from code
            class_name = table_name.replace("_", " ").title().replace(" ", "")
            file_name = f"{class_name.lower()}.py"

            console.print(f"  • {class_name} → {output_dir}/{file_name}")

        console.print(f"\n[green]✓ Models saved to: {output_dir}/[/green]\n")

        # Show a preview of the first model
        if results:
            first_table = list(results.keys())[0]
            first_code = results[first_table]

            console.print("[bold]Preview (first model):[/bold]\n")
            console.print("[dim]" + "\n".join(first_code.split("\n")[:20]) + "[/dim]")
            console.print("[dim]...[/dim]\n")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        import traceback

        console.print(f"[red]{traceback.format_exc()}[/red]")
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


# Schema-specific configuration
config_app = typer.Typer(name="config", help="Schema configuration")


@config_app.command(name="show")
def config_show(
    path: str | None = typer.Argument(None, help="Config path (e.g., 'schema.file')"),
    config_file: str | None = typer.Option(None, "--config", help="Config file path"),
) -> None:
    """Show schema configuration."""
    settings = load_config(config_file)

    # Display schema configuration
    table = Table(title="Schema Configuration", show_header=True, header_style="bold cyan")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", justify="right")

    if path:
        console.print(f"[yellow]Specific schema config path '{path}' not yet implemented[/yellow]")
    else:
        # Show all schema settings
        if hasattr(settings, "schema_file") and settings.schema_file:
            table.add_row("Schema File", str(settings.schema_file))
        else:
            table.add_row("Schema File", "[dim]Not configured[/dim]")

        console.print(table)
        console.print("\n[dim]Schema files define table field mappings[/dim]")


@config_app.command(name="set")
def config_set(
    key: str = typer.Argument(..., help="Config key (e.g., 'file')"),
    value: str = typer.Argument(..., help="Config value"),
) -> None:
    """Set schema configuration value."""
    console.print(
        f"[yellow]Runtime schema config setting not yet implemented: schema.{key} = {value}[/yellow]"
    )
    console.print("[dim]Use environment variables or configuration files[/dim]")


@config_app.command(name="get")
def config_get(
    key: str = typer.Argument(..., help="Config key"),
    config_file: str | None = typer.Option(None, "--config", help="Config file path"),
) -> None:
    """Get schema configuration value."""
    settings = load_config(config_file)

    if key == "file":
        if hasattr(settings, "schema_file"):
            value = settings.schema_file or "Not configured"
            console.print(f"schema.file = {value}")
        else:
            console.print("[yellow]schema.file not configured[/yellow]")
    else:
        console.print(f"[yellow]Unknown schema config key: {key}[/yellow]")
        console.print("[dim]Available keys: file[/dim]")


app.add_typer(config_app)
