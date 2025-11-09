"""Config command for managing configuration."""

import json
from pathlib import Path
from typing import Annotated, Literal

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
def show_command(
    path: str | None = typer.Argument(None, help="Configuration path (e.g., 'sync.subscriber')"),
    format: str = typer.Option("yaml", "--format", "-f", help="Output format: yaml, json, tree"),
    files: bool = typer.Option(False, "--files", help="Show configuration files being loaded"),
) -> None:
    """
    Show configuration settings.

    Display all settings or a specific section in YAML, JSON, or tree format.

    Examples:
        # Show all configuration as YAML (default)
        iptvportal config show

        # Show specific section
        iptvportal config show core
        iptvportal config show sync.subscriber

        # Show as JSON
        iptvportal config show --format json

        # Show as tree view
        iptvportal config show --format tree

        # Show loaded config files
        iptvportal config show --files
    """
    try:
        from iptvportal import project_conf

        # Show config files if requested
        if files:
            console.print("\n[bold cyan]Configuration Files:[/bold cyan]\n")
            config_files = project_conf.get_config_files()
            for i, file_path in enumerate(config_files, 1):
                console.print(f"  {i}. {file_path}")
            console.print()
            return

        # Get configuration values
        if path:
            # Show specific key
            value = project_conf.get_value(path)
            if value is None:
                console.print(f"[yellow]Configuration key '{path}' not found[/yellow]")
                return

            console.print(f"\n[bold cyan]{path}:[/bold cyan]\n")

            if format == "json":
                if isinstance(value, dict):
                    output = json.dumps(value, indent=2)
                    console.print(Syntax(output, "json", theme="monokai"))
                else:
                    console.print(f"  {value}")
            elif format == "tree":
                if isinstance(value, dict):
                    _print_tree(path, value)
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

            console.print("\n[bold cyan]IPTVPortal Configuration[/bold cyan]\n")

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
        settings = IPTVPortalSettings()  # type: ignore[call-arg]
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


def _print_tree(name: str, data: dict, tree: Tree | None = None) -> Tree:
    """Print configuration as a rich tree structure."""
    root = tree is None
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

    if root:
        console.print(tree)

    return tree


@config_app.command(name="generate")
def generate_command(
    scope: Annotated[
        str,
        typer.Option(
            "--scope",
            help="Directory to start scanning for settings classes (default: src)",
        ),
    ] = "src",
    ignore: Annotated[
        list[str] | None,
        typer.Option(
            "--ignore",
            help="Patterns to ignore during scanning (can be specified multiple times)",
        ),
    ] = None,
    settings_context: Annotated[
        str,
        typer.Option(
            "--settings-context",
            help="Base path in settings tree where discovered settings should be attached (e.g., 'sync', 'cli.advanced')",
        ),
    ] = "",
    strategy: Annotated[
        Literal["single", "per-module", "file-per-module"],
        typer.Option(
            "--strategy",
            help=(
                "File generation strategy: 'single' (one file), 'per-module' (one per Python module), "
                "'file-per-module' (one per settings class)"
            ),
        ),
    ] = "file-per-module",
    output: Annotated[
        str,
        typer.Option("--output", "-o", help="Output directory for generated configuration files"),
    ] = "config/generated",
    template: Annotated[
        str | None,
        typer.Option("--template", help="Generate template: env, yaml (overrides code scanning)"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be generated without creating files"),
    ] = False,
) -> None:
    """Generate configuration files from code or templates.

    This command scans Python modules for Pydantic BaseSettings classes,
    dynaconf configurations, and other settings models, then generates
    corresponding YAML configuration files. Alternatively, use --template
    to generate example configuration templates.

    Examples:
        # Scan src directory and generate one file per settings class
        iptvportal config generate

        # Scan specific directory with custom output
        iptvportal config generate --scope src/iptvportal/sync --output config/sync

        # Generate single settings.yaml with all discovered settings
        iptvportal config generate --strategy single

        # Ignore test files and generate files per module
        iptvportal config generate --ignore "test_*" --ignore "*_test.py" --strategy per-module

        # Attach discovered settings to a specific context
        iptvportal config generate --settings-context sync.advanced

        # Generate example .env template
        iptvportal config generate --template env

        # Generate example YAML template
        iptvportal config generate --template yaml

        # Dry run to see what would be generated
        iptvportal config generate --dry-run
    """
    # Handle template generation
    if template:
        console.print(f"\n[bold cyan]Generating {template.upper()} Template[/bold cyan]\n")

        if template == "env":
            env_template = """# IPTVPortal Configuration
IPTVPORTAL_DOMAIN=operator
IPTVPORTAL_USERNAME=admin
IPTVPORTAL_PASSWORD=your_password_here

# Optional settings
IPTVPORTAL_TIMEOUT=30.0
IPTVPORTAL_MAX_RETRIES=3
IPTVPORTAL_VERIFY_SSL=true
IPTVPORTAL_SESSION_CACHE=~/.iptvportal/session-cache
IPTVPORTAL_SESSION_TTL=3600
IPTVPORTAL_LOG_LEVEL=INFO
"""
            if dry_run:
                console.print("[bold yellow]Dry run - no files will be created[/bold yellow]\n")
                console.print(env_template)
            else:
                output_path = Path(output) if output != "config/generated" else Path(".env.example")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(env_template)
                console.print(f"[green]✓ Template written to {output_path}[/green]\n")
            return

        if template == "yaml":
            yaml_template = """# IPTVPortal Configuration Example
core:
  timeout: 30.0
  max_retries: 3
  verify_ssl: true
  session_ttl: 3600

cli:
  default_format: table
  max_limit: 10000
  enable_guardrails: true

sync:
  default_sync_strategy: full
  default_chunk_size: 1000
  max_concurrent_syncs: 3
"""
            if dry_run:
                console.print("[bold yellow]Dry run - no files will be created[/bold yellow]\n")
                console.print(yaml_template)
            else:
                output_path = (
                    Path(output) if output != "config/generated" else Path("config/example.yaml")
                )
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(yaml_template)
                console.print(f"[green]✓ Template written to {output_path}[/green]\n")
            return
        console.print(f"[bold red]Error:[/bold red] Unknown template type: {template}")
        console.print("[dim]Supported templates: env, yaml[/dim]")
        raise typer.Exit(1)

    # Original code scanning functionality
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
            console.print(
                "\n[dim]Tip: Make sure your settings classes inherit from BaseSettings[/dim]\n"
            )
            return

        # Display discovered classes
        console.print(f"[green]Found {len(settings_classes)} settings class(es):[/green]\n")

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Class", style="white")
        table.add_column("Module", style="dim")
        table.add_column("Fields", style="yellow")

        for class_info in settings_classes:
            table.add_row(class_info.class_name, class_info.module, str(len(class_info.fields)))

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
                    console.print(
                        f"  [dim]{class_info.docstring[:80]}...[/dim]"
                        if len(class_info.docstring) > 80
                        else f"  [dim]{class_info.docstring}[/dim]"
                    )

                console.print(
                    f"  [yellow]Fields:[/yellow] {', '.join(f.name for f in class_info.fields[:5])}"
                )
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
                    settings_classes, strategy, settings_context, output_path
                )

            console.print(
                f"[green]✓ Generated {len(generated_files)} file(s) in {output_path}[/green]\n"
            )

            for file_path in generated_files:
                rel_path = (
                    file_path.relative_to(Path.cwd())
                    if file_path.is_relative_to(Path.cwd())
                    else file_path
                )
                console.print(f"  [cyan]• {rel_path}[/cyan]")

            console.print()
            console.print("[dim]Review the generated files and adjust as needed.[/dim]")
            console.print(
                "[dim]Use 'iptvportal config show --files' to see loaded configuration files.[/dim]\n"
            )

    except ImportError as e:
        console.print(f"[bold red]Error:[/bold red] Failed to import introspection module: {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        import traceback

        console.print(traceback.format_exc())
        raise typer.Exit(1)


@config_app.command(name="validate")
def validate_command(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed validation info"),
) -> None:
    """
    Validate current configuration.

    Check that all required settings are present, types are correct,
    and file paths exist where applicable.

    Examples:
        # Validate configuration
        iptvportal config validate

        # Validate with verbose output
        iptvportal config validate --verbose
    """
    try:
        from iptvportal import project_conf

        console.print("\n[bold cyan]Configuration Validation[/bold cyan]\n")

        errors = []
        warnings = []
        success_count = 0

        # Check required core settings
        required_checks = [
            ("core.timeout", float, "Core timeout setting"),
            ("core.max_retries", int, "Core max retries setting"),
            ("core.session_ttl", int, "Session TTL setting"),
        ]

        for key, expected_type, description in required_checks:
            value = project_conf.get_value(key)
            if value is None:
                errors.append(f"{description} '{key}' is not set")
            elif not isinstance(value, expected_type):
                try:
                    # Try to convert to expected type
                    _ = expected_type(value)
                    if verbose:
                        console.print(
                            f"[yellow]•[/yellow] {key}: {value} (type: {type(value).__name__}) "
                            f"- convertible to {expected_type.__name__}"
                        )
                    success_count += 1
                except (ValueError, TypeError):
                    errors.append(
                        f"{description} '{key}' has wrong type: "
                        f"expected {expected_type.__name__}, got {type(value).__name__}"
                    )
            else:
                if verbose:
                    console.print(f"[green]✓[/green] {key}: {value}")
                success_count += 1

        # Check CLI settings if present
        cli_checks = [
            ("cli.default_format", str, "CLI default format"),
            ("cli.max_limit", int, "CLI max limit"),
            ("cli.enable_guardrails", bool, "CLI guardrails"),
        ]

        for key, expected_type, description in cli_checks:
            value = project_conf.get_value(key)
            if value is not None:
                if not isinstance(value, expected_type):
                    try:
                        _ = expected_type(value)
                        if verbose:
                            console.print(
                                f"[yellow]•[/yellow] {key}: {value} - convertible to {expected_type.__name__}"
                            )
                        success_count += 1
                    except (ValueError, TypeError):
                        warnings.append(
                            f"{description} '{key}' has wrong type: "
                            f"expected {expected_type.__name__}, got {type(value).__name__}"
                        )
                else:
                    if verbose:
                        console.print(f"[green]✓[/green] {key}: {value}")
                    success_count += 1

        # Check sync settings if present
        sync_checks = [
            ("sync.default_sync_strategy", str, "Sync default strategy"),
            ("sync.default_chunk_size", int, "Sync default chunk size"),
            ("sync.max_concurrent_syncs", int, "Sync max concurrent"),
        ]

        for key, expected_type, description in sync_checks:
            value = project_conf.get_value(key)
            if value is not None:
                if not isinstance(value, expected_type):
                    try:
                        _ = expected_type(value)
                        if verbose:
                            console.print(
                                f"[yellow]•[/yellow] {key}: {value} - convertible to {expected_type.__name__}"
                            )
                        success_count += 1
                    except (ValueError, TypeError):
                        warnings.append(
                            f"{description} '{key}' has wrong type: "
                            f"expected {expected_type.__name__}, got {type(value).__name__}"
                        )
                else:
                    if verbose:
                        console.print(f"[green]✓[/green] {key}: {value}")
                    success_count += 1

        # Check for config files
        config_files = project_conf.get_config_files()
        if verbose:
            console.print("\n[bold cyan]Configuration Files:[/bold cyan]")
            for file_path in config_files:
                if Path(file_path).exists():
                    console.print(f"[green]✓[/green] {file_path}")
                else:
                    console.print(f"[red]✗[/red] {file_path} (not found)")
                    warnings.append(f"Configuration file not found: {file_path}")

        # Print summary
        console.print()
        if errors:
            console.print("[bold red]Validation Errors:[/bold red]")
            for error in errors:
                console.print(f"  [red]✗[/red] {error}")
            console.print()

        if warnings:
            console.print("[bold yellow]Validation Warnings:[/bold yellow]")
            for warning in warnings:
                console.print(f"  [yellow]![/yellow] {warning}")
            console.print()

        if errors:
            console.print(f"[bold red]✗ Validation failed with {len(errors)} error(s)[/bold red]")
            if warnings:
                console.print(f"[yellow]  and {len(warnings)} warning(s)[/yellow]")
            console.print()
            raise typer.Exit(1)
        if warnings:
            console.print(
                f"[yellow]⚠ Validation completed with {len(warnings)} warning(s)[/yellow]"
            )
            console.print(f"[green]  {success_count} check(s) passed[/green]")
            console.print()
            raise typer.Exit(0)
        console.print(
            f"[green]✓ Validation successful! All {success_count} check(s) passed.[/green]"
        )
        console.print()
        raise typer.Exit(0)

    except typer.Exit:
        raise
    except ImportError:
        console.print("[bold red]Error:[/bold red] dynaconf not installed")
        console.print("Install with: pip install dynaconf")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(1)
