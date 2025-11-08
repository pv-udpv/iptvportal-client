"""CLI utilities and helpers."""

import json
from typing import Any, Optional
from pathlib import Path

import orjson
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel

from iptvportal.config import IPTVPortalSettings
from iptvportal.client import IPTVPortalClient


console = Console()


def load_config(config_file: Optional[str] = None) -> IPTVPortalSettings:
    """
    Load configuration from file or environment.
    
    Args:
        config_file: Optional path to config file
        
    Returns:
        IPTVPortalSettings instance
    """
    if config_file:
        # TODO: Load from YAML file when needed
        pass
    
    return IPTVPortalSettings()


def parse_json_param(param: Optional[str]) -> Any:
    """
    Parse JSON string parameter.
    
    Args:
        param: JSON string
        
    Returns:
        Parsed Python object
    """
    if param is None:
        return None
    
    try:
        return orjson.loads(param)
    except Exception as e:
        console.print(f"[red]Error parsing JSON:[/red] {e}")
        raise


def build_jsonrpc_request(method: str, params: dict[str, Any], request_id: int = 1) -> dict[str, Any]:
    """
    Build JSON-RPC 2.0 request.
    
    Args:
        method: RPC method name
        params: Method parameters
        request_id: Request ID
        
    Returns:
        JSON-RPC request dict
    """
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params,
    }


def execute_query(
    method: str,
    params: dict[str, Any],
    config_file: Optional[str] = None,
) -> Any:
    """
    Execute query through IPTVPortal client.
    
    Args:
        method: Query method (select, insert, update, delete)
        params: Query parameters
        config_file: Optional config file path
        
    Returns:
        Query result
    """
    settings = load_config(config_file)
    
    with IPTVPortalClient(settings) as client:
        request = build_jsonrpc_request(method, params)
        return client.execute(request)


def display_json(data: Any, title: Optional[str] = None) -> None:
    """
    Display data as formatted JSON with syntax highlighting.
    
    Args:
        data: Data to display
        title: Optional title
    """
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
    
    if title:
        console.print(Panel(syntax, title=title, border_style="cyan"))
    else:
        console.print(syntax)


def display_error(message: str, exception: Optional[Exception] = None) -> None:
    """
    Display error message.
    
    Args:
        message: Error message
        exception: Optional exception object
    """
    console.print(f"[bold red]Error:[/bold red] {message}")
    if exception:
        console.print(f"[red]{exception}[/red]")
