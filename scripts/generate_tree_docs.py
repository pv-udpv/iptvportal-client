#!/usr/bin/env python3
"""Generate tree structure with file descriptions from docstrings.

This script creates a visual tree representation of the project structure,
annotating Python files with their module docstrings or first significant comment.
"""

import argparse
import ast
from pathlib import Path
from typing import List, Tuple


def extract_description(file_path: Path) -> str:
    """Extract description from a Python file.

    Tries to extract in this order:
    1. Module docstring (__doc__)
    2. First comment line
    3. Empty string if nothing found
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Try to parse as Python and get module docstring
        try:
            tree = ast.parse(content)
            docstring = ast.get_docstring(tree)
            if docstring:
                # Return first line of docstring, stripped
                first_line = docstring.split('\n')[0].strip()
                return first_line
        except SyntaxError:
            pass

        # Fallback: look for first comment
        for line in content.split('\n'):
            stripped = line.strip()
            if stripped.startswith('#'):
                comment = stripped.lstrip('#').strip()
                if comment and not comment.startswith('!'):  # Skip shebang
                    return comment
            elif stripped and not stripped.startswith('"""') and not stripped.startswith("'''"):
                # If we hit code before finding a comment, stop
                break

    except Exception:
        pass

    return ""


def should_include_path(path: Path, exclude_patterns: List[str]) -> bool:
    """Check if path should be included in the tree."""
    # Common excludes - these are matched as exact directory names
    common_excludes = [
        '__pycache__',
        '.git',
        '.venv',
        'venv',
        '.pytest_cache',
        '.mypy_cache',
        '.ruff_cache',
        'dist',
        'build',
        '.env',
        'uv.lock',
    ]
    
    # Special patterns that can appear as part of a name
    substring_excludes = [
        '.egg-info',
    ]
    
    all_excludes = common_excludes + exclude_patterns
    
    # Check path parts for exact matches
    parts = path.parts
    for part in parts:
        # Check exact matches
        if part in all_excludes:
            return False
        # Check substring patterns
        for pattern in substring_excludes:
            if pattern in part:
                return False
    
    return True


def generate_tree(
    root_path: Path,
    prefix: str = "",
    is_last: bool = True,
    exclude_patterns: List[str] = None,
    max_depth: int = None,
    current_depth: int = 0,
    annotate_files: bool = True,
) -> List[str]:
    """Generate tree structure recursively.

    Args:
        root_path: Root directory to start from
        prefix: Current line prefix for tree drawing
        is_last: Whether this is the last item in current level
        exclude_patterns: Additional patterns to exclude
        max_depth: Maximum depth to traverse (None for unlimited)
        current_depth: Current traversal depth
        annotate_files: Whether to add descriptions to Python files

    Returns:
        List of formatted lines
    """
    if exclude_patterns is None:
        exclude_patterns = []

    lines = []
    
    if not should_include_path(root_path, exclude_patterns):
        return lines

    # Add current item
    connector = "└── " if is_last else "├── "
    name = root_path.name
    
    # Add description for Python files
    description = ""
    if annotate_files and root_path.is_file() and root_path.suffix == '.py':
        desc = extract_description(root_path)
        if desc:
            description = f"  # {desc}"
    
    lines.append(f"{prefix}{connector}{name}{description}")

    # If it's a file or we've reached max depth, stop here
    if root_path.is_file() or (max_depth is not None and current_depth >= max_depth):
        return lines

    # If it's a directory, process children
    if root_path.is_dir():
        try:
            children = sorted(
                [p for p in root_path.iterdir() if should_include_path(p, exclude_patterns)],
                key=lambda p: (not p.is_dir(), p.name)  # Directories first
            )
            
            for i, child in enumerate(children):
                is_last_child = (i == len(children) - 1)
                extension = "    " if is_last else "│   "
                child_lines = generate_tree(
                    child,
                    prefix=prefix + extension,
                    is_last=is_last_child,
                    exclude_patterns=exclude_patterns,
                    max_depth=max_depth,
                    current_depth=current_depth + 1,
                    annotate_files=annotate_files,
                )
                lines.extend(child_lines)
        except PermissionError:
            pass

    return lines


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate annotated tree structure of the project"
    )
    parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='Root path to generate tree from (default: current directory)'
    )
    parser.add_argument(
        '--max-depth',
        type=int,
        default=None,
        help='Maximum depth to traverse'
    )
    parser.add_argument(
        '--exclude',
        action='append',
        default=[],
        help='Additional patterns to exclude (can be used multiple times)'
    )
    parser.add_argument(
        '--no-annotations',
        action='store_true',
        help='Disable file annotations (just show tree structure)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output file (default: stdout)'
    )

    args = parser.parse_args()

    root = Path(args.path).resolve()
    
    if not root.exists():
        print(f"Error: Path {root} does not exist")
        return 1

    # Generate tree
    lines = [str(root) + "/"]
    tree_lines = generate_tree(
        root,
        exclude_patterns=args.exclude,
        max_depth=args.max_depth,
        annotate_files=not args.no_annotations,
    )
    lines.extend(tree_lines)

    # Output
    output_text = '\n'.join(lines)
    
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(output_text)
        print(f"Tree written to {output_path}")
    else:
        print(output_text)

    return 0


if __name__ == '__main__':
    exit(main())
