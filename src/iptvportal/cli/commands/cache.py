"""Cache management commands."""

import typer
from rich.console import Console
from rich.table import Table

from iptvportal.cli.utils import load_config
from iptvportal.client import IPTVPortalClient

console = Console()

cache_app = typer.Typer(
    name="cache",
    help="Manage query result cache",
    no_args_is_help=True,
)


@cache_app.command("clear")
def clear_cache_command(
    config_file: str | None = typer.Option(None, "--config", help="Config file path"),
    table: str | None = typer.Option(
        None, "--table", "-t", help="Clear cache for specific table (not implemented yet)"
    ),
) -> None:
    """
    Clear the query result cache.

    Examples:
        # Clear all cached results
        iptvportal cache clear

        # Clear cache for specific table (not yet implemented)
        iptvportal cache clear --table tv_channel
    """
    settings = load_config(config_file)

    if not settings.enable_query_cache:
        console.print("[yellow]Query cache is disabled in settings[/yellow]")
        return

    try:
        with IPTVPortalClient(settings) as client:
            if not client._cache:
                console.print("[yellow]Cache is not initialized[/yellow]")
                return

            # Clear cache
            cleared_count = client._cache.clear(table_name=table)

            if table:
                console.print(
                    f"[green]✓ Cleared {cleared_count} cached entries for table: {table}[/green]"
                )
            else:
                console.print(f"[green]✓ Cleared {cleared_count} cached entries[/green]")

    except Exception as e:
        console.print(f"[red]Error clearing cache:[/red] {e}")
        raise typer.Exit(1)


@cache_app.command("stats")
def cache_stats_command(
    config_file: str | None = typer.Option(None, "--config", help="Config file path"),
    reset: bool = typer.Option(False, "--reset", help="Reset statistics after showing"),
) -> None:
    """
    Show cache statistics.

    Examples:
        # Show cache stats
        iptvportal cache stats

        # Show stats and reset counters
        iptvportal cache stats --reset
    """
    settings = load_config(config_file)

    if not settings.enable_query_cache:
        console.print("[yellow]Query cache is disabled in settings[/yellow]")
        return

    try:
        with IPTVPortalClient(settings) as client:
            if not client._cache:
                console.print("[yellow]Cache is not initialized[/yellow]")
                return

            # Get statistics
            stats = client._cache.get_stats()

            # Display statistics in a table
            table = Table(
                title="Query Cache Statistics", show_header=True, header_style="bold cyan"
            )
            table.add_column("Metric", style="cyan")
            table.add_column("Value", justify="right", style="green")

            table.add_row("Cache Size", f"{stats['size']} / {stats['max_size']}")
            table.add_row("Hit Rate", f"{stats['hit_rate']}%")
            table.add_row("Cache Hits", str(stats["hits"]))
            table.add_row("Cache Misses", str(stats["misses"]))
            table.add_row("Total Requests", str(stats["total_requests"]))
            table.add_row("Evictions", str(stats["evictions"]))

            console.print(table)

            # Display cache efficiency assessment
            if stats["total_requests"] > 0:
                if stats["hit_rate"] >= 80:
                    console.print("\n[green]✓ Cache is performing well![/green]")
                elif stats["hit_rate"] >= 50:
                    console.print("\n[yellow]⚠ Cache hit rate could be improved[/yellow]")
                else:
                    console.print(
                        "\n[red]⚠ Low cache hit rate - consider adjusting cache settings[/red]"
                    )

            # Reset if requested
            if reset:
                client._cache.reset_stats()
                console.print("\n[dim]Statistics counters have been reset[/dim]")

    except Exception as e:
        console.print(f"[red]Error getting cache stats:[/red] {e}")
        raise typer.Exit(1)


@cache_app.command("info")
def cache_info_command(
    config_file: str | None = typer.Option(None, "--config", help="Config file path"),
) -> None:
    """
    Show cache configuration information.

    Examples:
        # Show cache config
        iptvportal cache info
    """
    settings = load_config(config_file)

    # Display cache configuration
    table = Table(title="Cache Configuration", show_header=True, header_style="bold cyan")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row(
        "Enabled", "[green]Yes[/green]" if settings.enable_query_cache else "[red]No[/red]"
    )
    table.add_row("Max Size", str(settings.cache_max_size))
    table.add_row("TTL", f"{settings.cache_ttl} seconds")

    console.print(table)

    if settings.enable_query_cache:
        console.print("\n[dim]Cache stores query results to avoid repeated API calls[/dim]")
        console.print("[dim]Only SELECT queries are cached[/dim]")
    else:
        console.print("\n[yellow]Set IPTVPORTAL_ENABLE_QUERY_CACHE=true to enable caching[/yellow]")
