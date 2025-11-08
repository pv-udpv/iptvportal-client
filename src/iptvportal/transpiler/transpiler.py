"""Main SQL to JSONSQL transpiler."""

from typing import Any, Optional
import sqlglot
from sqlglot import exp

from .exceptions import TranspilerError, UnsupportedFeatureError, ParseError
from .operators import (
    build_comparison,
    build_logical,
    build_pattern,
    build_in,
    build_not,
    build_math,
    build_is,
    build_is_not,
    COMPARISON_OPERATORS,
    LOGICAL_OPERATORS,
    PATTERN_OPERATORS,
    MATH_OPERATORS,
)
from .functions import build_function, build_distinct_function, normalize_function_name


class SQLTranspiler:
    """
    Transpiler for converting SQL (PostgreSQL dialect) to JSONSQL format.

    Example:
        >>> transpiler = SQLTranspiler()
        >>> result = transpiler.transpile("SELECT id, name FROM users WHERE age > 18")
        >>> print(result)
        {'data': ['id', 'name'], 'from': 'users', 'where': {'gt': ['age', 18]}}
    """

    def __init__(
        self,
        dialect: str = "postgres",
        schema_registry: Optional[Any] = None,
        auto_order_by_id: bool = True,
    ):
        """
        Initialize the transpiler.

        Args:
            dialect: SQL dialect to use (default: 'postgres')
            schema_registry: Optional SchemaRegistry for SELECT * expansion
            auto_order_by_id: Automatically add ORDER BY id to SELECT queries without ordering
        """
        self.dialect = dialect
        self.schema_registry = schema_registry
        self.auto_order_by_id = auto_order_by_id

    def transpile(self, sql: str) -> dict[str, Any]:
        """
        Transpile SQL query to JSONSQL format.

        Args:
            sql: SQL query string

        Returns:
            Dictionary representing the query in JSONSQL format

        Raises:
            ParseError: If SQL cannot be parsed
            TranspilerError: If transpilation fails
            UnsupportedFeatureError: If an unsupported SQL feature is used
        """
        try:
            # Parse SQL
            parsed = sqlglot.parse_one(sql, dialect=self.dialect)

            # Handle different statement types
            if isinstance(parsed, exp.Select):
                return self._transpile_select(parsed)
            elif isinstance(parsed, exp.Insert):
                return self._transpile_insert(parsed)
            elif isinstance(parsed, exp.Update):
                return self._transpile_update(parsed)
            elif isinstance(parsed, exp.Delete):
                return self._transpile_delete(parsed)
            else:
                raise UnsupportedFeatureError(f"Unsupported statement type: {type(parsed)}")

        except sqlglot.errors.ParseError as e:
            raise ParseError(f"Failed to parse SQL: {e}") from e
        except Exception as e:
            if isinstance(e, (TranspilerError, UnsupportedFeatureError, ParseError)):
                raise
            raise TranspilerError(f"Transpilation failed: {e}") from e

    def _transpile_select(self, select: exp.Select) -> dict[str, Any]:
        """Transpile SELECT statement."""
        result: dict[str, Any] = {}

        # Extract table name for schema lookup
        from_table = None
        if select.args.get("from"):
            from_expr = select.args["from"].this
            if isinstance(from_expr, exp.Table):
                from_table = from_expr.name

        # Handle SELECT columns
        if select.expressions:
            result["data"] = self._transpile_select_columns(select.expressions, from_table)

        # Handle FROM clause with JOINs
        if select.args.get("from"):
            result["from"] = self._transpile_from(select.args["from"], select.args.get("joins"))

        # Handle WHERE clause
        if select.args.get("where"):
            result["where"] = self._transpile_expression(select.args["where"].this)

        # Handle GROUP BY
        if select.args.get("group"):
            result["group_by"] = self._transpile_group_by(select.args["group"])

        # Handle HAVING
        if select.args.get("having"):
            result["having"] = self._transpile_expression(select.args["having"].this)

        # Handle ORDER BY
        if select.args.get("order"):
            result["order_by"] = self._transpile_order_by(select.args["order"])
        elif self.auto_order_by_id and from_table and not isinstance(from_table, dict):
            # Auto-add ORDER BY id if:
            # 1. auto_order_by_id is enabled
            # 2. Query has a simple table (not a subquery)
            # 3. No explicit ORDER BY clause
            # 4. No GROUP BY clause (aggregate queries don't need ORDER BY id)
            # 5. No aggregate functions in SELECT (they conflict with ORDER BY)
            # 6. Query selects id field (either explicitly or via SELECT *)
            # 7. No JOINs (ORDER BY id would be ambiguous with multiple tables)
            has_group_by = select.args.get("group") is not None
            has_aggregate = self._has_aggregate_functions(select.expressions)
            has_id_field = self._has_id_field(select.expressions)
            has_joins = bool(select.args.get("joins"))

            if not has_group_by and not has_aggregate and has_id_field and not has_joins:
                result["order_by"] = "id"

        # Handle LIMIT
        if select.args.get("limit"):
            result["limit"] = self._transpile_limit(select.args["limit"])

        # Handle OFFSET
        if select.args.get("offset"):
            result["offset"] = self._transpile_offset(select.args["offset"])

        # Handle DISTINCT
        if select.args.get("distinct"):
            result["distinct"] = True

        return result

    def _has_id_field(self, expressions: list[exp.Expression]) -> bool:
        """
        Check if the SELECT expressions include the 'id' field.

        Returns True if:
        - SELECT * is used
        - 'id' field is explicitly selected
        """

        def check_expr(expr: exp.Expression) -> bool:
            """Check if expression represents the id field."""
            # Check for SELECT *
            if isinstance(expr, exp.Star):
                return True

            # Check for explicit 'id' column
            if isinstance(expr, exp.Column):
                return expr.name.lower() == "id"

            # Check within alias
            if isinstance(expr, exp.Alias):
                return check_expr(expr.this)

            return False

        return any(check_expr(expr) for expr in expressions)

    def _has_aggregate_functions(self, expressions: list[exp.Expression]) -> bool:
        """
        Check if any of the SELECT expressions contain aggregate functions.

        Aggregate functions: COUNT, SUM, AVG, MAX, MIN, etc.
        """
        aggregate_functions = {
            "COUNT",
            "SUM",
            "AVG",
            "MAX",
            "MIN",
            "STDDEV",
            "VARIANCE",
            "ARRAY_AGG",
            "STRING_AGG",
            "BOOL_AND",
            "BOOL_OR",
            "EVERY",
            "JSON_AGG",
            "JSONB_AGG",
        }

        def check_expr(expr: exp.Expression) -> bool:
            """Recursively check if expression contains aggregate functions."""
            if isinstance(expr, (exp.Anonymous, exp.Func)):
                func_name = expr.sql_name() if hasattr(expr, "sql_name") else type(expr).__name__
                if func_name.upper() in aggregate_functions:
                    return True

            # Check nested expressions
            if isinstance(expr, exp.Alias):
                return check_expr(expr.this)

            # Check function arguments
            if hasattr(expr, "expressions") and expr.expressions:
                for arg in expr.expressions:
                    if check_expr(arg):
                        return True

            if hasattr(expr, "this") and expr.this and isinstance(expr.this, exp.Expression):
                return check_expr(expr.this)

            return False

        return any(check_expr(expr) for expr in expressions)

    def _transpile_select_columns(
        self, expressions: list[exp.Expression], from_table: Optional[str] = None
    ) -> list[Any]:
        """Transpile SELECT column expressions."""
        columns = []

        for expr in expressions:
            if isinstance(expr, exp.Star):
                # SELECT * - expand using schema if available
                if from_table and self.schema_registry and self.schema_registry.has(from_table):
                    schema = self.schema_registry.get(from_table)
                    columns.extend(schema.resolve_select_star())
                else:
                    columns.append("*")
            elif isinstance(expr, exp.Alias):
                # Column with alias
                column_expr = self._transpile_column_expression(expr.this)
                if isinstance(column_expr, dict) and "function" in column_expr:
                    column_expr["as"] = expr.alias
                    columns.append(column_expr)
                else:
                    columns.append(
                        {str(column_expr): expr.alias}
                        if not isinstance(column_expr, dict)
                        else {**column_expr, "as": expr.alias}
                    )
            else:
                # Simple column
                columns.append(self._transpile_column_expression(expr))

        return columns

    def _transpile_column_expression(self, expr: exp.Expression) -> Any:
        """Transpile a column expression."""
        if isinstance(expr, exp.Column):
            # Qualified column: table.column
            if expr.table:
                return {expr.table: expr.name}
            return expr.name
        elif isinstance(expr, exp.Literal):
            return self._transpile_literal(expr)
        elif isinstance(expr, exp.Anonymous) or isinstance(expr, exp.Func):
            # Function call
            return self._transpile_function(expr)
        elif isinstance(expr, exp.Distinct):
            # DISTINCT
            args = [self._transpile_column_expression(arg) for arg in expr.expressions]
            return build_distinct_function(args)
        else:
            # Try to transpile as expression
            return self._transpile_expression(expr)

    def _transpile_function(self, func: exp.Expression) -> dict[str, Any]:
        """Transpile function call."""
        func_name = func.sql_name() if hasattr(func, "sql_name") else type(func).__name__
        func_name = normalize_function_name(func_name)

        # Get function arguments
        args = []

        # First check if there are expressions (multiple arguments)
        if hasattr(func, "expressions") and func.expressions:
            for arg in func.expressions:
                if isinstance(arg, exp.Distinct):
                    # Handle DISTINCT inside function like COUNT(DISTINCT col)
                    inner_args = [self._transpile_column_expression(a) for a in arg.expressions]
                    args.append(build_distinct_function(inner_args))
                else:
                    args.append(self._transpile_expression(arg))
        # Then check for 'this' (single argument like COUNT(*) or COUNT(column))
        elif hasattr(func, "this") and func.this:
            # Special handling for DISTINCT in 'this' (e.g., COUNT(DISTINCT col))
            if isinstance(func.this, exp.Distinct):
                inner_args = [self._transpile_column_expression(a) for a in func.this.expressions]
                args.append(build_distinct_function(inner_args))
            else:
                args.append(self._transpile_expression(func.this))

        return build_function(func_name, args)

    def _transpile_from(self, from_clause: exp.From, joins: list[exp.Join] | None = None) -> Any:
        """Transpile FROM clause with JOINs from SELECT statement."""
        tables = []

        # Handle main table
        main_table = from_clause.this
        if isinstance(main_table, exp.Table):
            # Simple table without alias
            if not main_table.alias:
                # Check if there are joins - if so, need full format
                if joins:
                    table_ref = {"table": main_table.name, "as": main_table.name}
                    tables.append(table_ref)
                else:
                    # Simple case: just return table name
                    return main_table.name
            else:
                # Table with alias
                table_ref = {"table": main_table.name, "as": main_table.alias}
                tables.append(table_ref)
        elif isinstance(main_table, exp.Subquery):
            # Subquery in FROM
            subquery_result = self._transpile_select(main_table.this)
            table_ref = {"select": subquery_result}
            if main_table.alias:
                table_ref["as"] = main_table.alias
            tables.append(table_ref)

        # Handle JOINs from SELECT statement
        if joins:
            for join in joins:
                tables.append(self._transpile_join(join))

        # Return list of tables for joins
        return tables

    def _transpile_join(self, join: exp.Join) -> dict[str, Any]:
        """Transpile JOIN clause."""
        join_table = join.this

        result: dict[str, Any] = {}

        # Determine join type (default to INNER JOIN)
        join_type = "join"  # JSONSQL uses "join" for all join types

        # Get table name
        if isinstance(join_table, exp.Table):
            result["join"] = join_table.name
            if join_table.alias:
                result["as"] = join_table.alias
        elif isinstance(join_table, exp.Subquery):
            subquery_result = self._transpile_select(join_table.this)
            result["join"] = {"select": subquery_result}
            if join_table.alias:
                result["as"] = join_table.alias

        # Handle ON condition
        if join.args.get("on"):
            on_condition = self._transpile_expression(join.args["on"])
            # Wrap in AND if not already wrapped
            if isinstance(on_condition, dict) and "and" not in on_condition:
                on_condition = {"and": [on_condition]}
            result["on"] = on_condition

        return result

    def _transpile_expression(self, expr: exp.Expression) -> Any:
        """Transpile general expression."""
        if isinstance(expr, exp.Column):
            if expr.table:
                return {expr.table: expr.name}
            return expr.name

        elif isinstance(expr, exp.Literal):
            return self._transpile_literal(expr)

        elif isinstance(expr, exp.Is):
            # Handle IS NULL / IS <value>
            left = self._transpile_expression(expr.this)
            right = self._transpile_expression(expr.expression)
            return build_is(left, right)

        elif isinstance(expr, exp.Binary):
            return self._transpile_binary(expr)

        elif isinstance(expr, exp.In):
            return self._transpile_in(expr)

        elif isinstance(expr, exp.Not):
            # Check if this is IS NOT (NOT wrapping IS expression)
            if isinstance(expr.this, exp.Is):
                # Handle IS NOT NULL / IS NOT <value>
                left = self._transpile_expression(expr.this.this)
                right = self._transpile_expression(expr.this.expression)
                return build_is_not(left, right)
            else:
                # Regular NOT operator
                operand = self._transpile_expression(expr.this)
                return build_not(operand)

        elif isinstance(expr, (exp.Anonymous, exp.Func)):
            return self._transpile_function(expr)

        elif isinstance(expr, exp.Paren):
            return self._transpile_expression(expr.this)

        elif isinstance(expr, exp.Star):
            return "*"

        elif isinstance(expr, exp.Alias):
            return self._transpile_column_expression(expr.this)

        elif isinstance(expr, exp.Null):
            # Handle NULL literal
            return None

        elif isinstance(expr, exp.Boolean):
            # Handle TRUE/FALSE literals
            return expr.this

        else:
            # Fallback: try to convert to string
            return str(expr)

    def _transpile_binary(self, binary: exp.Binary) -> dict[str, Any]:
        """Transpile binary operations (comparisons, logical ops, math)."""
        operator = binary.key.upper()
        left = self._transpile_expression(binary.left)
        right = self._transpile_expression(binary.right)

        # Check for comparison operators (including IS/IS NOT)
        if operator in COMPARISON_OPERATORS:
            return build_comparison(operator, left, right)

        # Check for logical operators
        elif operator in LOGICAL_OPERATORS:
            return build_logical(operator, [left, right])

        # Check for pattern matching
        elif operator in PATTERN_OPERATORS:
            return build_pattern(operator, left, right)

        # Check for mathematical operators
        elif operator in MATH_OPERATORS or binary.key in MATH_OPERATORS:
            # Use the symbol for operators like +, -, *, /, %
            op_key = binary.key if binary.key in MATH_OPERATORS else operator
            return build_math(op_key, left, right)

        else:
            raise UnsupportedFeatureError(f"Unsupported binary operator: {operator}")

    def _transpile_in(self, in_expr: exp.In) -> dict[str, Any]:
        """Transpile IN expression."""
        column = self._transpile_expression(in_expr.this)

        # Handle values
        values = []
        if isinstance(in_expr.expressions[0], exp.Tuple):
            for val in in_expr.expressions[0].expressions:
                values.append(self._transpile_expression(val))
        else:
            for val in in_expr.expressions:
                values.append(self._transpile_expression(val))

        result = build_in(column, values)

        # Handle NOT IN
        if in_expr.args.get("negated"):
            result = build_not(result)

        return result

    def _transpile_literal(self, literal: exp.Literal) -> Any:
        """Transpile literal value."""
        if literal.is_string:
            return literal.this
        elif literal.is_int:
            return int(literal.this)
        elif literal.is_number:
            return float(literal.this)
        else:
            # Handle boolean and null
            value = literal.this.upper()
            if value == "TRUE":
                return True
            elif value == "FALSE":
                return False
            elif value == "NULL":
                return None
            return literal.this

    def _transpile_group_by(self, group: exp.Group) -> list[Any]:
        """Transpile GROUP BY clause."""
        result = []
        for expr in group.expressions:
            result.append(self._transpile_expression(expr))
        return result if len(result) > 1 else result[0]

    def _transpile_order_by(self, order: exp.Order) -> Any:
        """Transpile ORDER BY clause."""
        result = []
        for ordered in order.expressions:
            col = self._transpile_expression(ordered.this)
            # Note: JSONSQL might need special handling for ASC/DESC
            result.append(col)
        return result if len(result) > 1 else result[0]

    def _transpile_limit(self, limit: exp.Limit) -> int:
        """Transpile LIMIT clause."""
        return int(limit.expression.this)

    def _transpile_offset(self, offset: exp.Offset) -> int:
        """Transpile OFFSET clause."""
        return int(offset.expression.this)

    def _transpile_insert(self, insert: exp.Insert) -> dict[str, Any]:
        """Transpile INSERT statement."""
        result: dict[str, Any] = {}

        # Get table name
        if insert.this:
            result["into"] = insert.this.name

        # Get columns
        if insert.args.get("columns"):
            result["columns"] = [col.name for col in insert.args["columns"]]

        # Get values
        if insert.expression:
            if isinstance(insert.expression, exp.Values):
                values = []
                for tuple_expr in insert.expression.expressions:
                    row = [self._transpile_expression(val) for val in tuple_expr.expressions]
                    values.append(row)
                result["values"] = values

        # Handle RETURNING
        if insert.args.get("returning"):
            returning = [
                self._transpile_expression(expr) for expr in insert.args["returning"].expressions
            ]
            result["returning"] = returning if len(returning) > 1 else returning[0]

        return result

    def _transpile_update(self, update: exp.Update) -> dict[str, Any]:
        """Transpile UPDATE statement."""
        result: dict[str, Any] = {}

        # Get table name
        if update.this:
            result["table"] = update.this.name

        # Get SET clause
        if update.expressions:
            set_dict = {}
            for expr in update.expressions:
                if isinstance(expr, exp.EQ):
                    key = expr.left.name if isinstance(expr.left, exp.Column) else str(expr.left)
                    value = self._transpile_expression(expr.right)
                    set_dict[key] = value
            result["set"] = set_dict

        # Handle WHERE clause
        if update.args.get("where"):
            result["where"] = self._transpile_expression(update.args["where"].this)

        # Handle RETURNING
        if update.args.get("returning"):
            returning = [
                self._transpile_expression(expr) for expr in update.args["returning"].expressions
            ]
            result["returning"] = returning if len(returning) > 1 else returning[0]

        return result

    def _transpile_delete(self, delete: exp.Delete) -> dict[str, Any]:
        """Transpile DELETE statement."""
        result: dict[str, Any] = {}

        # Get table name
        if delete.this:
            result["from"] = delete.this.name

        # Handle WHERE clause
        if delete.args.get("where"):
            result["where"] = self._transpile_expression(delete.args["where"].this)

        # Handle RETURNING
        if delete.args.get("returning"):
            returning = [
                self._transpile_expression(expr) for expr in delete.args["returning"].expressions
            ]
            result["returning"] = returning if len(returning) > 1 else returning[0]

        return result
