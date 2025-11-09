"""CLI command auto-discovery system."""

import importlib
import pkgutil
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

console = Console()


def discover_cli_modules(
    package_name: str = "iptvportal",
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Auto-discover __cli__.py modules in all subpackages.

    Convention: Each service package can have __cli__.py with 'app' attribute.

    Args:
        package_name: Base package to scan for CLI modules
        verbose: Print discovery progress

    Returns:
        dict mapping service name to typer app
    """
    discovered = {}

    try:
        package = importlib.import_module(package_name)
        package_path = Path(package.__file__).parent if package.__file__ else None
    except (ImportError, AttributeError):
        return discovered

    if not package_path:
        return discovered

    for _, module_name, is_pkg in pkgutil.iter_modules([str(package_path)]):
        if is_pkg:
            cli_module_name = f"{package_name}.{module_name}.__cli__"
            try:
                cli_module = importlib.import_module(cli_module_name)
                if hasattr(cli_module, "app"):
                    discovered[module_name] = cli_module.app
                    if verbose:
                        console.print(
                            f"[green]✓[/green] Registered: iptvportal {module_name}"
                        )
            except (ImportError, AttributeError):
                # No __cli__.py or no app attribute, skip silently
                pass

    return discovered
