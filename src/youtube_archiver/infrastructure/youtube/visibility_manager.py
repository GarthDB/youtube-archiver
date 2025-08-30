"""YouTube API visibility manager implementation."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from googleapiclient.errors import HttpError

from youtube_archiver.domain.exceptions import (
    APIError,
    AuthenticationError,
    InsufficientPermissionsError,
    ProcessingError,
    RateLimitError,
    VideoNotFoundError,
)
from youtube_archiver.domain.models.processing import ProcessingResult
from youtube_archiver.domain.models.video import Video, VideoStatus, VideoVisibility
from youtube_archiver.domain.services.visibility_manager import VisibilityManager
from youtube_archiver.infrastructure.youtube.auth_manager import YouTubeAuthManager


class YouTubeVisibilityManager(VisibilityManager):
    """
    YouTube API implementation of the visibility manager.
    
    This class handles changing video visibility settings using the
    YouTube Data API v3, with proper error handling and rate limiting.
    """

    def __init__(self, auth_manager: YouTubeAuthManager) -> None:
        """
        Initialize the YouTube visibility manager.
        
        Args:
            auth_manager: YouTube authentication manager
        """
        self.auth_manager = auth_manager

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
        """
        try:
            service = self.auth_manager.get_authenticated_service()
            
            # Prepare the update request
            body = {
                "id": video.id,
                "status": {
                    "privacyStatus": new_visibility.value
                }
            }
            
            # Execute the update
            request = service.videos().update(
                part="status",
                body=body
            )
            
            response = request.execute()
            
            if response.get("id") == video.id:
                return ProcessingResult(
                    video=video,
                    status=VideoStatus.PROCESSED,
                    processed_at=datetime.now()
                )
            else:
                return ProcessingResult(
                    video=video,
                    status=VideoStatus.FAILED,
                    error_message="API response did not confirm update",
                    processed_at=datetime.now()
                )
                
        except HttpError as e:
            return self._handle_http_error(video, e)
        except Exception as e:
            return ProcessingResult(
                video=video,
                status=VideoStatus.FAILED,
                error_message=f"Unexpected error: {e}",
                processed_at=datetime.now()
            )

    async def change_visibility_batch(
        self, videos: list[Video], new_visibility: VideoVisibility
    ) -> list[ProcessingResult]:
        """
        Change the visibility of multiple videos in a batch operation.
        
        Args:
            videos: List of videos to update
            new_visibility: The new visibility setting for all videos
            
        Returns:
            List of ProcessingResults, one for each video
        """
        results = []
        
        # Process videos in smaller batches to avoid rate limiting
        batch_size = 10  # Conservative batch size
        
        for i in range(0, len(videos), batch_size):
            batch = videos[i:i + batch_size]
            
            # Process batch concurrently but with limited concurrency
            batch_tasks = [
                self.change_visibility(video, new_visibility)
                for video in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Handle any exceptions in the batch
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    results.append(ProcessingResult(
                        video=batch[j],
                        status=VideoStatus.FAILED,
                        error_message=f"Batch processing error: {result}",
                        processed_at=datetime.now()
                    ))
                elif isinstance(result, ProcessingResult):
                    results.append(result)
                else:
                    # This shouldn't happen, but handle it gracefully
                    results.append(ProcessingResult(
                        video=batch[j],
                        status=VideoStatus.FAILED,
                        error_message="Unknown processing result type",
                        processed_at=datetime.now()
                    ))
            
            # Add delay between batches to respect rate limits
            if i + batch_size < len(videos):
                await asyncio.sleep(1)  # 1 second delay between batches
        
        return results

    async def get_current_visibility(self, video_id: str) -> VideoVisibility:
        """
        Get the current visibility setting of a video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Current visibility setting
            
        Raises:
            VideoNotFoundError: If the video doesn't exist or isn't accessible
            APIError: If the API call fails
            AuthenticationError: If authentication is invalid
        """
        try:
            service = self.auth_manager.get_authenticated_service()
            
            response = service.videos().list(
                part="status",
                id=video_id
            ).execute()
            
            if not response.get("items"):
                raise VideoNotFoundError(video_id)
            
            privacy_status = response["items"][0]["status"]["privacyStatus"]
            
            visibility_map = {
                "public": VideoVisibility.PUBLIC,
                "unlisted": VideoVisibility.UNLISTED,
                "private": VideoVisibility.PRIVATE,
            }
            
            return visibility_map.get(privacy_status, VideoVisibility.PRIVATE)
            
        except HttpError as e:
            if e.resp.status == 404:
                raise VideoNotFoundError(video_id) from e
            elif e.resp.status == 403:
                if "quotaExceeded" in str(e):
                    raise RateLimitError("YouTube API quota exceeded") from e
                else:
                    raise AuthenticationError("Insufficient permissions") from e
            else:
                raise APIError(f"YouTube API error: {e}", e.resp.status) from e
        except Exception as e:
            raise APIError(f"Failed to get video visibility: {e}") from e

    async def can_modify_video(self, video_id: str) -> bool:
        """
        Check if the current user has permissions to modify a video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            True if the video can be modified, False otherwise
        """
        try:
            service = self.auth_manager.get_authenticated_service()
            
            # Try to get video details with snippet part
            # If we can access it, we likely have permissions
            response = service.videos().list(
                part="snippet,status",
                id=video_id
            ).execute()
            
            if not response.get("items"):
                return False
            
            # Additional check: see if we own this video
            # by checking if our channel ID matches
            try:
                user_info = self.auth_manager.get_user_info()
                if not user_info.get("has_channel"):
                    return False
                
                video_channel_id = response["items"][0]["snippet"]["channelId"]
                user_channel_id = user_info.get("channel_id")
                
                return bool(video_channel_id == user_channel_id)
                
            except Exception:
                # If we can't determine ownership, assume we can't modify
                return False
                
        except Exception:
            return False

    def _handle_http_error(self, video: Video, error: HttpError) -> ProcessingResult:
        """
        Handle HTTP errors from YouTube API and convert to ProcessingResult.
        
        Args:
            video: The video being processed
            error: The HTTP error from the API
            
        Returns:
            ProcessingResult with appropriate error information
        """
        status_code = error.resp.status
        error_content = str(error)
        
        if status_code == 404:
            return ProcessingResult(
                video=video,
                status=VideoStatus.FAILED,
                error_message="Video not found or not accessible",
                processed_at=datetime.now()
            )
        elif status_code == 403:
            if "quotaExceeded" in error_content:
                return ProcessingResult(
                    video=video,
                    status=VideoStatus.FAILED,
                    error_message="YouTube API quota exceeded",
                    processed_at=datetime.now()
                )
            elif "forbidden" in error_content.lower():
                return ProcessingResult(
                    video=video,
                    status=VideoStatus.FAILED,
                    error_message="Insufficient permissions to modify video",
                    processed_at=datetime.now()
                )
            else:
                return ProcessingResult(
                    video=video,
                    status=VideoStatus.FAILED,
                    error_message="Access denied",
                    processed_at=datetime.now()
                )
        elif status_code == 400:
            return ProcessingResult(
                video=video,
                status=VideoStatus.FAILED,
                error_message="Invalid request (video may not support visibility changes)",
                processed_at=datetime.now()
            )
        elif status_code == 429:
            return ProcessingResult(
                video=video,
                status=VideoStatus.FAILED,
                error_message="Rate limit exceeded, please try again later",
                processed_at=datetime.now()
            )
        else:
            return ProcessingResult(
                video=video,
                status=VideoStatus.FAILED,
                error_message=f"YouTube API error (HTTP {status_code}): {error_content}",
                processed_at=datetime.now()
            )

    async def batch_check_permissions(self, video_ids: list[str]) -> dict[str, bool]:
        """
        Check permissions for multiple videos efficiently.
        
        Args:
            video_ids: List of YouTube video IDs
            
        Returns:
            Dictionary mapping video ID to permission status
        """
        permissions = {}
        
        try:
            service = self.auth_manager.get_authenticated_service()
            
            # Get user's channel ID once
            user_info = self.auth_manager.get_user_info()
            if not user_info.get("has_channel"):
                return {video_id: False for video_id in video_ids}
            
            user_channel_id = user_info.get("channel_id")
            
            # Process in batches of 50 (YouTube API limit)
            for i in range(0, len(video_ids), 50):
                batch_ids = video_ids[i:i + 50]
                
                response = service.videos().list(
                    part="snippet",
                    id=",".join(batch_ids)
                ).execute()
                
                # Check each video in the response
                found_videos = {item["id"]: item for item in response.get("items", [])}
                
                for video_id in batch_ids:
                    if video_id in found_videos:
                        video_channel_id = found_videos[video_id]["snippet"]["channelId"]
                        permissions[video_id] = video_channel_id == user_channel_id
                    else:
                        permissions[video_id] = False
            
            return permissions
            
        except Exception:
            # If batch check fails, assume no permissions
            return {video_id: False for video_id in video_ids}
