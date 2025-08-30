"""Domain-specific exceptions for the YouTube Archiver application."""

from typing import Optional


class YouTubeArchiverError(Exception):
    """Base exception for all YouTube Archiver errors."""

    def __init__(self, message: str, cause: Optional[Exception] = None) -> None:
        super().__init__(message)
        self.message = message
        self.cause = cause


class ConfigurationError(YouTubeArchiverError):
    """Raised when there are configuration-related errors."""

    pass


class AuthenticationError(YouTubeArchiverError):
    """Raised when YouTube API authentication fails."""

    pass


class APIError(YouTubeArchiverError):
    """Raised when YouTube API calls fail."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message, cause)
        self.status_code = status_code


class RateLimitError(APIError):
    """Raised when YouTube API rate limits are exceeded."""

    def __init__(
        self,
        message: str = "YouTube API rate limit exceeded",
        retry_after: Optional[int] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message, 429, cause)
        self.retry_after = retry_after


class VideoNotFoundError(YouTubeArchiverError):
    """Raised when a video cannot be found or accessed."""

    def __init__(self, video_id: str, cause: Optional[Exception] = None) -> None:
        message = f"Video not found or not accessible: {video_id}"
        super().__init__(message, cause)
        self.video_id = video_id


class ChannelNotFoundError(YouTubeArchiverError):
    """Raised when a channel cannot be found or accessed."""

    def __init__(self, channel_id: str, cause: Optional[Exception] = None) -> None:
        message = f"Channel not found or not accessible: {channel_id}"
        super().__init__(message, cause)
        self.channel_id = channel_id


class InsufficientPermissionsError(YouTubeArchiverError):
    """Raised when the user lacks permissions to perform an operation."""

    def __init__(
        self, operation: str, resource_id: str, cause: Optional[Exception] = None
    ) -> None:
        message = f"Insufficient permissions to {operation} on resource: {resource_id}"
        super().__init__(message, cause)
        self.operation = operation
        self.resource_id = resource_id


class ValidationError(YouTubeArchiverError):
    """Raised when data validation fails."""

    def __init__(self, field: str, value: str, reason: str) -> None:
        message = f"Validation failed for {field}='{value}': {reason}"
        super().__init__(message)
        self.field = field
        self.value = value
        self.reason = reason


class ProcessingError(YouTubeArchiverError):
    """Raised when video processing fails."""

    def __init__(
        self, video_id: str, operation: str, cause: Optional[Exception] = None
    ) -> None:
        message = f"Failed to {operation} video: {video_id}"
        super().__init__(message, cause)
        self.video_id = video_id
        self.operation = operation
