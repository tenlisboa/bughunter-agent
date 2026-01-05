"""Tests for ConfigurationManager class."""

import os
import tempfile
from pathlib import Path

import pytest

from src.config.manager import ConfigurationManager, get_config_manager
from src.config.models import GlobalConfig, ProjectConfig
from src.config.yaml_loader import (
    clear_global_config_cache,
    clear_project_configs_cache,
)


class TestConfigurationManager:
    """Tests for the ConfigurationManager class."""

    def setup_method(self) -> None:
        """Set up test environment before each test."""
        # Clear all caches before each test
        clear_global_config_cache()
        clear_project_configs_cache()
        # Reset the singleton instance
        ConfigurationManager.reset_instance()
        # Store original env vars to restore later
        self.original_env = os.environ.copy()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        # Clear all caches
        clear_global_config_cache()
        clear_project_configs_cache()
        # Reset the singleton instance
        ConfigurationManager.reset_instance()
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_singleton_behavior(self) -> None:
        """Test that ConfigurationManager follows singleton pattern."""
        # Get two instances
        manager1 = ConfigurationManager.get_instance()
        manager2 = ConfigurationManager.get_instance()

        # Should be the same instance
        assert manager1 is manager2

    def test_singleton_with_different_paths_ignored(self) -> None:
        """Test that subsequent calls to get_instance() ignore path parameters."""
        # Create first instance with default paths
        manager1 = ConfigurationManager.get_instance()

        # Try to create another instance with different paths
        manager2 = ConfigurationManager.get_instance(
            global_config_path="config/other.yaml",
            projects_dir="config/other_projects",
        )

        # Should still be the same instance
        assert manager1 is manager2

    def test_reset_instance(self) -> None:
        """Test that reset_instance() allows creating a new singleton."""
        # Get first instance
        manager1 = ConfigurationManager.get_instance()

        # Reset the singleton
        ConfigurationManager.reset_instance()

        # Get a new instance
        manager2 = ConfigurationManager.get_instance()

        # Should be different instances
        assert manager1 is not manager2

    def test_get_global_config(self) -> None:
        """Test getting global configuration."""
        # Create a temporary global config file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("""
app:
  name: "Test Manager App"
  version: "1.0.0"

server:
  host: "localhost"
  port: 9000

database:
  url: "postgresql://localhost:5432/testdb"

llm:
  provider: "openai"
  model: "gpt-4"

output:
  format: "json"

cors:
  origins: []

logging:
  level: "INFO"
""")
            temp_file = f.name

        try:
            # Create manager with custom path
            ConfigurationManager.reset_instance()
            manager = ConfigurationManager.get_instance(
                global_config_path=temp_file
            )

            # Get global config
            config = manager.get_global_config()

            # Verify the config was loaded correctly
            assert isinstance(config, GlobalConfig)
            assert config.app.name == "Test Manager App"
            assert config.app.version == "1.0.0"
            assert config.server.port == 9000
        finally:
            Path(temp_file).unlink()

    def test_get_global_config_caching(self) -> None:
        """Test that global config is cached across multiple calls."""
        # Create a temporary global config file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("""
app:
  name: "Cached Manager App"

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
            ConfigurationManager.reset_instance()
            manager = ConfigurationManager.get_instance(
                global_config_path=temp_file
            )

            # Get global config twice
            config1 = manager.get_global_config()
            config2 = manager.get_global_config()

            # Should return the same instance (cached)
            assert config1 is config2
        finally:
            Path(temp_file).unlink()

    def test_get_all_projects(self) -> None:
        """Test getting all project configurations."""
        # Create a temporary projects directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create two project config files
            project1 = Path(temp_dir) / "project1.yaml"
            project1.write_text("""
name: "manager-project-one"
display_name: "Manager Project One"
repository:
  url: "https://github.com/test/repo1.git"
  clone_path: "./repos/project1"
languages:
  - "python"
""")

            project2 = Path(temp_dir) / "project2.yaml"
            project2.write_text("""
name: "manager-project-two"
display_name: "Manager Project Two"
repository:
  url: "https://github.com/test/repo2.git"
  clone_path: "./repos/project2"
languages:
  - "javascript"
""")

            ConfigurationManager.reset_instance()
            manager = ConfigurationManager.get_instance(projects_dir=temp_dir)

            # Get all projects
            projects = manager.get_all_projects()

            # Verify all projects were loaded
            assert len(projects) == 2
            assert "manager-project-one" in projects
            assert "manager-project-two" in projects
            assert isinstance(projects["manager-project-one"], ProjectConfig)
            assert isinstance(projects["manager-project-two"], ProjectConfig)
            assert projects["manager-project-one"].display_name == "Manager Project One"
            assert projects["manager-project-two"].display_name == "Manager Project Two"

    def test_get_all_projects_caching(self) -> None:
        """Test that project configs are cached across multiple calls."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "cached.yaml"
            project_file.write_text("""
name: "cached-project"
display_name: "Cached Project"
repository:
  url: "https://github.com/test/repo.git"
  clone_path: "./repos/cached"
""")

            ConfigurationManager.reset_instance()
            manager = ConfigurationManager.get_instance(projects_dir=temp_dir)

            # Get all projects twice
            projects1 = manager.get_all_projects()
            projects2 = manager.get_all_projects()

            # Should return the same instance (cached)
            assert projects1 is projects2

    def test_get_project_config_by_name(self) -> None:
        """Test getting a specific project configuration by name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple project configs
            project1 = Path(temp_dir) / "project1.yaml"
            project1.write_text("""
name: "specific-project"
display_name: "Specific Project"
description: "A specific project for testing"
repository:
  url: "https://github.com/test/specific.git"
  clone_path: "./repos/specific"
languages:
  - "python"
  - "go"
""")

            project2 = Path(temp_dir) / "project2.yaml"
            project2.write_text("""
name: "other-project"
display_name: "Other Project"
repository:
  url: "https://github.com/test/other.git"
  clone_path: "./repos/other"
""")

            ConfigurationManager.reset_instance()
            manager = ConfigurationManager.get_instance(projects_dir=temp_dir)

            # Get a specific project
            project = manager.get_project_config("specific-project")

            # Verify the correct project was returned
            assert isinstance(project, ProjectConfig)
            assert project.name == "specific-project"
            assert project.display_name == "Specific Project"
            assert project.description == "A specific project for testing"
            assert project.repository.url == "https://github.com/test/specific.git"
            assert project.languages == ["python", "go"]

    def test_get_project_config_missing_project(self) -> None:
        """Test that KeyError is raised when requesting a non-existent project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create one project
            project_file = Path(temp_dir) / "existing.yaml"
            project_file.write_text("""
name: "existing-project"
display_name: "Existing Project"
repository:
  url: "https://github.com/test/repo.git"
  clone_path: "./repos/existing"
""")

            ConfigurationManager.reset_instance()
            manager = ConfigurationManager.get_instance(projects_dir=temp_dir)

            # Try to get a non-existent project
            with pytest.raises(KeyError, match="Project 'nonexistent' not found"):
                manager.get_project_config("nonexistent")

    def test_get_project_config_missing_project_shows_available(self) -> None:
        """Test that error message shows available projects when project is missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create two projects
            project1 = Path(temp_dir) / "project1.yaml"
            project1.write_text("""
name: "project-alpha"
display_name: "Project Alpha"
repository:
  url: "https://github.com/test/alpha.git"
  clone_path: "./repos/alpha"
""")

            project2 = Path(temp_dir) / "project2.yaml"
            project2.write_text("""
name: "project-beta"
display_name: "Project Beta"
repository:
  url: "https://github.com/test/beta.git"
  clone_path: "./repos/beta"
""")

            ConfigurationManager.reset_instance()
            manager = ConfigurationManager.get_instance(projects_dir=temp_dir)

            # Try to get a non-existent project
            with pytest.raises(KeyError) as exc_info:
                manager.get_project_config("project-gamma")

            # Verify error message includes available projects
            error_message = str(exc_info.value)
            assert "project-alpha" in error_message
            assert "project-beta" in error_message
            assert "Available projects:" in error_message

    def test_get_project_config_empty_directory(self) -> None:
        """Test getting project when directory is empty shows 'none' available."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ConfigurationManager.reset_instance()
            manager = ConfigurationManager.get_instance(projects_dir=temp_dir)

            # Try to get a project from empty directory
            with pytest.raises(KeyError) as exc_info:
                manager.get_project_config("any-project")

            # Verify error message indicates no projects available
            error_message = str(exc_info.value)
            assert "Available projects: none" in error_message

    def test_reload_clears_caches(self) -> None:
        """Test that reload() clears all configuration caches."""
        # Create temporary files
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as global_file:
            global_file.write("""
app:
  name: "Original App"

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
            global_temp = global_file.name

        with tempfile.TemporaryDirectory() as projects_temp:
            project_file = Path(projects_temp) / "test.yaml"
            project_file.write_text("""
name: "reload-project"
display_name: "Reload Project"
repository:
  url: "https://github.com/test/repo.git"
  clone_path: "./repos/reload"
""")

            try:
                ConfigurationManager.reset_instance()
                manager = ConfigurationManager.get_instance(
                    global_config_path=global_temp,
                    projects_dir=projects_temp,
                )

                # Load configs
                global_config1 = manager.get_global_config()
                projects1 = manager.get_all_projects()

                # Reload configurations
                manager.reload()

                # Load again
                global_config2 = manager.get_global_config()
                projects2 = manager.get_all_projects()

                # Should be different instances after reload
                assert global_config1 is not global_config2
                assert projects1 is not projects2

                # But should have same values
                assert global_config1.app.name == global_config2.app.name
                assert (
                    projects1["reload-project"].name
                    == projects2["reload-project"].name
                )
            finally:
                Path(global_temp).unlink()

    def test_reload_allows_detecting_config_changes(self) -> None:
        """Test that reload() allows detecting configuration file changes."""
        # Create a temporary project directory
        with tempfile.TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "changing.yaml"
            project_file.write_text("""
name: "changing-project"
display_name: "Original Name"
repository:
  url: "https://github.com/test/repo.git"
  clone_path: "./repos/changing"
""")

            ConfigurationManager.reset_instance()
            manager = ConfigurationManager.get_instance(projects_dir=temp_dir)

            # Load initial config
            project1 = manager.get_project_config("changing-project")
            assert project1.display_name == "Original Name"

            # Modify the file
            project_file.write_text("""
name: "changing-project"
display_name: "Updated Name"
repository:
  url: "https://github.com/test/repo.git"
  clone_path: "./repos/changing"
""")

            # Without reload, should still see old cached value
            project2 = manager.get_project_config("changing-project")
            assert project2.display_name == "Original Name"  # Still cached

            # After reload, should see new value
            manager.reload()
            project3 = manager.get_project_config("changing-project")
            assert project3.display_name == "Updated Name"  # Reloaded

    def test_get_config_manager_convenience_function(self) -> None:
        """Test the get_config_manager() convenience function."""
        ConfigurationManager.reset_instance()

        # Get manager using convenience function
        manager1 = get_config_manager()

        # Should return ConfigurationManager instance
        assert isinstance(manager1, ConfigurationManager)

        # Should follow singleton pattern
        manager2 = get_config_manager()
        assert manager1 is manager2

    def test_get_config_manager_with_custom_paths(self) -> None:
        """Test get_config_manager() with custom paths."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("""
app:
  name: "Custom Path App"

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
            ConfigurationManager.reset_instance()

            # Get manager with custom path
            manager = get_config_manager(global_config_path=temp_file)

            # Verify it uses the custom path
            config = manager.get_global_config()
            assert config.app.name == "Custom Path App"
        finally:
            Path(temp_file).unlink()

    def test_manager_with_environment_variable_substitution(self) -> None:
        """Test that manager handles environment variable substitution."""
        os.environ["TEST_DB_URL"] = "postgresql://testhost:5432/testdb"
        os.environ["TEST_REPO_URL"] = "https://github.com/prod/repo.git"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as global_file:
            global_file.write("""
app:
  name: "Env Test App"

server:
  host: "localhost"

database:
  url: "${TEST_DB_URL}"

llm:
  provider: "openai"

output:
  format: "json"

cors:
  origins: []

logging:
  level: "INFO"
""")
            global_temp = global_file.name

        with tempfile.TemporaryDirectory() as projects_temp:
            project_file = Path(projects_temp) / "env-test.yaml"
            project_file.write_text("""
name: "env-project"
display_name: "Env Project"
repository:
  url: "${TEST_REPO_URL}"
  clone_path: "./repos/env"
""")

            try:
                ConfigurationManager.reset_instance()
                manager = ConfigurationManager.get_instance(
                    global_config_path=global_temp,
                    projects_dir=projects_temp,
                )

                # Verify environment variables were substituted
                global_config = manager.get_global_config()
                assert global_config.database.url == "postgresql://testhost:5432/testdb"

                project = manager.get_project_config("env-project")
                assert project.repository.url == "https://github.com/prod/repo.git"
            finally:
                Path(global_temp).unlink()

    def test_manager_handles_file_not_found(self) -> None:
        """Test that manager propagates FileNotFoundError for missing files."""
        ConfigurationManager.reset_instance()
        manager = ConfigurationManager.get_instance(
            global_config_path="/nonexistent/config.yaml"
        )

        # Should raise FileNotFoundError when trying to load
        with pytest.raises(FileNotFoundError):
            manager.get_global_config()

    def test_manager_handles_invalid_yaml(self) -> None:
        """Test that manager propagates errors for invalid YAML."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("invalid: yaml: content: [[[")
            temp_file = f.name

        try:
            ConfigurationManager.reset_instance()
            manager = ConfigurationManager.get_instance(
                global_config_path=temp_file
            )

            # Should raise ValueError for invalid YAML
            with pytest.raises(ValueError, match="Failed to parse YAML file"):
                manager.get_global_config()
        finally:
            Path(temp_file).unlink()

    def test_manager_handles_validation_errors(self) -> None:
        """Test that manager propagates validation errors."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
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
            ConfigurationManager.reset_instance()
            manager = ConfigurationManager.get_instance(
                global_config_path=temp_file
            )

            # Should raise ValueError for validation failure
            with pytest.raises(ValueError, match="Configuration validation failed"):
                manager.get_global_config()
        finally:
            Path(temp_file).unlink()

    def test_manager_initialization_parameters(self) -> None:
        """Test that manager stores initialization parameters."""
        ConfigurationManager.reset_instance()
        manager = ConfigurationManager.get_instance(
            global_config_path="config/custom.yaml",
            projects_dir="config/custom_projects",
        )

        # Verify parameters are stored
        assert manager._global_config_path == "config/custom.yaml"
        assert manager._projects_dir == "config/custom_projects"

    def test_manager_multiple_operations_sequence(self) -> None:
        """Test multiple manager operations in sequence."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as global_file:
            global_file.write("""
app:
  name: "Sequence Test App"

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
            global_temp = global_file.name

        with tempfile.TemporaryDirectory() as projects_temp:
            project1 = Path(projects_temp) / "proj1.yaml"
            project1.write_text("""
name: "project-one"
display_name: "Project One"
repository:
  url: "https://github.com/test/proj1.git"
  clone_path: "./repos/proj1"
""")

            project2 = Path(projects_temp) / "proj2.yaml"
            project2.write_text("""
name: "project-two"
display_name: "Project Two"
repository:
  url: "https://github.com/test/proj2.git"
  clone_path: "./repos/proj2"
""")

            try:
                ConfigurationManager.reset_instance()
                manager = ConfigurationManager.get_instance(
                    global_config_path=global_temp,
                    projects_dir=projects_temp,
                )

                # Perform multiple operations
                global_config = manager.get_global_config()
                assert global_config.app.name == "Sequence Test App"

                all_projects = manager.get_all_projects()
                assert len(all_projects) == 2

                project_one = manager.get_project_config("project-one")
                assert project_one.display_name == "Project One"

                project_two = manager.get_project_config("project-two")
                assert project_two.display_name == "Project Two"

                # Reload and access again
                manager.reload()

                global_config2 = manager.get_global_config()
                assert global_config2.app.name == "Sequence Test App"

                all_projects2 = manager.get_all_projects()
                assert len(all_projects2) == 2
            finally:
                Path(global_temp).unlink()
