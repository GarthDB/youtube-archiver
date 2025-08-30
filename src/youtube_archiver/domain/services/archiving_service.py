"""Abstract base class for the main archiving service orchestration."""

from abc import ABC, abstractmethod
from typing import Any

from youtube_archiver.domain.models.channel import Channel
from youtube_archiver.domain.models.processing import (
    BatchProcessingResult,
    ChannelProcessingResult,
)


class ArchivingService(ABC):
    """
    Abstract service for orchestrating the video archiving workflow.

    This is the main business logic interface that coordinates between
    the video repository, visibility manager, and configuration provider
    to execute the complete archiving workflow.
    """

    @abstractmethod
    async def process_all_channels(self) -> BatchProcessingResult:
        """
        Process all configured channels in a batch operation.

        This is the main entry point for the archiving workflow. It should:
        1. Load channel configuration
        2. Process each enabled channel
        3. Aggregate results and statistics
        4. Handle global error conditions

        Returns:
            BatchProcessingResult with overall statistics and channel results

        Raises:
            ConfigurationError: If configuration is invalid
            AuthenticationError: If API authentication fails globally
        """
        pass

    @abstractmethod
    async def process_channel(self, channel: Channel) -> ChannelProcessingResult:
        """
        Process a single channel's videos.

        This method should:
        1. Retrieve videos from the channel
        2. Filter for eligible videos (age, visibility, live content)
        3. Change visibility for eligible videos
        4. Track results and errors

        Args:
            channel: The channel to process

        Returns:
            ChannelProcessingResult with statistics and individual video results

        Raises:
            ChannelNotFoundError: If the channel doesn't exist or isn't accessible
            APIError: If API operations fail
        """
        pass

    @abstractmethod
    async def process_specific_channels(
        self, channel_ids: list[str]
    ) -> BatchProcessingResult:
        """
        Process only specific channels by ID.

        This allows selective processing of channels, useful for testing
        or handling specific issues with individual channels.

        Args:
            channel_ids: List of YouTube channel IDs to process

        Returns:
            BatchProcessingResult for the specified channels

        Raises:
            ConfigurationError: If any channel ID is not configured
            ChannelNotFoundError: If any channel doesn't exist
        """
        pass

    @abstractmethod
    async def dry_run_all_channels(self) -> BatchProcessingResult:
        """
        Perform a dry-run of all channels without making changes.

        This method should execute the complete workflow but skip
        the actual visibility changes, useful for testing and validation.

        Returns:
            BatchProcessingResult showing what would be processed
        """
        pass

    @abstractmethod
    async def get_eligible_videos_summary(self) -> dict[str, Any]:
        """
        Get a summary of videos eligible for processing across all channels.

        This provides a preview of what would be processed without
        actually making changes, useful for reporting and validation.

        Returns:
            Dictionary with summary statistics:
            - total_channels: Number of channels checked
            - total_videos: Total videos found
            - eligible_videos: Videos that would be processed
            - by_channel: Per-channel breakdown
        """
        pass

    @abstractmethod
    def validate_configuration(self) -> list[str]:
        """
        Validate the current configuration without processing.

        This checks for common configuration issues like:
        - Invalid channel IDs
        - Missing permissions
        - API connectivity
        - Invalid settings

        Returns:
            List of validation error messages (empty if valid)
        """
        pass
