"""Dependency injection container configuration."""

from __future__ import annotations

from pathlib import Path

from dependency_injector import containers, providers

from youtube_archiver.domain.services.archiving_service import ArchivingService
from youtube_archiver.domain.services.configuration_provider import ConfigurationProvider
from youtube_archiver.domain.services.video_repository import VideoRepository
from youtube_archiver.domain.services.visibility_manager import VisibilityManager
from youtube_archiver.infrastructure.config.yaml_provider import YamlConfigurationProvider
from youtube_archiver.infrastructure.youtube.auth_manager import YouTubeAuthManager
from youtube_archiver.infrastructure.youtube.video_repository import YouTubeVideoRepository
from youtube_archiver.infrastructure.youtube.visibility_manager import YouTubeVisibilityManager
from youtube_archiver.application.services.archiving_service import DefaultArchivingService


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

    # Note: Services are created lazily in the getter functions
    # to avoid dependency injection complexity with method calls


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
    auth_manager = get_youtube_auth_manager(container)
    return YouTubeVideoRepository(auth_manager)


def get_visibility_manager(container: Container) -> VisibilityManager:
    """Get the visibility manager service."""
    auth_manager = get_youtube_auth_manager(container)
    return YouTubeVisibilityManager(auth_manager)


def get_youtube_auth_manager(container: Container) -> YouTubeAuthManager:
    """Get the YouTube authentication manager."""
    config_provider = get_configuration_provider(container)
    return YouTubeAuthManager(
        credentials_file=config_provider.get_credentials_file(),
        token_file=config_provider.get_token_file(),
        scopes=config_provider.get_oauth_scopes(),
    )


def get_archiving_service(container: Container) -> ArchivingService:
    """Get the main archiving service."""
    config_provider = get_configuration_provider(container)
    video_repository = get_video_repository(container)
    visibility_manager = get_visibility_manager(container)
    
    return DefaultArchivingService(
        video_repository=video_repository,
        visibility_manager=visibility_manager,
        config_provider=config_provider,
    )
