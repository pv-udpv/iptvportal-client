"""Editor integration for CLI."""

import contextlib
import os
import subprocess
import tempfile

from rich.console import Console

console = Console()


def get_editor() -> str:
    """
    Get the user's preferred editor from environment.

    Returns:
        Editor command

    Raises:
        RuntimeError: If no editor is configured
    """
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")

    if not editor:
        # Try common editors as fallback
        for cmd in ["vim", "vi", "nano", "emacs"]:
            if subprocess.run(["which", cmd], capture_output=True).returncode == 0:
                return cmd

        raise RuntimeError(
            "No editor configured. Please set the EDITOR or VISUAL environment variable."
        )

    return editor


def open_editor(
    initial_content: str | None = None,
    suffix: str = ".sql",
    prompt: str | None = None,
) -> str:
    """
    Open editor for user input.

    Args:
        initial_content: Initial content to populate in editor
        suffix: File extension for temp file
        prompt: Optional prompt to display before opening editor

    Returns:
        Content from editor

    Raises:
        RuntimeError: If editor fails or returns empty content
    """
    editor = get_editor()

    if prompt:
        console.print(prompt)

    # Create temporary file
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=suffix,
        delete=False,
        encoding="utf-8",
    ) as tmp_file:
        if initial_content:
            tmp_file.write(initial_content)
        tmp_path = tmp_file.name

    try:
        # Open editor
        subprocess.run([editor, tmp_path], check=True)

        # Read content
        with open(tmp_path, encoding="utf-8") as f:
            content = f.read().strip()

        if not content:
            raise RuntimeError("Editor returned empty content")

        return content

    finally:
        # Clean up temp file
        with contextlib.suppress(Exception):
            os.unlink(tmp_path)


def open_sql_editor(initial_sql: str | None = None) -> str:
    """
    Open editor for SQL query input.

    Args:
        initial_sql: Initial SQL to populate

    Returns:
        SQL query from editor
    """
    prompt_text = (
        "[cyan]Opening editor for SQL query...[/cyan]\n"
        "[dim]Save and exit to execute the query[/dim]"
    )

    return open_editor(
        initial_content=initial_sql,
        suffix=".sql",
        prompt=prompt_text,
    )


def open_jsonsql_editor(initial_json: str | None = None) -> str:
    """
    Open editor for JSONSQL query input.

    Args:
        initial_json: Initial JSONSQL to populate

    Returns:
        JSONSQL query from editor
    """
    prompt_text = (
        "[cyan]Opening editor for JSONSQL query...[/cyan]\n"
        "[dim]Save and exit to execute the query[/dim]"
    )

    return open_editor(
        initial_content=initial_json,
        suffix=".json",
        prompt=prompt_text,
    )
