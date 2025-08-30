"""Pydantic configuration models for application settings."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, validator

from youtube_archiver.domain.models.channel import ChannelConfig


class RetrySettings(BaseModel):
    """Configuration for API retry behavior."""

    max_attempts: int = Field(default=3, ge=1, le=10, description="Maximum retry attempts")
    backoff_factor: float = Field(default=2.0, ge=1.0, le=10.0, description="Exponential backoff factor")
    max_delay: int = Field(default=300, ge=1, description="Maximum delay between retries in seconds")
    
    class Config:
        """Pydantic configuration."""
        extra = "forbid"


class LoggingConfig(BaseModel):
    """Configuration for application logging."""

    level: str = Field(default="INFO", description="Log level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    file_path: str | None = Field(default=None, description="Log file path (None for console only)")
    max_file_size: int = Field(default=10485760, ge=1024, description="Max log file size in bytes (10MB)")
    backup_count: int = Field(default=5, ge=1, description="Number of backup log files to keep")
    
    @validator("level")
    def validate_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()
    
    class Config:
        """Pydantic configuration."""
        extra = "forbid"


class ProcessingSettings(BaseModel):
    """Configuration for video processing behavior."""

    age_threshold_hours: int = Field(default=24, ge=1, le=168, description="Age threshold in hours")
    target_visibility: str = Field(default="unlisted", description="Target visibility for processed videos")
    max_videos_per_channel: int = Field(default=50, ge=1, le=200, description="Max videos to check per channel")
    dry_run: bool = Field(default=False, description="Run in dry-run mode (no actual changes)")
    
    @validator("target_visibility")
    def validate_target_visibility(cls, v: str) -> str:
        """Validate target visibility setting."""
        valid_visibility = {"unlisted", "private"}
        if v.lower() not in valid_visibility:
            raise ValueError(f"Invalid target visibility: {v}. Must be one of {valid_visibility}")
        return v.lower()
    
    class Config:
        """Pydantic configuration."""
        extra = "forbid"


class StakeInfo(BaseModel):
    """Information about the stake and tech specialist."""

    name: str = Field(..., min_length=1, description="Stake name")
    tech_specialist: str = Field(..., min_length=1, description="Tech specialist name or email")
    region: str | None = Field(default=None, description="Geographic region")
    notes: str | None = Field(default=None, description="Additional notes")
    
    class Config:
        """Pydantic configuration."""
        extra = "forbid"


class YouTubeAPIConfig(BaseModel):
    """Configuration for YouTube API access."""

    credentials_file: str | None = Field(default=None, description="Path to OAuth2 credentials file")
    token_file: str | None = Field(default=None, description="Path to stored access token")
    scopes: list[str] = Field(
        default=["https://www.googleapis.com/auth/youtube"],
        description="OAuth2 scopes required"
    )
    
    @validator("scopes")
    def validate_scopes(cls, v: list[str]) -> list[str]:
        """Validate YouTube API scopes."""
        required_scope = "https://www.googleapis.com/auth/youtube"
        if required_scope not in v:
            raise ValueError(f"Required scope {required_scope} must be included")
        return v
    
    class Config:
        """Pydantic configuration."""
        extra = "forbid"


class AppConfig(BaseModel):
    """
    Main application configuration model.
    
    This is the root configuration object that contains all application settings,
    validated using Pydantic for type safety and runtime validation.
    """

    # Core settings
    stake_info: StakeInfo
    channels: list[ChannelConfig] = Field(..., description="List of channels to process", min_length=1)
    
    # Processing configuration
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)
    
    # API configuration
    youtube_api: YouTubeAPIConfig = Field(default_factory=YouTubeAPIConfig)
    
    # Infrastructure settings
    retry_settings: RetrySettings = Field(default_factory=RetrySettings)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    @validator("channels")
    def validate_channels(cls, v: list[ChannelConfig]) -> list[ChannelConfig]:
        """Validate channel configurations."""
        if not v:
            raise ValueError("At least one channel must be configured")
        
        # Check for duplicate channel IDs
        channel_ids = [channel.channel_id for channel in v]
        if len(channel_ids) != len(set(channel_ids)):
            raise ValueError("Duplicate channel IDs found in configuration")
        
        return v
    
    def get_enabled_channels(self) -> list[ChannelConfig]:
        """Get only the enabled channels."""
        return [channel for channel in self.channels if channel.enabled]
    
    def get_channel_by_id(self, channel_id: str) -> ChannelConfig | None:
        """Get a channel configuration by ID."""
        for channel in self.channels:
            if channel.channel_id == channel_id:
                return channel
        return None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return self.dict()
    
    class Config:
        """Pydantic configuration."""
        extra = "forbid"
        validate_assignment = True
        use_enum_values = True
