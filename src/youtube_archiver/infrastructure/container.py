"""Dependency injection container configuration."""

from __future__ import annotations

from pathlib import Path

from dependency_injector import containers, providers

from youtube_archiver.domain.services.archiving_service import ArchivingService
from youtube_archiver.domain.services.configuration_provider import ConfigurationProvider
from youtube_archiver.domain.services.video_repository import VideoRepository
from youtube_archiver.domain.services.visibility_manager import VisibilityManager
from youtube_archiver.infrastructure.config.yaml_provider import YamlConfigurationProvider


class Container(containers.DeclarativeContainer):
    """
    Dependency injection container for the YouTube Archiver application.
    
    This container manages all application dependencies and their lifecycles,
    providing a clean separation between interface definitions and concrete
    implementations.
    """

    # Configuration
    config_file_path = providers.Configuration()

    # Configuration Provider
    configuration_provider = providers.Singleton(
        YamlConfigurationProvider,
        config_path=config_file_path,
    )

    # Core Services (will be implemented later)
    # These are placeholders for the concrete implementations
    
    # video_repository = providers.Singleton(
    #     YouTubeVideoRepository,
    #     config_provider=configuration_provider,
    # )
    
    # visibility_manager = providers.Singleton(
    #     YouTubeVisibilityManager,
    #     config_provider=configuration_provider,
    # )
    
    # archiving_service = providers.Singleton(
    #     DefaultArchivingService,
    #     video_repository=video_repository,
    #     visibility_manager=visibility_manager,
    #     config_provider=configuration_provider,
    # )


def create_container(config_path: str | Path) -> Container:
    """
    Create and configure the dependency injection container.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Configured container instance
    """
    container = Container()
    container.config_file_path.override(str(config_path))
    return container


def get_configuration_provider(container: Container) -> ConfigurationProvider:
    """
    Get the configuration provider from the container.
    
    Args:
        container: The dependency injection container
        
    Returns:
        Configuration provider instance
    """
    return container.configuration_provider()


# Convenience functions for getting services (will be expanded as we add implementations)

def get_video_repository(container: Container) -> VideoRepository:
    """Get the video repository service."""
    # return container.video_repository()
    raise NotImplementedError("Video repository implementation not yet available")


def get_visibility_manager(container: Container) -> VisibilityManager:
    """Get the visibility manager service."""
    # return container.visibility_manager()
    raise NotImplementedError("Visibility manager implementation not yet available")


def get_archiving_service(container: Container) -> ArchivingService:
    """Get the main archiving service."""
    # return container.archiving_service()
    raise NotImplementedError("Archiving service implementation not yet available")
