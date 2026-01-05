"""Tests for project configuration loading and validation."""

import os
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.config.models import ProjectConfig
from src.config.yaml_loader import (
    clear_project_configs_cache,
    load_project_configs,
)


class TestLoadProjectConfigs:
    """Tests for loading and validating project configurations."""

    def setup_method(self) -> None:
        """Set up test environment before each test."""
        # Clear the project configs cache before each test
        clear_project_configs_cache()
        # Store original env vars to restore later
        self.original_env = os.environ.copy()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        clear_project_configs_cache()
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_load_single_valid_project_config(self) -> None:
        """Test loading a single valid project configuration file."""
        # Create a temporary directory for projects
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a valid project config file
            project_file = Path(temp_dir) / "test-project.yaml"
            project_file.write_text("""
name: "test-project"
display_name: "Test Project"
description: "A test project"
enabled: true

repository:
  url: "https://github.com/test/repo.git"
  branch: "main"
  clone_path: "./repos/test-project"

languages:
  - "python"
  - "javascript"

indexing:
  include:
    - "src/**/*.py"
    - "src/**/*.js"
  exclude:
    - "**/__pycache__/**"
    - "**/node_modules/**"
  max_file_size: 500

ownership:
  rules:
    - path: "src/backend/**"
      team: "backend-team"
      owners:
        - "dev@example.com"

settings:
  enable_static_analysis: true
  enable_security_scanning: true
  complexity_threshold: 10
""")

            # Load the project configs
            configs = load_project_configs(temp_dir)

            # Verify the config was loaded correctly
            assert len(configs) == 1
            assert "test-project" in configs

            config = configs["test-project"]
            assert isinstance(config, ProjectConfig)
            assert config.name == "test-project"
            assert config.display_name == "Test Project"
            assert config.description == "A test project"
            assert config.enabled is True
            assert config.repository.url == "https://github.com/test/repo.git"
            assert config.repository.branch == "main"
            assert config.repository.clone_path == "./repos/test-project"
            assert config.languages == ["python", "javascript"]
            assert "src/**/*.py" in config.indexing.include
            assert "**/__pycache__/**" in config.indexing.exclude
            assert config.indexing.max_file_size == 500
            assert len(config.ownership.rules) == 1
            assert config.ownership.rules[0].path == "src/backend/**"
            assert config.ownership.rules[0].team == "backend-team"
            assert config.ownership.rules[0].owners == ["dev@example.com"]
            assert config.settings.enable_static_analysis is True
            assert config.settings.complexity_threshold == 10

    def test_load_multiple_project_configs(self) -> None:
        """Test loading multiple project configuration files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create first project config
            project1 = Path(temp_dir) / "project1.yaml"
            project1.write_text("""
name: "project-one"
display_name: "Project One"
repository:
  url: "https://github.com/test/repo1.git"
  clone_path: "./repos/project1"
languages:
  - "python"
""")

            # Create second project config
            project2 = Path(temp_dir) / "project2.yaml"
            project2.write_text("""
name: "project-two"
display_name: "Project Two"
repository:
  url: "https://github.com/test/repo2.git"
  clone_path: "./repos/project2"
languages:
  - "javascript"
""")

            # Load all project configs
            configs = load_project_configs(temp_dir)

            # Verify both configs were loaded
            assert len(configs) == 2
            assert "project-one" in configs
            assert "project-two" in configs
            assert configs["project-one"].display_name == "Project One"
            assert configs["project-two"].display_name == "Project Two"
            assert configs["project-one"].languages == ["python"]
            assert configs["project-two"].languages == ["javascript"]

    def test_load_project_config_with_env_vars(self) -> None:
        """Test environment variable substitution in project config."""
        os.environ["TEST_REPO_URL"] = "https://github.com/prod/repo.git"
        os.environ["TEST_BRANCH"] = "production"
        os.environ["TEST_CLONE_PATH"] = "/var/repos/prod-project"

        with tempfile.TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "prod.yaml"
            project_file.write_text("""
name: "prod-project"
display_name: "Production Project"
repository:
  url: "${TEST_REPO_URL}"
  branch: "${TEST_BRANCH}"
  clone_path: "${TEST_CLONE_PATH}"
languages:
  - "python"
""")

            configs = load_project_configs(temp_dir)

            # Verify environment variables were substituted
            config = configs["prod-project"]
            assert config.repository.url == "https://github.com/prod/repo.git"
            assert config.repository.branch == "production"
            assert config.repository.clone_path == "/var/repos/prod-project"

    def test_load_project_config_with_env_var_defaults(self) -> None:
        """Test environment variable default values are used when var is not set."""
        # Ensure the env vars don't exist
        os.environ.pop("MISSING_BRANCH", None)
        os.environ.pop("MISSING_PATH", None)

        with tempfile.TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "test.yaml"
            project_file.write_text("""
name: "test-project"
display_name: "Test Project"
repository:
  url: "https://github.com/test/repo.git"
  branch: "${MISSING_BRANCH:-develop}"
  clone_path: "${MISSING_PATH:-./default-repos/test}"
languages:
  - "python"
""")

            configs = load_project_configs(temp_dir)

            # Verify default values from env var syntax were used
            config = configs["test-project"]
            assert config.repository.branch == "develop"
            assert config.repository.clone_path == "./default-repos/test"

    def test_load_project_config_with_defaults(self) -> None:
        """Test that default values are applied when fields are missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "minimal.yaml"
            project_file.write_text("""
# Minimal config - most fields should use defaults
name: "minimal-project"
display_name: "Minimal Project"
repository:
  url: "https://github.com/test/repo.git"
  clone_path: "./repos/minimal"
""")

            configs = load_project_configs(temp_dir)
            config = configs["minimal-project"]

            # Verify defaults were applied
            assert config.description == ""  # Default empty string
            assert config.enabled is True  # Default enabled
            assert config.repository.branch == "main"  # Default branch
            assert config.repository.ssh_key is None  # Default None
            assert config.languages == []  # Default empty list
            assert config.indexing.include == []  # Default empty list
            assert config.indexing.exclude == []  # Default empty list
            assert config.indexing.max_file_size == 500  # Default max_file_size
            assert config.ownership.rules == []  # Default empty list
            assert config.settings.enable_static_analysis is True  # Default True
            assert config.settings.complexity_threshold == 10  # Default 10
            assert config.settings.duplication_threshold == 5  # Default 5

    def test_load_project_config_invalid_field_value(self) -> None:
        """Test that invalid field values raise validation errors with filename."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "invalid.yaml"
            project_file.write_text("""
name: "invalid-project"
display_name: "Invalid Project"
repository:
  url: "https://github.com/test/repo.git"
  clone_path: "./repos/invalid"
indexing:
  max_file_size: 0  # Invalid: must be >= 1
""")

            with pytest.raises(ValueError, match="Configuration validation failed for invalid.yaml"):
                load_project_configs(temp_dir)

    def test_load_project_config_invalid_complexity_threshold(self) -> None:
        """Test that invalid complexity threshold raises error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "bad-complexity.yaml"
            project_file.write_text("""
name: "bad-project"
display_name: "Bad Project"
repository:
  url: "https://github.com/test/repo.git"
  clone_path: "./repos/bad"
settings:
  complexity_threshold: 0  # Invalid: must be >= 1
""")

            with pytest.raises(ValueError, match="Configuration validation failed"):
                load_project_configs(temp_dir)

    def test_load_project_config_invalid_duplication_threshold(self) -> None:
        """Test that invalid duplication threshold raises error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "bad-dup.yaml"
            project_file.write_text("""
name: "bad-project"
display_name: "Bad Project"
repository:
  url: "https://github.com/test/repo.git"
  clone_path: "./repos/bad"
settings:
  duplication_threshold: 150  # Invalid: must be <= 100
""")

            with pytest.raises(ValueError, match="Configuration validation failed"):
                load_project_configs(temp_dir)

    def test_load_project_config_missing_required_field(self) -> None:
        """Test that missing required fields raise validation errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "missing.yaml"
            project_file.write_text("""
# Missing required 'name' field
display_name: "Missing Name Project"
repository:
  url: "https://github.com/test/repo.git"
  clone_path: "./repos/missing"
""")

            with pytest.raises(ValueError, match="Configuration validation failed"):
                load_project_configs(temp_dir)

    def test_load_project_config_missing_required_env_var(self) -> None:
        """Test that missing required environment variable raises error."""
        os.environ.pop("REQUIRED_REPO_URL", None)

        with tempfile.TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "missing-env.yaml"
            project_file.write_text("""
name: "env-project"
display_name: "Env Project"
repository:
  url: "${REQUIRED_REPO_URL}"  # No default provided
  clone_path: "./repos/env"
""")

            with pytest.raises(ValueError, match="Required environment variable 'REQUIRED_REPO_URL'"):
                load_project_configs(temp_dir)

    def test_load_project_configs_directory_not_found(self) -> None:
        """Test that loading from non-existent directory raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Projects directory not found"):
            load_project_configs("/nonexistent/projects/dir")

    def test_load_project_config_invalid_yaml(self) -> None:
        """Test that malformed YAML raises appropriate error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "malformed.yaml"
            project_file.write_text("invalid: yaml: content: [[[")

            with pytest.raises(ValueError, match="Failed to parse YAML file"):
                load_project_configs(temp_dir)

    def test_load_project_configs_empty_directory(self) -> None:
        """Test loading from directory with no YAML files returns empty dict."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create directory but no YAML files
            configs = load_project_configs(temp_dir)

            # Should return empty dict
            assert configs == {}
            assert len(configs) == 0

    def test_load_project_configs_duplicate_names(self) -> None:
        """Test that duplicate project names are detected and raise error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create two files with the same project name
            project1 = Path(temp_dir) / "project1.yaml"
            project1.write_text("""
name: "duplicate-name"
display_name: "First Project"
repository:
  url: "https://github.com/test/repo1.git"
  clone_path: "./repos/project1"
""")

            project2 = Path(temp_dir) / "project2.yaml"
            project2.write_text("""
name: "duplicate-name"
display_name: "Second Project"
repository:
  url: "https://github.com/test/repo2.git"
  clone_path: "./repos/project2"
""")

            with pytest.raises(ValueError, match="Duplicate project name 'duplicate-name'"):
                load_project_configs(temp_dir)

    def test_load_project_configs_caching(self) -> None:
        """Test that project configs are cached as singleton."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "cached.yaml"
            project_file.write_text("""
name: "cached-project"
display_name: "Cached Project"
repository:
  url: "https://github.com/test/repo.git"
  clone_path: "./repos/cached"
""")

            # Load configs twice
            configs1 = load_project_configs(temp_dir)
            configs2 = load_project_configs(temp_dir)

            # Should return the same instance (singleton)
            assert configs1 is configs2

    def test_clear_project_configs_cache(self) -> None:
        """Test that clearing cache forces reload."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "test.yaml"
            project_file.write_text("""
name: "test-project"
display_name: "Test Project"
repository:
  url: "https://github.com/test/repo.git"
  clone_path: "./repos/test"
""")

            # Load configs
            configs1 = load_project_configs(temp_dir)

            # Clear cache
            clear_project_configs_cache()

            # Load again
            configs2 = load_project_configs(temp_dir)

            # Should be different instances after cache clear
            assert configs1 is not configs2
            # But should have same values
            assert configs1["test-project"].name == configs2["test-project"].name

    def test_load_project_config_type_coercion(self) -> None:
        """Test that string values are correctly coerced to expected types."""
        os.environ["STR_MAX_SIZE"] = "1000"
        os.environ["STR_ENABLED"] = "false"
        os.environ["STR_COMPLEXITY"] = "15"

        with tempfile.TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "coerce.yaml"
            project_file.write_text("""
name: "coerce-project"
display_name: "Type Coercion Project"
enabled: ${STR_ENABLED}
repository:
  url: "https://github.com/test/repo.git"
  clone_path: "./repos/coerce"
indexing:
  max_file_size: ${STR_MAX_SIZE}
settings:
  complexity_threshold: ${STR_COMPLEXITY}
""")

            configs = load_project_configs(temp_dir)
            config = configs["coerce-project"]

            # Verify types were coerced correctly
            assert config.enabled is False
            assert isinstance(config.enabled, bool)
            assert config.indexing.max_file_size == 1000
            assert isinstance(config.indexing.max_file_size, int)
            assert config.settings.complexity_threshold == 15
            assert isinstance(config.settings.complexity_threshold, int)

    def test_load_project_config_ownership_structure(self) -> None:
        """Test loading project config with complex ownership mapping."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "ownership.yaml"
            project_file.write_text("""
name: "ownership-project"
display_name: "Ownership Project"
repository:
  url: "https://github.com/test/repo.git"
  clone_path: "./repos/ownership"

ownership:
  rules:
    - path: "src/frontend/**"
      team: "frontend-team"
      owners:
        - "john.doe@example.com"
        - "jane.smith@example.com"
    - path: "src/backend/**"
      team: "backend-team"
      owners:
        - "bob.johnson@example.com"
    - path: "**"
      team: "general"
      owners:
        - "tech-lead@example.com"
""")

            configs = load_project_configs(temp_dir)
            config = configs["ownership-project"]

            # Verify ownership structure
            assert len(config.ownership.rules) == 3

            rule1 = config.ownership.rules[0]
            assert rule1.path == "src/frontend/**"
            assert rule1.team == "frontend-team"
            assert len(rule1.owners) == 2
            assert "john.doe@example.com" in rule1.owners
            assert "jane.smith@example.com" in rule1.owners

            rule2 = config.ownership.rules[1]
            assert rule2.path == "src/backend/**"
            assert rule2.team == "backend-team"
            assert len(rule2.owners) == 1
            assert "bob.johnson@example.com" in rule2.owners

            rule3 = config.ownership.rules[2]
            assert rule3.path == "**"
            assert rule3.team == "general"
            assert len(rule3.owners) == 1

    def test_load_project_config_mixed_env_and_literals(self) -> None:
        """Test config with mix of environment variables and literal values."""
        os.environ["PROD_REPO"] = "https://github.com/prod/main.git"
        os.environ["PROD_PATH"] = "/prod/repos/main"

        with tempfile.TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "mixed.yaml"
            project_file.write_text("""
name: "mixed-project"
display_name: "Mixed Project"
description: "Mix of env vars and literals"
enabled: true
repository:
  url: "${PROD_REPO}"
  branch: "main"
  clone_path: "${PROD_PATH}"
languages:
  - "python"
  - "rust"
indexing:
  max_file_size: 1000
settings:
  enable_static_analysis: false
  complexity_threshold: 20
""")

            configs = load_project_configs(temp_dir)
            config = configs["mixed-project"]

            # Verify mix of env vars and literals
            assert config.name == "mixed-project"  # Literal
            assert config.repository.url == "https://github.com/prod/main.git"  # Env var
            assert config.repository.branch == "main"  # Literal
            assert config.repository.clone_path == "/prod/repos/main"  # Env var
            assert config.languages == ["python", "rust"]  # Literal
            assert config.indexing.max_file_size == 1000  # Literal

    def test_load_project_config_optional_auth_fields(self) -> None:
        """Test that optional authentication fields can be set."""
        os.environ["SSH_KEY_PATH"] = "/home/user/.ssh/id_rsa"
        os.environ["GIT_USERNAME"] = "deploy-user"
        os.environ["GIT_TOKEN"] = "ghp_secrettoken123"

        with tempfile.TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "auth.yaml"
            project_file.write_text("""
name: "auth-project"
display_name: "Auth Project"
repository:
  url: "https://github.com/private/repo.git"
  clone_path: "./repos/auth"
  ssh_key: "${SSH_KEY_PATH}"
  username: "${GIT_USERNAME}"
  password: "${GIT_TOKEN}"
""")

            configs = load_project_configs(temp_dir)
            config = configs["auth-project"]

            # Verify auth fields were set
            assert config.repository.ssh_key == "/home/user/.ssh/id_rsa"
            assert config.repository.username == "deploy-user"
            assert config.repository.password == "ghp_secrettoken123"

    def test_load_project_config_complex_settings(self) -> None:
        """Test loading config with complex settings structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "settings.yaml"
            project_file.write_text("""
name: "settings-project"
display_name: "Settings Project"
repository:
  url: "https://github.com/test/repo.git"
  clone_path: "./repos/settings"

settings:
  enable_static_analysis: true
  enable_security_scanning: true
  enable_code_quality_checks: false
  notify_on_high_severity: true
  notify_on_medium_severity: true
  notification_channels:
    - "slack"
    - "email"
    - "pagerduty"
  complexity_threshold: 15
  duplication_threshold: 8
""")

            configs = load_project_configs(temp_dir)
            config = configs["settings-project"]

            # Verify settings structure
            assert config.settings.enable_static_analysis is True
            assert config.settings.enable_security_scanning is True
            assert config.settings.enable_code_quality_checks is False
            assert config.settings.notify_on_high_severity is True
            assert config.settings.notify_on_medium_severity is True
            assert len(config.settings.notification_channels) == 3
            assert "slack" in config.settings.notification_channels
            assert "email" in config.settings.notification_channels
            assert "pagerduty" in config.settings.notification_channels
            assert config.settings.complexity_threshold == 15
            assert config.settings.duplication_threshold == 8


class TestProjectConfigModel:
    """Tests for ProjectConfig Pydantic model validation."""

    def test_project_config_direct_instantiation(self) -> None:
        """Test creating ProjectConfig directly with valid data."""
        config = ProjectConfig(
            name="direct-project",
            display_name="Direct Project",
            repository={  # type: ignore[arg-type]
                "url": "https://github.com/test/repo.git",
                "clone_path": "./repos/direct",
            },
        )

        assert config.name == "direct-project"
        assert config.display_name == "Direct Project"
        assert config.repository.url == "https://github.com/test/repo.git"

    def test_project_config_validation_error_details(self) -> None:
        """Test that validation errors provide clear field-level details."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectConfig(
                name="test",
                display_name="Test",
                repository={  # type: ignore[arg-type]
                    "url": "https://github.com/test/repo.git",
                    "clone_path": "./repos/test",
                },
                indexing={  # type: ignore[arg-type]
                    "max_file_size": 0,  # Invalid: must be >= 1
                },
            )

        # Verify error contains field information
        errors = exc_info.value.errors()
        assert any("max_file_size" in str(error["loc"]) for error in errors)

    def test_project_config_optional_fields(self) -> None:
        """Test that optional fields can be omitted."""
        config = ProjectConfig(
            name="minimal",
            display_name="Minimal",
            repository={  # type: ignore[arg-type]
                "url": "https://github.com/test/repo.git",
                "clone_path": "./repos/minimal",
            },
        )

        # Verify optional fields are None or have defaults
        assert config.description == ""
        assert config.enabled is True
        assert config.repository.ssh_key is None
        assert config.repository.username is None
        assert config.repository.password is None
        assert config.languages == []

    def test_project_config_serialization(self) -> None:
        """Test that ProjectConfig can be serialized to dict."""
        config = ProjectConfig(
            name="serialize",
            display_name="Serialize Test",
            repository={  # type: ignore[arg-type]
                "url": "https://github.com/test/repo.git",
                "clone_path": "./repos/serialize",
            },
            languages=["python", "go"],
        )

        # Serialize to dict
        config_dict = config.model_dump()

        # Verify structure
        assert isinstance(config_dict, dict)
        assert config_dict["name"] == "serialize"
        assert config_dict["display_name"] == "Serialize Test"
        assert config_dict["languages"] == ["python", "go"]
        assert config_dict["repository"]["url"] == "https://github.com/test/repo.git"
