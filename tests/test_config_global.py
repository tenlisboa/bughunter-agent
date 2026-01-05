"""Tests for global configuration loading and validation."""

import os
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.config.models import GlobalConfig
from src.config.yaml_loader import (
    clear_global_config_cache,
    load_global_config,
)


class TestLoadGlobalConfig:
    """Tests for loading and validating global configuration."""

    def setup_method(self) -> None:
        """Set up test environment before each test."""
        # Clear the global config cache before each test
        clear_global_config_cache()
        # Store original env vars to restore later
        self.original_env = os.environ.copy()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        clear_global_config_cache()
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_load_valid_global_config(self) -> None:
        """Test loading a valid global configuration file."""
        # Create a valid config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
app:
  name: "Test App"
  version: "1.0.0"

server:
  host: "localhost"
  port: 9000

database:
  url: "postgresql://localhost:5432/testdb"
  pool_size: 5

llm:
  provider: "openai"
  model: "gpt-4"

output:
  format: "json"
  directory: "./test-output"

cors:
  origins:
    - "http://localhost:3000"

logging:
  level: "DEBUG"
""")
            temp_file = f.name

        try:
            config = load_global_config(temp_file)

            # Verify the config was loaded correctly
            assert isinstance(config, GlobalConfig)
            assert config.app.name == "Test App"
            assert config.app.version == "1.0.0"
            assert config.server.host == "localhost"
            assert config.server.port == 9000
            assert config.database.url == "postgresql://localhost:5432/testdb"
            assert config.database.pool_size == 5
            assert config.llm.provider == "openai"
            assert config.llm.model == "gpt-4"
            assert config.output.format == "json"
            assert config.output.directory == "./test-output"
            assert config.cors.origins == ["http://localhost:3000"]
            assert config.logging.level == "DEBUG"
        finally:
            Path(temp_file).unlink()

    def test_load_global_config_with_env_vars(self) -> None:
        """Test environment variable substitution in global config."""
        os.environ["TEST_HOST"] = "0.0.0.0"
        os.environ["TEST_PORT"] = "8080"
        os.environ["TEST_DB_URL"] = "postgresql://prod.example.com/db"
        os.environ["TEST_LLM_KEY"] = "sk-test123"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
app:
  name: "Test App"

server:
  host: "${TEST_HOST}"
  port: ${TEST_PORT}

database:
  url: "${TEST_DB_URL}"

llm:
  provider: "openai"
  model: "gpt-4"
  api_key: "${TEST_LLM_KEY}"

output:
  format: "json"

cors:
  origins:
    - "http://localhost:3000"

logging:
  level: "INFO"
""")
            temp_file = f.name

        try:
            config = load_global_config(temp_file)

            # Verify environment variables were substituted
            assert config.server.host == "0.0.0.0"
            assert config.server.port == 8080
            assert config.database.url == "postgresql://prod.example.com/db"
            assert config.llm.api_key == "sk-test123"
        finally:
            Path(temp_file).unlink()

    def test_load_global_config_with_defaults(self) -> None:
        """Test that default values are applied when fields are missing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
# Minimal config - most fields should use defaults
app:
  name: "Minimal App"

server:
  host: "localhost"

database:
  url: "postgresql://localhost/db"

llm:
  provider: "openai"

output:
  format: "json"

cors:
  origins: []

logging:
  level: "INFO"
""")
            temp_file = f.name

        try:
            config = load_global_config(temp_file)

            # Verify defaults were applied
            assert config.app.version == "0.1.0"  # Default version
            assert config.server.port == 8000  # Default port
            assert config.server.debug is False  # Default debug
            assert config.database.pool_size == 10  # Default pool_size
            assert config.database.max_overflow == 20  # Default max_overflow
            assert config.llm.model == "gpt-4"  # Default model
            assert config.llm.temperature == 0.7  # Default temperature
            assert config.output.pretty_print is True  # Default pretty_print
        finally:
            Path(temp_file).unlink()

    def test_load_global_config_with_env_var_defaults(self) -> None:
        """Test environment variable default values are used when var is not set."""
        # Ensure the env vars don't exist
        os.environ.pop("MISSING_HOST", None)
        os.environ.pop("MISSING_PORT", None)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
app:
  name: "Test App"

server:
  host: "${MISSING_HOST:-default.example.com}"
  port: ${MISSING_PORT:-9999}

database:
  url: "postgresql://localhost/db"

llm:
  provider: "openai"

output:
  format: "json"

cors:
  origins: []

logging:
  level: "INFO"
""")
            temp_file = f.name

        try:
            config = load_global_config(temp_file)

            # Verify default values from env var syntax were used
            assert config.server.host == "default.example.com"
            assert config.server.port == 9999
        finally:
            Path(temp_file).unlink()

    def test_load_global_config_invalid_field_value(self) -> None:
        """Test that invalid field values raise validation errors."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
app:
  name: "Test App"

server:
  host: "localhost"
  port: 99999  # Invalid: port must be <= 65535

database:
  url: "postgresql://localhost/db"

llm:
  provider: "openai"

output:
  format: "json"

cors:
  origins: []

logging:
  level: "INFO"
""")
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="Configuration validation failed"):
                load_global_config(temp_file)
        finally:
            Path(temp_file).unlink()

    def test_load_global_config_invalid_temperature(self) -> None:
        """Test that LLM temperature outside valid range raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
app:
  name: "Test App"

server:
  host: "localhost"

database:
  url: "postgresql://localhost/db"

llm:
  provider: "openai"
  temperature: 3.0  # Invalid: must be <= 2.0

output:
  format: "json"

cors:
  origins: []

logging:
  level: "INFO"
""")
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="Configuration validation failed"):
                load_global_config(temp_file)
        finally:
            Path(temp_file).unlink()

    def test_load_global_config_invalid_pool_size(self) -> None:
        """Test that invalid database pool_size raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
app:
  name: "Test App"

server:
  host: "localhost"

database:
  url: "postgresql://localhost/db"
  pool_size: 0  # Invalid: must be >= 1

llm:
  provider: "openai"

output:
  format: "json"

cors:
  origins: []

logging:
  level: "INFO"
""")
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="Configuration validation failed"):
                load_global_config(temp_file)
        finally:
            Path(temp_file).unlink()

    def test_load_global_config_missing_required_env_var(self) -> None:
        """Test that missing required environment variable raises error."""
        os.environ.pop("REQUIRED_VAR", None)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
app:
  name: "Test App"

server:
  host: "${REQUIRED_VAR}"  # No default provided

database:
  url: "postgresql://localhost/db"

llm:
  provider: "openai"

output:
  format: "json"

cors:
  origins: []

logging:
  level: "INFO"
""")
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="Required environment variable 'REQUIRED_VAR'"):
                load_global_config(temp_file)
        finally:
            Path(temp_file).unlink()

    def test_load_global_config_file_not_found(self) -> None:
        """Test that loading non-existent config file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_global_config("/nonexistent/config.yaml")

    def test_load_global_config_invalid_yaml(self) -> None:
        """Test that malformed YAML raises appropriate error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [[[")
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="Failed to parse YAML file"):
                load_global_config(temp_file)
        finally:
            Path(temp_file).unlink()

    def test_load_global_config_caching(self) -> None:
        """Test that global config is cached as singleton."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
app:
  name: "Cached App"

server:
  host: "localhost"

database:
  url: "postgresql://localhost/db"

llm:
  provider: "openai"

output:
  format: "json"

cors:
  origins: []

logging:
  level: "INFO"
""")
            temp_file = f.name

        try:
            # Load config twice
            config1 = load_global_config(temp_file)
            config2 = load_global_config(temp_file)

            # Should return the same instance (singleton)
            assert config1 is config2
        finally:
            Path(temp_file).unlink()

    def test_clear_global_config_cache(self) -> None:
        """Test that clearing cache forces reload."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
app:
  name: "Test App"

server:
  host: "localhost"

database:
  url: "postgresql://localhost/db"

llm:
  provider: "openai"

output:
  format: "json"

cors:
  origins: []

logging:
  level: "INFO"
""")
            temp_file = f.name

        try:
            # Load config
            config1 = load_global_config(temp_file)

            # Clear cache
            clear_global_config_cache()

            # Load again
            config2 = load_global_config(temp_file)

            # Should be different instances after cache clear
            assert config1 is not config2
            # But should have same values
            assert config1.app.name == config2.app.name
        finally:
            Path(temp_file).unlink()

    def test_load_global_config_type_coercion(self) -> None:
        """Test that string values are correctly coerced to expected types."""
        os.environ["STR_PORT"] = "8888"
        os.environ["STR_DEBUG"] = "true"
        os.environ["STR_POOL"] = "15"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
app:
  name: "Test App"

server:
  host: "localhost"
  port: ${STR_PORT}
  debug: ${STR_DEBUG}

database:
  url: "postgresql://localhost/db"
  pool_size: ${STR_POOL}

llm:
  provider: "openai"

output:
  format: "json"

cors:
  origins: []

logging:
  level: "INFO"
""")
            temp_file = f.name

        try:
            config = load_global_config(temp_file)

            # Verify types were coerced correctly
            assert config.server.port == 8888
            assert isinstance(config.server.port, int)
            assert config.server.debug is True
            assert isinstance(config.server.debug, bool)
            assert config.database.pool_size == 15
            assert isinstance(config.database.pool_size, int)
        finally:
            Path(temp_file).unlink()

    def test_load_global_config_empty_sections(self) -> None:
        """Test loading config with empty sections uses all defaults."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
# Config with mostly empty sections - should use defaults
app: {}
server: {}
database: {}
llm: {}
output: {}
cors: {}
logging: {}
""")
            temp_file = f.name

        try:
            config = load_global_config(temp_file)

            # Verify all defaults were applied
            assert config.app.name == "PX BugHunter"
            assert config.server.host == "0.0.0.0"
            assert config.server.port == 8000
            assert config.database.url == "postgresql://localhost:5432/px_bughunter"
            assert config.llm.provider == "openai"
            assert config.output.format == "json"
            assert config.logging.level == "INFO"
        finally:
            Path(temp_file).unlink()

    def test_load_global_config_mixed_env_and_literals(self) -> None:
        """Test config with mix of environment variables and literal values."""
        os.environ["PROD_DB_URL"] = "postgresql://prod.db.example.com/maindb"
        os.environ["PROD_HOST"] = "api.example.com"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
app:
  name: "Production App"
  version: "2.0.0"

server:
  host: "${PROD_HOST}"
  port: 443
  environment: "production"

database:
  url: "${PROD_DB_URL}"
  pool_size: 20

llm:
  provider: "openai"
  model: "gpt-4"

output:
  format: "json"

cors:
  origins:
    - "https://example.com"

logging:
  level: "WARNING"
""")
            temp_file = f.name

        try:
            config = load_global_config(temp_file)

            # Verify mix of env vars and literals
            assert config.app.name == "Production App"  # Literal
            assert config.server.host == "api.example.com"  # Env var
            assert config.server.port == 443  # Literal
            assert config.database.url == "postgresql://prod.db.example.com/maindb"  # Env var
            assert config.database.pool_size == 20  # Literal
        finally:
            Path(temp_file).unlink()

    def test_load_global_config_complex_types(self) -> None:
        """Test loading config with complex nested structures."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
app:
  name: "Test App"

server:
  host: "localhost"

database:
  url: "postgresql://localhost/db"

llm:
  provider: "openai"

output:
  format: "json"

cors:
  origins:
    - "http://localhost:3000"
    - "http://localhost:3001"
    - "https://app.example.com"
  allow_credentials: true
  allow_methods:
    - "GET"
    - "POST"
    - "PUT"
    - "DELETE"
  allow_headers:
    - "Authorization"
    - "Content-Type"

logging:
  level: "DEBUG"
  format: "%(levelname)s - %(message)s"
""")
            temp_file = f.name

        try:
            config = load_global_config(temp_file)

            # Verify complex nested structures
            assert len(config.cors.origins) == 3
            assert "http://localhost:3000" in config.cors.origins
            assert config.cors.allow_credentials is True
            assert len(config.cors.allow_methods) == 4
            assert "GET" in config.cors.allow_methods
            assert len(config.cors.allow_headers) == 2
            assert "Authorization" in config.cors.allow_headers
        finally:
            Path(temp_file).unlink()


class TestGlobalConfigModel:
    """Tests for GlobalConfig Pydantic model validation."""

    def test_global_config_direct_instantiation(self) -> None:
        """Test creating GlobalConfig directly with valid data."""
        config = GlobalConfig(
            app={"name": "Direct App"},  # type: ignore[arg-type]
            server={"host": "localhost", "port": 8080},  # type: ignore[arg-type]
            database={"url": "postgresql://localhost/db"},  # type: ignore[arg-type]
            llm={"provider": "openai"},  # type: ignore[arg-type]
            output={"format": "json"},  # type: ignore[arg-type]
            cors={"origins": []},  # type: ignore[arg-type]
            logging={"level": "INFO"},  # type: ignore[arg-type]
        )

        assert config.app.name == "Direct App"
        assert config.server.port == 8080

    def test_global_config_validation_error_details(self) -> None:
        """Test that validation errors provide clear field-level details."""
        with pytest.raises(ValidationError) as exc_info:
            GlobalConfig(
                app={"name": "Test"},  # type: ignore[arg-type]
                server={"port": 99999},  # type: ignore[arg-type]  # Invalid port
                database={"url": "postgresql://localhost/db"},  # type: ignore[arg-type]
                llm={"provider": "openai"},  # type: ignore[arg-type]
                output={"format": "json"},  # type: ignore[arg-type]
                cors={"origins": []},  # type: ignore[arg-type]
                logging={"level": "INFO"},  # type: ignore[arg-type]
            )

        # Verify error contains field information
        errors = exc_info.value.errors()
        assert any("port" in str(error["loc"]) for error in errors)

    def test_global_config_optional_fields(self) -> None:
        """Test that optional fields can be omitted."""
        config = GlobalConfig(
            app={},  # type: ignore[arg-type]
            server={},  # type: ignore[arg-type]
            database={},  # type: ignore[arg-type]
            llm={},  # type: ignore[arg-type]
            output={},  # type: ignore[arg-type]
            cors={},  # type: ignore[arg-type]
            logging={},  # type: ignore[arg-type]
        )

        # Verify optional fields are None or have defaults
        assert config.llm.api_key is None
        assert config.logging.file is None

    def test_global_config_serialization(self) -> None:
        """Test that GlobalConfig can be serialized to dict."""
        config = GlobalConfig(
            app={"name": "Serialize Test"},  # type: ignore[arg-type]
            server={"port": 9000},  # type: ignore[arg-type]
            database={"url": "postgresql://localhost/db"},  # type: ignore[arg-type]
            llm={"provider": "openai"},  # type: ignore[arg-type]
            output={"format": "yaml"},  # type: ignore[arg-type]
            cors={"origins": ["http://example.com"]},  # type: ignore[arg-type]
            logging={"level": "DEBUG"},  # type: ignore[arg-type]
        )

        # Serialize to dict
        config_dict = config.model_dump()

        # Verify structure
        assert isinstance(config_dict, dict)
        assert config_dict["app"]["name"] == "Serialize Test"
        assert config_dict["server"]["port"] == 9000
        assert config_dict["cors"]["origins"] == ["http://example.com"]
