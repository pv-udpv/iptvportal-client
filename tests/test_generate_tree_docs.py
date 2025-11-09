"""Tests for generate_tree_docs.py script."""

import sys
import tempfile
from pathlib import Path

import pytest

# Import the script functions
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from generate_tree_docs import (
    extract_docstring,
    format_with_markdown,
    generate_tree,
    parse_gitignore,
    should_exclude,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_python_file(temp_dir):
    """Create a sample Python file with a docstring."""
    py_file = temp_dir / "test.py"
    py_file.write_text(
        '"""Sample module docstring.\n\nMore details here.\n"""\n\ndef foo():\n    pass\n'
    )
    return py_file


@pytest.fixture
def sample_gitignore(temp_dir):
    """Create a sample .gitignore file."""
    gitignore = temp_dir / ".gitignore"
    gitignore.write_text(
        "# Python\n__pycache__/\n*.pyc\n\n# Build\ndist/\nbuild/\n\n# IDE\n.vscode/\n"
    )
    return gitignore


def test_parse_gitignore_valid_file(sample_gitignore):
    """Test parsing a valid gitignore file."""
    patterns = parse_gitignore(sample_gitignore)
    assert "__pycache__/" in patterns
    assert "*.pyc" in patterns
    assert "dist/" in patterns
    assert ".vscode/" in patterns
    # Comments should not be included
    assert not any(p.startswith("#") for p in patterns)


def test_parse_gitignore_nonexistent_file(temp_dir):
    """Test parsing a nonexistent gitignore file."""
    patterns = parse_gitignore(temp_dir / "nonexistent.gitignore")
    assert patterns == []


def test_extract_docstring_valid_file(sample_python_file):
    """Test extracting docstring from a Python file."""
    docstring = extract_docstring(sample_python_file)
    assert docstring == "Sample module docstring."


def test_extract_docstring_no_docstring(temp_dir):
    """Test extracting from a file without docstring."""
    py_file = temp_dir / "no_doc.py"
    py_file.write_text("# Just a comment\ndef foo():\n    pass\n")
    docstring = extract_docstring(py_file)
    assert docstring == "Just a comment"


def test_extract_docstring_invalid_file(temp_dir):
    """Test extracting from an invalid Python file."""
    py_file = temp_dir / "invalid.py"
    py_file.write_text("this is not valid python {{{")
    docstring = extract_docstring(py_file)
    assert docstring is None


def test_should_exclude_git_directory(temp_dir):
    """Test that .git directory is always excluded."""
    git_dir = temp_dir / ".git"
    git_dir.mkdir()
    assert should_exclude(git_dir, temp_dir, [], [])


def test_should_exclude_pycache_directory(temp_dir, sample_gitignore):
    """Test that __pycache__ is excluded based on gitignore."""
    patterns = parse_gitignore(sample_gitignore)
    pycache_dir = temp_dir / "__pycache__"
    pycache_dir.mkdir()
    assert should_exclude(pycache_dir, temp_dir, patterns, [])


def test_should_exclude_additional_patterns(temp_dir):
    """Test exclusion with additional patterns."""
    test_dir = temp_dir / "tests"
    test_dir.mkdir()
    assert should_exclude(test_dir, temp_dir, [], ["tests"])


def test_should_exclude_wildcard_pattern(temp_dir):
    """Test exclusion with wildcard patterns."""
    patterns = ["*.pyc"]
    pyc_file = temp_dir / "test.pyc"
    pyc_file.touch()
    assert should_exclude(pyc_file, temp_dir, patterns, [])


def test_generate_tree_basic(temp_dir):
    """Test basic tree generation."""
    # Create a simple structure
    (temp_dir / "file1.py").write_text('"""File 1 docstring."""')
    (temp_dir / "file2.py").write_text('"""File 2 docstring."""')
    subdir = temp_dir / "subdir"
    subdir.mkdir()
    (subdir / "file3.py").write_text('"""File 3 docstring."""')

    lines = generate_tree(temp_dir, base_path=temp_dir)

    # Check that files are included
    tree_text = "\n".join(lines)
    assert "file1.py" in tree_text
    assert "file2.py" in tree_text
    assert "subdir/" in tree_text
    assert "File 1 docstring" in tree_text


def test_generate_tree_with_max_depth(temp_dir):
    """Test tree generation with max depth limit."""
    # Create nested structure
    level1 = temp_dir / "level1"
    level1.mkdir()
    level2 = level1 / "level2"
    level2.mkdir()
    (level2 / "deep_file.py").write_text('"""Deep file."""')

    lines = generate_tree(temp_dir, max_depth=1, base_path=temp_dir)
    tree_text = "\n".join(lines)

    # Level 1 should be included
    assert "level1/" in tree_text
    # But level 2 should not (depth limit)
    assert "level2/" not in tree_text
    assert "deep_file.py" not in tree_text


def test_generate_tree_no_annotations(temp_dir):
    """Test tree generation without annotations."""
    (temp_dir / "file1.py").write_text('"""File 1 docstring."""')

    lines = generate_tree(temp_dir, annotations=False, base_path=temp_dir)
    tree_text = "\n".join(lines)

    # File should be included but not its docstring
    assert "file1.py" in tree_text
    assert "File 1 docstring" not in tree_text


def test_format_with_markdown():
    """Test markdown formatting."""
    tree_lines = ["└── test/", "    ├── file1.py", "    └── file2.py"]
    root_path = Path("/tmp/test")

    result = format_with_markdown(tree_lines, root_path)

    # Check markdown elements
    assert result.startswith("# PROJECT STRUCTURE")
    assert "> Auto-generated on" in result
    assert "```sh" in result
    assert "```\n" in result
    assert str(root_path.resolve()) in result
    for line in tree_lines:
        assert line in result


def test_format_with_markdown_custom_title():
    """Test markdown formatting with custom title."""
    tree_lines = ["└── test/"]
    root_path = Path("/tmp/test")

    result = format_with_markdown(tree_lines, root_path, title="Custom Title")

    assert result.startswith("# Custom Title")


def test_format_with_markdown_no_timestamp():
    """Test markdown formatting without timestamp."""
    tree_lines = ["└── test/"]
    root_path = Path("/tmp/test")

    result = format_with_markdown(
        tree_lines, root_path, include_timestamp=False
    )

    assert "# PROJECT STRUCTURE" in result
    assert "> Auto-generated on" not in result


def test_generate_tree_respects_gitignore(temp_dir, sample_gitignore):
    """Test that tree generation respects gitignore patterns."""
    patterns = parse_gitignore(sample_gitignore)

    # Create files/dirs that should be excluded
    pycache = temp_dir / "__pycache__"
    pycache.mkdir()
    (pycache / "test.pyc").touch()

    dist = temp_dir / "dist"
    dist.mkdir()

    # Create files that should be included
    (temp_dir / "main.py").write_text('"""Main module."""')

    lines = generate_tree(
        temp_dir, gitignore_patterns=patterns, base_path=temp_dir
    )
    tree_text = "\n".join(lines)

    # Included
    assert "main.py" in tree_text

    # Excluded
    assert "__pycache__" not in tree_text
    assert "dist" not in tree_text


def test_generate_tree_sorting(temp_dir):
    """Test that tree items are sorted (directories first, then files)."""
    # Create files and directories in non-sorted order
    (temp_dir / "zebra.py").write_text('"""Zebra."""')
    (temp_dir / "apple.py").write_text('"""Apple."""')
    beta_dir = temp_dir / "beta"
    beta_dir.mkdir()
    alpha_dir = temp_dir / "alpha"
    alpha_dir.mkdir()

    lines = generate_tree(temp_dir, base_path=temp_dir)
    tree_text = "\n".join(lines)

    # Find positions
    alpha_pos = tree_text.find("alpha/")
    beta_pos = tree_text.find("beta/")
    apple_pos = tree_text.find("apple.py")
    zebra_pos = tree_text.find("zebra.py")

    # Directories should come before files
    assert alpha_pos < apple_pos
    assert beta_pos < apple_pos

    # Items should be alphabetically sorted within groups
    assert alpha_pos < beta_pos
    assert apple_pos < zebra_pos
