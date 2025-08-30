"""Abstract base class for video visibility management operations."""

from abc import ABC, abstractmethod

from youtube_archiver.domain.models.processing import ProcessingResult
from youtube_archiver.domain.models.video import Video, VideoVisibility


class VisibilityManager(ABC):
    """
    Abstract service for managing video visibility.

    This interface defines the contract for changing video visibility
    settings on external platforms (like YouTube). Implementations should
    handle API authentication, error handling, and rate limiting.
    """

    @abstractmethod
    async def change_visibility(
        self, video: Video, new_visibility: VideoVisibility
    ) -> ProcessingResult:
        """
        Change the visibility of a single video.

        Args:
            video: The video to update
            new_visibility: The new visibility setting

        Returns:
            ProcessingResult indicating success or failure

        Raises:
            VideoNotFoundError: If the video doesn't exist or isn't accessible
            InsufficientPermissionsError: If lacking permissions to modify the video
            APIError: If the API call fails
            AuthenticationError: If authentication is invalid
        """
        pass

    @abstractmethod
    async def change_visibility_batch(
        self, videos: list[Video], new_visibility: VideoVisibility
    ) -> list[ProcessingResult]:
        """
        Change the visibility of multiple videos in a batch operation.

        This method should handle batch processing efficiently, including
        proper error handling for individual failures and rate limiting.

        Args:
            videos: List of videos to update
            new_visibility: The new visibility setting for all videos

        Returns:
            List of ProcessingResults, one for each video

        Note:
            Individual video failures should not stop processing of other videos.
            Each video should have its own ProcessingResult indicating success/failure.
        """
        pass

    @abstractmethod
    async def get_current_visibility(self, video_id: str) -> VideoVisibility:
        """
        Get the current visibility setting of a video.

        This can be used to verify changes or check current state
        before making modifications.

        Args:
            video_id: YouTube video ID

        Returns:
            Current visibility setting

        Raises:
            VideoNotFoundError: If the video doesn't exist or isn't accessible
            APIError: If the API call fails
            AuthenticationError: If authentication is invalid
        """
        pass

    @abstractmethod
    async def can_modify_video(self, video_id: str) -> bool:
        """
        Check if the current user has permissions to modify a video.

        This can be used for validation before attempting changes
        to provide better error messages and avoid unnecessary API calls.

        Args:
            video_id: YouTube video ID

        Returns:
            True if the video can be modified, False otherwise

        Raises:
            APIError: If the API call fails
            AuthenticationError: If authentication is invalid
        """
        pass
