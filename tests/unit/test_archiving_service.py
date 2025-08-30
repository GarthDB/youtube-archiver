"""Tests for the ArchivingService."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from youtube_archiver.application.services.archiving_service import DefaultArchivingService
from youtube_archiver.domain.exceptions import (
    APIError,
    AuthenticationError,
    ChannelNotFoundError,
    RateLimitError,
)
from youtube_archiver.domain.models.channel import Channel
from youtube_archiver.domain.models.processing import ProcessingResult
from youtube_archiver.domain.models.video import Video, VideoStatus, VideoVisibility


class TestDefaultArchivingService:
    """Tests for DefaultArchivingService."""

    @pytest.fixture
    def archiving_service(
        self,
        mock_video_repository: AsyncMock,
        mock_visibility_manager: AsyncMock,
        mock_config_provider: Mock,
    ) -> DefaultArchivingService:
        """Create an archiving service instance for testing."""
        return DefaultArchivingService(
            video_repository=mock_video_repository,
            visibility_manager=mock_visibility_manager,
            config_provider=mock_config_provider,
        )

    @pytest.mark.asyncio
    async def test_process_all_channels_success(
        self,
        archiving_service: DefaultArchivingService,
        mock_video_repository: AsyncMock,
        mock_visibility_manager: AsyncMock,
        mock_config_provider: Mock,
        sample_video_old: Video,
    ) -> None:
        """Test successful processing of all channels."""
        # Setup mocks
        mock_video_repository.get_channel_videos.return_value = [sample_video_old]
        mock_visibility_manager.change_visibility_batch.return_value = [
                    ProcessingResult(
            video=sample_video_old,
            status=VideoStatus.PROCESSED,
        )
        ]

        # Execute
        result = await archiving_service.process_all_channels()

        # Verify
        assert result.has_errors is False
        assert result.overall_stats.channels_processed == 2  # 2 enabled channels
        assert result.overall_stats.videos_processed == 2  # 1 video per channel
        assert len(result.channel_results) == 2

    @pytest.mark.asyncio
    async def test_process_all_channels_no_enabled_channels(
        self,
        archiving_service: DefaultArchivingService,
        mock_config_provider: Mock,
    ) -> None:
        """Test processing when no channels are enabled."""
        # Setup mock to return no enabled channels
        mock_config_provider.get_channels.return_value = []

        # Execute
        result = await archiving_service.process_all_channels()

        # Verify
        assert result.has_errors is True
        assert result.global_error == "No enabled channels configured"
        assert result.overall_stats.channels_processed == 0

    @pytest.mark.asyncio
    async def test_process_channel_success(
        self,
        archiving_service: DefaultArchivingService,
        mock_video_repository: AsyncMock,
        mock_visibility_manager: AsyncMock,
        sample_channel: Channel,
        sample_video_old: Video,
    ) -> None:
        """Test successful processing of a single channel."""
        # Setup mocks
        mock_video_repository.get_channel_videos.return_value = [sample_video_old]
        mock_visibility_manager.change_visibility_batch.return_value = [
                    ProcessingResult(
            video=sample_video_old,
            status=VideoStatus.PROCESSED,
        )
        ]

        # Execute
        result = await archiving_service.process_channel(sample_channel)

        # Verify
        assert result.channel_id == sample_channel.id
        assert result.channel_name == sample_channel.name
        assert result.has_errors is False
        assert result.stats.videos_processed == 1

    @pytest.mark.asyncio
    async def test_process_channel_no_videos(
        self,
        archiving_service: DefaultArchivingService,
        mock_video_repository: AsyncMock,
        sample_channel: Channel,
    ) -> None:
        """Test processing a channel with no videos."""
        # Setup mock to return no videos
        mock_video_repository.get_channel_videos.return_value = []

        # Execute
        result = await archiving_service.process_channel(sample_channel)

        # Verify
        assert result.channel_id == sample_channel.id
        assert result.has_errors is False
        assert result.stats.videos_processed == 0
        assert len(result.results) == 0

    @pytest.mark.asyncio
    async def test_process_channel_no_eligible_videos(
        self,
        archiving_service: DefaultArchivingService,
        mock_video_repository: AsyncMock,
        sample_channel: Channel,
        sample_video_new: Video,
    ) -> None:
        """Test processing a channel with no eligible videos."""
        # Setup mock to return only new (ineligible) videos
        mock_video_repository.get_channel_videos.return_value = [sample_video_new]

        # Execute
        result = await archiving_service.process_channel(sample_channel)

        # Verify
        assert result.channel_id == sample_channel.id
        assert result.has_errors is False
        assert result.stats.videos_processed == 0
        assert len(result.results) == 0

    @pytest.mark.asyncio
    async def test_process_channel_dry_run(
        self,
        archiving_service: DefaultArchivingService,
        mock_video_repository: AsyncMock,
        mock_config_provider: Mock,
        sample_channel: Channel,
        sample_video_old: Video,
    ) -> None:
        """Test processing a channel in dry-run mode."""
        # Setup mocks for dry-run mode
        mock_config_provider.get_dry_run_mode.return_value = True
        mock_video_repository.get_channel_videos.return_value = [sample_video_old]

        # Execute
        result = await archiving_service.process_channel(sample_channel)

        # Verify
        assert result.channel_id == sample_channel.id
        assert result.has_errors is False
        assert result.stats.videos_skipped == 1
        assert result.stats.videos_processed == 0
        assert result.results[0].status == VideoStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_process_channel_authentication_error(
        self,
        archiving_service: DefaultArchivingService,
        mock_video_repository: AsyncMock,
        sample_channel: Channel,
    ) -> None:
        """Test processing a channel with authentication error."""
        # Setup mock to raise authentication error
        mock_video_repository.get_channel_videos.side_effect = AuthenticationError(
            "Invalid credentials"
        )

        # Execute
        result = await archiving_service.process_channel(sample_channel)

        # Verify
        assert result.channel_id == sample_channel.id
        assert result.has_errors is True
        assert "Authentication error" in result.error_message

    @pytest.mark.asyncio
    async def test_process_channel_not_found_error(
        self,
        archiving_service: DefaultArchivingService,
        mock_video_repository: AsyncMock,
        sample_channel: Channel,
    ) -> None:
        """Test processing a channel that is not found."""
        # Setup mock to raise channel not found error
        mock_video_repository.get_channel_videos.side_effect = ChannelNotFoundError(
            "Channel not found"
        )

        # Execute
        result = await archiving_service.process_channel(sample_channel)

        # Verify
        assert result.channel_id == sample_channel.id
        assert result.has_errors is True
        assert "Channel not found" in result.error_message

    @pytest.mark.asyncio
    async def test_process_channel_rate_limit_error(
        self,
        archiving_service: DefaultArchivingService,
        mock_video_repository: AsyncMock,
        sample_channel: Channel,
    ) -> None:
        """Test processing a channel with rate limit error."""
        # Setup mock to raise rate limit error
        mock_video_repository.get_channel_videos.side_effect = RateLimitError(
            "Rate limit exceeded"
        )

        # Execute
        result = await archiving_service.process_channel(sample_channel)

        # Verify
        assert result.channel_id == sample_channel.id
        assert result.has_errors is True
        assert "Rate limit exceeded" in result.error_message

    @pytest.mark.asyncio
    async def test_process_channel_api_error(
        self,
        archiving_service: DefaultArchivingService,
        mock_video_repository: AsyncMock,
        sample_channel: Channel,
    ) -> None:
        """Test processing a channel with API error."""
        # Setup mock to raise API error
        mock_video_repository.get_channel_videos.side_effect = APIError("API error")

        # Execute
        result = await archiving_service.process_channel(sample_channel)

        # Verify
        assert result.channel_id == sample_channel.id
        assert result.has_errors is True
        assert "API error" in result.error_message

    @pytest.mark.asyncio
    async def test_process_specific_channels(
        self,
        archiving_service: DefaultArchivingService,
        mock_video_repository: AsyncMock,
        mock_visibility_manager: AsyncMock,
        mock_config_provider: Mock,
        sample_video_old: Video,
    ) -> None:
        """Test processing specific channels by ID."""
        # Setup mocks
        mock_video_repository.get_channel_videos.return_value = [sample_video_old]
        mock_visibility_manager.change_visibility_batch.return_value = [
                    ProcessingResult(
            video=sample_video_old,
            status=VideoStatus.PROCESSED,
        )
        ]

        # Execute - process only the first channel
        channel_ids = ["UCTestChannelID000000001"]
        result = await archiving_service.process_specific_channels(channel_ids)

        # Verify
        assert result.has_errors is False
        assert result.overall_stats.channels_processed == 1
        assert len(result.channel_results) == 1

    @pytest.mark.asyncio
    async def test_process_specific_channels_invalid_id(
        self,
        archiving_service: DefaultArchivingService,
        mock_config_provider: Mock,
    ) -> None:
        """Test processing specific channels with invalid channel ID."""
        # Execute with invalid channel ID
        channel_ids = ["UCInvalidChannelID000123"]
        result = await archiving_service.process_specific_channels(channel_ids)

        # Verify
        assert result.has_errors is True
        assert len(result.channel_results) == 1
        assert result.channel_results["UCInvalidChannelID000123"].error_message == "Channel not found in configuration"

    @pytest.mark.asyncio
    async def test_dry_run_all_channels(
        self,
        archiving_service: DefaultArchivingService,
        mock_video_repository: AsyncMock,
        mock_config_provider: Mock,
        sample_video_old: Video,
    ) -> None:
        """Test dry-run of all channels."""
        # Setup mocks
        mock_video_repository.get_channel_videos.return_value = [sample_video_old]

        # Execute
        result = await archiving_service.dry_run_all_channels()

        # Verify - should process channels but not make actual changes
        assert result.overall_stats.channels_processed == 2  # 2 enabled channels

    @pytest.mark.asyncio
    async def test_get_eligible_videos_summary(
        self,
        archiving_service: DefaultArchivingService,
        mock_video_repository: AsyncMock,
        mock_config_provider: Mock,
        sample_video_old: Video,
        sample_video_new: Video,
    ) -> None:
        """Test getting eligible videos summary."""
        # Setup mocks
        mock_video_repository.get_channel_videos.return_value = [
            sample_video_old,  # Eligible
            sample_video_new,  # Not eligible
        ]

        # Execute
        summary = await archiving_service.get_eligible_videos_summary()

        # Verify
        assert summary["total_channels"] == 3
        assert summary["enabled_channels"] == 2
        assert summary["total_videos"] == 4  # 2 videos × 2 enabled channels
        assert summary["eligible_videos"] == 2  # 1 eligible video × 2 enabled channels
        assert "by_channel" in summary
        assert "generated_at" in summary

    @pytest.mark.asyncio
    async def test_get_eligible_videos_summary_with_errors(
        self,
        archiving_service: DefaultArchivingService,
        mock_video_repository: AsyncMock,
        mock_config_provider: Mock,
    ) -> None:
        """Test getting eligible videos summary with channel errors."""
        # Setup mock to raise error for some channels
        mock_video_repository.get_channel_videos.side_effect = [
            [],  # First channel succeeds
            ChannelNotFoundError("Channel not found"),  # Second channel fails
        ]

        # Execute
        summary = await archiving_service.get_eligible_videos_summary()

        # Verify
        assert summary["total_channels"] == 3
        assert summary["enabled_channels"] == 2
        assert "by_channel" in summary
        
        # Check that error channels are handled
        channel_summaries = summary["by_channel"]
        error_channels = [
            ch for ch in channel_summaries.values() 
            if "error" in ch
        ]
        assert len(error_channels) == 1

    def test_validate_configuration_success(
        self,
        archiving_service: DefaultArchivingService,
        mock_config_provider: Mock,
    ) -> None:
        """Test successful configuration validation."""
        # Execute
        errors = archiving_service.validate_configuration()

        # Verify
        assert len(errors) == 0

    def test_validate_configuration_no_channels(
        self,
        archiving_service: DefaultArchivingService,
        mock_config_provider: Mock,
    ) -> None:
        """Test configuration validation with no channels."""
        # Setup mock to return no channels
        mock_config_provider.get_channels.return_value = []

        # Execute
        errors = archiving_service.validate_configuration()

        # Verify
        assert len(errors) > 0
        assert any("No channels configured" in error for error in errors)

    def test_validate_configuration_no_enabled_channels(
        self,
        archiving_service: DefaultArchivingService,
        mock_config_provider: Mock,
        sample_channel_config: Mock,
    ) -> None:
        """Test configuration validation with no enabled channels."""
        # Setup mock to return only disabled channels
        sample_channel_config.enabled = False
        mock_config_provider.get_channels.return_value = [sample_channel_config]

        # Execute
        errors = archiving_service.validate_configuration()

        # Verify
        assert len(errors) > 0
        assert any("No enabled channels found" in error for error in errors)

    def test_validate_configuration_invalid_age_threshold(
        self,
        archiving_service: DefaultArchivingService,
        mock_config_provider: Mock,
    ) -> None:
        """Test configuration validation with invalid age threshold."""
        # Setup mock to return invalid age threshold
        mock_config_provider.get_age_threshold_hours.return_value = 0

        # Execute
        errors = archiving_service.validate_configuration()

        # Verify
        assert len(errors) > 0
        assert any("Invalid age threshold" in error for error in errors)

    def test_validate_configuration_invalid_target_visibility(
        self,
        archiving_service: DefaultArchivingService,
        mock_config_provider: Mock,
    ) -> None:
        """Test configuration validation with invalid target visibility."""
        # Setup mock to return invalid target visibility
        mock_config_provider.get_target_visibility.return_value = "invalid"

        # Execute
        errors = archiving_service.validate_configuration()

        # Verify
        assert len(errors) > 0
        assert any("Invalid target visibility" in error for error in errors)

    def test_get_batch_size_default(
        self,
        archiving_service: DefaultArchivingService,
    ) -> None:
        """Test getting default batch size."""
        batch_size = archiving_service._get_batch_size()
        assert batch_size == 10

    def test_get_batch_size_from_config(
        self,
        archiving_service: DefaultArchivingService,
        mock_config_provider: Mock,
    ) -> None:
        """Test getting batch size from configuration."""
        # Setup mock config with processing settings
        mock_processing = Mock()
        mock_processing.batch_size = 20
        mock_config = Mock()
        mock_config.processing = mock_processing
        mock_config_provider.config = mock_config

        batch_size = archiving_service._get_batch_size()
        assert batch_size == 20

    @pytest.mark.asyncio
    async def test_check_permissions_batch(
        self,
        archiving_service: DefaultArchivingService,
        mock_visibility_manager: AsyncMock,
        sample_video_old: Video,
        sample_video_new: Video,
    ) -> None:
        """Test batch permission checking."""
        # Setup mock
        mock_visibility_manager.can_modify_video.side_effect = [True, False]

        # Execute
        videos = [sample_video_old, sample_video_new]
        permissions = await archiving_service._check_permissions_batch(videos)

        # Verify
        assert len(permissions) == 2
        assert permissions[sample_video_old.id] is True
        assert permissions[sample_video_new.id] is False
