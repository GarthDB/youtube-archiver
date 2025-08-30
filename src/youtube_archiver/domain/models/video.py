"""Video domain model and related enums."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class VideoVisibility(str, Enum):
    """YouTube video visibility options."""

    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"


class VideoStatus(str, Enum):
    """Video processing status."""

    PENDING = "pending"
    PROCESSED = "processed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class Video:
    """
    Represents a YouTube video with metadata relevant to archiving.

    This is an immutable domain entity that encapsulates all the information
    needed to make decisions about video visibility management.
    """

    id: str
    title: str
    channel_id: str
    published_at: datetime
    visibility: VideoVisibility
    is_live_content: bool
    duration_seconds: int | None = None
    view_count: int | None = None
    description: str | None = None
    thumbnail_url: str | None = None

    def __post_init__(self) -> None:
        """Validate video data after initialization."""
        if not self.id:
            raise ValueError("Video ID cannot be empty")
        if not self.title:
            raise ValueError("Video title cannot be empty")
        if not self.channel_id:
            raise ValueError("Channel ID cannot be empty")

    @property
    def age_hours(self) -> float:
        """Calculate the age of the video in hours from now."""
        now = datetime.now(tz=self.published_at.tzinfo)
        delta = now - self.published_at
        return delta.total_seconds() / 3600

    @property
    def is_eligible_for_archiving(self) -> bool:
        """
        Determine if this video is eligible for visibility change.

        A video is eligible if:
        - It's live content (sacrament meetings are typically live streams)
        - It's currently public
        - It's older than 24 hours
        """
        return (
            self.is_live_content
            and self.visibility == VideoVisibility.PUBLIC
            and self.age_hours > 24
        )

    def with_visibility(self, new_visibility: VideoVisibility) -> Video:
        """Create a new Video instance with updated visibility."""
        return Video(
            id=self.id,
            title=self.title,
            channel_id=self.channel_id,
            published_at=self.published_at,
            visibility=new_visibility,
            is_live_content=self.is_live_content,
            duration_seconds=self.duration_seconds,
            view_count=self.view_count,
            description=self.description,
            thumbnail_url=self.thumbnail_url,
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"Video(id={self.id}, title='{self.title[:50]}...', visibility={self.visibility.value})"

    def __repr__(self) -> str:
        """Developer-friendly string representation."""
        return (
            f"Video(id='{self.id}', title='{self.title}', "
            f"channel_id='{self.channel_id}', published_at={self.published_at}, "
            f"visibility={self.visibility}, is_live_content={self.is_live_content})"
        )
