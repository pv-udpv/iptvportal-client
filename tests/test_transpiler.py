"""Tests for SQL to JSONSQL transpiler."""

import pytest

from iptvportal.jsonsql import SQLTranspiler
from iptvportal.jsonsql.exceptions import ParseError, TranspilerError


@pytest.fixture
def transpiler():
    """Create a transpiler instance."""
    return SQLTranspiler()


class TestBasicSelect:
    """Test basic SELECT statements."""

    def test_simple_select(self, transpiler):
        """Test simple SELECT with columns."""
        sql = "SELECT id, name FROM users"
        result = transpiler.transpile(sql)
        assert result["data"] == ["id", "name"]
        assert result["from"] == "users"

    def test_select_star(self, transpiler):
        """Test SELECT *."""
        sql = "SELECT * FROM users"
        result = transpiler.transpile(sql)
        assert result["data"] == ["*"]
        assert result["from"] == "users"

    def test_select_with_alias(self, transpiler):
        """Test SELECT with column aliases."""
        sql = "SELECT id, name AS user_name FROM users"
        result = transpiler.transpile(sql)
        assert "data" in result
        assert result["from"] == "users"

    def test_select_with_limit(self, transpiler):
        """Test SELECT with LIMIT."""
        sql = "SELECT id, name FROM users LIMIT 10"
        result = transpiler.transpile(sql)
        assert result["limit"] == 10

    def test_select_with_offset(self, transpiler):
        """Test SELECT with OFFSET."""
        sql = "SELECT id, name FROM users LIMIT 10 OFFSET 5"
        result = transpiler.transpile(sql)
        assert result["limit"] == 10
        assert result["offset"] == 5


class TestWhereClause:
    """Test WHERE clause transpilation."""

    def test_simple_where(self, transpiler):
        """Test simple WHERE with comparison."""
        sql = "SELECT id FROM users WHERE age > 18"
        result = transpiler.transpile(sql)
        assert "where" in result
        assert "gt" in result["where"]

    def test_where_and(self, transpiler):
        """Test WHERE with AND."""
        sql = "SELECT id FROM users WHERE age > 18 AND disabled = false"
        result = transpiler.transpile(sql)
        assert "where" in result
        assert "and" in result["where"]

    def test_where_or(self, transpiler):
        """Test WHERE with OR."""
        sql = "SELECT id FROM users WHERE age < 18 OR age > 65"
        result = transpiler.transpile(sql)
        assert "where" in result
        assert "or" in result["where"]

    def test_where_in(self, transpiler):
        """Test WHERE with IN."""
        sql = "SELECT id FROM users WHERE status IN ('active', 'pending')"
        result = transpiler.transpile(sql)
        assert "where" in result
        assert "in" in result["where"]

    def test_where_like(self, transpiler):
        """Test WHERE with LIKE."""
        sql = "SELECT id FROM users WHERE name LIKE 'admin%'"
        result = transpiler.transpile(sql)
        assert "where" in result
        assert "like" in result["where"]

    def test_where_is(self, transpiler):
        """Test WHERE with IS (from docs/jsonsql.md)."""
        sql = "SELECT id, name FROM media WHERE is_tv IS TRUE"
        result = transpiler.transpile(sql)
        assert "where" in result
        assert "is" in result["where"]
        assert result["where"]["is"] == ["is_tv", True]

    def test_where_is_not(self, transpiler):
        """Test WHERE with IS NOT."""
        sql = "SELECT id FROM users WHERE disabled IS NOT NULL"
        result = transpiler.transpile(sql)
        assert "where" in result
        assert "is_not" in result["where"]


class TestMathOperators:
    """Test mathematical operators (from docs/jsonsql.md)."""

    def test_addition(self, transpiler):
        """Test addition operator."""
        sql = "SELECT id, price + tax AS total FROM orders"
        result = transpiler.transpile(sql)
        assert "data" in result
        # Check that addition is in the data
        total_field = result["data"][1]
        assert isinstance(total_field, dict)
        assert "add" in total_field or "as" in total_field

    def test_subtraction(self, transpiler):
        """Test subtraction operator."""
        sql = "SELECT id, price - discount AS final_price FROM products"
        result = transpiler.transpile(sql)
        assert "data" in result

    def test_multiplication(self, transpiler):
        """Test multiplication operator."""
        sql = "SELECT id, quantity * price AS total FROM order_items"
        result = transpiler.transpile(sql)
        assert "data" in result

    def test_division(self, transpiler):
        """Test division operator."""
        sql = "SELECT id, total / count AS average FROM statistics"
        result = transpiler.transpile(sql)
        assert "data" in result

    def test_modulo(self, transpiler):
        """Test modulo operator."""
        sql = "SELECT id, value % 10 AS remainder FROM numbers"
        result = transpiler.transpile(sql)
        assert "data" in result


class TestJoins:
    """Test JOIN transpilation."""

    def test_inner_join(self, transpiler):
        """Test INNER JOIN."""
        sql = """
        SELECT t.start, c.name 
        FROM terminal_playlog t
        JOIN tv_channel c ON c.id = t.channel_id
        """
        result = transpiler.transpile(sql)
        assert "from" in result
        assert isinstance(result["from"], list)
        assert len(result["from"]) == 2
        assert result["from"][1]["join"] == "tv_channel"
        assert "on" in result["from"][1]

    def test_multiple_joins(self, transpiler):
        """Test multiple JOINs."""
        sql = """
        SELECT t.start, c.name, p.title
        FROM terminal_playlog t
        JOIN tv_channel c ON c.id = t.channel_id
        JOIN tv_program p ON p.id = t.program_id
        """
        result = transpiler.transpile(sql)
        assert isinstance(result["from"], list)
        assert len(result["from"]) == 3


class TestFunctions:
    """Test SQL function transpilation."""

    def test_count_star(self, transpiler):
        """Test COUNT(*)."""
        sql = "SELECT COUNT(*) FROM users"
        result = transpiler.transpile(sql)
        assert "data" in result
        assert isinstance(result["data"][0], dict)
        assert result["data"][0]["function"] == "count"

    def test_count_distinct(self, transpiler):
        """Test COUNT(DISTINCT column)."""
        sql = "SELECT COUNT(DISTINCT user_id) FROM sessions"
        result = transpiler.transpile(sql)
        assert "data" in result
        func = result["data"][0]
        assert func["function"] == "count"
        assert isinstance(func["args"], dict)
        assert func["args"]["function"] == "distinct"

    def test_aggregate_with_alias(self, transpiler):
        """Test aggregate function with alias."""
        sql = "SELECT COUNT(*) AS total FROM users"
        result = transpiler.transpile(sql)
        assert result["data"][0]["as"] == "total"


class TestGroupBy:
    """Test GROUP BY transpilation."""

    def test_simple_group_by(self, transpiler):
        """Test simple GROUP BY."""
        sql = "SELECT status, COUNT(*) FROM users GROUP BY status"
        result = transpiler.transpile(sql)
        assert "group_by" in result

    def test_multiple_group_by(self, transpiler):
        """Test GROUP BY with multiple columns."""
        sql = "SELECT status, city, COUNT(*) FROM users GROUP BY status, city"
        result = transpiler.transpile(sql)
        assert "group_by" in result
        assert isinstance(result["group_by"], list)


class TestOrderBy:
    """Test ORDER BY transpilation."""

    def test_simple_order_by(self, transpiler):
        """Test simple ORDER BY."""
        sql = "SELECT id, name FROM users ORDER BY name"
        result = transpiler.transpile(sql)
        assert "order_by" in result


class TestSubqueries:
    """Test subquery transpilation."""

    def test_subquery_in_from(self, transpiler):
        """Test subquery in FROM clause."""
        sql = """
        SELECT q.id 
        FROM (SELECT id FROM users WHERE age > 18) AS q
        """
        result = transpiler.transpile(sql)
        assert "from" in result
        assert isinstance(result["from"], list)
        assert len(result["from"]) == 1
        assert "select" in result["from"][0]


class TestInsert:
    """Test INSERT statement transpilation."""

    def test_simple_insert(self, transpiler):
        """Test simple INSERT."""
        sql = "INSERT INTO users (name, email) VALUES ('John', 'john@example.com')"
        result = transpiler.transpile(sql)
        assert result["into"] == "users"
        assert result["columns"] == ["name", "email"]
        assert result["values"] == [["John", "john@example.com"]]


class TestUpdate:
    """Test UPDATE statement transpilation."""

    def test_simple_update(self, transpiler):
        """Test simple UPDATE."""
        sql = "UPDATE users SET name = 'Jane' WHERE id = 1"
        result = transpiler.transpile(sql)
        assert result["table"] == "users"
        assert result["set"] == {"name": "Jane"}
        assert "where" in result


class TestDelete:
    """Test DELETE statement transpilation."""

    def test_simple_delete(self, transpiler):
        """Test simple DELETE."""
        sql = "DELETE FROM users WHERE id = 1"
        result = transpiler.transpile(sql)
        assert result["from"] == "users"
        assert "where" in result


class TestComplexQueries:
    """Test complex real-world queries."""

    def test_complex_join_query(self, transpiler):
        """Test complex query with multiple JOINs and WHERE."""
        sql = """
        SELECT 
            t.start AS playlog__start,
            t.domain_id AS playlog__domain_id,
            t.mac_addr AS playlog__mac_addr,
            c.name AS playlog__channel_name
        FROM terminal_playlog t
        JOIN tv_channel c ON c.id = t.channel_id
        WHERE t.start > '2020-02-17 00:00:00' 
        AND t.start < '2020-04-20 00:00:00'
        """
        result = transpiler.transpile(sql)
        assert "data" in result
        assert "from" in result
        assert isinstance(result["from"], list)
        assert "where" in result
        assert "and" in result["where"]


class TestDocExamples:
    """Test examples from docs/jsonsql.md."""

    def test_doc_select_example(self, transpiler):
        """Test SELECT example from docs."""
        sql = """
        SELECT id, name, protocol, inet_addr, port
        FROM media
        WHERE is_tv IS TRUE
        ORDER BY name
        """
        result = transpiler.transpile(sql)
        assert result["data"] == ["id", "name", "protocol", "inet_addr", "port"]
        assert result["from"] == "media"
        assert "where" in result
        assert "is" in result["where"]
        assert result["order_by"] == "name"

    def test_doc_insert_example(self, transpiler):
        """Test INSERT example from docs."""
        sql = """
        INSERT INTO package (name, paid) VALUES
          ('movie', true), ('sports', true)
        RETURNING id
        """
        result = transpiler.transpile(sql)
        assert result["into"] == "package"
        assert result["columns"] == ["name", "paid"]
        assert len(result["values"]) == 2
        assert result["values"][0] == ["movie", True]
        assert result["values"][1] == ["sports", True]
        assert result["returning"] == "id"

    def test_doc_update_example(self, transpiler):
        """Test UPDATE example from docs."""
        sql = """
        UPDATE subscriber 
        SET disabled = TRUE 
        WHERE username = '12345'
        RETURNING id
        """
        result = transpiler.transpile(sql)
        assert result["table"] == "subscriber"
        assert result["set"] == {"disabled": True}
        assert "where" in result
        assert result["where"]["eq"] == ["username", "12345"]
        assert result["returning"] == "id"

    def test_doc_delete_with_subquery(self, transpiler):
        """Test DELETE with subquery example from docs."""
        sql = """
        DELETE FROM terminal
        WHERE subscriber_id IN (
          SELECT id FROM subscriber WHERE username = 'test'
        )
        RETURNING id
        """
        result = transpiler.transpile(sql)
        assert result["from"] == "terminal"
        assert "where" in result
        assert "in" in result["where"]
        assert result["returning"] == "id"

    def test_doc_aggregate_example(self, transpiler):
        """Test aggregate functions example from docs."""
        sql = """
        SELECT 
            COUNT(*) AS cnt,
            COUNT(DISTINCT mac_addr) AS uniq
        FROM terminal_playlog
        """
        result = transpiler.transpile(sql)
        assert "data" in result
        assert len(result["data"]) == 2
        # First function: COUNT(*)
        assert result["data"][0]["function"] == "count"
        assert result["data"][0]["as"] == "cnt"
        # Second function: COUNT(DISTINCT mac_addr)
        assert result["data"][1]["function"] == "count"
        assert result["data"][1]["as"] == "uniq"

    def test_doc_complex_join_example(self, transpiler):
        """Test complex JOIN example from docs."""
        sql = """
        SELECT
          subscriber.id,
          subscriber.username,
          COUNT(terminal.id) AS term_count
        FROM subscriber
        JOIN terminal ON subscriber.id = terminal.subscriber_id
        WHERE subscriber.created_at > '2023-01-01 00:00:00'
        GROUP BY subscriber.id, subscriber.username
        ORDER BY term_count DESC
        """
        result = transpiler.transpile(sql)
        assert "data" in result
        assert len(result["data"]) == 3
        assert isinstance(result["from"], list)
        assert len(result["from"]) == 2
        assert "where" in result
        assert "group_by" in result
        assert isinstance(result["group_by"], list)
        assert "order_by" in result


class TestErrors:
    """Test error handling."""

    def test_invalid_sql(self, transpiler):
        """Test that invalid SQL raises ParseError."""
        with pytest.raises(ParseError):
            transpiler.transpile("SELECT FROM")

    def test_empty_sql(self, transpiler):
        """Test that empty SQL raises error."""
        with pytest.raises((ParseError, TranspilerError)):
            transpiler.transpile("")
