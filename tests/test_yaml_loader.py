"""Tests for YAML configuration loading with environment variable substitution."""

import os
import tempfile
from pathlib import Path

import pytest

from src.config.yaml_loader import (
    load_yaml_with_env_vars,
    substitute_env_vars,
)


class TestSubstituteEnvVars:
    """Tests for the substitute_env_vars function."""

    def test_substitute_existing_env_var(self) -> None:
        """Test substitution of an existing environment variable."""
        os.environ["TEST_VAR"] = "test_value"
        try:
            result = substitute_env_vars("${TEST_VAR}")
            assert result == "test_value"
        finally:
            del os.environ["TEST_VAR"]

    def test_substitute_env_var_in_string(self) -> None:
        """Test substitution within a larger string."""
        os.environ["TEST_HOST"] = "localhost"
        try:
            result = substitute_env_vars("http://${TEST_HOST}:8000")
            assert result == "http://localhost:8000"
        finally:
            del os.environ["TEST_HOST"]

    def test_substitute_multiple_env_vars(self) -> None:
        """Test substitution of multiple environment variables in one string."""
        os.environ["TEST_HOST"] = "localhost"
        os.environ["TEST_PORT"] = "8000"
        try:
            result = substitute_env_vars("${TEST_HOST}:${TEST_PORT}")
            assert result == "localhost:8000"
        finally:
            del os.environ["TEST_HOST"]
            del os.environ["TEST_PORT"]

    def test_substitute_with_default_when_var_missing(self) -> None:
        """Test default value is used when environment variable is missing."""
        # Ensure the variable doesn't exist
        os.environ.pop("MISSING_VAR", None)
        result = substitute_env_vars("${MISSING_VAR:-default_value}")
        assert result == "default_value"

    def test_substitute_with_default_when_var_exists(self) -> None:
        """Test environment variable takes precedence over default value."""
        os.environ["EXISTING_VAR"] = "actual_value"
        try:
            result = substitute_env_vars("${EXISTING_VAR:-default_value}")
            assert result == "actual_value"
        finally:
            del os.environ["EXISTING_VAR"]

    def test_substitute_with_empty_default(self) -> None:
        """Test empty default value."""
        os.environ.pop("MISSING_VAR", None)
        result = substitute_env_vars("${MISSING_VAR:-}")
        assert result == ""

    def test_substitute_missing_required_var_raises_error(self) -> None:
        """Test that missing required variable raises ValueError."""
        os.environ.pop("MISSING_REQUIRED", None)
        with pytest.raises(ValueError, match="Required environment variable 'MISSING_REQUIRED'"):
            substitute_env_vars("${MISSING_REQUIRED}")

    def test_substitute_in_dict(self) -> None:
        """Test substitution in dictionary values."""
        os.environ["DB_HOST"] = "localhost"
        os.environ["DB_PORT"] = "5432"
        try:
            config = {
                "database": {
                    "host": "${DB_HOST}",
                    "port": "${DB_PORT}",
                }
            }
            result = substitute_env_vars(config)
            assert result == {
                "database": {
                    "host": "localhost",
                    "port": "5432",
                }
            }
        finally:
            del os.environ["DB_HOST"]
            del os.environ["DB_PORT"]

    def test_substitute_in_list(self) -> None:
        """Test substitution in list items."""
        os.environ["HOST1"] = "host1.example.com"
        os.environ["HOST2"] = "host2.example.com"
        try:
            hosts = ["${HOST1}", "${HOST2}", "${HOST3:-host3.example.com}"]
            result = substitute_env_vars(hosts)
            assert result == [
                "host1.example.com",
                "host2.example.com",
                "host3.example.com",
            ]
        finally:
            del os.environ["HOST1"]
            del os.environ["HOST2"]

    def test_substitute_nested_structures(self) -> None:
        """Test substitution in deeply nested structures."""
        os.environ["API_KEY"] = "secret123"
        os.environ["ENV"] = "production"
        try:
            config = {
                "services": [
                    {
                        "name": "api",
                        "credentials": {
                            "api_key": "${API_KEY}",
                            "environment": "${ENV}",
                        },
                    },
                    {
                        "name": "worker",
                        "timeout": "${TIMEOUT:-30}",
                    },
                ]
            }
            result = substitute_env_vars(config)
            assert result == {
                "services": [
                    {
                        "name": "api",
                        "credentials": {
                            "api_key": "secret123",
                            "environment": "production",
                        },
                    },
                    {
                        "name": "worker",
                        "timeout": "30",
                    },
                ]
            }
        finally:
            del os.environ["API_KEY"]
            del os.environ["ENV"]

    def test_substitute_preserves_non_string_types(self) -> None:
        """Test that non-string types are preserved."""
        config = {
            "port": 8000,
            "debug": True,
            "timeout": None,
            "rate_limit": 100.5,
        }
        result = substitute_env_vars(config)
        assert result == config
        assert isinstance(result["port"], int)
        assert isinstance(result["debug"], bool)
        assert result["timeout"] is None
        assert isinstance(result["rate_limit"], float)


class TestLoadYamlWithEnvVars:
    """Tests for the load_yaml_with_env_vars function."""

    def test_load_yaml_file_with_env_vars(self) -> None:
        """Test loading a YAML file with environment variable substitution."""
        os.environ["TEST_DB_HOST"] = "testdb.example.com"
        os.environ["TEST_DB_PORT"] = "5432"

        try:
            # Create a temporary YAML file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                f.write("""
database:
  host: ${TEST_DB_HOST}
  port: ${TEST_DB_PORT}
  name: ${TEST_DB_NAME:-testdb}
""")
                temp_file = f.name

            try:
                result = load_yaml_with_env_vars(temp_file)
                assert result == {
                    "database": {
                        "host": "testdb.example.com",
                        "port": "5432",
                        "name": "testdb",
                    }
                }
            finally:
                Path(temp_file).unlink()
        finally:
            del os.environ["TEST_DB_HOST"]
            del os.environ["TEST_DB_PORT"]

    def test_load_yaml_file_not_found(self) -> None:
        """Test that loading a non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_yaml_with_env_vars("/nonexistent/file.yaml")

    def test_load_yaml_invalid_yaml(self) -> None:
        """Test that loading invalid YAML raises ValueError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="Failed to parse YAML file"):
                load_yaml_with_env_vars(temp_file)
        finally:
            Path(temp_file).unlink()

    def test_load_yaml_empty_file(self) -> None:
        """Test loading an empty YAML file returns empty dict."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            temp_file = f.name

        try:
            result = load_yaml_with_env_vars(temp_file)
            assert result == {}
        finally:
            Path(temp_file).unlink()

    def test_load_yaml_non_dict_content(self) -> None:
        """Test that loading YAML with non-dict root raises ValueError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("- item1\n- item2\n")
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="Expected YAML file .* to contain a mapping"):
                load_yaml_with_env_vars(temp_file)
        finally:
            Path(temp_file).unlink()

    def test_load_yaml_missing_required_var(self) -> None:
        """Test that missing required variable in YAML file raises ValueError with context."""
        os.environ.pop("MISSING_VAR", None)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("value: ${MISSING_VAR}\n")
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match=f"Error in {temp_file}"):
                load_yaml_with_env_vars(temp_file)
        finally:
            Path(temp_file).unlink()
