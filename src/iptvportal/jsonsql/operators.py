"""Operator mappings for SQL to JSONSQL conversion."""

from typing import Any

# Comparison operators - support both symbol and keyword forms
COMPARISON_OPERATORS = {
    "=": "eq",
    "==": "eq",
    "EQ": "eq",
    "!=": "neq",
    "<>": "neq",
    "NEQ": "neq",
    ">": "gt",
    "GT": "gt",
    ">=": "gte",
    "GTE": "gte",
    "<": "lt",
    "LT": "lt",
    "<=": "lte",
    "LTE": "lte",
    "IS": "is",
    "IS_NOT": "is_not",
}

# Logical operators
LOGICAL_OPERATORS = {
    "AND": "and",
    "OR": "or",
    "NOT": "not",
}

# Pattern matching operators
PATTERN_OPERATORS = {
    "LIKE": "like",
    "ILIKE": "ilike",
}

# Set operators
SET_OPERATORS = {
    "IN": "in",
}

# Mathematical operators
MATH_OPERATORS = {
    "+": "add",
    "ADD": "add",
    "-": "sub",
    "SUB": "sub",
    "*": "mul",
    "MUL": "mul",
    "/": "div",
    "DIV": "div",
    "%": "mod",
    "MOD": "mod",
}


def build_comparison(operator: str, left: Any, right: Any) -> dict[str, list[Any]]:
    """Build a comparison operation in JSONSQL format."""
    jsonsql_op = COMPARISON_OPERATORS.get(operator.upper())
    if not jsonsql_op:
        raise ValueError(f"Unsupported comparison operator: {operator}")
    return {jsonsql_op: [left, right]}


def build_logical(operator: str, operands: list[Any]) -> dict[str, list[Any]]:
    """Build a logical operation in JSONSQL format."""
    jsonsql_op = LOGICAL_OPERATORS.get(operator.upper())
    if not jsonsql_op:
        raise ValueError(f"Unsupported logical operator: {operator}")
    return {jsonsql_op: operands}


def build_pattern(operator: str, column: Any, pattern: str) -> dict[str, list[Any]]:
    """Build a pattern matching operation in JSONSQL format."""
    jsonsql_op = PATTERN_OPERATORS.get(operator.upper())
    if not jsonsql_op:
        raise ValueError(f"Unsupported pattern operator: {operator}")
    return {jsonsql_op: [column, pattern]}


def build_in(column: Any, values: list[Any]) -> dict[str, list[Any]]:
    """Build an IN operation in JSONSQL format."""
    return {"in": [column, values]}


def build_not(operand: Any) -> dict[str, Any]:
    """Build a NOT operation in JSONSQL format."""
    return {"not": operand}


def build_math(operator: str, left: Any, right: Any) -> dict[str, list[Any]]:
    """Build a mathematical operation in JSONSQL format."""
    jsonsql_op = MATH_OPERATORS.get(operator.upper() if operator.isalpha() else operator)
    if not jsonsql_op:
        raise ValueError(f"Unsupported math operator: {operator}")
    return {jsonsql_op: [left, right]}


def build_is(column: Any, value: Any) -> dict[str, list[Any]]:
    """Build an IS operation in JSONSQL format."""
    return {"is": [column, value]}


def build_is_not(column: Any, value: Any) -> dict[str, list[Any]]:
    """Build an IS NOT operation in JSONSQL format."""
    return {"is_not": [column, value]}
