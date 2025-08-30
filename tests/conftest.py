"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
import yaml

from youtube_archiver.domain.models.channel import Channel, ChannelConfig
from youtube_archiver.domain.models.processing import (
    BatchProcessingResult,
    ChannelProcessingResult,
    ProcessingResult,
)
from youtube_archiver.domain.models.video import Video, VideoStatus, VideoVisibility
from youtube_archiver.infrastructure.config.models import (
    AppConfig,
    LoggingConfig,
    ProcessingSettings,
    RetrySettings,
    StakeInfo,
    YouTubeAPIConfig,
)


@pytest.fixture
def sample_config_data() -> dict[str, Any]:
    """Sample configuration data for testing."""
    return {
        "stake_info": {
            "name": "Test Stake",
            "tech_specialist": "test@example.com",
            "region": "Test Region",
            "notes": "Test configuration",
        },
        "channels": [
            {
                "name": "Test Ward 1",
                "channel_id": "UCTestChannelID000000001",
                "timezone": "America/Denver",
                "enabled": True,
                "max_videos_to_check": 50,
            },
            {
                "name": "Test Ward 2",
                "channel_id": "UCTestChannelID000000002",
                "timezone": "America/Denver",
                "enabled": True,
                "max_videos_to_check": 50,
            },
            {
                "name": "Test Ward 3",
                "channel_id": "UCTestChannelID000000003",
                "timezone": "America/Denver",
                "enabled": False,
                "max_videos_to_check": 50,
            },
        ],
        "processing": {
            "age_threshold_hours": 24,
            "target_visibility": "unlisted",
            "max_videos_per_channel": 100,
            "dry_run": False,
            "batch_size": 10,
            "initial_backlog_mode": False,
        },
        "youtube_api": {
            "credentials_file": "test_credentials.json",
            "token_file": "test_token.json",
            "scopes": ["https://www.googleapis.com/auth/youtube"],
        },
        "retry_settings": {
            "max_attempts": 3,
            "backoff_factor": 2.0,
            "max_delay": 300,
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file_path": None,
            "max_file_size": 10485760,
            "backup_count": 5,
        },
    }


@pytest.fixture
def temp_config_file(sample_config_data: dict[str, Any]) -> Path:
    """Create a temporary configuration file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(sample_config_data, f)
        return Path(f.name)


@pytest.fixture
def app_config(sample_config_data: dict[str, Any]) -> AppConfig:
    """Create an AppConfig instance for testing."""
    return AppConfig(**sample_config_data)


@pytest.fixture
def sample_channel() -> Channel:
    """Create a sample channel for testing."""
    return Channel(
        id="UCTestChannelID000000001",
        name="Test Ward 1",
    )


@pytest.fixture
def sample_channel_config() -> ChannelConfig:
    """Create a sample channel config for testing."""
    return ChannelConfig(
        name="Test Ward 1",
                    channel_id="UCTestChannelID000000001",
        timezone="America/Denver",
        enabled=True,
        max_videos_to_check=50,
    )


@pytest.fixture
def sample_video_old() -> Video:
    """Create a sample old video (eligible for archiving)."""
    return Video(
        id="test_video_old_123",
        title="Old Sacrament Meeting - Test Ward",
        description="Test description",
        published_at=datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        - timedelta(days=2),  # 2 days old
        visibility=VideoVisibility.PUBLIC,
        duration_seconds=3600,
        view_count=50,
        is_live_content=True,
                    channel_id="UCTestChannelID000000001",

    )


@pytest.fixture
def sample_video_new() -> Video:
    """Create a sample new video (not eligible for archiving)."""
    return Video(
        id="test_video_new_456",
        title="Recent Sacrament Meeting - Test Ward",
        description="Test description",
        published_at=datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        - timedelta(hours=12),  # 12 hours old
        visibility=VideoVisibility.PUBLIC,
        duration_seconds=3600,
        view_count=25,
        is_live_content=True,
                    channel_id="UCTestChannelID000000001",

    )


@pytest.fixture
def sample_video_unlisted() -> Video:
    """Create a sample unlisted video (not eligible for archiving)."""
    return Video(
        id="test_video_unlisted_789",
        title="Already Unlisted Meeting - Test Ward",
        description="Test description",
        published_at=datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        - timedelta(days=3),  # 3 days old
        visibility=VideoVisibility.UNLISTED,
        duration_seconds=3600,
        view_count=75,
        is_live_content=True,
                    channel_id="UCTestChannelID000000001",

    )


@pytest.fixture
def sample_processing_result_success(sample_video_old: Video) -> ProcessingResult:
    """Create a successful processing result."""
    return ProcessingResult(
        video=sample_video_old,
        status=VideoStatus.PROCESSED,
    )


@pytest.fixture
def sample_processing_result_failed(sample_video_old: Video) -> ProcessingResult:
    """Create a failed processing result."""
    return ProcessingResult(
        video=sample_video_old,
        status=VideoStatus.FAILED,
        error_message="API rate limit exceeded",
    )


@pytest.fixture
def sample_channel_result(
    sample_processing_result_success: ProcessingResult,
    sample_processing_result_failed: ProcessingResult,
) -> ChannelProcessingResult:
    """Create a sample channel processing result."""
    result = ChannelProcessingResult(
                    channel_id="UCTestChannelID000000001",
        channel_name="Test Ward 1",
    )
    result.add_result(sample_processing_result_success)
    result.add_result(sample_processing_result_failed)
    return result


@pytest.fixture
def sample_batch_result(sample_channel_result: ChannelProcessingResult) -> BatchProcessingResult:
    """Create a sample batch processing result."""
    result = BatchProcessingResult()
    result.add_channel_result(sample_channel_result)
    result.complete()
    return result


@pytest.fixture
def mock_auth_manager() -> Mock:
    """Create a mock authentication manager."""
    mock = Mock()
    mock.is_authenticated = True
    mock.get_user_info.return_value = {
        "authenticated": True,
        "has_channel": True,
        "channel_title": "Test Channel",
        "channel_id": "UCTestChannelID00000001",
        "subscriber_count": "100",
        "video_count": "50",
    }
    mock.test_api_access.return_value = True
    return mock


@pytest.fixture
def mock_video_repository() -> AsyncMock:
    """Create a mock video repository."""
    mock = AsyncMock()
    mock.get_channel_videos.return_value = []
    mock.get_video_details.return_value = None
    mock.get_live_videos.return_value = []
    mock.search_videos.return_value = []
    return mock


@pytest.fixture
def mock_visibility_manager() -> AsyncMock:
    """Create a mock visibility manager."""
    mock = AsyncMock()
    mock.change_visibility.return_value = ProcessingResult(
        video=Mock(),
        status=VideoStatus.PROCESSED,
    )
    mock.change_visibility_batch.return_value = []
    mock.get_current_visibility.return_value = VideoVisibility.PUBLIC
    mock.can_modify_video.return_value = True
    return mock


@pytest.fixture
def mock_config_provider(app_config: AppConfig) -> Mock:
    """Create a mock configuration provider."""
    mock = Mock()
    mock.get_channels.return_value = app_config.channels
    mock.get_age_threshold_hours.return_value = app_config.processing.age_threshold_hours
    mock.get_target_visibility.return_value = app_config.processing.target_visibility
    mock.get_max_videos_per_channel.return_value = app_config.processing.max_videos_per_channel
    mock.get_dry_run_mode.return_value = app_config.processing.dry_run
    mock.get_credentials_file.return_value = app_config.youtube_api.credentials_file
    mock.get_token_file.return_value = app_config.youtube_api.token_file
    mock.get_oauth_scopes.return_value = app_config.youtube_api.scopes
    mock.get_retry_settings.return_value = app_config.retry_settings
    mock.get_logging_config.return_value = app_config.logging
    return mock


# Async test utilities
@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Test data cleanup
@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Clean up temporary files after each test."""
    yield
    # Cleanup happens automatically with tempfile.NamedTemporaryFile(delete=False)
    # but we could add explicit cleanup here if needed
