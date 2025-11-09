"""Tests for RemoteFieldValidator and data-driven field mapping validation."""

from unittest.mock import AsyncMock

import pytest

from iptvportal.core.async_client import AsyncIPTVPortalClient
from iptvportal.validation import RemoteFieldValidator


@pytest.fixture
def mock_client():
    """Mock AsyncIPTVPortalClient."""
    return AsyncMock(spec=AsyncIPTVPortalClient)


@pytest.fixture
def validator(mock_client):
    """Create RemoteFieldValidator instance."""
    return RemoteFieldValidator(mock_client)


class TestRemoteFieldValidator:
    """Tests for RemoteFieldValidator."""

    @pytest.mark.asyncio
    async def test_validate_field_mapping_perfect_match(self, validator, mock_client):
        """Test validation with perfect match between local and remote."""
        # Mock SELECT * returns rows with data at position 1
        result_all = [
            [1, "user1", "email1@example.com"],
            [2, "user2", "email2@example.com"],
            [3, "user3", "email3@example.com"],
        ]

        # Mock SELECT username returns same data
        result_remote = [
            ["user1"],
            ["user2"],
            ["user3"],
        ]

        mock_client.execute.side_effect = [result_all, result_remote]

        # Validate position 1 (username in SELECT *) against "username" column
        result = await validator.validate_field_mapping(
            table_name="subscriber", local_position=1, remote_column_name="username", sample_size=3
        )

        assert result["match_ratio"] == 1.0
        assert result["sample_size"] == 3
        assert result["remote_column"] == "username"
        assert "validated_at" in result
        assert "dtype" in result
        assert result["null_count"] >= 0
        assert result["unique_count"] == 3

    @pytest.mark.asyncio
    async def test_validate_field_mapping_partial_match(self, validator, mock_client):
        """Test validation with partial match (some mismatches)."""
        # Mock SELECT * returns data at position 2
        result_all = [
            [1, "user1", "email1@example.com"],
            [2, "user2", "email2@example.com"],
            [3, "user3", "WRONG_EMAIL"],  # Mismatch here
        ]

        # Mock SELECT email returns correct data
        result_remote = [
            ["email1@example.com"],
            ["email2@example.com"],
            ["email3@example.com"],  # Correct value
        ]

        mock_client.execute.side_effect = [result_all, result_remote]

        result = await validator.validate_field_mapping(
            table_name="subscriber", local_position=2, remote_column_name="email", sample_size=3
        )

        # 2 out of 3 match
        assert result["match_ratio"] == pytest.approx(2.0 / 3.0)
        assert result["sample_size"] == 3
        assert result["remote_column"] == "email"

    @pytest.mark.asyncio
    async def test_validate_field_mapping_with_nulls(self, validator, mock_client):
        """Test validation with NULL values."""
        # Mock SELECT * with NULL values at position 1
        result_all = [
            [1, None, "email1@example.com"],
            [2, "user2", "email2@example.com"],
            [3, None, "email3@example.com"],
        ]

        # Mock SELECT username with same NULLs
        result_remote = [
            [None],
            ["user2"],
            [None],
        ]

        mock_client.execute.side_effect = [result_all, result_remote]

        result = await validator.validate_field_mapping(
            table_name="subscriber", local_position=1, remote_column_name="username", sample_size=3
        )

        # All match (including NULL == NULL)
        assert result["match_ratio"] == 1.0
        assert result["null_count"] == 2

    @pytest.mark.asyncio
    async def test_validate_field_mapping_numeric_types(self, validator, mock_client):
        """Test validation with numeric data types."""
        # Mock SELECT * with integers at position 0
        result_all = [
            [1, "user1"],
            [2, "user2"],
            [3, "user3"],
        ]

        # Mock SELECT id
        result_remote = [
            [1],
            [2],
            [3],
        ]

        mock_client.execute.side_effect = [result_all, result_remote]

        result = await validator.validate_field_mapping(
            table_name="subscriber", local_position=0, remote_column_name="id", sample_size=3
        )

        assert result["match_ratio"] == 1.0
        assert result["dtype"] == "int64"  # pandas dtype for integers
        assert result["min_value"] == 1.0
        assert result["max_value"] == 3.0

    @pytest.mark.asyncio
    async def test_validate_table_schema_multiple_fields(self, validator, mock_client):
        """Test validation of multiple fields in a table."""
        # Mock responses for multiple fields
        # Field 0: id
        result_all_0 = [[1, "user1"], [2, "user2"]]
        result_remote_0 = [[1], [2]]

        # Field 1: username
        result_all_1 = [[1, "user1"], [2, "user2"]]
        result_remote_1 = [["user1"], ["user2"]]

        mock_client.execute.side_effect = [
            result_all_0,
            result_remote_0,
            result_all_1,
            result_remote_1,
        ]

        field_mappings = {0: "id", 1: "username"}

        results = await validator.validate_table_schema(
            table_name="subscriber", field_mappings=field_mappings, sample_size=2
        )

        assert len(results) == 2
        assert 0 in results
        assert 1 in results
        assert results[0]["match_ratio"] == 1.0
        assert results[1]["match_ratio"] == 1.0

    def test_infer_field_type_from_dtype(self, validator):
        """Test field type inference from pandas dtype."""
        assert validator.infer_field_type_from_dtype("int64") == "integer"
        assert validator.infer_field_type_from_dtype("float64") == "float"
        assert validator.infer_field_type_from_dtype("bool") == "boolean"
        assert validator.infer_field_type_from_dtype("datetime64[ns]") == "datetime"
        assert validator.infer_field_type_from_dtype("object") == "string"
        assert validator.infer_field_type_from_dtype("string") == "string"
        assert validator.infer_field_type_from_dtype("unknown_type") == "unknown"

    @pytest.mark.asyncio
    async def test_validate_field_mapping_error_handling(self, validator, mock_client):
        """Test error handling in validation."""
        # Mock client raises exception
        mock_client.execute.side_effect = Exception("Connection failed")

        with pytest.raises(ValueError, match="Failed to validate field mapping"):
            await validator.validate_field_mapping(
                table_name="subscriber", local_position=0, remote_column_name="id"
            )

    @pytest.mark.asyncio
    async def test_validate_table_schema_partial_errors(self, validator, mock_client):
        """Test table schema validation with some fields failing."""
        # First field succeeds
        result_all_0 = [[1, "user1"]]
        result_remote_0 = [[1]]

        # Second field fails
        mock_client.execute.side_effect = [
            result_all_0,
            result_remote_0,
            Exception("Field not found"),
        ]

        field_mappings = {0: "id", 1: "nonexistent"}

        results = await validator.validate_table_schema(
            table_name="subscriber", field_mappings=field_mappings, sample_size=1
        )

        # First field should succeed
        assert results[0]["match_ratio"] == 1.0

        # Second field should have error
        assert "error" in results[1]
        assert "Field not found" in results[1]["error"]
