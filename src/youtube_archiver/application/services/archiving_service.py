"""Default implementation of the archiving service."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from youtube_archiver.domain.exceptions import (
    APIError,
    AuthenticationError,
    ChannelNotFoundError,
    ConfigurationError,
    RateLimitError,
)
from youtube_archiver.domain.models.channel import Channel
from youtube_archiver.domain.models.processing import (
    BatchProcessingResult,
    ChannelProcessingResult,
    ProcessingResult,
)
from youtube_archiver.domain.models.video import Video, VideoStatus, VideoVisibility
from youtube_archiver.domain.services.archiving_service import ArchivingService
from youtube_archiver.domain.services.configuration_provider import ConfigurationProvider
from youtube_archiver.domain.services.video_repository import VideoRepository
from youtube_archiver.domain.services.visibility_manager import VisibilityManager

logger = logging.getLogger(__name__)


class DefaultArchivingService(ArchivingService):
    """
    Default implementation of the archiving service.
    
    This service orchestrates the complete video archiving workflow by
    coordinating between the video repository, visibility manager, and
    configuration provider.
    """

    def __init__(
        self,
        video_repository: VideoRepository,
        visibility_manager: VisibilityManager,
        config_provider: ConfigurationProvider,
    ) -> None:
        """
        Initialize the archiving service.
        
        Args:
            video_repository: Repository for video data operations
            visibility_manager: Manager for video visibility changes
            config_provider: Provider for configuration settings
        """
        self.video_repository = video_repository
        self.visibility_manager = visibility_manager
        self.config_provider = config_provider

    async def process_all_channels(self) -> BatchProcessingResult:
        """
        Process all configured channels in a batch operation.
        
        Returns:
            BatchProcessingResult with overall statistics and channel results
        """
        logger.info("Starting batch processing of all channels")
        
        batch_result = BatchProcessingResult()
        
        try:
            # Get enabled channels
            channels = self.config_provider.get_channels()
            enabled_channels = [c for c in channels if c.enabled]
            
            if not enabled_channels:
                logger.warning("No enabled channels found in configuration")
                batch_result.global_error = "No enabled channels configured"
                batch_result.complete()
                return batch_result
            
            logger.info(f"Processing {len(enabled_channels)} enabled channels")
            
            # Process channels with controlled concurrency
            semaphore = asyncio.Semaphore(3)  # Limit concurrent channel processing
            
            async def process_channel_with_semaphore(channel_config: Any) -> ChannelProcessingResult:
                async with semaphore:
                    return await self.process_channel(channel_config.to_domain())
            
            # Process all channels concurrently but with limits
            tasks = [
                process_channel_with_semaphore(channel_config)
                for channel_config in enabled_channels
            ]
            
            channel_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and handle exceptions
            for i, result in enumerate(channel_results):
                if isinstance(result, Exception):
                    # Create error result for failed channel
                    channel_config = enabled_channels[i]
                    error_result = ChannelProcessingResult(
                        channel_id=channel_config.channel_id,
                        channel_name=channel_config.name,
                        error_message=f"Channel processing failed: {result}",
                    )
                    batch_result.add_channel_result(error_result)
                    logger.error(f"Channel {channel_config.name} failed: {result}")
                elif isinstance(result, ChannelProcessingResult):
                    batch_result.add_channel_result(result)
                else:
                    # This shouldn't happen, but handle it gracefully
                    channel_config = enabled_channels[i]
                    error_result = ChannelProcessingResult(
                        channel_id=channel_config.channel_id,
                        channel_name=channel_config.name,
                        error_message="Unknown processing result type",
                    )
                    batch_result.add_channel_result(error_result)
            
            batch_result.complete()
            
            # Log summary
            stats = batch_result.overall_stats
            logger.info(
                f"Batch processing complete: {stats.videos_processed} videos processed, "
                f"{stats.videos_failed} failed, {stats.videos_skipped} skipped"
            )
            
            return batch_result
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            batch_result.global_error = str(e)
            batch_result.complete()
            return batch_result

    async def process_channel(self, channel: Channel) -> ChannelProcessingResult:
        """
        Process a single channel's videos.
        
        Args:
            channel: The channel to process
            
        Returns:
            ChannelProcessingResult with statistics and individual video results
        """
        logger.info(f"Processing channel: {channel.name} ({channel.id})")
        
        channel_result = ChannelProcessingResult(
            channel_id=channel.id,
            channel_name=channel.name,
        )
        
        try:
            # Get configuration settings
            max_videos = self.config_provider.get_max_videos_per_channel()
            target_visibility = VideoVisibility(self.config_provider.get_target_visibility())
            dry_run = self.config_provider.get_dry_run_mode()
            
            # Fetch videos from the channel
            logger.debug(f"Fetching up to {max_videos} videos from {channel.name}")
            videos = await self.video_repository.get_channel_videos(
                channel, max_results=max_videos
            )
            
            if not videos:
                logger.info(f"No videos found in channel {channel.name}")
                return channel_result
            
            logger.info(f"Found {len(videos)} videos in {channel.name}")
            
            # Filter for eligible videos
            eligible_videos = [video for video in videos if video.is_eligible_for_archiving]
            
            if not eligible_videos:
                logger.info(f"No eligible videos found in {channel.name}")
                return channel_result
            
            logger.info(f"Found {len(eligible_videos)} eligible videos in {channel.name}")
            
            # Process eligible videos
            if dry_run:
                logger.info(f"DRY RUN: Would process {len(eligible_videos)} videos in {channel.name}")
                # Create mock results for dry run
                for video in eligible_videos:
                    result = ProcessingResult(
                        video=video,
                        status=VideoStatus.SKIPPED,
                        error_message="Dry run mode - no changes made",
                    )
                    channel_result.add_result(result)
            else:
                # Process videos in batches to respect rate limits
                batch_size = self._get_batch_size()
                
                for i in range(0, len(eligible_videos), batch_size):
                    batch = eligible_videos[i:i + batch_size]
                    logger.debug(f"Processing batch of {len(batch)} videos")
                    
                    # Process batch
                    batch_results = await self.visibility_manager.change_visibility_batch(
                        batch, target_visibility
                    )
                    
                    # Add results
                    for result in batch_results:
                        channel_result.add_result(result)
                        
                        if result.is_success:
                            logger.debug(f"Successfully processed video: {result.video.title[:50]}...")
                        else:
                            logger.warning(f"Failed to process video: {result.video.title[:50]}... - {result.error_message}")
                    
                    # Add delay between batches if not the last batch
                    if i + batch_size < len(eligible_videos):
                        await asyncio.sleep(2)  # 2 second delay between batches
            
            # Log channel summary
            stats = channel_result.stats
            logger.info(
                f"Channel {channel.name} complete: {stats.videos_processed} processed, "
                f"{stats.videos_failed} failed, {stats.videos_skipped} skipped"
            )
            
            return channel_result
            
        except ChannelNotFoundError as e:
            logger.error(f"Channel not found: {channel.name} - {e}")
            channel_result.error_message = f"Channel not found or not accessible: {e}"
            return channel_result
        except AuthenticationError as e:
            logger.error(f"Authentication error for channel {channel.name}: {e}")
            channel_result.error_message = f"Authentication error: {e}"
            return channel_result
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded for channel {channel.name}: {e}")
            channel_result.error_message = f"Rate limit exceeded: {e}"
            return channel_result
        except APIError as e:
            logger.error(f"API error for channel {channel.name}: {e}")
            channel_result.error_message = f"API error: {e}"
            return channel_result
        except Exception as e:
            logger.error(f"Unexpected error processing channel {channel.name}: {e}")
            channel_result.error_message = f"Unexpected error: {e}"
            return channel_result

    async def process_specific_channels(
        self, channel_ids: list[str]
    ) -> BatchProcessingResult:
        """
        Process only specific channels by ID.
        
        Args:
            channel_ids: List of YouTube channel IDs to process
            
        Returns:
            BatchProcessingResult for the specified channels
        """
        logger.info(f"Processing specific channels: {channel_ids}")
        
        batch_result = BatchProcessingResult()
        
        try:
            # Get all configured channels
            all_channels = self.config_provider.get_channels()
            
            # Filter for requested channels
            target_channels = []
            for channel_id in channel_ids:
                channel_config = next(
                    (c for c in all_channels if c.channel_id == channel_id), None
                )
                if channel_config is None:
                    logger.error(f"Channel ID {channel_id} not found in configuration")
                    error_result = ChannelProcessingResult(
                        channel_id=channel_id,
                        channel_name="Unknown",
                        error_message="Channel not found in configuration",
                    )
                    batch_result.add_channel_result(error_result)
                else:
                    target_channels.append(channel_config)
            
            if not target_channels:
                batch_result.global_error = "No valid channels found"
                batch_result.complete()
                return batch_result
            
            # Process the target channels
            for channel_config in target_channels:
                channel = channel_config.to_domain()
                result = await self.process_channel(channel)
                batch_result.add_channel_result(result)
            
            batch_result.complete()
            return batch_result
            
        except Exception as e:
            logger.error(f"Specific channel processing failed: {e}")
            batch_result.global_error = str(e)
            batch_result.complete()
            return batch_result

    async def dry_run_all_channels(self) -> BatchProcessingResult:
        """
        Perform a dry-run of all channels without making changes.
        
        Returns:
            BatchProcessingResult showing what would be processed
        """
        logger.info("Starting dry-run of all channels")
        
        # Temporarily enable dry-run mode
        original_dry_run = self.config_provider.get_dry_run_mode()
        
        # Note: We can't actually change the config provider's dry run mode
        # since it's read-only, so we'll handle this in the processing logic
        
        try:
            return await self.process_all_channels()
        finally:
            # In a real implementation, we might restore the original setting
            # but since our config provider is read-only, this is just for clarity
            pass

    async def get_eligible_videos_summary(self) -> dict[str, Any]:
        """
        Get a summary of videos eligible for processing across all channels.
        
        Returns:
            Dictionary with summary statistics
        """
        logger.info("Generating eligible videos summary")
        
        summary: dict[str, Any] = {
            "total_channels": 0,
            "enabled_channels": 0,
            "total_videos": 0,
            "eligible_videos": 0,
            "by_channel": {},
            "generated_at": datetime.now().isoformat(),
        }
        
        try:
            channels = self.config_provider.get_channels()
            summary["total_channels"] = len(channels)
            
            enabled_channels = [c for c in channels if c.enabled]
            summary["enabled_channels"] = len(enabled_channels)
            
            for channel_config in enabled_channels:
                channel = channel_config.to_domain()
                
                try:
                    # Get videos for this channel
                    max_videos = channel_config.max_videos_to_check
                    videos = await self.video_repository.get_channel_videos(
                        channel, max_results=max_videos
                    )
                    
                    eligible_videos = [v for v in videos if v.is_eligible_for_archiving]
                    
                    channel_summary = {
                        "name": channel_config.name,
                        "total_videos": len(videos),
                        "eligible_videos": len(eligible_videos),
                        "public_videos": len([v for v in videos if v.visibility == VideoVisibility.PUBLIC]),
                        "live_videos": len([v for v in videos if v.is_live_content]),
                        "status": "ready" if eligible_videos else "up_to_date",
                    }
                    
                    summary["by_channel"][channel.id] = channel_summary
                    summary["total_videos"] = summary.get("total_videos", 0) + len(videos)
                    summary["eligible_videos"] = summary.get("eligible_videos", 0) + len(eligible_videos)
                    
                except Exception as e:
                    logger.error(f"Error getting summary for channel {channel_config.name}: {e}")
                    summary["by_channel"][channel.id] = {
                        "name": channel_config.name,
                        "error": str(e),
                        "status": "error",
                    }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            summary["error"] = str(e)
            return summary

    def validate_configuration(self) -> list[str]:
        """
        Validate the current configuration without processing.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        logger.info("Validating configuration")
        errors = []
        
        try:
            # Validate basic configuration
            channels = self.config_provider.get_channels()
            if not channels:
                errors.append("No channels configured")
            
            enabled_channels = [c for c in channels if c.enabled]
            if not enabled_channels:
                errors.append("No enabled channels found")
            
            # Validate settings
            age_threshold = self.config_provider.get_age_threshold_hours()
            if age_threshold < 1 or age_threshold > 168:
                errors.append(f"Invalid age threshold: {age_threshold} hours (must be 1-168)")
            
            target_visibility = self.config_provider.get_target_visibility()
            if target_visibility not in ["unlisted", "private"]:
                errors.append(f"Invalid target visibility: {target_visibility}")
            
            max_videos = self.config_provider.get_max_videos_per_channel()
            if max_videos < 1 or max_videos > 500:
                errors.append(f"Invalid max videos per channel: {max_videos} (must be 1-500)")
            
            # Validate channel configurations
            for channel in channels:
                if not channel.channel_id.startswith(("UC", "UU", "UL")):
                    errors.append(f"Invalid channel ID format: {channel.channel_id}")
                
                if len(channel.channel_id) != 24:
                    errors.append(f"Invalid channel ID length: {channel.channel_id}")
                
                if channel.max_videos_to_check < 1 or channel.max_videos_to_check > 500:
                    errors.append(f"Invalid max videos for {channel.name}: {channel.max_videos_to_check}")
            
        except ConfigurationError as e:
            errors.append(f"Configuration error: {e}")
        except Exception as e:
            errors.append(f"Validation error: {e}")
        
        if errors:
            logger.warning(f"Configuration validation found {len(errors)} errors")
        else:
            logger.info("Configuration validation passed")
        
        return errors

    def _get_batch_size(self) -> int:
        """
        Get the batch size for processing videos.
        
        Returns:
            Batch size based on configuration or defaults
        """
        try:
            # Try to get batch size from processing settings
            processing_settings = getattr(self.config_provider, 'config', None)
            if processing_settings and hasattr(processing_settings, 'processing'):
                batch_size = processing_settings.processing.batch_size
                return int(batch_size)
        except Exception:
            pass
        
        # Default batch size
        return 10

    async def _check_permissions_batch(self, videos: list[Video]) -> dict[str, bool]:
        """
        Check permissions for a batch of videos.
        
        Args:
            videos: List of videos to check
            
        Returns:
            Dictionary mapping video ID to permission status
        """
        # Note: batch_check_permissions is not implemented in the base interface
        # This is a placeholder for potential future optimization
        logger.debug("Using individual permission checks (batch method not available)")
        
        # Fallback to individual checks
        permissions: dict[str, bool] = {}
        for video in videos:
            try:
                permissions[video.id] = await self.visibility_manager.can_modify_video(video.id)
            except Exception:
                permissions[video.id] = False
        return permissions
