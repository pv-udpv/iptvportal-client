"""Function mappings for SQL to JSONSQL conversion."""

from typing import Any

def build_function(name: str, args: list[Any], alias: str | None = None) -> dict[str, Any]:
    """
    Build a function call in JSONSQL format.
    
    Args:
        name: Function name (e.g., 'COUNT', 'SUM')
        args: Function arguments
        alias: Optional alias for the result
        
    Returns:
        Dictionary representing the function in JSONSQL format
    """
    result: dict[str, Any] = {
        "function": name.lower(),
        "args": args if len(args) > 1 else args[0] if args else []
    }
    
    if alias:
        result["as"] = alias
        
    return result

def build_distinct_function(args: list[Any]) -> dict[str, Any]:
    """
    Build a DISTINCT function in JSONSQL format.
    
    Args:
        args: Columns to select distinctly
        
    Returns:
        Dictionary representing DISTINCT in JSONSQL format
    """
    return {
        "function": "distinct",
        "args": args if len(args) > 1 else args[0] if args else []
    }

def build_aggregate_function(name: str, column: Any, alias: str | None = None) -> dict[str, Any]:
    """
    Build an aggregate function (COUNT, SUM, AVG, etc.) in JSONSQL format.
    
    Args:
        name: Aggregate function name
        column: Column to aggregate
        alias: Optional alias for the result
        
    Returns:
        Dictionary representing the aggregate function
    """
    return build_function(name, [column], alias)

def build_nested_function(outer_func: str, inner_func: str, 
                         inner_args: list[Any], alias: str | None = None) -> dict[str, Any]:
    """
    Build nested function calls like COUNT(DISTINCT column).
    
    Args:
        outer_func: Outer function name (e.g., 'COUNT')
        inner_func: Inner function name (e.g., 'DISTINCT')
        inner_args: Arguments for inner function
        alias: Optional alias for the result
        
    Returns:
        Dictionary representing nested functions
    """
    inner = build_function(inner_func, inner_args)
    return build_function(outer_func, [inner], alias)

# Common SQL functions that need special handling
SPECIAL_FUNCTIONS = {
    "REGEXP_REPLACE": "regexp_replace",
    "DATE": "date",
    "COUNT": "count",
    "SUM": "sum",
    "AVG": "avg",
    "MIN": "min",
    "MAX": "max",
    "DISTINCT": "distinct",
}

def normalize_function_name(name: str) -> str:
    """Normalize function name to JSONSQL format."""
    return SPECIAL_FUNCTIONS.get(name.upper(), name.lower())
