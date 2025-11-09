"""Transpiler-specific exceptions."""


class TranspilerError(Exception):
    """Base exception for transpiler errors."""

    pass


class UnsupportedFeatureError(TranspilerError):
    """Raised when an unsupported SQL feature is encountered."""

    pass


class ParseError(TranspilerError):
    """Raised when SQL parsing fails."""

    pass
