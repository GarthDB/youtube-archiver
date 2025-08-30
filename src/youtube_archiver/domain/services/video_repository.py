"""Abstract base class for video repository operations."""

from abc import ABC, abstractmethod
from typing import Optional

from youtube_archiver.domain.models.channel import Channel
from youtube_archiver.domain.models.video import Video


class VideoRepository(ABC):
    """
    Abstract repository for video data operations.

    This interface defines the contract for retrieving video information
    from external sources (like YouTube API). Implementations should handle
    API calls, pagination, error handling, and data mapping.
    """

    @abstractmethod
    async def get_channel_videos(
        self, channel: Channel, max_results: Optional[int] = None
    ) -> list[Video]:
        """
        Retrieve videos from a specific channel.

        Args:
            channel: The channel to retrieve videos from
            max_results: Maximum number of videos to retrieve (None for all)

        Returns:
            List of videos from the channel, ordered by publish date (newest first)

        Raises:
            ChannelNotFoundError: If the channel doesn't exist or isn't accessible
            APIError: If the API call fails
            AuthenticationError: If authentication is invalid
        """
        pass

    @abstractmethod
    async def get_video_details(self, video_id: str) -> Optional[Video]:
        """
        Retrieve detailed information about a specific video.

        Args:
            video_id: YouTube video ID

        Returns:
            Video details if found, None if not found or not accessible

        Raises:
            APIError: If the API call fails
            AuthenticationError: If authentication is invalid
        """
        pass

    @abstractmethod
    async def get_live_videos(
        self, channel: Channel, max_results: Optional[int] = None
    ) -> list[Video]:
        """
        Retrieve only live/streamed videos from a channel.

        This is an optimization for the common use case of finding
        sacrament meeting recordings, which are typically live streams.

        Args:
            channel: The channel to search
            max_results: Maximum number of videos to retrieve

        Returns:
            List of live videos from the channel

        Raises:
            ChannelNotFoundError: If the channel doesn't exist or isn't accessible
            APIError: If the API call fails
            AuthenticationError: If authentication is invalid
        """
        pass

    @abstractmethod
    async def search_videos(
        self, channel: Channel, query: str, max_results: Optional[int] = None
    ) -> list[Video]:
        """
        Search for videos in a channel matching a query.

        This can be used to find videos with specific titles or descriptions,
        such as "sacrament meeting" or specific dates.

        Args:
            channel: The channel to search in
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            List of matching videos

        Raises:
            ChannelNotFoundError: If the channel doesn't exist or isn't accessible
            APIError: If the API call fails
            AuthenticationError: If authentication is invalid
        """
        pass
