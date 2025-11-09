"""DuckDB-based statistical analysis for schema introspection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class DuckDBAnalyzer:
    """
    Performs statistical analysis on sampled data using DuckDB.

    Features:
    - Column data types inference
    - Null percentage calculation
    - Unique value counts
    - Min/max values for numeric columns
    - String length statistics
    - Distribution analysis
    - Cardinality estimates
    """

    def __init__(self):
        """Initialize DuckDB analyzer."""
        try:
            import duckdb

            self.duckdb = duckdb
            self.available = True
        except ImportError:
            self.available = False

    def analyze_sample(
        self, sample_data: list[list[Any]], field_names: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Analyze a sample of data using DuckDB.

        Args:
            sample_data: List of rows (each row is a list of values)
            field_names: Optional list of field names. If None, uses Field_0, Field_1, etc.

        Returns:
            Dictionary containing analysis results per field
        """
        if not self.available:
            return {
                "error": "DuckDB not installed. Install with: pip install iptvportal-client[analysis]"
            }

        if not sample_data:
            return {"error": "No sample data provided"}

        # Determine field names
        num_fields = len(sample_data[0]) if sample_data else 0
        if not field_names:
            field_names = [f"Field_{i}" for i in range(num_fields)]
        elif len(field_names) < num_fields:
            # Extend field names if needed
            field_names = list(field_names) + [
                f"Field_{i}" for i in range(len(field_names), num_fields)
            ]

        try:
            import pandas as pd
            
            # Create a DuckDB connection
            conn = self.duckdb.connect(":memory:")

            # Convert sample data to DataFrame first, then to DuckDB table
            df = pd.DataFrame(sample_data, columns=field_names)
            conn.execute("CREATE TABLE sample_data AS SELECT * FROM df")

            # Perform analysis
            analysis_results = {}

            # Get basic statistics for each column
            describe_result = conn.execute("DESCRIBE sample_data").fetchall()

            for col_info in describe_result:
                col_name = col_info[0]
                col_type = col_info[1]

                # Basic stats
                stats = {
                    "dtype": col_type,
                    "sample_size": len(sample_data),
                }

                try:
                    # Count nulls
                    null_count = conn.execute(
                        f'SELECT COUNT(*) FROM sample_data WHERE "{col_name}" IS NULL'
                    ).fetchone()[0]
                    stats["null_count"] = null_count
                    stats["null_percentage"] = (null_count / len(sample_data)) * 100

                    # Count unique values
                    unique_count = conn.execute(
                        f'SELECT COUNT(DISTINCT "{col_name}") FROM sample_data'
                    ).fetchone()[0]
                    stats["unique_count"] = unique_count
                    stats["cardinality"] = unique_count / len(sample_data)

                    # Type-specific statistics
                    if "INT" in col_type.upper() or "DOUBLE" in col_type.upper():
                        # Numeric statistics
                        min_val, max_val, avg_val = conn.execute(
                            f'SELECT MIN("{col_name}"), MAX("{col_name}"), AVG("{col_name}") FROM sample_data WHERE "{col_name}" IS NOT NULL'
                        ).fetchone()
                        stats["min_value"] = min_val
                        stats["max_value"] = max_val
                        stats["avg_value"] = float(avg_val) if avg_val is not None else None

                    elif "VARCHAR" in col_type.upper() or "STRING" in col_type.upper():
                        # String statistics
                        min_len, max_len, avg_len = conn.execute(
                            f'SELECT MIN(LENGTH("{col_name}")), MAX(LENGTH("{col_name}")), AVG(LENGTH("{col_name}")) FROM sample_data WHERE "{col_name}" IS NOT NULL'
                        ).fetchone()
                        stats["min_length"] = min_len
                        stats["max_length"] = max_len
                        stats["avg_length"] = float(avg_len) if avg_len is not None else None

                    # Top values (for low cardinality columns)
                    if unique_count <= 20:
                        top_values = conn.execute(
                            f'SELECT "{col_name}", COUNT(*) as cnt FROM sample_data WHERE "{col_name}" IS NOT NULL GROUP BY "{col_name}" ORDER BY cnt DESC LIMIT 5'
                        ).fetchall()
                        stats["top_values"] = [(str(val), cnt) for val, cnt in top_values]

                except Exception as e:
                    stats["analysis_error"] = str(e)

                analysis_results[col_name] = stats

            conn.close()
            return analysis_results

        except Exception as e:
            return {"error": f"DuckDB analysis failed: {str(e)}"}

    def analyze_field_types(self, sample_data: list[list[Any]]) -> list[str]:
        """
        Infer field types using DuckDB's type inference.

        Args:
            sample_data: List of rows

        Returns:
            List of inferred types
        """
        if not self.available:
            return []

        try:
            import pandas as pd
            
            conn = self.duckdb.connect(":memory:")
            # Create DataFrame with default column names
            df = pd.DataFrame(sample_data)
            conn.execute("CREATE TABLE sample AS SELECT * FROM df")
            describe = conn.execute("DESCRIBE sample").fetchall()
            conn.close()

            return [col_info[1] for col_info in describe]
        except Exception:
            return []


__all__ = ["DuckDBAnalyzer"]
