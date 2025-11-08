"""Sync cache management commands."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Sync cache management")
console = Console()


def get_database(cache_db_path: str | None = None):
    """Get sync database with minimal configuration."""

    # Create minimal settings for database operations
    class MinimalSettings:
        def __init__(self):
            self.cache_db_path = cache_db_path or "~/.iptvportal/cache.db"
            self.cache_db_journal_mode = "WAL"
            self.cache_db_page_size = 4096
            self.cache_db_cache_size = -64000

    from iptvportal.sync.database import SyncDatabase

    settings = MinimalSettings()
    return SyncDatabase(settings.cache_db_path, settings)


@app.command()
def init(
    cache_db: str | None = typer.Option(None, "--cache-db", "-d", help="Path to cache database"),
    force: bool = typer.Option(False, "--force", "-f", help="Force re-initialization"),
):
    """Initialize cache database."""
    try:
        database = get_database(cache_db)

        if force and Path(database.db_path).exists():
            Path(database.db_path).unlink()
            console.print(f"🗑️  Removed existing database: {database.db_path}")

        database.initialize()
        console.print(f"✅ Cache database initialized: {database.db_path}")
        console.print(
            "💡 Next: Register schemas with 'iptvportal sync register --file config/schemas.yaml'"
        )

    except Exception as e:
        console.print(f"❌ Failed to initialize cache: {e}", style="red")
        raise typer.Exit(1)


@app.command()
def register(
    schema_file: str | None = typer.Option(None, "--file", "-f", help="Schema file to load"),
    table: str | None = typer.Option(None, "--table", "-t", help="Specific table to register"),
    cache_db: str | None = typer.Option(None, "--cache-db", "-d", help="Path to cache database"),
    config_file: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """
    Register table schemas for syncing.

    Examples:
        iptvportal sync register --file config/schemas.yaml
        iptvportal sync register --table media
        iptvportal sync register  # Uses default schema_file from config
    """
    try:
        from iptvportal.cli.utils import load_config
        from iptvportal.schema import SchemaLoader

        database = get_database(cache_db)

        # Load schemas
        if schema_file:
            console.print(f"📂 Loading schemas from: {schema_file}")
            registry = SchemaLoader.from_yaml(schema_file)
        elif config_file or table:
            # Load from config
            settings = load_config(config_file)
            if settings.schema_file:
                console.print(f"📂 Loading schemas from config: {settings.schema_file}")
                registry = SchemaLoader.from_yaml(settings.schema_file)
            else:
                console.print(
                    "❌ No schema file specified. Use --file or set schema_file in config",
                    style="red",
                )
                raise typer.Exit(1)
        else:
            # Try default location
            default_path = "config/schemas.yaml"
            if Path(default_path).exists():
                console.print(f"📂 Loading schemas from: {default_path}")
                registry = SchemaLoader.from_yaml(default_path)
            else:
                console.print(
                    "❌ No schema file found. Use --file to specify a schema file", style="red"
                )
                raise typer.Exit(1)

        # Get tables to register
        if table:
            if not registry.has(table):
                console.print(f"❌ Schema for table '{table}' not found in file", style="red")
                raise typer.Exit(1)
            tables_to_register = [table]
        else:
            tables_to_register = registry.list_tables()

        if not tables_to_register:
            console.print("❌ No schemas found to register", style="red")
            raise typer.Exit(1)

        # Register each table
        registered = []
        errors = []

        # Get client for metadata queries
        from iptvportal.async_client import AsyncIPTVPortalClient
        from iptvportal.cli.utils import load_config

        settings = load_config(config_file)

        async def register_with_metadata():
            async with AsyncIPTVPortalClient(settings) as client:
                with console.status(f"Registering {len(tables_to_register)} table(s)..."):
                    for table_name in tables_to_register:
                        try:
                            schema = registry.get(table_name)
                            if schema is None:
                                errors.append((table_name, "Schema not found in registry"))
                                continue

                            # Fetch metadata and schema from remote table
                            try:
                                # Import introspector for schema introspection
                                from iptvportal.introspector import SchemaIntrospector

                                SchemaIntrospector(client)

                                # Get sample row to determine total fields
                                sample_sql = f"SELECT * FROM {table_name} LIMIT 1"
                                from iptvportal.transpiler.transpiler import SQLTranspiler

                                transpiler = SQLTranspiler()
                                sample_jsonsql = transpiler.transpile(sample_sql)
                                sample_query = {
                                    "jsonrpc": "2.0",
                                    "id": 1,
                                    "method": "select",
                                    "params": sample_jsonsql,
                                }
                                sample_result = await client.execute(sample_query)

                                if sample_result and len(sample_result) > 0:
                                    sample_row = sample_result[0]
                                    total_fields = len(sample_row)

                                    # Update schema with total fields
                                    schema.total_fields = total_fields
                                    console.print(
                                        f"📊 Remote schema for {table_name}: {total_fields} total fields"
                                    )

                                    # Get row count
                                    count_sql = f"SELECT COUNT(*) as row_count FROM {table_name}"
                                    count_jsonsql = transpiler.transpile(count_sql)
                                    count_query = {
                                        "jsonrpc": "2.0",
                                        "id": 2,
                                        "method": "select",
                                        "params": count_jsonsql,
                                    }
                                    count_result = await client.execute(count_query)
                                    row_count = (
                                        count_result[0][0]
                                        if count_result and count_result[0]
                                        else 0
                                    )

                                    # Get min/max id if id field exists
                                    min_id = max_id = None
                                    if any(
                                        getattr(f, "name", "").lower() == "id"
                                        for f in schema.fields.values()
                                    ):
                                        minmax_sql = f"SELECT MIN(id) as min_id, MAX(id) as max_id FROM {table_name}"
                                        minmax_jsonsql = transpiler.transpile(minmax_sql)
                                        minmax_query = {
                                            "jsonrpc": "2.0",
                                            "id": 3,
                                            "method": "select",
                                            "params": minmax_jsonsql,
                                        }
                                        minmax_result = await client.execute(minmax_query)
                                        if minmax_result and minmax_result[0]:
                                            min_id = minmax_result[0][0]
                                            max_id = minmax_result[0][1]

                                    # Update schema metadata
                                    if schema.metadata is None:
                                        from iptvportal.schema import TableMetadata

                                        schema.metadata = TableMetadata()

                                    schema.metadata.row_count = row_count
                                    schema.metadata.min_id = min_id
                                    schema.metadata.max_id = max_id

                                    console.print(
                                        f"📊 Fetched metadata for {table_name}: {row_count:,} rows, ID range: {min_id or 'N/A'}-{max_id or 'N/A'}"
                                    )
                                else:
                                    console.print(
                                        f"⚠️  Could not get sample row for {table_name} - using configured fields only"
                                    )

                            except Exception as meta_error:
                                # Check if it's a 403 Forbidden error - disable the table
                                error_str = str(meta_error)
                                if "403" in error_str or "Forbidden" in error_str:
                                    console.print(
                                        f"🚫 Access denied for {table_name} (403 Forbidden) - disabling sync",
                                        style="red",
                                    )
                                    schema.sync_config.disabled = True
                                else:
                                    console.print(
                                        f"⚠️  Could not fetch metadata for {table_name}: {meta_error}",
                                        style="yellow",
                                    )
                                # Continue with registration even if metadata fetch fails

                            database.register_table(schema)
                            registered.append(table_name)

                        except Exception as e:
                            errors.append((table_name, str(e)))

        # Run async registration
        import asyncio

        asyncio.run(register_with_metadata())

        # Display results
        if registered:
            console.print(f"\n✅ Registered {len(registered)} table(s):")
            for table_name in registered:
                schema = registry.get(table_name)
                if schema:
                    console.print(
                        f"  • {table_name} ({schema.total_fields} fields, {schema.sync_config.cache_strategy} strategy)"
                    )

        if errors:
            console.print(f"\n⚠️  Failed to register {len(errors)} table(s):", style="yellow")
            for table_name, error in errors:
                console.print(f"  • {table_name}: {error}", style="yellow")

        console.print("\n💡 Use 'iptvportal sync status' to verify registration")

    except Exception as e:
        console.print(f"❌ Failed to register schemas: {e}", style="red")
        raise typer.Exit(1)


@app.command()
def run(
    table: str | None = typer.Argument(None, help="Specific table to sync (omit for all tables)"),
    strategy: str | None = typer.Option(
        None, "--strategy", "-s", help="Sync strategy (full/incremental/on_demand)"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Force sync even if data is fresh"),
    config_file: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """
    Run sync operation for table(s).

    Examples:
        iptvportal sync run media
        iptvportal sync run --strategy full
        iptvportal sync run --force
        iptvportal sync run tv_channel --strategy incremental
    """
    try:
        from iptvportal.async_client import AsyncIPTVPortalClient
        from iptvportal.cli.utils import load_config
        from iptvportal.sync.manager import SyncManager

        settings = load_config(config_file)
        database = get_database()

        async def do_sync():
            try:
                async with AsyncIPTVPortalClient(settings) as client:
                    # Load registered schemas from sync database into client registry
                    from iptvportal.schema import SchemaLoader

                    # Get registered tables from metadata
                    try:
                        result = database.execute_query(
                            "_sync_metadata", "SELECT table_name FROM _sync_metadata"
                        )
                        registered_tables = [row["table_name"] for row in result]
                    except Exception:
                        registered_tables = []

                    for table_name in registered_tables:
                        # Try to find schema file that contains this table
                        schema_files = [
                            "config/schemas.yaml",
                            "config/media-schema.yaml",
                            f"config/{table_name}-schema.yaml",
                        ]
                        for schema_file in schema_files:
                            if Path(schema_file).exists():
                                try:
                                    registry = SchemaLoader.from_yaml(schema_file)
                                    if registry.has(table_name):
                                        schema = registry.get(table_name)
                                        if schema:
                                            client.schema_registry.register(schema)
                                            break
                                except Exception:
                                    continue

                    manager = SyncManager(database, client, client.schema_registry, settings)

                    if table:
                        # Sync specific table
                        console.print(f"🔄 Syncing table: {table}")
                        with console.status(f"Syncing {table}..."):
                            result = await manager.sync_table(table, strategy=strategy, force=force)

                        # Display result
                        if result.status == "success":
                            console.print(f"✅ Synced {result.rows_fetched} rows for {table}")
                            console.print(
                                f"   Inserted: {result.rows_inserted}, Updated: {result.rows_updated}, Deleted: {result.rows_deleted}"
                            )
                            console.print(
                                f"   Duration: {result.duration_ms}ms, Chunks: {result.chunks_processed}"
                            )
                        elif result.status == "skipped":
                            console.print(f"⏭️  Skipped {table} (data is fresh)")
                        else:
                            console.print(
                                f"❌ Failed to sync {table}: {result.error_message}", style="red"
                            )

                    else:
                        # Sync all tables
                        console.print("🔄 Syncing all registered tables")
                        with console.status("Syncing all tables..."):
                            results = await manager.sync_all()

                        # Display results
                        successful = 0
                        failed = 0
                        skipped = 0
                        total_rows = 0

                        for table_name, result in results.items():
                            if result.status == "success":
                                successful += 1
                                total_rows += result.rows_fetched
                                console.print(f"✅ {table_name}: {result.rows_fetched} rows")
                            elif result.status == "skipped":
                                skipped += 1
                                console.print(f"⏭️  {table_name}: skipped (fresh)")
                            else:
                                failed += 1
                                console.print(
                                    f"❌ {table_name}: {result.error_message}", style="red"
                                )

                        console.print(
                            f"\n📊 Summary: {successful} successful, {skipped} skipped, {failed} failed"
                        )
                        if total_rows > 0:
                            console.print(f"   Total rows synced: {total_rows}")

            except Exception as e:
                console.print(f"❌ Sync failed: {e}", style="red")
                raise

        # Run async sync
        import asyncio

        asyncio.run(do_sync())

    except Exception as e:
        console.print(f"❌ Failed to run sync: {e}", style="red")
        raise typer.Exit(1)


@app.command()
def status():
    """Show cache database status."""
    try:
        database = get_database()

        if not Path(database.db_path).exists():
            console.print(
                "❌ Cache database not initialized. Run 'iptvportal sync init' first.", style="red"
            )
            return

        # Get basic stats
        stats = database.get_stats()

        table_display = Table(title="Cache Database Status")
        table_display.add_column("Property", style="cyan")
        table_display.add_column("Value", style="magenta")

        # Database info
        table_display.add_row("Database Path", str(database.db_path))
        table_display.add_row(
            "Database Size", f"{stats.get('database_size_bytes', 0) / (1024 * 1024):.2f} MB"
        )

        # Table counts
        table_display.add_row("Total Tables", str(stats.get("total_tables", 0)))
        table_display.add_row("Total Rows", f"{stats.get('total_rows', 0):,}")

        # Sync activity
        table_display.add_row("Total Syncs", str(stats.get("total_syncs", 0)))
        table_display.add_row("Successful Syncs", str(stats.get("successful_syncs", 0)))
        table_display.add_row("Failed Syncs", str(stats.get("failed_syncs", 0)))

        console.print(table_display)

        # Show registered tables with enhanced metadata
        console.print("\n📋 Registered Tables:")
        try:
            # Query metadata table with enhanced fields
            result = database.execute_query(
                "_sync_metadata",
                """
                SELECT table_name, strategy, row_count, local_row_count, min_id, max_id,
                       last_sync_at, total_syncs, failed_syncs
                FROM _sync_metadata ORDER BY table_name
            """,
            )
            if result:
                tables_table = Table()
                tables_table.add_column("Table", style="cyan")
                tables_table.add_column("Strategy", style="green")
                tables_table.add_column("Remote Rows", style="yellow", justify="right")
                tables_table.add_column("Local Rows", style="magenta", justify="right")
                tables_table.add_column("ID Range", style="blue")
                tables_table.add_column("Syncs", style="white", justify="right")
                tables_table.add_column("Last Sync", style="blue")

                for row in result:
                    last_sync = row.get("last_sync_at", "Never")
                    if last_sync and last_sync != "Never":
                        try:
                            from datetime import datetime

                            dt = datetime.fromisoformat(last_sync.replace("Z", "+00:00"))
                            last_sync = dt.strftime("%Y-%m-%d %H:%M")
                        except Exception:
                            pass

                    # Format ID range
                    min_id = row.get("min_id")
                    max_id = row.get("max_id")
                    if min_id is not None and max_id is not None:
                        id_range = f"{min_id:,}-{max_id:,}"
                    else:
                        id_range = "N/A"

                    # Format sync counts
                    total_syncs = row.get("total_syncs", 0)
                    failed_syncs = row.get("failed_syncs", 0)
                    if failed_syncs > 0:
                        sync_display = f"{total_syncs} ({failed_syncs} failed)"
                    else:
                        sync_display = str(total_syncs)

                    tables_table.add_row(
                        row["table_name"],
                        row.get("strategy", "unknown"),
                        f"{row.get('row_count', 0):,}" if row.get("row_count") else "Unknown",
                        f"{row.get('local_row_count', 0):,}",
                        id_range,
                        sync_display,
                        last_sync,
                    )

                console.print(tables_table)
            else:
                console.print("   No tables registered yet.")
        except Exception:
            console.print("   No tables registered yet.")

    except Exception as e:
        console.print(f"❌ Failed to get cache status: {e}", style="red")
        raise typer.Exit(1)


@app.command()
def clear(
    table: str | None = typer.Argument(None, help="Specific table to clear"),
    all_tables: bool = typer.Option(False, "--all", "-a", help="Clear all tables"),
    confirm: bool = typer.Option(True, "--confirm/--no-confirm", help="Skip confirmation"),
):
    """Clear cache for table(s)."""
    try:
        database = get_database()

        if all_tables and confirm:
            if not typer.confirm("Are you sure you want to clear ALL cached data?"):
                console.print("Operation cancelled")
                return

            # Get all registered tables
            try:
                result = database.execute_query(
                    "_sync_metadata", "SELECT table_name FROM _sync_metadata"
                )
                table_names = [row["table_name"] for row in result]
            except Exception:
                table_names = []

            total_cleared = 0
            for table_name in table_names:
                cleared = database.clear_table(table_name)
                total_cleared += cleared
                console.print(f"🗑️  Cleared {cleared:,} rows from {table_name}")

            console.print(f"✅ Cleared {total_cleared:,} total rows from all tables")

        elif table and confirm:
            if not typer.confirm(f"Are you sure you want to clear cache for '{table}'?"):
                console.print("Operation cancelled")
                return

            cleared = database.clear_table(table)
            console.print(f"🗑️  Cleared {cleared:,} rows from {table}")

        else:
            console.print("❌ Specify a table name or use --all", style="red")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"❌ Failed to clear cache: {e}", style="red")
        raise typer.Exit(1)


@app.command()
def stats():
    """Show detailed cache statistics."""
    try:
        database = get_database()

        stats = database.get_stats()

        table_display = Table(title="Cache Statistics")
        table_display.add_column("Metric", style="cyan")
        table_display.add_column("Value", style="magenta")

        for key, value in stats.items():
            if key == "database_size_bytes":
                # Format bytes
                if value < 1024:
                    formatted = f"{value} B"
                elif value < 1024 * 1024:
                    formatted = f"{value / 1024:.1f} KB"
                else:
                    formatted = f"{value / (1024 * 1024):.1f} MB"
                table_display.add_row(key.replace("_", " ").title(), formatted)
            else:
                table_display.add_row(key.replace("_", " ").title(), str(value))

        console.print(table_display)

    except Exception as e:
        console.print(f"❌ Failed to get cache stats: {e}", style="red")
        raise typer.Exit(1)


@app.command()
def vacuum(analyze: bool = typer.Option(True, "--analyze/--no-analyze", help="Also run ANALYZE")):
    """Vacuum and optimize cache database."""
    try:
        database = get_database()

        with console.status("🧹 Vacuuming database..."):
            database.vacuum()

        if analyze:
            with console.status("📊 Analyzing database..."):
                database.analyze()

        console.print("✅ Database maintenance completed")

    except Exception as e:
        console.print(f"❌ Maintenance failed: {e}", style="red")
        raise typer.Exit(1)


@app.command()
def tables():
    """List all registered tables."""
    try:
        database = get_database()

        try:
            result = database.execute_query(
                "_sync_metadata",
                "SELECT table_name, strategy, local_row_count, schema_hash FROM _sync_metadata ORDER BY table_name",
            )

            if not result:
                console.print(
                    "No tables registered. Use 'iptvportal sync register --file <schema-file>' to register tables."
                )
                return

            table_display = Table(title="Registered Tables")
            table_display.add_column("Table Name", style="cyan")
            table_display.add_column("Strategy", style="green")
            table_display.add_column("Rows", style="magenta", justify="right")
            table_display.add_column("Schema Hash", style="blue")

            for row in result:
                table_display.add_row(
                    row["table_name"],
                    row.get("strategy", "unknown"),
                    f"{row.get('local_row_count', 0):,}",
                    row.get("schema_hash", "")[:8] + "..." if row.get("schema_hash") else "",
                )

            console.print(table_display)

        except Exception:
            console.print(
                "No tables registered. Use 'iptvportal sync register --file <schema-file>' to register tables."
            )

    except Exception as e:
        console.print(f"❌ Failed to list tables: {e}", style="red")
        raise typer.Exit(1)
