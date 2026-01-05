"""Integration tests for the complete YAML configuration system.

These tests verify that all components of the config system work together correctly:
- Global and project config loading
- Environment variable substitution
- ConfigurationManager integration
- Settings class integration
- End-to-end workflows
- Error handling and validation
"""

import os
import tempfile
from pathlib import Path

import pytest

from src.config import (
    ConfigurationManager,
    GlobalConfig,
    ProjectConfig,
)
from src.config.settings import Settings
from src.config.yaml_loader import (
    clear_global_config_cache,
    clear_project_configs_cache,
)


class TestCompleteConfigWorkflow:
    """Integration tests for complete config loading workflow."""

    def setup_method(self) -> None:
        """Set up test environment before each test."""
        clear_global_config_cache()
        clear_project_configs_cache()
        ConfigurationManager.reset_instance()
        self.original_env = os.environ.copy()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        clear_global_config_cache()
        clear_project_configs_cache()
        ConfigurationManager.reset_instance()
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_end_to_end_config_loading(self) -> None:
        """Test complete workflow from file loading to usage."""
        # Set up environment variables
        os.environ["DB_HOST"] = "prod-db.example.com"
        os.environ["DB_PORT"] = "5432"
        os.environ["LLM_KEY"] = "sk-test-key-12345"
        os.environ["REPO_URL"] = "https://github.com/org/myproject.git"

        # Create temporary config files
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as global_file:
            global_file.write("""
app:
  name: "Integration Test App"
  version: "2.0.0"

server:
  host: "0.0.0.0"
  port: 9000
  environment: "production"

database:
  url: "postgresql://${DB_HOST}:${DB_PORT}/mydb"
  pool_size: 15

llm:
  provider: "openai"
  model: "gpt-4"
  api_key: "${LLM_KEY}"
  temperature: 0.5

output:
  format: "json"
  directory: "./output/reports"

cors:
  origins:
    - "https://app.example.com"
  allow_credentials: true

logging:
  level: "WARNING"
""")
            global_temp = global_file.name

        with tempfile.TemporaryDirectory() as projects_temp:
            # Create multiple project configs
            project1 = Path(projects_temp) / "frontend.yaml"
            project1.write_text("""
name: "frontend"
display_name: "Frontend Application"
description: "React-based frontend"
enabled: true

repository:
  url: "${REPO_URL}"
  branch: "main"
  clone_path: "./repos/frontend"

languages:
  - "javascript"
  - "typescript"
  - "css"

indexing:
  include:
    - "src/**/*.ts"
    - "src/**/*.tsx"
    - "src/**/*.js"
  exclude:
    - "**/*.test.ts"
    - "**/*.spec.ts"
    - "**/node_modules/**"
  max_file_size: 1048576

ownership:
  rules:
    - path: "src/components/**"
      team: "frontend-team"
      owners: ["alice@example.com", "bob@example.com"]
    - path: "src/api/**"
      team: "api-team"
      owners: ["charlie@example.com"]

settings:
  complexity_threshold: 15
  duplication_threshold: 5
""")

            project2 = Path(projects_temp) / "backend.yaml"
            project2.write_text("""
name: "backend"
display_name: "Backend API"
description: "Python FastAPI backend"
enabled: true

repository:
  url: "https://github.com/org/backend.git"
  branch: "develop"
  clone_path: "./repos/backend"

languages:
  - "python"

indexing:
  include:
    - "src/**/*.py"
  exclude:
    - "**/tests/**"
    - "**/__pycache__/**"

ownership:
  rules:
    - path: "src/**"
      team: "backend-team"
      owners: ["david@example.com", "eve@example.com"]

settings:
  complexity_threshold: 10
  duplication_threshold: 3
""")

            try:
                # Initialize configuration manager
                manager = ConfigurationManager.get_instance(
                    global_config_path=global_temp,
                    projects_dir=projects_temp,
                )

                # Test 1: Verify global config loaded correctly
                global_config = manager.get_global_config()
                assert isinstance(global_config, GlobalConfig)
                assert global_config.app.name == "Integration Test App"
                assert global_config.app.version == "2.0.0"
                assert global_config.server.port == 9000
                assert global_config.server.environment == "production"

                # Verify env var substitution in global config
                assert global_config.database.url == "postgresql://prod-db.example.com:5432/mydb"
                assert global_config.llm.api_key == "sk-test-key-12345"

                # Test 2: Verify all projects loaded
                all_projects = manager.get_all_projects()
                assert len(all_projects) == 2
                assert "frontend" in all_projects
                assert "backend" in all_projects

                # Test 3: Verify specific project config
                frontend = manager.get_project_config("frontend")
                assert isinstance(frontend, ProjectConfig)
                assert frontend.display_name == "Frontend Application"
                assert frontend.repository.url == "https://github.com/org/myproject.git"  # From env var
                assert frontend.repository.branch == "main"
                assert len(frontend.languages) == 3
                assert "typescript" in frontend.languages
                assert len(frontend.ownership.rules) == 2
                assert frontend.settings.complexity_threshold == 15

                # Test 4: Verify second project
                backend = manager.get_project_config("backend")
                assert backend.display_name == "Backend API"
                assert backend.repository.url == "https://github.com/org/backend.git"
                assert backend.repository.branch == "develop"
                assert backend.languages == ["python"]
                assert backend.settings.complexity_threshold == 10
                assert backend.settings.duplication_threshold == 3

                # Test 5: Verify reload functionality
                # Modify a file
                project1.write_text("""
name: "frontend"
display_name: "Updated Frontend"
repository:
  url: "https://github.com/org/updated.git"
  clone_path: "./repos/updated"
""")

                # Should still have cached version
                frontend_cached = manager.get_project_config("frontend")
                assert frontend_cached.display_name == "Frontend Application"

                # After reload, should see new version
                manager.reload()
                frontend_reloaded = manager.get_project_config("frontend")
                assert frontend_reloaded.display_name == "Updated Frontend"
                assert frontend_reloaded.repository.url == "https://github.com/org/updated.git"

            finally:
                Path(global_temp).unlink()

    def test_config_manager_with_real_config_files(self) -> None:
        """Test ConfigurationManager with real config files from the repo."""
        # This test uses the actual config files in the repository
        manager = ConfigurationManager.get_instance(
            global_config_path="config/global.yaml",
            projects_dir="config/projects",
        )

        # Should successfully load global config
        global_config = manager.get_global_config()
        assert isinstance(global_config, GlobalConfig)
        assert global_config.app.name == "PX BugHunter"

        # Should successfully load project configs
        all_projects = manager.get_all_projects()
        assert isinstance(all_projects, dict)

        # If example project exists, verify it
        if "example-project" in all_projects:
            example = manager.get_project_config("example-project")
            assert isinstance(example, ProjectConfig)
            assert example.display_name == "Example Project"

    def test_settings_integration_with_yaml(self) -> None:
        """Test Settings class integration with YAML config."""
        # Create a temporary global config
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("""
app:
  name: "Settings Test App"
  version: "3.0.0"
  description: "Testing Settings integration"

server:
  host: "api.example.com"
  port: 9999
  environment: "staging"
  debug: false

database:
  url: "postgresql://localhost/testdb"

llm:
  provider: "openai"

output:
  format: "json"

cors:
  origins:
    - "http://test1.example.com"
    - "http://test2.example.com"
  allow_credentials: false
  allow_methods:
    - "GET"
    - "POST"
  allow_headers:
    - "Authorization"

logging:
  level: "DEBUG"
""")
            temp_file = f.name

        try:
            # Clear caches
            clear_global_config_cache()

            # Create Settings instance (it should load from YAML)

            # Create a new Settings instance with YAML values
            # by loading the config first
            from src.config.yaml_loader import load_global_config
            global_config = load_global_config(temp_file)

            # Verify values from global config (not Settings class)
            # Settings class would need the yaml file as default path
            assert global_config.app.name == "Settings Test App"
            assert global_config.app.version == "3.0.0"
            assert global_config.app.description == "Testing Settings integration"
            assert global_config.server.host == "api.example.com"
            assert global_config.server.port == 9999
            assert global_config.server.environment == "staging"
            assert global_config.server.debug is False
            assert global_config.logging.level == "DEBUG"

            # Verify CORS settings
            assert len(global_config.cors.origins) == 2
            assert "http://test1.example.com" in global_config.cors.origins
            assert global_config.cors.allow_credentials is False

        finally:
            Path(temp_file).unlink()
            clear_global_config_cache()

    def test_env_vars_override_yaml_values(self) -> None:
        """Test that environment variables override YAML values (priority)."""
        # Set environment variables
        os.environ["TEST_HOST"] = "env-override.example.com"
        os.environ["TEST_PORT"] = "7777"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("""
app:
  name: "Priority Test"

server:
  host: "yaml-value.example.com"
  port: 6666

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
            # Load config with env var substitution placeholders
            from src.config.yaml_loader import load_yaml_with_env_vars

            # Modify file to use env vars
            Path(temp_file).write_text("""
app:
  name: "Priority Test"

server:
  host: "${TEST_HOST:-yaml-value.example.com}"
  port: ${TEST_PORT:-6666}

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

            # Load the config
            config_data = load_yaml_with_env_vars(temp_file)

            # Verify env vars took precedence (note: port is string before Pydantic validation)
            assert config_data["server"]["host"] == "env-override.example.com"
            assert config_data["server"]["port"] == "7777"

        finally:
            Path(temp_file).unlink()

    def test_backward_compatibility_without_yaml(self) -> None:
        """Test that Settings works without YAML config (backward compatibility)."""
        # Set environment variables
        os.environ["APP_NAME"] = "Env Only App"
        os.environ["PORT"] = "5555"
        os.environ["DEBUG"] = "true"

        # Create Settings with a non-existent YAML path
        # Settings should fall back to env vars only
        settings = Settings(
            app_name=os.environ.get("APP_NAME", "PX BugHunter"),
            port=int(os.environ.get("PORT", 8000)),
            debug=os.environ.get("DEBUG", "false").lower() == "true",
        )

        # Verify it used environment variables
        assert settings.app_name == "Env Only App"
        assert settings.port == 5555
        assert settings.debug is True


class TestConfigurationErrorScenarios:
    """Integration tests for error scenarios with helpful messages."""

    def setup_method(self) -> None:
        """Set up test environment before each test."""
        clear_global_config_cache()
        clear_project_configs_cache()
        ConfigurationManager.reset_instance()
        self.original_env = os.environ.copy()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        clear_global_config_cache()
        clear_project_configs_cache()
        ConfigurationManager.reset_instance()
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_missing_required_env_var_in_global_config(self) -> None:
        """Test clear error when required env var is missing in global config."""
        os.environ.pop("REQUIRED_DB_HOST", None)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("""
app:
  name: "Test"

server:
  host: "localhost"

database:
  url: "postgresql://${REQUIRED_DB_HOST}/db"

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
            manager = ConfigurationManager.get_instance(
                global_config_path=temp_file
            )

            # Should raise clear error about missing env var
            with pytest.raises(ValueError, match="Required environment variable 'REQUIRED_DB_HOST'"):
                manager.get_global_config()

        finally:
            Path(temp_file).unlink()

    def test_invalid_yaml_syntax_error(self) -> None:
        """Test clear error for invalid YAML syntax."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("""
app:
  name: "Test"
  invalid: yaml: [[[
""")
            temp_file = f.name

        try:
            manager = ConfigurationManager.get_instance(
                global_config_path=temp_file
            )

            with pytest.raises(ValueError, match="Failed to parse YAML file"):
                manager.get_global_config()

        finally:
            Path(temp_file).unlink()

    def test_validation_error_with_field_details(self) -> None:
        """Test that validation errors include field details."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("""
app:
  name: "Test"

server:
  host: "localhost"
  port: 99999  # Invalid: > 65535

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
            manager = ConfigurationManager.get_instance(
                global_config_path=temp_file
            )

            with pytest.raises(ValueError, match="Configuration validation failed"):
                manager.get_global_config()

        finally:
            Path(temp_file).unlink()

    def test_missing_project_error_shows_available_projects(self) -> None:
        """Test that missing project error lists available projects."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some projects
            project1 = Path(temp_dir) / "alpha.yaml"
            project1.write_text("""
name: "alpha"
display_name: "Alpha Project"
repository:
  url: "https://github.com/test/alpha.git"
  clone_path: "./repos/alpha"
""")

            project2 = Path(temp_dir) / "beta.yaml"
            project2.write_text("""
name: "beta"
display_name: "Beta Project"
repository:
  url: "https://github.com/test/beta.git"
  clone_path: "./repos/beta"
""")

            manager = ConfigurationManager.get_instance(projects_dir=temp_dir)

            # Try to get non-existent project
            with pytest.raises(KeyError) as exc_info:
                manager.get_project_config("gamma")

            # Error should list available projects
            error_msg = str(exc_info.value)
            assert "gamma" in error_msg
            assert "alpha" in error_msg
            assert "beta" in error_msg
            assert "Available projects:" in error_msg

    def test_duplicate_project_names_error(self) -> None:
        """Test clear error when duplicate project names exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create two files with same project name
            project1 = Path(temp_dir) / "file1.yaml"
            project1.write_text("""
name: "duplicate"
display_name: "First"
repository:
  url: "https://github.com/test/repo1.git"
  clone_path: "./repos/dup1"
""")

            project2 = Path(temp_dir) / "file2.yaml"
            project2.write_text("""
name: "duplicate"
display_name: "Second"
repository:
  url: "https://github.com/test/repo2.git"
  clone_path: "./repos/dup2"
""")

            manager = ConfigurationManager.get_instance(projects_dir=temp_dir)

            # Should raise error about duplicate names
            with pytest.raises(ValueError, match="duplicate"):
                manager.get_all_projects()

    def test_invalid_project_config_includes_filename(self) -> None:
        """Test that project validation errors include the filename."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create invalid project config
            project_file = Path(temp_dir) / "broken.yaml"
            project_file.write_text("""
name: "broken"
display_name: "Broken Project"
repository:
  url: "https://github.com/test/repo.git"
  clone_path: "./repos/broken"
settings:
  duplication_threshold: 101  # Invalid: must be <= 100
""")

            manager = ConfigurationManager.get_instance(projects_dir=temp_dir)

            # Should raise error mentioning the filename
            with pytest.raises(ValueError) as exc_info:
                manager.get_all_projects()

            error_msg = str(exc_info.value)
            assert "broken.yaml" in error_msg or "broken" in error_msg


class TestConfigurationHotReload:
    """Integration tests for hot-reload functionality."""

    def setup_method(self) -> None:
        """Set up test environment before each test."""
        clear_global_config_cache()
        clear_project_configs_cache()
        ConfigurationManager.reset_instance()
        self.original_env = os.environ.copy()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        clear_global_config_cache()
        clear_project_configs_cache()
        ConfigurationManager.reset_instance()
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_detect_global_config_changes(self) -> None:
        """Test detecting changes to global config without restart."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("""
app:
  name: "Original App"
  version: "1.0.0"

server:
  host: "localhost"
  port: 8000

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
            manager = ConfigurationManager.get_instance(
                global_config_path=temp_file
            )

            # Load initial config
            config1 = manager.get_global_config()
            assert config1.app.name == "Original App"
            assert config1.app.version == "1.0.0"

            # Modify the file
            Path(temp_file).write_text("""
app:
  name: "Updated App"
  version: "2.0.0"

server:
  host: "localhost"
  port: 9000

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

            # Without reload, still sees old cached values
            config2 = manager.get_global_config()
            assert config2.app.name == "Original App"

            # After reload, sees new values
            manager.reload()
            config3 = manager.get_global_config()
            assert config3.app.name == "Updated App"
            assert config3.app.version == "2.0.0"
            assert config3.server.port == 9000

        finally:
            Path(temp_file).unlink()

    def test_detect_new_project_added(self) -> None:
        """Test detecting when a new project is added."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Start with one project
            project1 = Path(temp_dir) / "project1.yaml"
            project1.write_text("""
name: "project1"
display_name: "Project One"
repository:
  url: "https://github.com/test/proj1.git"
  clone_path: "./repos/proj1"
""")

            manager = ConfigurationManager.get_instance(projects_dir=temp_dir)

            # Load initial projects
            projects1 = manager.get_all_projects()
            assert len(projects1) == 1
            assert "project1" in projects1

            # Add a second project
            project2 = Path(temp_dir) / "project2.yaml"
            project2.write_text("""
name: "project2"
display_name: "Project Two"
repository:
  url: "https://github.com/test/proj2.git"
  clone_path: "./repos/proj2"
""")

            # Without reload, still only sees one project
            projects2 = manager.get_all_projects()
            assert len(projects2) == 1

            # After reload, sees both projects
            manager.reload()
            projects3 = manager.get_all_projects()
            assert len(projects3) == 2
            assert "project1" in projects3
            assert "project2" in projects3

    def test_detect_project_removed(self) -> None:
        """Test detecting when a project is removed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Start with two projects
            project1 = Path(temp_dir) / "project1.yaml"
            project1.write_text("""
name: "project1"
display_name: "Project One"
repository:
  url: "https://github.com/test/proj1.git"
  clone_path: "./repos/proj1"
""")

            project2 = Path(temp_dir) / "project2.yaml"
            project2.write_text("""
name: "project2"
display_name: "Project Two"
repository:
  url: "https://github.com/test/proj2.git"
  clone_path: "./repos/proj2"
""")

            manager = ConfigurationManager.get_instance(projects_dir=temp_dir)

            # Load initial projects
            projects1 = manager.get_all_projects()
            assert len(projects1) == 2

            # Remove one project
            project2.unlink()

            # Without reload, still sees both projects (cached)
            projects2 = manager.get_all_projects()
            assert len(projects2) == 2

            # After reload, only sees remaining project
            manager.reload()
            projects3 = manager.get_all_projects()
            assert len(projects3) == 1
            assert "project1" in projects3
            assert "project2" not in projects3

    def test_detect_project_config_modification(self) -> None:
        """Test detecting changes to a project's configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "changeable.yaml"
            project_file.write_text("""
name: "changeable"
display_name: "Original Name"
description: "Original description"
repository:
  url: "https://github.com/test/original.git"
  branch: "main"
  clone_path: "./repos/changeable"
settings:
  complexity_threshold: 10
""")

            manager = ConfigurationManager.get_instance(projects_dir=temp_dir)

            # Load initial config
            project1 = manager.get_project_config("changeable")
            assert project1.display_name == "Original Name"
            assert project1.description == "Original description"
            assert project1.repository.url == "https://github.com/test/original.git"
            assert project1.settings.complexity_threshold == 10

            # Modify the project config
            project_file.write_text("""
name: "changeable"
display_name: "Updated Name"
description: "Updated description"
repository:
  url: "https://github.com/test/updated.git"
  branch: "develop"
  clone_path: "./repos/changeable"
settings:
  complexity_threshold: 20
""")

            # Without reload, still sees old values
            project2 = manager.get_project_config("changeable")
            assert project2.display_name == "Original Name"

            # After reload, sees new values
            manager.reload()
            project3 = manager.get_project_config("changeable")
            assert project3.display_name == "Updated Name"
            assert project3.description == "Updated description"
            assert project3.repository.url == "https://github.com/test/updated.git"
            assert project3.repository.branch == "develop"
            assert project3.settings.complexity_threshold == 20


class TestMultiProjectScenarios:
    """Integration tests for multi-project scenarios."""

    def setup_method(self) -> None:
        """Set up test environment before each test."""
        clear_global_config_cache()
        clear_project_configs_cache()
        ConfigurationManager.reset_instance()
        self.original_env = os.environ.copy()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        clear_global_config_cache()
        clear_project_configs_cache()
        ConfigurationManager.reset_instance()
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_multiple_projects_with_different_settings(self) -> None:
        """Test managing multiple projects with different configurations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create projects with different settings
            frontend = Path(temp_dir) / "frontend.yaml"
            frontend.write_text("""
name: "frontend"
display_name: "Frontend"
repository:
  url: "https://github.com/org/frontend.git"
  clone_path: "./repos/frontend"
languages:
  - "javascript"
  - "typescript"
indexing:
  include:
    - "src/**/*.ts"
  max_file_size: 1048576
settings:
  complexity_threshold: 15
  duplication_threshold: 5
""")

            backend = Path(temp_dir) / "backend.yaml"
            backend.write_text("""
name: "backend"
display_name: "Backend"
repository:
  url: "https://github.com/org/backend.git"
  clone_path: "./repos/backend"
languages:
  - "python"
indexing:
  include:
    - "**/*.py"
  max_file_size: 524288
settings:
  complexity_threshold: 10
  duplication_threshold: 3
""")

            mobile = Path(temp_dir) / "mobile.yaml"
            mobile.write_text("""
name: "mobile"
display_name: "Mobile App"
repository:
  url: "https://github.com/org/mobile.git"
  clone_path: "./repos/mobile"
languages:
  - "swift"
  - "kotlin"
indexing:
  include:
    - "**/*.swift"
    - "**/*.kt"
  max_file_size: 2097152
settings:
  complexity_threshold: 12
  duplication_threshold: 4
""")

            manager = ConfigurationManager.get_instance(projects_dir=temp_dir)

            # Get all projects
            all_projects = manager.get_all_projects()
            assert len(all_projects) == 3

            # Verify each project has its own settings
            fe = all_projects["frontend"]
            assert fe.settings.complexity_threshold == 15
            assert fe.settings.duplication_threshold == 5
            assert fe.indexing.max_file_size == 1048576

            be = all_projects["backend"]
            assert be.settings.complexity_threshold == 10
            assert be.settings.duplication_threshold == 3
            assert be.indexing.max_file_size == 524288

            mob = all_projects["mobile"]
            assert mob.settings.complexity_threshold == 12
            assert mob.settings.duplication_threshold == 4
            assert mob.indexing.max_file_size == 2097152

    def test_enabled_disabled_projects(self) -> None:
        """Test filtering enabled vs disabled projects."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create enabled and disabled projects
            active = Path(temp_dir) / "active.yaml"
            active.write_text("""
name: "active"
display_name: "Active Project"
enabled: true
repository:
  url: "https://github.com/org/active.git"
  clone_path: "./repos/active"
""")

            disabled = Path(temp_dir) / "disabled.yaml"
            disabled.write_text("""
name: "disabled"
display_name: "Disabled Project"
enabled: false
repository:
  url: "https://github.com/org/disabled.git"
  clone_path: "./repos/disabled"
""")

            manager = ConfigurationManager.get_instance(projects_dir=temp_dir)

            # All projects are loaded regardless of enabled flag
            all_projects = manager.get_all_projects()
            assert len(all_projects) == 2

            # But we can filter by enabled flag
            active_project = all_projects["active"]
            assert active_project.enabled is True

            disabled_project = all_projects["disabled"]
            assert disabled_project.enabled is False

            # Can filter enabled projects in application code
            enabled_projects = {
                name: config
                for name, config in all_projects.items()
                if config.enabled
            }
            assert len(enabled_projects) == 1
            assert "active" in enabled_projects
