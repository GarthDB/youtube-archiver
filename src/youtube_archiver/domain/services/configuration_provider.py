"""Abstract base class for configuration management."""

from abc import ABC, abstractmethod
from typing import Any, Optional

from youtube_archiver.domain.models.channel import ChannelConfig


class ConfigurationProvider(ABC):
    """
    Abstract service for providing application configuration.

    This interface defines the contract for loading and validating
    configuration data from various sources (files, environment variables,
    remote configuration services, etc.).
    """

    @abstractmethod
    def get_channels(self) -> list[ChannelConfig]:
        """
        Get the list of configured channels to process.

        Returns:
            List of validated channel configurations

        Raises:
            ConfigurationError: If configuration is invalid or cannot be loaded
        """
        pass

    @abstractmethod
    def get_age_threshold_hours(self) -> int:
        """
        Get the age threshold in hours for video processing.

        Videos older than this threshold are eligible for visibility changes.

        Returns:
            Age threshold in hours (typically 24)

        Raises:
            ConfigurationError: If configuration is invalid
        """
        pass

    @abstractmethod
    def get_target_visibility(self) -> str:
        """
        Get the target visibility setting for processed videos.

        Returns:
            Target visibility ("unlisted", "private", etc.)

        Raises:
            ConfigurationError: If configuration is invalid
        """
        pass

    @abstractmethod
    def get_dry_run_mode(self) -> bool:
        """
        Get whether the application should run in dry-run mode.

        In dry-run mode, no actual changes are made to videos.

        Returns:
            True if in dry-run mode, False for normal operation
        """
        pass

    @abstractmethod
    def get_max_videos_per_channel(self) -> int:
        """
        Get the maximum number of videos to check per channel.

        This helps limit API usage and processing time.

        Returns:
            Maximum number of videos to process per channel

        Raises:
            ConfigurationError: If configuration is invalid
        """
        pass

    @abstractmethod
    def get_stake_info(self) -> Optional[dict[str, Any]]:
        """
        Get stake information for reporting and identification.

        Returns:
            Dictionary containing stake name, tech specialist info, etc.
            None if not configured
        """
        pass

    @abstractmethod
    def is_channel_enabled(self, channel_id: str) -> bool:
        """
        Check if a specific channel is enabled for processing.

        This allows selective enabling/disabling of channels without
        removing them from configuration.

        Args:
            channel_id: YouTube channel ID

        Returns:
            True if the channel should be processed, False otherwise
        """
        pass

    @abstractmethod
    def get_retry_settings(self) -> Any:
        """
        Get retry configuration for API operations.

        Returns:
            Retry settings (RetrySettings model or equivalent dict)
        """
        pass

    @abstractmethod
    def get_logging_config(self) -> Any:
        """
        Get logging configuration.

        Returns:
            Logging settings (LoggingConfig model or equivalent dict)
        """
        pass

    def get_credentials_file(self) -> Optional[str]:
        """Get the path to the OAuth2 credentials file. Returns None if not configured."""
        return None

    def get_token_file(self) -> Optional[str]:
        """Get the path to the stored access token file. Returns None if not configured."""
        return None

    def get_oauth_scopes(self) -> list[str]:
        """Get the required OAuth2 scopes."""
        return ["https://www.googleapis.com/auth/youtube"]

    @abstractmethod
    def reload(self) -> None:
        """
        Reload configuration from source.

        This allows updating configuration without restarting the application.

        Raises:
            ConfigurationError: If configuration cannot be reloaded or is invalid
        """
        pass
