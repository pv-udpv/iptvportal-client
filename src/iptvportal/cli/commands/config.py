"""Config command for managing configuration."""

import json
from pathlib import Path
from typing import Literal

import typer
import yaml
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree

from iptvportal.config.settings import IPTVPortalSettings

console = Console()
config_app = typer.Typer(name="config", help="Manage configuration")


@config_app.command(name="show")
def show_command() -> None:
    """
    Show current configuration.

    Examples:
        iptvportal config show
    """
    try:
        settings = IPTVPortalSettings()

        console.print("\n[bold cyan]IPTVPortal Configuration[/bold cyan]\n")

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Setting", style="white")
        table.add_column("Value", style="green")

        table.add_row("Domain", settings.domain)
        table.add_row("Username", settings.username)
        table.add_row("Password", "***" if settings.password else "not set")
        table.add_row("Auth URL", settings.auth_url)
        table.add_row("API URL", settings.api_url)
        table.add_row("Timeout", f"{settings.timeout}s")
        table.add_row("Max Retries", str(settings.max_retries))
        table.add_row("Retry Delay", f"{settings.retry_delay}s")
        table.add_row("Verify SSL", str(settings.verify_ssl))
        table.add_row("Session Cache", str(settings.session_cache))
        table.add_row("Session TTL", f"{settings.session_ttl}s")
        table.add_row("Log Level", settings.log_level)
        table.add_row("Log Requests", str(settings.log_requests))
        table.add_row("Log Responses", str(settings.log_responses))

        console.print(table)
        console.print()
        console.print(
            "[dim]Configuration is loaded from environment variables with IPTVPORTAL_ prefix[/dim]"
        )
        console.print("[dim]or from .env file in the current directory[/dim]\n")

    except Exception as e:
        console.print(f"[bold red]Error loading configuration:[/bold red] {e}")
        raise typer.Exit(1)


@config_app.command(name="init")
def init_command() -> None:
    """
    Initialize configuration interactively.

    Examples:
        iptvportal config init
    """
    console.print("\n[bold cyan]IPTVPortal Configuration Wizard[/bold cyan]\n")
    console.print("This wizard will help you create a .env file with your configuration.\n")

    # Prompt for required settings
    domain = typer.prompt("Operator domain (e.g., 'operator' for operator.admin.iptvportal.ru)")
    username = typer.prompt("Admin username")
    password = typer.prompt("Admin password", hide_input=True)

    # Optional settings
    console.print("\n[dim]Optional settings (press Enter to use defaults):[/dim]\n")

    timeout = typer.prompt("Request timeout in seconds", default="30.0")
    max_retries = typer.prompt("Maximum retry attempts", default="3")
    verify_ssl = typer.confirm("Verify SSL certificates?", default=True)

    # Create .env file
    env_content = f"""# IPTVPortal Configuration
IPTVPORTAL_DOMAIN={domain}
IPTVPORTAL_USERNAME={username}
IPTVPORTAL_PASSWORD={password}
IPTVPORTAL_TIMEOUT={timeout}
IPTVPORTAL_MAX_RETRIES={max_retries}
IPTVPORTAL_VERIFY_SSL={str(verify_ssl).lower()}
"""

    with open(".env", "w") as f:
        f.write(env_content)

    console.print("\n[green]✓ Configuration saved to .env file[/green]")
    console.print("\n[dim]You can now use the iptvportal CLI commands.[/dim]\n")


@config_app.command(name="set")
def set_command(
    key: str = typer.Argument(..., help="Configuration key (e.g., domain, username)"),
    value: str = typer.Argument(..., help="Configuration value"),
) -> None:
    """
    Set a configuration value in .env file.

    Examples:
        iptvportal config set domain operator
        iptvportal config set timeout 60
    """
    # Read existing .env file
    try:
        with open(".env") as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []

    # Update or add the key
    key_upper = f"IPTVPORTAL_{key.upper()}"
    key_found = False

    for i, line in enumerate(lines):
        if line.startswith(f"{key_upper}="):
            lines[i] = f"{key_upper}={value}\n"
            key_found = True
            break

    if not key_found:
        lines.append(f"{key_upper}={value}\n")

    # Write back to .env file
    with open(".env", "w") as f:
        f.writelines(lines)

    console.print(f"[green]✓ Set {key} = {value}[/green]")


@config_app.command(name="get")
def get_command(
    key: str = typer.Argument(..., help="Configuration key (e.g., domain, username)"),
) -> None:
    """
    Get a configuration value.

    Examples:
        iptvportal config get domain
        iptvportal config get timeout
    """
    try:
        settings = IPTVPortalSettings()
        value = getattr(settings, key, None)

        if value is None:
            console.print(f"[yellow]Configuration key '{key}' not found[/yellow]")
        else:
            # Hide password
            if key == "password":
                console.print(f"{key} = ***")
            else:
                console.print(f"{key} = {value}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@config_app.command(name="conf")
def conf_command(
    key: str = typer.Argument(None, help="Configuration key in dot notation (e.g., 'core.timeout', 'sync.subscriber')"),
    set_value: str = typer.Option(None, "--set", help="Set configuration value at runtime"),
    format: str = typer.Option("yaml", "--format", "-f", help="Output format: yaml, json, or tree"),
    show_files: bool = typer.Option(False, "--files", help="Show configuration files being loaded"),
) -> None:
    """
    Advanced configuration management using dynaconf.
    
    Show, list, or set configuration values from the modular settings tree.
    
    Examples:
        # Show all configuration
        iptvportal config conf
        
        # Show specific section
        iptvportal config conf core
        iptvportal config conf sync.subscriber
        
        # Show as JSON
        iptvportal config conf --format json
        
        # Show as tree view
        iptvportal config conf --format tree
        
        # Set value at runtime (not persisted)
        iptvportal config conf core.timeout --set 60.0
        iptvportal config conf cli.verbose --set true
        
        # Show loaded config files
        iptvportal config conf --files
    """
    try:
        from iptvportal import project_conf
        
        # Show config files if requested
        if show_files:
            console.print("\n[bold cyan]Configuration Files:[/bold cyan]\n")
            files = project_conf.get_config_files()
            for i, file_path in enumerate(files, 1):
                console.print(f"  {i}. {file_path}")
            console.print()
            return
        
        # Set value if requested
        if set_value is not None:
            if not key:
                console.print("[bold red]Error:[/bold red] Key required when using --set")
                raise typer.Exit(1)
            
            # Parse value (handle boolean, numbers, strings)
            parsed_value = set_value
            if set_value.lower() in ("true", "false"):
                parsed_value = set_value.lower() == "true"
            elif set_value.isdigit():
                parsed_value = int(set_value)
            else:
                try:
                    parsed_value = float(set_value)
                except ValueError:
                    parsed_value = set_value
            
            project_conf.set_value(key, parsed_value)
            console.print(f"[green]✓ Set {key} = {parsed_value} (runtime only)[/green]")
            console.print("[dim]Note: Changes are not persisted to disk[/dim]\n")
            return
        
        # Get configuration values
        if key:
            # Show specific key
            value = project_conf.get_value(key)
            if value is None:
                console.print(f"[yellow]Configuration key '{key}' not found[/yellow]")
                return
            
            console.print(f"\n[bold cyan]{key}:[/bold cyan]\n")
            
            if format == "json":
                if isinstance(value, dict):
                    output = json.dumps(value, indent=2)
                    console.print(Syntax(output, "json", theme="monokai"))
                else:
                    console.print(f"  {value}")
            elif format == "tree":
                if isinstance(value, dict):
                    _print_tree(key, value)
                else:
                    console.print(f"  {value}")
            else:  # yaml
                if isinstance(value, dict):
                    output = yaml.dump(value, default_flow_style=False, sort_keys=False)
                    console.print(Syntax(output, "yaml", theme="monokai"))
                else:
                    console.print(f"  {value}")
        else:
            # Show all configuration
            all_settings = project_conf.list_settings()
            
            console.print("\n[bold cyan]IPTVPortal Configuration (Dynaconf)[/bold cyan]\n")
            
            if format == "json":
                output = json.dumps(all_settings, indent=2)
                console.print(Syntax(output, "json", theme="monokai"))
            elif format == "tree":
                _print_tree("settings", all_settings)
            else:  # yaml
                output = yaml.dump(all_settings, default_flow_style=False, sort_keys=False)
                console.print(Syntax(output, "yaml", theme="monokai"))
        
        console.print()
        
    except ImportError:
        console.print("[bold red]Error:[/bold red] dynaconf not installed")
        console.print("Install with: pip install dynaconf")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


def _print_tree(name: str, data: dict, tree: Tree | None = None) -> Tree:
    """Print configuration as a rich tree structure."""
    if tree is None:
        tree = Tree(f"[bold cyan]{name}[/bold cyan]")
    
    for key, value in data.items():
        if isinstance(value, dict):
            branch = tree.add(f"[yellow]{key}[/yellow]")
            _print_tree(key, value, branch)
        elif isinstance(value, list):
            branch = tree.add(f"[yellow]{key}[/yellow]")
            for item in value:
                branch.add(f"[green]{item}[/green]")
        else:
            tree.add(f"[yellow]{key}[/yellow]: [green]{value}[/green]")
    
    if tree.label.plain.startswith(name):
        console.print(tree)
    
    return tree


@config_app.command(name="inspect")
def inspect_command(
    scope: str = typer.Option(
        "src",
        "--scope",
        help="Directory to start scanning for settings classes (default: src)"
    ),
    ignore: list[str] = typer.Option(
        None,
        "--ignore",
        help="Patterns to ignore during scanning (can be specified multiple times)"
    ),
    settings_context: str = typer.Option(
        "",
        "--settings-context",
        help="Base path in settings tree where discovered settings should be attached (e.g., 'sync', 'cli.advanced')"
    ),
    strategy: Literal["single", "per-module", "file-per-module"] = typer.Option(
        "file-per-module",
        "--strategy",
        help="File generation strategy: 'single' (one file), 'per-module' (one per Python module), 'file-per-module' (one per settings class)"
    ),
    output: str = typer.Option(
        "config/generated",
        "--output",
        "-o",
        help="Output directory for generated configuration files"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be generated without creating files"
    ),
) -> None:
    """Inspect code for settings classes and generate configuration files.
    
    This command scans Python modules for Pydantic BaseSettings classes,
    dynaconf configurations, and other settings models, then generates
    corresponding YAML configuration files.
    
    Examples:
        # Scan src directory and generate one file per settings class
        iptvportal config inspect
        
        # Scan specific directory with custom output
        iptvportal config inspect --scope src/iptvportal/sync --output config/sync
        
        # Generate single settings.yaml with all discovered settings
        iptvportal config inspect --strategy single
        
        # Ignore test files and generate files per module
        iptvportal config inspect --ignore "test_*" --ignore "*_test.py" --strategy per-module
        
        # Attach discovered settings to a specific context
        iptvportal config inspect --settings-context sync.advanced
        
        # Dry run to see what would be generated
        iptvportal config inspect --dry-run
    """
    try:
        from iptvportal.cli.introspection import (
            discover_settings_classes,
            generate_settings_yaml,
        )
        
        console.print("\n[bold cyan]Configuration Inspection[/bold cyan]\n")
        
        # Resolve paths
        scope_path = Path(scope)
        if not scope_path.is_absolute():
            scope_path = Path.cwd() / scope_path
        
        if not scope_path.exists():
            console.print(f"[bold red]Error:[/bold red] Scope directory not found: {scope_path}")
            raise typer.Exit(1)
        
        console.print(f"[dim]Scanning:[/dim] {scope_path}")
        
        # Set default ignore patterns
        ignore_patterns = list(ignore) if ignore else []
        if not ignore_patterns:
            ignore_patterns = ["test_*", "*_test.py", "__pycache__", ".*"]
        
        console.print(f"[dim]Ignoring:[/dim] {', '.join(ignore_patterns)}")
        console.print(f"[dim]Strategy:[/dim] {strategy}")
        if settings_context:
            console.print(f"[dim]Context:[/dim] {settings_context}")
        console.print()
        
        # Discover settings classes
        with console.status("[bold green]Discovering settings classes..."):
            settings_classes = discover_settings_classes(scope_path, ignore_patterns)
        
        if not settings_classes:
            console.print("[yellow]No settings classes found.[/yellow]")
            console.print("\n[dim]Tip: Make sure your settings classes inherit from BaseSettings[/dim]\n")
            return
        
        # Display discovered classes
        console.print(f"[green]Found {len(settings_classes)} settings class(es):[/green]\n")
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Class", style="white")
        table.add_column("Module", style="dim")
        table.add_column("Fields", style="yellow")
        
        for class_info in settings_classes:
            table.add_row(
                class_info.class_name,
                class_info.module,
                str(len(class_info.fields))
            )
        
        console.print(table)
        console.print()
        
        if dry_run:
            console.print("[bold yellow]Dry run - no files will be created[/bold yellow]\n")
            
            # Show what would be generated
            console.print("[bold cyan]Would generate:[/bold cyan]\n")
            
            for class_info in settings_classes:
                console.print(f"[green]• {class_info.class_name}[/green]")
                console.print(f"  [dim]{class_info.module}[/dim]")
                
                if class_info.docstring:
                    console.print(f"  [dim]{class_info.docstring[:80]}...[/dim]" if len(class_info.docstring) > 80 else f"  [dim]{class_info.docstring}[/dim]")
                
                console.print(f"  [yellow]Fields:[/yellow] {', '.join(f.name for f in class_info.fields[:5])}")
                if len(class_info.fields) > 5:
                    console.print(f"    [dim]...and {len(class_info.fields) - 5} more[/dim]")
                console.print()
        else:
            # Generate files
            output_path = Path(output)
            if not output_path.is_absolute():
                output_path = Path.cwd() / output_path
            
            with console.status("[bold green]Generating configuration files..."):
                generated_files = generate_settings_yaml(
                    settings_classes,
                    strategy,
                    settings_context,
                    output_path
                )
            
            console.print(f"[green]✓ Generated {len(generated_files)} file(s) in {output_path}[/green]\n")
            
            for file_path in generated_files:
                rel_path = file_path.relative_to(Path.cwd()) if file_path.is_relative_to(Path.cwd()) else file_path
                console.print(f"  [cyan]• {rel_path}[/cyan]")
            
            console.print()
            console.print("[dim]Review the generated files and adjust as needed.[/dim]")
            console.print("[dim]Use 'iptvportal config conf --files' to see loaded configuration files.[/dim]\n")
    
    except ImportError as e:
        console.print(f"[bold red]Error:[/bold red] Failed to import introspection module: {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        import traceback
        if "--verbose" in typer.get_current_context().args:
            console.print(traceback.format_exc())
        raise typer.Exit(1)

