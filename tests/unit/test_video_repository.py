"""Unit tests for YouTubeVideoRepository parse helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from youtube_archiver.infrastructure.youtube.video_repository import (
    YouTubeVideoRepository,
)


@pytest.fixture
def repo() -> YouTubeVideoRepository:
    """A repository instance with a mock auth manager (no API calls)."""
    return YouTubeVideoRepository(auth_manager=Mock())


class TestParseDuration:
    """Tests for _parse_duration (ISO 8601 → seconds)."""

    def test_hours_minutes_seconds(self, repo: YouTubeVideoRepository) -> None:
        assert repo._parse_duration("PT1H2M3S") == 3723

    def test_minutes_and_seconds(self, repo: YouTubeVideoRepository) -> None:
        assert repo._parse_duration("PT4M13S") == 253

    def test_hours_only(self, repo: YouTubeVideoRepository) -> None:
        assert repo._parse_duration("PT1H") == 3600

    def test_seconds_only(self, repo: YouTubeVideoRepository) -> None:
        assert repo._parse_duration("PT45S") == 45

    def test_zero_duration(self, repo: YouTubeVideoRepository) -> None:
        # YouTube sends "PT0S" for live streams with no duration
        assert repo._parse_duration("PT0S") == 0

    def test_invalid_format_returns_none(self, repo: YouTubeVideoRepository) -> None:
        assert repo._parse_duration("not-a-duration") is None

    def test_empty_string_returns_none(self, repo: YouTubeVideoRepository) -> None:
        assert repo._parse_duration("") is None


class TestParseBroadcastTime:
    """Tests for _parse_broadcast_time (liveStreamingDetails extraction)."""

    def test_returns_none_when_no_live_details(
        self, repo: YouTubeVideoRepository
    ) -> None:
        item: dict = {"snippet": {}, "status": {}}
        assert repo._parse_broadcast_time(item) is None

    def test_returns_none_when_live_details_empty(
        self, repo: YouTubeVideoRepository
    ) -> None:
        item: dict = {"liveStreamingDetails": {}}
        assert repo._parse_broadcast_time(item) is None

    def test_prefers_actual_start_time(self, repo: YouTubeVideoRepository) -> None:
        item: dict = {
            "liveStreamingDetails": {
                "actualStartTime": "2024-01-14T18:00:00Z",
                "scheduledStartTime": "2024-01-14T17:30:00Z",
            }
        }
        result = repo._parse_broadcast_time(item)
        assert result is not None
        assert result == datetime(2024, 1, 14, 18, 0, 0, tzinfo=timezone.utc)

    def test_falls_back_to_scheduled_when_no_actual(
        self, repo: YouTubeVideoRepository
    ) -> None:
        item: dict = {
            "liveStreamingDetails": {
                "scheduledStartTime": "2024-01-14T17:30:00Z",
            }
        }
        result = repo._parse_broadcast_time(item)
        assert result is not None
        assert result == datetime(2024, 1, 14, 17, 30, 0, tzinfo=timezone.utc)

    def test_returns_none_for_unparseable_time_string(
        self, repo: YouTubeVideoRepository
    ) -> None:
        item: dict = {
            "liveStreamingDetails": {
                "actualStartTime": "not-a-date",
            }
        }
        assert repo._parse_broadcast_time(item) is None

    def test_result_is_utc_aware(self, repo: YouTubeVideoRepository) -> None:
        item: dict = {
            "liveStreamingDetails": {
                "actualStartTime": "2024-06-01T10:00:00Z",
            }
        }
        result = repo._parse_broadcast_time(item)
        assert result is not None
        assert result.tzinfo is not None


class TestIsLiveContent:
    """Tests for _is_live_content heuristic."""

    def test_live_streaming_details_present_means_live(
        self, repo: YouTubeVideoRepository
    ) -> None:
        item: dict = {
            "liveStreamingDetails": {"actualStartTime": "2024-01-14T18:00:00Z"},
            "snippet": {"title": "Regular video"},
        }
        assert repo._is_live_content(item) is True

    def test_sacrament_meeting_in_title_is_live(
        self, repo: YouTubeVideoRepository
    ) -> None:
        item: dict = {
            "snippet": {"title": "Sacrament Meeting - 1st Ward"},
        }
        assert repo._is_live_content(item) is True

    def test_ordinary_title_with_no_live_details_is_not_live(
        self, repo: YouTubeVideoRepository
    ) -> None:
        item: dict = {
            "snippet": {"title": "Ward Choir Rehearsal"},
        }
        assert repo._is_live_content(item) is False
