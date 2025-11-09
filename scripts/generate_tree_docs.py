#!/usr/bin/env python3
"""Generate annotated tree structure documentation for the project.

This script generates a tree view of a directory with annotations extracted from
Python file docstrings. It can output to stdout or save to a file with optional
markdown formatting.
"""

import argparse
import ast
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set


def parse_gitignore(gitignore_path: Path) -> List[str]:
    """Parse .gitignore file and return list of patterns.
    
    Args:
        gitignore_path: Path to .gitignore file
        
    Returns:
        List of gitignore patterns
    """
    if not gitignore_path.exists():
        return []
    
    patterns = []
    with open(gitignore_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith('#'):
                patterns.append(line)
    
    return patterns


def should_exclude(path: Path, base_path: Path, patterns: List[str], 
                   additional_excludes: List[str]) -> bool:
    """Check if a path should be excluded based on gitignore patterns.
    
    Args:
        path: Path to check
        base_path: Base directory path
        patterns: List of gitignore patterns
        additional_excludes: Additional patterns to exclude
        
    Returns:
        True if path should be excluded
    """
    relative_path = path.relative_to(base_path)
    path_str = str(relative_path)
    name = path.name
    
    # Check additional excludes first
    for pattern in additional_excludes:
        if pattern in path_str or pattern == name:
            return True
    
    # Check gitignore patterns
    for pattern in patterns:
        # Remove leading/trailing slashes for matching
        pattern = pattern.strip('/')
        
        # Handle directory patterns (ending with /)
        if pattern.endswith('/'):
            pattern = pattern[:-1]
            if path.is_dir() and (name == pattern or path_str.startswith(pattern + '/')):
                return True
        # Handle wildcard patterns
        elif '*' in pattern:
            # Convert gitignore pattern to regex
            regex_pattern = pattern.replace('.', r'\.').replace('*', '.*')
            if re.match(regex_pattern, name) or re.search(regex_pattern, path_str):
                return True
        # Handle exact matches
        elif name == pattern or path_str == pattern or path_str.startswith(pattern + '/'):
            return True
    
    # Always exclude .git directory even if not in gitignore
    if name == '.git':
        return True
    
    return False


def extract_docstring(file_path: Path) -> Optional[str]:
    """Extract the module docstring from a Python file.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        First line of docstring or None if not found
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        docstring = ast.get_docstring(tree)
        
        if docstring:
            # Return first line only
            return docstring.split('\n')[0].strip()
        
        # Fallback: try to find first comment line
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('#') and not line.startswith('#!'):
                return line.lstrip('#').strip()
        
        return None
    except Exception:
        return None


def generate_tree(
    root_path: Path,
    prefix: str = "",
    is_last: bool = True,
    max_depth: Optional[int] = None,
    current_depth: int = 0,
    annotations: bool = True,
    gitignore_patterns: Optional[List[str]] = None,
    additional_excludes: Optional[List[str]] = None,
    base_path: Optional[Path] = None
) -> List[str]:
    """Generate tree structure with annotations.
    
    Args:
        root_path: Root directory to generate tree for
        prefix: Prefix for tree structure lines
        is_last: Whether this is the last item in current level
        max_depth: Maximum depth to traverse (None for unlimited)
        current_depth: Current depth level
        annotations: Whether to include annotations
        gitignore_patterns: List of gitignore patterns
        additional_excludes: Additional patterns to exclude
        base_path: Base path for relative path calculations
        
    Returns:
        List of lines representing the tree
    """
    if gitignore_patterns is None:
        gitignore_patterns = []
    if additional_excludes is None:
        additional_excludes = []
    if base_path is None:
        base_path = root_path
    
    lines = []
    
    # Add current item
    connector = "└── " if is_last else "├── "
    name = root_path.name
    
    if root_path.is_file():
        annotation = ""
        if annotations and root_path.suffix == '.py':
            docstring = extract_docstring(root_path)
            if docstring:
                annotation = f"  # {docstring}"
        
        lines.append(f"{prefix}{connector}{name}{annotation}")
    else:
        lines.append(f"{prefix}{connector}{name}/")
        
        # Check depth limit
        if max_depth is not None and current_depth >= max_depth:
            return lines
        
        # Get children and sort them (directories first, then files)
        try:
            children = list(root_path.iterdir())
        except PermissionError:
            return lines
        
        # Filter excluded items
        children = [
            child for child in children
            if not should_exclude(child, base_path, gitignore_patterns, additional_excludes)
        ]
        
        # Sort: directories first, then files, alphabetically within each group
        children.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
        
        # Generate tree for children
        new_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(children):
            is_last_child = (i == len(children) - 1)
            lines.extend(
                generate_tree(
                    child,
                    new_prefix,
                    is_last_child,
                    max_depth,
                    current_depth + 1,
                    annotations,
                    gitignore_patterns,
                    additional_excludes,
                    base_path
                )
            )
    
    return lines


def format_with_markdown(
    tree_lines: List[str],
    root_path: Path,
    title: str = "PROJECT STRUCTURE",
    include_timestamp: bool = True
) -> str:
    """Format tree output with markdown.
    
    Args:
        tree_lines: List of tree lines
        root_path: Root path that was processed
        title: Title for the markdown header
        include_timestamp: Whether to include timestamp note
        
    Returns:
        Markdown-formatted string
    """
    lines = []
    
    # Add header
    lines.append(f"# {title}")
    
    # Add autogeneration note with timestamp
    if include_timestamp:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines.append(f"> Auto-generated on {timestamp}")
    
    lines.append("")
    
    # Add tree in code block
    lines.append("```sh")
    
    # Add root directory line
    lines.append(f"{root_path.resolve()}/")
    
    # Add tree content
    lines.extend(tree_lines)
    
    lines.append("```")
    
    return "\n".join(lines) + "\n"


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate annotated tree structure documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate tree with max depth of 3
  python scripts/generate_tree_docs.py src/iptvportal --max-depth 3
  
  # Generate and save to file with markdown formatting
  python scripts/generate_tree_docs.py src/iptvportal --output PROJECT_STRUCTURE.md
  
  # Save without markdown formatting
  python scripts/generate_tree_docs.py src/iptvportal --output tree.txt --no-markdown
  
  # Custom title
  python scripts/generate_tree_docs.py src/iptvportal --output tree.md --title "My Project Structure"
  
  # Exclude additional patterns
  python scripts/generate_tree_docs.py . --exclude examples --exclude tests
  
  # Without annotations
  python scripts/generate_tree_docs.py src/iptvportal --no-annotations
        """
    )
    
    parser.add_argument(
        "path",
        type=Path,
        help="Root directory to generate tree for"
    )
    
    parser.add_argument(
        "--max-depth",
        type=int,
        help="Maximum depth to traverse (default: unlimited)"
    )
    
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path (default: stdout)"
    )
    
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Additional patterns to exclude (can be used multiple times)"
    )
    
    parser.add_argument(
        "--no-annotations",
        action="store_true",
        help="Disable docstring annotations"
    )
    
    parser.add_argument(
        "--no-markdown",
        action="store_true",
        help="Disable markdown formatting when saving to file"
    )
    
    parser.add_argument(
        "--title",
        default="PROJECT STRUCTURE",
        help="Custom title for markdown header (default: 'PROJECT STRUCTURE')"
    )
    
    args = parser.parse_args()
    
    # Validate path
    if not args.path.exists():
        print(f"Error: Path '{args.path}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    if not args.path.is_dir():
        print(f"Error: Path '{args.path}' is not a directory", file=sys.stderr)
        sys.exit(1)
    
    # Parse gitignore from the repository root
    repo_root = Path.cwd()
    gitignore_path = repo_root / '.gitignore'
    gitignore_patterns = parse_gitignore(gitignore_path)
    
    # Generate tree
    tree_lines = generate_tree(
        args.path,
        prefix="",
        is_last=True,
        max_depth=args.max_depth,
        annotations=not args.no_annotations,
        gitignore_patterns=gitignore_patterns,
        additional_excludes=args.exclude,
        base_path=args.path
    )
    
    # Format output
    if args.output:
        # Saving to file - use markdown formatting unless disabled
        if args.no_markdown:
            # Plain output
            content = f"{args.path.resolve()}/\n" + "\n".join(tree_lines) + "\n"
        else:
            # Markdown formatted
            content = format_with_markdown(
                tree_lines,
                args.path,
                title=args.title,
                include_timestamp=True
            )
        
        # Write to file
        args.output.write_text(content, encoding='utf-8')
        print(f"Tree structure written to {args.output}", file=sys.stderr)
    else:
        # Print to stdout
        print(f"{args.path.resolve()}/")
        for line in tree_lines:
            print(line)


if __name__ == "__main__":
    main()
