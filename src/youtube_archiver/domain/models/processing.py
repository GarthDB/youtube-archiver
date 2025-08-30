"""Processing result models for tracking archiving operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from youtube_archiver.domain.models.video import Video, VideoStatus


@dataclass
class ProcessingResult:
    """
    Result of processing a single video.

    Tracks the outcome of attempting to change a video's visibility,
    including success/failure status and any error information.
    """

    video: Video
    status: VideoStatus
    error_message: str | None = None
    processed_at: datetime = field(default_factory=datetime.now)

    @property
    def is_success(self) -> bool:
        """Whether the processing was successful."""
        return self.status == VideoStatus.PROCESSED

    @property
    def is_failure(self) -> bool:
        """Whether the processing failed."""
        return self.status == VideoStatus.FAILED

    def __str__(self) -> str:
        """Human-readable string representation."""
        status_emoji = {
            VideoStatus.PROCESSED: "✅",
            VideoStatus.SKIPPED: "⏭️",
            VideoStatus.FAILED: "❌",
            VideoStatus.PENDING: "⏳",
        }
        emoji = status_emoji.get(self.status, "❓")

        error_part = f" - {self.error_message}" if self.error_message else ""
        return f"{emoji} {self.video.title[:50]}... ({self.status.value}){error_part}"


@dataclass
class ProcessingStats:
    """
    Statistics for a batch processing operation.

    Provides aggregate information about processing multiple videos
    across one or more channels.
    """

    total_videos_checked: int = 0
    videos_processed: int = 0
    videos_skipped: int = 0
    videos_failed: int = 0
    channels_processed: int = 0
    processing_time_seconds: float = 0.0
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    @property
    def success_rate(self) -> float:
        """Calculate the success rate as a percentage."""
        if self.total_videos_checked == 0:
            return 0.0
        return (self.videos_processed / self.total_videos_checked) * 100

    @property
    def is_completed(self) -> bool:
        """Whether the processing batch is completed."""
        return self.completed_at is not None

    def add_result(self, result: ProcessingResult) -> None:
        """Add a processing result to the statistics."""
        self.total_videos_checked += 1

        if result.status == VideoStatus.PROCESSED:
            self.videos_processed += 1
        elif result.status == VideoStatus.SKIPPED:
            self.videos_skipped += 1
        elif result.status == VideoStatus.FAILED:
            self.videos_failed += 1

    def complete(self) -> None:
        """Mark the processing batch as completed."""
        self.completed_at = datetime.now()
        if self.completed_at:
            delta = self.completed_at - self.started_at
            self.processing_time_seconds = delta.total_seconds()

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"ProcessingStats(checked={self.total_videos_checked}, "
            f"processed={self.videos_processed}, skipped={self.videos_skipped}, "
            f"failed={self.videos_failed}, success_rate={self.success_rate:.1f}%)"
        )


@dataclass
class ChannelProcessingResult:
    """
    Result of processing all videos in a single channel.

    Aggregates results for all videos processed in a specific channel,
    providing channel-level statistics and error tracking.
    """

    channel_id: str
    channel_name: str
    results: list[ProcessingResult] = field(default_factory=list)
    error_message: str | None = None
    processed_at: datetime = field(default_factory=datetime.now)

    @property
    def stats(self) -> ProcessingStats:
        """Generate statistics for this channel's processing."""
        stats = ProcessingStats(
            channels_processed=1,
            started_at=self.processed_at,
        )

        for result in self.results:
            stats.add_result(result)

        stats.complete()
        return stats

    @property
    def successful_results(self) -> list[ProcessingResult]:
        """Get only the successful processing results."""
        return [r for r in self.results if r.is_success]

    @property
    def failed_results(self) -> list[ProcessingResult]:
        """Get only the failed processing results."""
        return [r for r in self.results if r.is_failure]

    @property
    def has_errors(self) -> bool:
        """Whether this channel had any processing errors."""
        return self.error_message is not None or any(r.is_failure for r in self.results)

    def add_result(self, result: ProcessingResult) -> None:
        """Add a processing result for this channel."""
        self.results.append(result)

    def __str__(self) -> str:
        """Human-readable string representation."""
        stats = self.stats
        error_part = f" (ERROR: {self.error_message})" if self.error_message else ""
        return f"{self.channel_name}: {stats}{error_part}"


@dataclass
class BatchProcessingResult:
    """
    Result of processing multiple channels in a batch operation.

    Top-level result that aggregates all channel processing results
    and provides overall statistics for the entire archiving run.
    """

    channel_results: dict[str, ChannelProcessingResult] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    global_error: str | None = None

    @property
    def overall_stats(self) -> ProcessingStats:
        """Generate overall statistics across all channels."""
        stats = ProcessingStats(
            started_at=self.started_at,
            channels_processed=len(self.channel_results),
        )

        for channel_result in self.channel_results.values():
            for result in channel_result.results:
                stats.add_result(result)

        if self.completed_at:
            stats.completed_at = self.completed_at
            delta = self.completed_at - self.started_at
            stats.processing_time_seconds = delta.total_seconds()

        return stats

    @property
    def has_errors(self) -> bool:
        """Whether any channel had processing errors."""
        return self.global_error is not None or any(
            cr.has_errors for cr in self.channel_results.values()
        )

    @property
    def successful_channels(self) -> list[ChannelProcessingResult]:
        """Get channels that processed successfully without errors."""
        return [cr for cr in self.channel_results.values() if not cr.has_errors]

    @property
    def failed_channels(self) -> list[ChannelProcessingResult]:
        """Get channels that had processing errors."""
        return [cr for cr in self.channel_results.values() if cr.has_errors]

    def add_channel_result(self, channel_result: ChannelProcessingResult) -> None:
        """Add a channel processing result."""
        self.channel_results[channel_result.channel_id] = channel_result

    def complete(self) -> None:
        """Mark the batch processing as completed."""
        self.completed_at = datetime.now()

    def __str__(self) -> str:
        """Human-readable string representation."""
        stats = self.overall_stats
        error_part = (
            f" (GLOBAL ERROR: {self.global_error})" if self.global_error else ""
        )
        return f"BatchProcessingResult: {stats}{error_part}"
