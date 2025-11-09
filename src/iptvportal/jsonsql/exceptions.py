# ruff: noqa: I001
"""Exceptions used in the JSONSQL module.

Includes transpiler-specific errors and re-exports selected core
exceptions for backwards compatibility in tests and examples.
"""

from iptvportal.exceptions import AuthenticationError  # re-export for compat


__all__ = [
    "AuthenticationError",
    "TranspilerError",
    "UnsupportedFeatureError",
    "ParseError",
]


class TranspilerError(Exception):
    """Base exception for transpiler errors."""

    pass


class UnsupportedFeatureError(TranspilerError):
    """Raised when an unsupported SQL feature is encountered."""

    pass


class ParseError(TranspilerError):
    """Raised when SQL parsing fails."""

    pass
