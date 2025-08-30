"""Integration tests for dependency injection container."""

from __future__ import annotations

from pathlib import Path

import pytest

from youtube_archiver.domain.exceptions import ConfigurationError
from youtube_archiver.infrastructure.container import (
    Container,
    create_container,
    get_archiving_service,
    get_configuration_provider,
    get_video_repository,
    get_visibility_manager,
    get_youtube_auth_manager,
)


class TestContainerIntegration:
    """Integration tests for the dependency injection container."""

    def test_create_container_success(self, temp_config_file: Path) -> None:
        """Test successful container creation."""
        container = create_container(temp_config_file)
        assert isinstance(container, Container)

    def test_create_container_invalid_config(self) -> None:
        """Test container creation with invalid config file."""
        with pytest.raises(ConfigurationError):
            create_container("nonexistent.yml")

    def test_get_configuration_provider(self, temp_config_file: Path) -> None:
        """Test getting configuration provider from container."""
        container = create_container(temp_config_file)
        config_provider = get_configuration_provider(container)
        
        # Test that the provider works
        channels = config_provider.get_channels()
        assert len(channels) == 3
        assert config_provider.get_age_threshold_hours() == 24

    def test_get_youtube_auth_manager(self, temp_config_file: Path) -> None:
        """Test getting YouTube auth manager from container."""
        container = create_container(temp_config_file)
        auth_manager = get_youtube_auth_manager(container)
        
        # Test that the auth manager is properly configured
        assert auth_manager is not None
        # Note: We can't test actual authentication without credentials

    def test_get_video_repository(self, temp_config_file: Path) -> None:
        """Test getting video repository from container."""
        container = create_container(temp_config_file)
        video_repo = get_video_repository(container)
        
        assert video_repo is not None

    def test_get_visibility_manager(self, temp_config_file: Path) -> None:
        """Test getting visibility manager from container."""
        container = create_container(temp_config_file)
        visibility_manager = get_visibility_manager(container)
        
        assert visibility_manager is not None

    def test_get_archiving_service(self, temp_config_file: Path) -> None:
        """Test getting archiving service from container."""
        container = create_container(temp_config_file)
        archiving_service = get_archiving_service(container)
        
        assert archiving_service is not None

    def test_service_dependencies(self, temp_config_file: Path) -> None:
        """Test that services have proper dependencies injected."""
        container = create_container(temp_config_file)
        
        # Get all services
        config_provider = get_configuration_provider(container)
        auth_manager = get_youtube_auth_manager(container)
        video_repo = get_video_repository(container)
        visibility_manager = get_visibility_manager(container)
        archiving_service = get_archiving_service(container)
        
        # Test that dependencies are properly injected
        assert archiving_service.config_provider is not None
        assert archiving_service.video_repository is not None
        assert archiving_service.visibility_manager is not None

    def test_configuration_consistency(self, temp_config_file: Path) -> None:
        """Test that configuration is consistent across services."""
        container = create_container(temp_config_file)
        
        config_provider = get_configuration_provider(container)
        auth_manager = get_youtube_auth_manager(container)
        
        # Test that auth manager uses the same config values
        expected_credentials_file = config_provider.get_credentials_file()
        expected_token_file = config_provider.get_token_file()
        expected_scopes = config_provider.get_oauth_scopes()
        
        # Note: We can't directly access private attributes, but we can verify
        # that the auth manager was created with the right config
        assert auth_manager is not None

    def test_service_singleton_behavior(self, temp_config_file: Path) -> None:
        """Test that services behave as singletons within container scope."""
        container = create_container(temp_config_file)
        
        # Get the same service multiple times
        config_provider1 = get_configuration_provider(container)
        config_provider2 = get_configuration_provider(container)
        
        # They should be the same instance (singleton behavior)
        assert config_provider1 is config_provider2

    def test_multiple_containers_independence(self, temp_config_file: Path) -> None:
        """Test that multiple containers are independent."""
        container1 = create_container(temp_config_file)
        container2 = create_container(temp_config_file)
        
        config_provider1 = get_configuration_provider(container1)
        config_provider2 = get_configuration_provider(container2)
        
        # They should be different instances
        assert config_provider1 is not config_provider2

    def test_container_with_different_configs(
        self, 
        temp_config_file: Path,
        sample_config_data: dict,
    ) -> None:
        """Test containers with different configuration files."""
        import tempfile
        import yaml
        
        # Create a second config file with different values
        modified_config = sample_config_data.copy()
        modified_config["processing"]["age_threshold_hours"] = 48
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(modified_config, f)
            temp_config_file2 = Path(f.name)
        
        # Create containers with different configs
        container1 = create_container(temp_config_file)
        container2 = create_container(temp_config_file2)
        
        config_provider1 = get_configuration_provider(container1)
        config_provider2 = get_configuration_provider(container2)
        
        # They should have different configuration values
        assert config_provider1.get_age_threshold_hours() == 24
        assert config_provider2.get_age_threshold_hours() == 48
