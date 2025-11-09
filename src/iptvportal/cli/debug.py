"""Debug logging utilities for CLI.

Includes helper `_sanitize_data` that masks secrets (pydantic SecretStr) in
nested data structures for safe debug output and file persistence.
"""

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import SecretStr
from rich.console import Console
from rich.syntax import Syntax

console = Console()


def _sanitize_data(data: Any) -> Any:
    """Recursively sanitize data for debug output.

    Masks pydantic SecretStr values while preserving structure of dicts,
    lists, tuples, and primitive types.
    """
    if isinstance(data, SecretStr):  # direct secret
        return "***MASKED***"
    if isinstance(data, dict):
        return {k: _sanitize_data(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_sanitize_data(v) for v in data]
    if isinstance(data, tuple):
        return tuple(_sanitize_data(v) for v in data)
    # Primitive or unhandled type – return as-is
    return data


class DebugLogger:
    """Debug logger for CLI operations."""

    def __init__(
        self,
        enabled: bool = False,
        format_type: str = "text",
        output_file: str | None = None,
    ):
        """
        Initialize debug logger.

        Args:
            enabled: Whether debug logging is enabled
            format_type: Format for debug output (text, json, yaml)
            output_file: Optional file path to write debug logs
        """
        self.enabled = enabled
        self.format_type = format_type
        self.output_file = output_file
        self._logs: list[dict[str, Any]] = []

    def log(self, step: str, data: Any, title: str | None = None) -> None:
        """
        Log a debug step.

        Args:
            step: Step identifier (e.g., 'sql_input', 'transpiled', 'request')
            data: Data to log
            title: Optional display title
        """
        if not self.enabled:
            return

        # Store for potential file output
        self._logs.append({"step": step, "data": data, "title": title})

        # Display sanitized representation based on selected format
        if self.format_type == "text":
            self._display_text(step, data, title)
        elif self.format_type == "json":
            self._display_json(step, data, title)
        elif self.format_type == "yaml":
            self._display_yaml(step, data, title)

    def _display_text(self, step: str, data: Any, title: str | None = None) -> None:
        """Display debug info in human-readable text format."""
        display_title = title or step.replace("_", " ").title()
        console.print(f"\n[bold cyan][DEBUG] {display_title}[/bold cyan]")
        sanitized = _sanitize_data(data)

        if isinstance(sanitized, str):
            # For strings, determine if it's SQL, JSON, etc.
            if step in ("sql_input", "sql"):
                syntax = Syntax(sanitized, "sql", theme="monokai", line_numbers=False)
                console.print(syntax)
            else:
                console.print(sanitized)
        elif isinstance(sanitized, (dict, list)):
            # For structured data, show as formatted JSON
            json_str = json.dumps(sanitized, indent=2, ensure_ascii=False)
            syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
            console.print(syntax)
        else:
            console.print(str(sanitized))

    def _display_json(self, step: str, data: Any, title: str | None = None) -> None:
        """Display debug info in JSON format."""
        log_entry = {"step": step, "data": _sanitize_data(data)}
        if title:
            log_entry["title"] = title
        json_str = json.dumps(log_entry, indent=2, ensure_ascii=False)
        console.print(json_str)

    def _display_yaml(self, step: str, data: Any, title: str | None = None) -> None:
        """Display debug info in YAML format."""
        log_entry = {"step": step, "data": _sanitize_data(data)}
        if title:
            log_entry["title"] = title
        yaml_str = yaml.dump(log_entry, allow_unicode=True, default_flow_style=False)
        console.print(yaml_str)

    def save_to_file(self) -> None:
        """Save all debug logs to file if output_file is specified."""
        if not self.output_file or not self._logs:
            return

        output_path = Path(self.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            if self.format_type == "json":
                sanitized = [{**log, "data": _sanitize_data(log["data"])} for log in self._logs]
                json.dump(sanitized, f, indent=2, ensure_ascii=False)
            elif self.format_type == "yaml":
                sanitized = [{**log, "data": _sanitize_data(log["data"])} for log in self._logs]
                yaml.dump(sanitized, f, allow_unicode=True, default_flow_style=False)
            else:
                # Text format
                for log in self._logs:
                    f.write(f"\n=== {log.get('title', log['step'])} ===\n")
                    data_to_write = _sanitize_data(log["data"])
                    if isinstance(data_to_write, (dict, list)):
                        f.write(json.dumps(data_to_write, indent=2, ensure_ascii=False))
                    else:
                        f.write(str(data_to_write))
                    f.write("\n")

        console.print(f"\n[green]Debug logs saved to: {output_path}[/green]")

    def exception(self, exc: Exception, message: str | None = None) -> None:
        """
        Log an exception with full traceback.

        Args:
            exc: Exception to log
            message: Optional context message
        """
        if not self.enabled:
            return

        import traceback

        console.print("\n[bold red][DEBUG] Exception Occurred[/bold red]")
        if message:
            console.print(f"[yellow]{message}[/yellow]")

        console.print(f"\n[red]Exception Type:[/red] {type(exc).__name__}")
        console.print(f"[red]Exception Message:[/red] {str(exc)}")
        console.print("\n[red]Traceback:[/red]")

        tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
        for line in tb_lines:
            console.print(line.rstrip())
