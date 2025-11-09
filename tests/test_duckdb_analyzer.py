"""Tests for DuckDB analyzer functionality.

Run with:
    uv run pytest tests/test_duckdb_analyzer.py
    uv run pytest tests/test_duckdb_analyzer.py -v
"""

import pytest

from iptvportal.schema.duckdb_analyzer import DuckDBAnalyzer


class TestDuckDBAnalyzer:
    """Test DuckDBAnalyzer functionality."""

    @pytest.fixture
    def analyzer(self):
        """Create DuckDBAnalyzer instance."""
        return DuckDBAnalyzer()

    def test_analyzer_availability(self, analyzer):
        """Test that analyzer reports availability correctly."""
        # DuckDB may or may not be installed depending on environment
        # Just check the flag is set correctly
        assert isinstance(analyzer.available, bool)

    def test_analyze_sample_no_duckdb(self):
        """Test analyzer gracefully handles missing DuckDB."""
        analyzer = DuckDBAnalyzer()
        # Force unavailable state
        analyzer.available = False

        result = analyzer.analyze_sample([[1, "test"], [2, "test2"]])
        assert "error" in result
        assert "DuckDB not installed" in result["error"]

    def test_analyze_sample_empty_data(self, analyzer):
        """Test analyzer handles empty data."""
        if not analyzer.available:
            pytest.skip("DuckDB not installed")

        result = analyzer.analyze_sample([])
        assert "error" in result

    @pytest.mark.skipif(
        not DuckDBAnalyzer().available, reason="DuckDB not installed"
    )
    def test_analyze_sample_basic(self, analyzer):
        """Test basic sample analysis."""
        sample_data = [
            [1, "Alice", 25],
            [2, "Bob", 30],
            [3, "Charlie", 35],
            [4, "Diana", None],
        ]

        field_names = ["id", "name", "age"]
        result = analyzer.analyze_sample(sample_data, field_names)

        # Check that we got analysis for each field
        assert "id" in result
        assert "name" in result
        assert "age" in result

        # Check id field
        id_stats = result["id"]
        assert id_stats["sample_size"] == 4
        assert id_stats["null_count"] == 0
        assert id_stats["unique_count"] == 4
        assert id_stats["min_value"] == 1
        assert id_stats["max_value"] == 4

        # Check name field
        name_stats = result["name"]
        assert name_stats["sample_size"] == 4
        assert name_stats["null_count"] == 0
        assert name_stats["unique_count"] == 4
        assert "min_length" in name_stats
        assert "max_length" in name_stats

        # Check age field
        age_stats = result["age"]
        assert age_stats["sample_size"] == 4
        assert age_stats["null_count"] == 1  # Diana has NULL age
        assert age_stats["null_percentage"] == 25.0

    @pytest.mark.skipif(
        not DuckDBAnalyzer().available, reason="DuckDB not installed"
    )
    def test_analyze_sample_with_nulls(self, analyzer):
        """Test analysis with NULL values."""
        sample_data = [
            [1, "test", 100],
            [2, None, 200],
            [3, "test", None],
            [None, "test", 300],
        ]

        result = analyzer.analyze_sample(sample_data)

        # Check null percentages
        assert result["Field_0"]["null_count"] == 1
        assert result["Field_1"]["null_count"] == 1
        assert result["Field_2"]["null_count"] == 1

    @pytest.mark.skipif(
        not DuckDBAnalyzer().available, reason="DuckDB not installed"
    )
    def test_analyze_sample_string_stats(self, analyzer):
        """Test string statistics."""
        sample_data = [
            [1, "a"],
            [2, "abc"],
            [3, "abcdef"],
        ]

        result = analyzer.analyze_sample(sample_data, ["id", "text"])

        text_stats = result["text"]
        assert text_stats["min_length"] == 1
        assert text_stats["max_length"] == 6
        assert text_stats["avg_length"] == pytest.approx(3.33, rel=0.1)

    @pytest.mark.skipif(
        not DuckDBAnalyzer().available, reason="DuckDB not installed"
    )
    def test_analyze_sample_numeric_stats(self, analyzer):
        """Test numeric statistics."""
        sample_data = [
            [10],
            [20],
            [30],
            [40],
            [50],
        ]

        result = analyzer.analyze_sample(sample_data, ["value"])

        value_stats = result["value"]
        assert value_stats["min_value"] == 10
        assert value_stats["max_value"] == 50
        assert value_stats["avg_value"] == 30.0

    @pytest.mark.skipif(
        not DuckDBAnalyzer().available, reason="DuckDB not installed"
    )
    def test_analyze_sample_cardinality(self, analyzer):
        """Test cardinality calculation."""
        # High cardinality - all unique
        high_card_data = [[i] for i in range(100)]
        result = analyzer.analyze_sample(high_card_data, ["id"])
        assert result["id"]["cardinality"] == 1.0  # All unique

        # Low cardinality - many duplicates
        low_card_data = [[1]] * 90 + [[2]] * 10
        result = analyzer.analyze_sample(low_card_data, ["category"])
        assert result["category"]["cardinality"] == 0.02  # 2 unique out of 100

    @pytest.mark.skipif(
        not DuckDBAnalyzer().available, reason="DuckDB not installed"
    )
    def test_analyze_sample_top_values(self, analyzer):
        """Test top values for low cardinality columns."""
        sample_data = [
            ["red"],
            ["blue"],
            ["red"],
            ["red"],
            ["green"],
            ["blue"],
        ]

        result = analyzer.analyze_sample(sample_data, ["color"])

        color_stats = result["color"]
        assert "top_values" in color_stats
        top_values = color_stats["top_values"]
        
        # Should have top values since cardinality is low
        assert len(top_values) > 0
        # Red should be the most common (3 occurrences)
        assert top_values[0][0] == "red"
        assert top_values[0][1] == 3

    @pytest.mark.skipif(
        not DuckDBAnalyzer().available, reason="DuckDB not installed"
    )
    def test_analyze_sample_no_field_names(self, analyzer):
        """Test analysis without explicit field names."""
        sample_data = [
            [1, "test"],
            [2, "test2"],
        ]

        result = analyzer.analyze_sample(sample_data)

        # Should use default Field_0, Field_1 names
        assert "Field_0" in result
        assert "Field_1" in result

    @pytest.mark.skipif(
        not DuckDBAnalyzer().available, reason="DuckDB not installed"
    )
    def test_analyze_field_types(self, analyzer):
        """Test field type inference."""
        sample_data = [
            [1, 3.14, "test", True],
            [2, 2.71, "test2", False],
        ]

        types = analyzer.analyze_field_types(sample_data)

        # DuckDB should infer appropriate types
        assert len(types) == 4
        # First column should be integer-like
        assert "INT" in types[0].upper() or "BIGINT" in types[0].upper()
        # Second column should be float/double
        assert "DOUBLE" in types[1].upper() or "FLOAT" in types[1].upper()
        # Third column should be string/varchar
        assert "VARCHAR" in types[2].upper() or "STRING" in types[2].upper()
        # Fourth column should be boolean
        assert "BOOL" in types[3].upper()

    def test_analyze_field_types_no_duckdb(self):
        """Test field type inference without DuckDB."""
        analyzer = DuckDBAnalyzer()
        analyzer.available = False

        types = analyzer.analyze_field_types([[1, 2], [3, 4]])
        assert types == []
