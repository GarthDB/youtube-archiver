"""Channel domain model and configuration."""

from __future__ import annotations

from dataclasses import dataclass
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, validator


@dataclass(frozen=True)
class Channel:
    """
    Represents a YouTube channel.

    This is an immutable domain entity representing a ward's YouTube channel.
    """

    id: str
    name: str
    title: str | None = None
    description: str | None = None
    subscriber_count: int | None = None
    video_count: int | None = None

    def __post_init__(self) -> None:
        """Validate channel data after initialization."""
        if not self.id:
            raise ValueError("Channel ID cannot be empty")
        if not self.name:
            raise ValueError("Channel name cannot be empty")
        if not self.id.startswith(("UC", "UU", "UL")):
            raise ValueError(f"Invalid YouTube channel ID format: {self.id}")

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"Channel(name='{self.name}', id={self.id})"

    def __repr__(self) -> str:
        """Developer-friendly string representation."""
        return (
            f"Channel(id='{self.id}', name='{self.name}', "
            f"title='{self.title}', video_count={self.video_count})"
        )


class ChannelConfig(BaseModel):
    """
    Configuration for a YouTube channel with validation.

    This Pydantic model provides runtime validation and type coercion
    for channel configuration loaded from YAML/JSON files.
    """

    name: str = Field(..., min_length=1, description="Human-readable name for the ward")
    channel_id: str = Field(..., min_length=1, description="YouTube channel ID")
    timezone: str = Field(
        default="America/Denver", description="Timezone for the ward location"
    )
    enabled: bool = Field(default=True, description="Whether to process this channel")
    max_videos_to_check: int = Field(
        default=50, ge=1, le=200, description="Maximum videos to check per run"
    )

    @validator("channel_id")
    def validate_channel_id(cls, v: str) -> str:
        """Validate YouTube channel ID format."""
        if not v.startswith(("UC", "UU", "UL")):
            raise ValueError(f"Invalid YouTube channel ID format: {v}")
        if len(v) != 24:
            raise ValueError(f"YouTube channel ID must be 24 characters long: {v}")
        return v

    @validator("timezone")
    def validate_timezone(cls, v: str) -> str:
        """Validate timezone string."""
        try:
            ZoneInfo(v)
        except Exception as e:
            raise ValueError(f"Invalid timezone: {v}") from e
        return v

    def to_domain(self) -> Channel:
        """Convert to domain Channel entity."""
        return Channel(
            id=self.channel_id,
            name=self.name,
        )

    class Config:
        """Pydantic configuration."""

        extra = "forbid"  # Don't allow extra fields
        validate_assignment = True  # Validate on assignment
        use_enum_values = True
