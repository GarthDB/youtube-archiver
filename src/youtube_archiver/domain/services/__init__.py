"""Abstract base classes for domain services."""

from youtube_archiver.domain.services.archiving_service import ArchivingService
from youtube_archiver.domain.services.configuration_provider import (
    ConfigurationProvider,
)
from youtube_archiver.domain.services.video_repository import VideoRepository
from youtube_archiver.domain.services.visibility_manager import VisibilityManager

__all__ = [
    "VideoRepository",
    "VisibilityManager",
    "ConfigurationProvider",
    "ArchivingService",
]
