"""Tests for domain models."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

import pytest

from youtube_archiver.domain.models.channel import Channel, ChannelConfig
from youtube_archiver.domain.models.processing import (
    BatchProcessingResult,
    ChannelProcessingResult,
    ProcessingResult,
    ProcessingStats,
)
from youtube_archiver.domain.models.video import Video, VideoStatus, VideoVisibility


class TestVideo:
    """Tests for Video domain model."""

    def test_video_creation(self, sample_video_old: Video) -> None:
        """Test video creation with all fields."""
        assert sample_video_old.id == "test_video_old_123"
        assert sample_video_old.title == "Old Sacrament Meeting - Test Ward"
        assert sample_video_old.visibility == VideoVisibility.PUBLIC
        assert sample_video_old.is_live_content is True
        assert sample_video_old.channel_id == "UCTestChannelID00000001"

    def test_video_age_calculation(self, sample_video_old: Video, sample_video_new: Video) -> None:
        """Test video age calculation."""
        # Old video should be around 48 hours old (2 days)
        assert sample_video_old.age_hours >= 47
        assert sample_video_old.age_hours <= 49

        # New video should be around 12 hours old
        assert sample_video_new.age_hours >= 11
        assert sample_video_new.age_hours <= 13

    def test_video_eligibility_for_archiving(
        self, sample_video_old: Video, sample_video_new: Video, sample_video_unlisted: Video
    ) -> None:
        """Test video eligibility for archiving."""
        # Old public video should be eligible
        assert sample_video_old.is_eligible_for_archiving is True

        # New video should not be eligible (too recent)
        assert sample_video_new.is_eligible_for_archiving is False

        # Already unlisted video should not be eligible
        assert sample_video_unlisted.is_eligible_for_archiving is False

    def test_video_eligibility_non_live_content(self) -> None:
        """Test that non-live content is not eligible for archiving."""
        video = Video(
            id="test_video_non_live",
            title="Non-Live Video",
            description="Test description",
            published_at=datetime.now(timezone.utc) - timedelta(days=5),
            visibility=VideoVisibility.PUBLIC,
            duration_seconds=3600,
            view_count=100,
            is_live_content=False,  # Not live content
            channel_id="UCTestChannelID00000001",
            channel_title="Test Ward 1",
        )
        assert video.is_eligible_for_archiving is False

    def test_video_str_representation(self, sample_video_old: Video) -> None:
        """Test video string representation."""
        str_repr = str(sample_video_old)
        assert "Old Sacrament Meeting - Test Ward" in str_repr
        assert "test_video_old_123" in str_repr


class TestChannel:
    """Tests for Channel domain model."""

    def test_channel_creation(self, sample_channel: Channel) -> None:
        """Test channel creation."""
        assert sample_channel.id == "UCTestChannelID00000001"
        assert sample_channel.name == "Test Ward 1"
        assert sample_channel.timezone == "America/Denver"

    def test_channel_str_representation(self, sample_channel: Channel) -> None:
        """Test channel string representation."""
        str_repr = str(sample_channel)
        assert "Test Ward 1" in str_repr
        assert "UCTestChannelID00000001" in str_repr


class TestChannelConfig:
    """Tests for ChannelConfig model."""

    def test_channel_config_creation(self, sample_channel_config: ChannelConfig) -> None:
        """Test channel config creation."""
        assert sample_channel_config.name == "Test Ward 1"
        assert sample_channel_config.channel_id == "UCTestChannelID00000001"
        assert sample_channel_config.enabled is True
        assert sample_channel_config.max_videos_to_check == 50

    def test_channel_config_to_domain(self, sample_channel_config: ChannelConfig) -> None:
        """Test conversion to domain model."""
        channel = sample_channel_config.to_domain()
        assert isinstance(channel, Channel)
        assert channel.id == sample_channel_config.channel_id
        assert channel.name == sample_channel_config.name
        assert channel.timezone == sample_channel_config.timezone

    def test_channel_config_validation_invalid_id(self) -> None:
        """Test channel config validation with invalid ID."""
        with pytest.raises(ValueError, match="YouTube channel ID must be 24 characters long"):
            ChannelConfig(
                name="Test Ward",
                channel_id="INVALID_ID",  # Too short
                timezone="America/Denver",
                enabled=True,
                max_videos_to_check=50,
            )

    def test_channel_config_validation_invalid_timezone(self) -> None:
        """Test channel config validation with invalid timezone."""
        with pytest.raises(ValueError, match="Invalid timezone"):
            ChannelConfig(
                name="Test Ward",
                channel_id="UCTestChannelID00000001",
                timezone="Invalid/Timezone",
                enabled=True,
                max_videos_to_check=50,
            )


class TestProcessingResult:
    """Tests for ProcessingResult model."""

    def test_processing_result_success(self, sample_processing_result_success: ProcessingResult) -> None:
        """Test successful processing result."""
        assert sample_processing_result_success.is_success is True
        assert sample_processing_result_success.is_failure is False
        assert sample_processing_result_success.status == VideoStatus.PROCESSED
        assert sample_processing_result_success.old_visibility == VideoVisibility.PUBLIC
        assert sample_processing_result_success.new_visibility == VideoVisibility.UNLISTED

    def test_processing_result_failure(self, sample_processing_result_failed: ProcessingResult) -> None:
        """Test failed processing result."""
        assert sample_processing_result_failed.is_success is False
        assert sample_processing_result_failed.is_failure is True
        assert sample_processing_result_failed.status == VideoStatus.FAILED
        assert sample_processing_result_failed.error_message == "API rate limit exceeded"

    def test_processing_result_skipped(self, sample_video_new: Video) -> None:
        """Test skipped processing result."""
        result = ProcessingResult(
            video=sample_video_new,
            status=VideoStatus.SKIPPED,
            error_message="Video too recent",
        )
        assert result.is_success is False
        assert result.is_failure is False
        assert result.status == VideoStatus.SKIPPED


class TestChannelProcessingResult:
    """Tests for ChannelProcessingResult model."""

    def test_channel_result_creation(self) -> None:
        """Test channel processing result creation."""
        result = ChannelProcessingResult(
            channel_id="UCTestChannelID00000001",
            channel_name="Test Ward 1",
        )
        assert result.channel_id == "UCTestChannelID00000001"
        assert result.channel_name == "Test Ward 1"
        assert result.has_errors is False
        assert len(result.results) == 0

    def test_channel_result_add_results(
        self,
        sample_processing_result_success: ProcessingResult,
        sample_processing_result_failed: ProcessingResult,
    ) -> None:
        """Test adding results to channel processing result."""
        channel_result = ChannelProcessingResult(
            channel_id="UCTestChannelID00000001",
            channel_name="Test Ward 1",
        )

        channel_result.add_result(sample_processing_result_success)
        channel_result.add_result(sample_processing_result_failed)

        assert len(channel_result.results) == 2
        assert channel_result.has_errors is True

    def test_channel_result_stats(self, sample_channel_result: ChannelProcessingResult) -> None:
        """Test channel processing result statistics."""
        stats = sample_channel_result.stats
        assert isinstance(stats, ProcessingStats)
        assert stats.videos_processed == 1
        assert stats.videos_failed == 1
        assert stats.videos_skipped == 0
        assert stats.total_videos_checked == 2

    def test_channel_result_successful_results(self, sample_channel_result: ChannelProcessingResult) -> None:
        """Test getting successful results."""
        successful = sample_channel_result.successful_results
        assert len(successful) == 1
        assert successful[0].is_success is True

    def test_channel_result_failed_results(self, sample_channel_result: ChannelProcessingResult) -> None:
        """Test getting failed results."""
        failed = sample_channel_result.failed_results
        assert len(failed) == 1
        assert failed[0].is_failure is True


class TestBatchProcessingResult:
    """Tests for BatchProcessingResult model."""

    def test_batch_result_creation(self) -> None:
        """Test batch processing result creation."""
        result = BatchProcessingResult()
        assert result.has_errors is False
        assert result.global_error is None
        assert len(result.channel_results) == 0

    def test_batch_result_add_channel_results(self, sample_batch_result: BatchProcessingResult) -> None:
        """Test adding channel results to batch processing result."""
        assert len(sample_batch_result.channel_results) == 1
        assert sample_batch_result.has_errors is True

    def test_batch_result_overall_stats(self, sample_batch_result: BatchProcessingResult) -> None:
        """Test batch processing result overall statistics."""
        stats = sample_batch_result.overall_stats
        assert isinstance(stats, ProcessingStats)
        assert stats.channels_processed == 1
        assert stats.videos_processed == 1
        assert stats.videos_failed == 1
        assert stats.total_videos_checked == 2

    def test_batch_result_successful_channels(self) -> None:
        """Test getting successful channels."""
        result = BatchProcessingResult()
        
        # Add successful channel
        successful_channel = ChannelProcessingResult(
            channel_id="UCTestChannelID00000001",
            channel_name="Successful Ward",
        )
        successful_channel.add_result(ProcessingResult(
            video=Mock(),
            status=VideoStatus.PROCESSED,
        ))
        
        # Add failed channel
        failed_channel = ChannelProcessingResult(
            channel_id="UCTestChannelID00000002",
            channel_name="Failed Ward",
            error_message="Channel not found",
        )
        
        result.add_channel_result(successful_channel)
        result.add_channel_result(failed_channel)
        
        successful = result.successful_channels
        assert len(successful) == 1
        assert successful[0].channel_name == "Successful Ward"

    def test_batch_result_failed_channels(self, sample_batch_result: BatchProcessingResult) -> None:
        """Test getting failed channels."""
        failed = sample_batch_result.failed_channels
        assert len(failed) == 1  # Channel has failed results

    def test_batch_result_complete(self) -> None:
        """Test completing batch processing result."""
        result = BatchProcessingResult()
        start_time = result.start_time
        
        result.complete()
        
        assert result.end_time is not None
        assert result.end_time >= start_time
        assert result.overall_stats.processing_time_seconds >= 0


class TestProcessingStats:
    """Tests for ProcessingStats model."""

    def test_processing_stats_creation(self) -> None:
        """Test processing stats creation."""
        stats = ProcessingStats()
        assert stats.channels_processed == 0
        assert stats.videos_processed == 0
        assert stats.videos_failed == 0
        assert stats.videos_skipped == 0
        assert stats.total_videos_checked == 0
        assert stats.processing_time_seconds == 0.0

    def test_processing_stats_success_rate(self) -> None:
        """Test success rate calculation."""
        stats = ProcessingStats(
            videos_processed=8,
            videos_failed=2,
            videos_skipped=0,
        )
        assert stats.success_rate == 80.0

    def test_processing_stats_success_rate_no_videos(self) -> None:
        """Test success rate with no videos processed."""
        stats = ProcessingStats()
        assert stats.success_rate == 100.0  # No failures = 100% success
