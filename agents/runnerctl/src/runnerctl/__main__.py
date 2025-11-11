#!/usr/bin/env python3
"""RunnerCTL CLI entry point."""

import typer

from runnerctl.manager import APP as manager_app

# Create main app
app = typer.Typer(help="RunnerCTL - GitHub Actions self-hosted runner management")

# Add manager as subcommand
app.add_typer(manager_app, name="manager", help="Managed mode runner pool supervisor")

def main() -> None:
    """Main CLI entry point."""
    app()

if __name__ == "__main__":
    main()
