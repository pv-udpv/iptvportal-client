"""Tests for debug logger utilities."""

import json

from pydantic import SecretStr

from iptvportal.cli.debug import DebugLogger, _sanitize_data


class TestSanitizeData:
    """Tests for _sanitize_data function."""

    def test_sanitize_secret_str(self):
        """Test that SecretStr objects are masked."""
        secret = SecretStr("my_secret_password")
        result = _sanitize_data(secret)
        assert result == "***MASKED***"

    def test_sanitize_dict_with_secret_str(self):
        """Test that SecretStr in dicts are masked."""
        data = {
            "username": "admin",
            "password": SecretStr("secret123"),
            "domain": "example.com",
        }
        result = _sanitize_data(data)
        assert result == {
            "username": "admin",
            "password": "***MASKED***",
            "domain": "example.com",
        }

    def test_sanitize_nested_dict_with_secret_str(self):
        """Test that SecretStr in nested dicts are masked."""
        data = {
            "config": {
                "auth": {
                    "username": "admin",
                    "password": SecretStr("secret123"),
                },
                "domain": "example.com",
            }
        }
        result = _sanitize_data(data)
        assert result == {
            "config": {
                "auth": {
                    "username": "admin",
                    "password": "***MASKED***",
                },
                "domain": "example.com",
            }
        }

    def test_sanitize_list_with_secret_str(self):
        """Test that SecretStr in lists are masked."""
        data = [
            "normal_value",
            SecretStr("secret123"),
            {"password": SecretStr("another_secret")},
        ]
        result = _sanitize_data(data)
        assert result == [
            "normal_value",
            "***MASKED***",
            {"password": "***MASKED***"},
        ]

    def test_sanitize_tuple_with_secret_str(self):
        """Test that SecretStr in tuples are masked."""
        data = (
            "normal_value",
            SecretStr("secret123"),
        )
        result = _sanitize_data(data)
        assert result == ("normal_value", "***MASKED***")

    def test_sanitize_primitive_types(self):
        """Test that primitive types are unchanged."""
        assert _sanitize_data("string") == "string"
        assert _sanitize_data(123) == 123
        assert _sanitize_data(45.67) == 45.67
        assert _sanitize_data(True) is True
        assert _sanitize_data(None) is None

    def test_sanitize_complex_nested_structure(self):
        """Test sanitization of complex nested structures."""
        data = {
            "users": [
                {
                    "id": 1,
                    "username": "admin",
                    "credentials": {
                        "password": SecretStr("secret1"),
                        "api_key": SecretStr("key123"),
                    },
                },
                {
                    "id": 2,
                    "username": "user",
                    "credentials": {
                        "password": SecretStr("secret2"),
                        "api_key": SecretStr("key456"),
                    },
                },
            ],
            "config": {
                "database_url": SecretStr("postgresql://user:pass@localhost/db"),
                "timeout": 30,
            },
        }
        result = _sanitize_data(data)
        assert result == {
            "users": [
                {
                    "id": 1,
                    "username": "admin",
                    "credentials": {
                        "password": "***MASKED***",
                        "api_key": "***MASKED***",
                    },
                },
                {
                    "id": 2,
                    "username": "user",
                    "credentials": {
                        "password": "***MASKED***",
                        "api_key": "***MASKED***",
                    },
                },
            ],
            "config": {
                "database_url": "***MASKED***",
                "timeout": 30,
            },
        }


class TestDebugLogger:
    """Tests for DebugLogger class."""

    def test_logger_disabled_by_default(self):
        """Test that logger is disabled by default."""
        logger = DebugLogger()
        assert logger.enabled is False

    def test_logger_enabled(self):
        """Test that logger can be enabled."""
        logger = DebugLogger(enabled=True)
        assert logger.enabled is True

    def test_log_when_disabled(self):
        """Test that logging does nothing when disabled."""
        logger = DebugLogger(enabled=False)
        logger.log("test", {"key": "value"})
        assert len(logger._logs) == 0

    def test_log_when_enabled(self):
        """Test that logging stores data when enabled."""
        logger = DebugLogger(enabled=True)
        logger.log("test", {"key": "value"}, "Test Title")
        assert len(logger._logs) == 1
        assert logger._logs[0]["step"] == "test"
        assert logger._logs[0]["data"] == {"key": "value"}
        assert logger._logs[0]["title"] == "Test Title"

    def test_log_with_secret_str(self, capsys):
        """Test that SecretStr is masked in console output."""
        logger = DebugLogger(enabled=True, format_type="text")
        data = {
            "username": "admin",
            "password": SecretStr("secret123"),
        }
        logger.log("config", data, "Configuration")

        # Verify data is stored as-is (not yet sanitized)
        assert isinstance(logger._logs[0]["data"]["password"], SecretStr)

        # Verify console output contains masked password
        captured = capsys.readouterr()
        assert "***MASKED***" in captured.out
        assert "secret123" not in captured.out

    def test_save_to_file_json(self, tmp_path):
        """Test saving logs to JSON file with masked secrets."""
        output_file = tmp_path / "debug.json"
        logger = DebugLogger(
            enabled=True,
            format_type="json",
            output_file=str(output_file),
        )

        data = {
            "username": "admin",
            "password": SecretStr("secret123"),
        }
        logger.log("config", data, "Configuration")
        logger.save_to_file()

        # Verify file exists and contains masked password
        assert output_file.exists()
        with open(output_file, encoding="utf-8") as f:
            saved_data = json.load(f)

        assert len(saved_data) == 1
        assert saved_data[0]["step"] == "config"
        assert saved_data[0]["data"]["password"] == "***MASKED***"
        assert "secret123" not in output_file.read_text()

    def test_save_to_file_yaml(self, tmp_path):
        """Test saving logs to YAML file with masked secrets."""
        output_file = tmp_path / "debug.yaml"
        logger = DebugLogger(
            enabled=True,
            format_type="yaml",
            output_file=str(output_file),
        )

        data = {
            "username": "admin",
            "password": SecretStr("secret123"),
        }
        logger.log("config", data, "Configuration")
        logger.save_to_file()

        # Verify file exists and contains masked password
        assert output_file.exists()
        content = output_file.read_text()
        assert "***MASKED***" in content
        assert "secret123" not in content

    def test_save_to_file_text(self, tmp_path):
        """Test saving logs to text file with masked secrets."""
        output_file = tmp_path / "debug.txt"
        logger = DebugLogger(
            enabled=True,
            format_type="text",
            output_file=str(output_file),
        )

        data = {
            "username": "admin",
            "password": SecretStr("secret123"),
        }
        logger.log("config", data, "Configuration")
        logger.save_to_file()

        # Verify file exists and contains masked password
        assert output_file.exists()
        content = output_file.read_text()
        assert "***MASKED***" in content
        assert "secret123" not in content

    def test_display_json_format(self, capsys):
        """Test JSON format output masks secrets."""
        logger = DebugLogger(enabled=True, format_type="json")
        data = {
            "username": "admin",
            "password": SecretStr("secret123"),
        }
        logger.log("config", data)

        captured = capsys.readouterr()
        assert "***MASKED***" in captured.out
        assert "secret123" not in captured.out

    def test_display_yaml_format(self, capsys):
        """Test YAML format output masks secrets."""
        logger = DebugLogger(enabled=True, format_type="yaml")
        data = {
            "username": "admin",
            "password": SecretStr("secret123"),
        }
        logger.log("config", data)

        captured = capsys.readouterr()
        assert "***MASKED***" in captured.out
        assert "secret123" not in captured.out

    def test_exception_logging(self, capsys):
        """Test exception logging."""
        logger = DebugLogger(enabled=True)

        try:
            raise ValueError("Test error")
        except ValueError as e:
            logger.exception(e, "Test context message")

        captured = capsys.readouterr()
        assert "Exception Occurred" in captured.out
        assert "ValueError" in captured.out
        assert "Test error" in captured.out
        assert "Test context message" in captured.out

    def test_exception_logging_when_disabled(self, capsys):
        """Test that exception logging does nothing when disabled."""
        logger = DebugLogger(enabled=False)

        try:
            raise ValueError("Test error")
        except ValueError as e:
            logger.exception(e, "Test context message")

        captured = capsys.readouterr()
        assert captured.out == ""
