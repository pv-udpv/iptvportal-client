"""Tests for SQL to JSONSQL transpiler."""

import pytest
from iptvportal.transpiler import SQLTranspiler
from iptvportal.transpiler.exceptions import TranspilerError, ParseError

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
        assert "select" in result["from"]

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
