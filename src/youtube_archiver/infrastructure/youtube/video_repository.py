"""YouTube API video repository implementation."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from googleapiclient.errors import HttpError

from youtube_archiver.domain.exceptions import (
    APIError,
    AuthenticationError,
    ChannelNotFoundError,
    RateLimitError,
)
from youtube_archiver.domain.models.channel import Channel
from youtube_archiver.domain.models.video import Video, VideoVisibility
from youtube_archiver.domain.services.video_repository import VideoRepository
from youtube_archiver.infrastructure.youtube.auth_manager import YouTubeAuthManager


class YouTubeVideoRepository(VideoRepository):
    """
    YouTube API implementation of the video repository.
    
    This class handles fetching video data from the YouTube Data API v3,
    including channel videos, video details, and live stream filtering.
    """

    def __init__(self, auth_manager: YouTubeAuthManager) -> None:
        """
        Initialize the YouTube video repository.
        
        Args:
            auth_manager: YouTube authentication manager
        """
        self.auth_manager = auth_manager

    async def get_channel_videos(
        self, channel: Channel, max_results: int | None = None
    ) -> list[Video]:
        """
        Retrieve videos from a specific channel.
        
        Args:
            channel: The channel to retrieve videos from
            max_results: Maximum number of videos to retrieve (None for all)
            
        Returns:
            List of videos from the channel, ordered by publish date (newest first)
            
        Raises:
            ChannelNotFoundError: If the channel doesn't exist or isn't accessible
            APIError: If the API call fails
            AuthenticationError: If authentication is invalid
        """
        try:
            service = self.auth_manager.get_authenticated_service()
            
            # Get channel's upload playlist ID
            channel_response = service.channels().list(
                part="contentDetails",
                id=channel.id
            ).execute()
            
            if not channel_response.get("items"):
                raise ChannelNotFoundError(channel.id)
            
            uploads_playlist_id = (
                channel_response["items"][0]
                ["contentDetails"]
                ["relatedPlaylists"]
                ["uploads"]
            )
            
            # Get videos from uploads playlist
            videos: list[Video] = []
            next_page_token = None
            
            while len(videos) < (max_results or float('inf')):
                # Calculate how many videos to request this page
                page_size = min(50, (max_results or 50) - len(videos))
                
                playlist_response = service.playlistItems().list(
                    part="snippet",
                    playlistId=uploads_playlist_id,
                    maxResults=page_size,
                    pageToken=next_page_token
                ).execute()
                
                if not playlist_response.get("items"):
                    break
                
                # Get detailed video information
                video_ids = [item["snippet"]["resourceId"]["videoId"] 
                           for item in playlist_response["items"]]
                
                video_details = await self._get_video_details_batch(video_ids)
                videos.extend(video_details)
                
                # Check for next page
                next_page_token = playlist_response.get("nextPageToken")
                if not next_page_token:
                    break
            
            return videos[:max_results] if max_results else videos
            
        except HttpError as e:
            if e.resp.status == 404:
                raise ChannelNotFoundError(channel.id) from e
            elif e.resp.status == 403:
                if "quotaExceeded" in str(e):
                    raise RateLimitError("YouTube API quota exceeded") from e
                else:
                    raise AuthenticationError("Insufficient permissions") from e
            else:
                raise APIError(f"YouTube API error: {e}", e.resp.status) from e
        except Exception as e:
            raise APIError(f"Failed to get channel videos: {e}") from e

    async def get_video_details(self, video_id: str) -> Video | None:
        """
        Retrieve detailed information about a specific video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Video details if found, None if not found or not accessible
            
        Raises:
            APIError: If the API call fails
            AuthenticationError: If authentication is invalid
        """
        try:
            videos = await self._get_video_details_batch([video_id])
            return videos[0] if videos else None
        except Exception as e:
            if "not found" in str(e).lower():
                return None
            raise

    async def get_live_videos(
        self, channel: Channel, max_results: int | None = None
    ) -> list[Video]:
        """
        Retrieve only live/streamed videos from a channel.
        
        Args:
            channel: The channel to search
            max_results: Maximum number of videos to retrieve
            
        Returns:
            List of live videos from the channel
        """
        # Get all videos and filter for live content
        all_videos = await self.get_channel_videos(channel, max_results)
        return [video for video in all_videos if video.is_live_content]

    async def search_videos(
        self, channel: Channel, query: str, max_results: int | None = None
    ) -> list[Video]:
        """
        Search for videos in a channel matching a query.
        
        Args:
            channel: The channel to search in
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of matching videos
        """
        try:
            service = self.auth_manager.get_authenticated_service()
            
            # Search for videos in the specific channel
            search_response = service.search().list(
                part="snippet",
                channelId=channel.id,
                q=query,
                type="video",
                order="date",
                maxResults=min(max_results or 50, 50)
            ).execute()
            
            if not search_response.get("items"):
                return []
            
            # Get detailed video information
            video_ids = [item["id"]["videoId"] for item in search_response["items"]]
            return await self._get_video_details_batch(video_ids)
            
        except HttpError as e:
            if e.resp.status == 404:
                raise ChannelNotFoundError(channel.id) from e
            elif e.resp.status == 403:
                if "quotaExceeded" in str(e):
                    raise RateLimitError("YouTube API quota exceeded") from e
                else:
                    raise AuthenticationError("Insufficient permissions") from e
            else:
                raise APIError(f"YouTube API error: {e}", e.resp.status) from e
        except Exception as e:
            raise APIError(f"Failed to search videos: {e}") from e

    async def _get_video_details_batch(self, video_ids: list[str]) -> list[Video]:
        """
        Get detailed information for a batch of videos.
        
        Args:
            video_ids: List of YouTube video IDs
            
        Returns:
            List of Video objects with detailed information
        """
        if not video_ids:
            return []

        try:
            service = self.auth_manager.get_authenticated_service()
            
            # YouTube API allows up to 50 IDs per request
            videos = []
            for i in range(0, len(video_ids), 50):
                batch_ids = video_ids[i:i + 50]
                
                response = service.videos().list(
                    part="snippet,status,liveStreamingDetails,statistics,contentDetails",
                    id=",".join(batch_ids)
                ).execute()
                
                for item in response.get("items", []):
                    video = self._parse_video_item(item)
                    if video:
                        videos.append(video)
            
            return videos
            
        except Exception as e:
            raise APIError(f"Failed to get video details: {e}") from e

    def _parse_video_item(self, item: dict[str, Any]) -> Video | None:
        """
        Parse a YouTube API video item into a Video domain object.
        
        Args:
            item: YouTube API video item
            
        Returns:
            Video domain object or None if parsing fails
        """
        try:
            snippet = item["snippet"]
            status = item["status"]
            
            # Parse published date
            published_at_str = snippet["publishedAt"]
            published_at = datetime.fromisoformat(
                published_at_str.replace("Z", "+00:00")
            )
            
            # Determine visibility
            privacy_status = status["privacyStatus"]
            visibility_map = {
                "public": VideoVisibility.PUBLIC,
                "unlisted": VideoVisibility.UNLISTED,
                "private": VideoVisibility.PRIVATE,
            }
            visibility = visibility_map.get(privacy_status, VideoVisibility.PRIVATE)
            
            # Check if it's live content
            is_live_content = self._is_live_content(item)
            
            # Parse optional fields
            statistics = item.get("statistics", {})
            content_details = item.get("content_details", {})
            
            # Parse duration (ISO 8601 format like PT4M13S)
            duration_seconds = None
            if "duration" in content_details:
                duration_seconds = self._parse_duration(content_details["duration"])
            
            return Video(
                id=item["id"],
                title=snippet["title"],
                channel_id=snippet["channelId"],
                published_at=published_at,
                visibility=visibility,
                is_live_content=is_live_content,
                duration_seconds=duration_seconds,
                view_count=int(statistics.get("viewCount", 0)),
                description=snippet.get("description"),
                thumbnail_url=snippet.get("thumbnails", {}).get("default", {}).get("url"),
            )
            
        except Exception as e:
            # Log the error but don't fail the entire batch
            print(f"Warning: Failed to parse video {item.get('id', 'unknown')}: {e}")
            return None

    def _is_live_content(self, item: dict[str, Any]) -> bool:
        """
        Determine if a video is live content (live stream or premiere).
        
        Args:
            item: YouTube API video item
            
        Returns:
            True if the video is live content
        """
        # Check if it was a live broadcast
        live_details = item.get("liveStreamingDetails")
        if live_details:
            return True
        
        # Check snippet for live indicators
        snippet = item.get("snippet", {})
        title = snippet.get("title", "").lower()
        
        # Common indicators of live content
        live_indicators = [
            "live", "stream", "streaming", "sacrament meeting",
            "worship service", "broadcast"
        ]
        
        return any(indicator in title for indicator in live_indicators)

    def _parse_duration(self, duration_str: str) -> int | None:
        """
        Parse ISO 8601 duration string to seconds.
        
        Args:
            duration_str: ISO 8601 duration (e.g., "PT4M13S")
            
        Returns:
            Duration in seconds or None if parsing fails
        """
        try:
            import re
            
            # Parse PT4M13S format
            pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
            match = re.match(pattern, duration_str)
            
            if not match:
                return None
            
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            
            return hours * 3600 + minutes * 60 + seconds
            
        except Exception:
            return None
