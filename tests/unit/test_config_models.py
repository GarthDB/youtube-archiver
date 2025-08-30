"""Tests for configuration models."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from youtube_archiver.infrastructure.config.models import (
    AppConfig,
    LoggingConfig,
    ProcessingSettings,
    RetrySettings,
    StakeInfo,
    YouTubeAPIConfig,
)


class TestStakeInfo:
    """Tests for StakeInfo model."""

    def test_stake_info_creation(self) -> None:
        """Test stake info creation with valid data."""
        stake_info = StakeInfo(
            name="Test Stake",
            tech_specialist="test@example.com",
            region="Test Region",
            notes="Test notes",
        )
        assert stake_info.name == "Test Stake"
        assert stake_info.tech_specialist == "test@example.com"
        assert stake_info.region == "Test Region"
        assert stake_info.notes == "Test notes"

    def test_stake_info_optional_fields(self) -> None:
        """Test stake info with optional fields."""
        stake_info = StakeInfo(
            name="Test Stake",
            tech_specialist="test@example.com",
        )
        assert stake_info.region is None
        assert stake_info.notes is None

    def test_stake_info_validation_invalid_email(self) -> None:
        """Test stake info validation with invalid email."""
        with pytest.raises(ValidationError):
            StakeInfo(
                name="Test Stake",
                tech_specialist="invalid-email",
            )


class TestProcessingSettings:
    """Tests for ProcessingSettings model."""

    def test_processing_settings_defaults(self) -> None:
        """Test processing settings with default values."""
        settings = ProcessingSettings()
        assert settings.age_threshold_hours == 24
        assert settings.target_visibility == "unlisted"
        assert settings.max_videos_per_channel == 50
        assert settings.dry_run is False
        assert settings.batch_size == 10
        assert settings.initial_backlog_mode is False

    def test_processing_settings_custom_values(self) -> None:
        """Test processing settings with custom values."""
        settings = ProcessingSettings(
            age_threshold_hours=48,
            target_visibility="private",
            max_videos_per_channel=100,
            dry_run=True,
            batch_size=20,
            initial_backlog_mode=True,
        )
        assert settings.age_threshold_hours == 48
        assert settings.target_visibility == "private"
        assert settings.max_videos_per_channel == 100
        assert settings.dry_run is True
        assert settings.batch_size == 20
        assert settings.initial_backlog_mode is True

    def test_processing_settings_validation_age_threshold(self) -> None:
        """Test processing settings validation for age threshold."""
        with pytest.raises(ValidationError):
            ProcessingSettings(age_threshold_hours=0)  # Too low

        with pytest.raises(ValidationError):
            ProcessingSettings(age_threshold_hours=169)  # Too high

    def test_processing_settings_validation_target_visibility(self) -> None:
        """Test processing settings validation for target visibility."""
        with pytest.raises(ValidationError):
            ProcessingSettings(target_visibility="invalid")

    def test_processing_settings_validation_max_videos(self) -> None:
        """Test processing settings validation for max videos."""
        with pytest.raises(ValidationError):
            ProcessingSettings(max_videos_per_channel=0)  # Too low

        with pytest.raises(ValidationError):
            ProcessingSettings(max_videos_per_channel=501)  # Too high

    def test_processing_settings_validation_batch_size(self) -> None:
        """Test processing settings validation for batch size."""
        with pytest.raises(ValidationError):
            ProcessingSettings(batch_size=0)  # Too low

        with pytest.raises(ValidationError):
            ProcessingSettings(batch_size=101)  # Too high


class TestYouTubeAPIConfig:
    """Tests for YouTubeAPIConfig model."""

    def test_youtube_api_settings_defaults(self) -> None:
        """Test YouTube API settings with default values."""
        settings = YouTubeAPIConfig()
        assert settings.credentials_file is None
        assert settings.token_file is None
        assert settings.scopes == ["https://www.googleapis.com/auth/youtube"]

    def test_youtube_api_settings_custom_values(self) -> None:
        """Test YouTube API settings with custom values."""
        settings = YouTubeAPIConfig(
            credentials_file="custom_credentials.json",
            token_file="custom_token.json",
            scopes=["https://www.googleapis.com/auth/youtube.readonly"],
        )
        assert settings.credentials_file == "custom_credentials.json"
        assert settings.token_file == "custom_token.json"
        assert settings.scopes == ["https://www.googleapis.com/auth/youtube.readonly"]

    def test_youtube_api_settings_validation_missing_required_scope(self) -> None:
        """Test YouTube API settings validation for missing required scope."""
        with pytest.raises(ValidationError):
            YouTubeAPIConfig(scopes=["https://www.googleapis.com/auth/youtube.readonly"])


class TestRetrySettings:
    """Tests for RetrySettings model."""

    def test_retry_settings_defaults(self) -> None:
        """Test retry settings with default values."""
        settings = RetrySettings()
        assert settings.max_attempts == 3
        assert settings.backoff_factor == 2.0
        assert settings.max_delay == 300

    def test_retry_settings_custom_values(self) -> None:
        """Test retry settings with custom values."""
        settings = RetrySettings(
            max_attempts=5,
            backoff_factor=1.5,
            max_delay=600,
        )
        assert settings.max_attempts == 5
        assert settings.backoff_factor == 1.5
        assert settings.max_delay == 600

    def test_retry_settings_validation_max_attempts(self) -> None:
        """Test retry settings validation for max attempts."""
        with pytest.raises(ValidationError):
            RetrySettings(max_attempts=0)  # Too low

        with pytest.raises(ValidationError):
            RetrySettings(max_attempts=11)  # Too high

    def test_retry_settings_validation_backoff_factor(self) -> None:
        """Test retry settings validation for backoff factor."""
        with pytest.raises(ValidationError):
            RetrySettings(backoff_factor=0.9)  # Too low

        with pytest.raises(ValidationError):
            RetrySettings(backoff_factor=5.1)  # Too high

    def test_retry_settings_validation_max_delay(self) -> None:
        """Test retry settings validation for max delay."""
        with pytest.raises(ValidationError):
            RetrySettings(max_delay=0)  # Too low

        with pytest.raises(ValidationError):
            RetrySettings(max_delay=3601)  # Too high


class TestLoggingConfig:
    """Tests for LoggingConfig model."""

    def test_logging_settings_defaults(self) -> None:
        """Test logging settings with default values."""
        settings = LoggingConfig()
        assert settings.level == "INFO"
        assert "%(asctime)s" in settings.format
        assert settings.file_path is None
        assert settings.max_file_size == 10485760  # 10MB
        assert settings.backup_count == 5

    def test_logging_settings_custom_values(self) -> None:
        """Test logging settings with custom values."""
        settings = LoggingConfig(
            level="DEBUG",
            format="%(levelname)s - %(message)s",
            file_path="app.log",
            max_file_size=20971520,  # 20MB
            backup_count=10,
        )
        assert settings.level == "DEBUG"
        assert settings.format == "%(levelname)s - %(message)s"
        assert settings.file_path == "app.log"
        assert settings.max_file_size == 20971520
        assert settings.backup_count == 10

    def test_logging_settings_validation_level(self) -> None:
        """Test logging settings validation for level."""
        with pytest.raises(ValidationError):
            LoggingConfig(level="INVALID")

    def test_logging_settings_validation_max_file_size(self) -> None:
        """Test logging settings validation for max file size."""
        with pytest.raises(ValidationError):
            LoggingConfig(max_file_size=0)  # Too low

    def test_logging_settings_validation_backup_count(self) -> None:
        """Test logging settings validation for backup count."""
        with pytest.raises(ValidationError):
            LoggingConfig(backup_count=-1)  # Negative


class TestAppConfig:
    """Tests for AppConfig model."""

    def test_app_config_creation(self, sample_config_data: dict[str, Any]) -> None:
        """Test app config creation with valid data."""
        config = AppConfig(**sample_config_data)
        assert config.stake_info.name == "Test Stake"
        assert len(config.channels) == 3
        assert config.processing.age_threshold_hours == 24
        assert config.youtube_api.credentials_file == "test_credentials.json"
        assert config.retry.max_attempts == 3
        assert config.logging.level == "INFO"

    def test_app_config_validation_no_channels(self, sample_config_data: dict[str, Any]) -> None:
        """Test app config validation with no channels."""
        sample_config_data["channels"] = []
        with pytest.raises(ValidationError, match="at least 1 item"):
            AppConfig(**sample_config_data)

    def test_app_config_validation_invalid_channel(self, sample_config_data: dict[str, Any]) -> None:
        """Test app config validation with invalid channel."""
        sample_config_data["channels"][0]["channel_id"] = "INVALID"
        with pytest.raises(ValidationError):
            AppConfig(**sample_config_data)

    def test_app_config_default_sections(self) -> None:
        """Test app config with minimal required data and defaults."""
        minimal_config = {
            "stake_info": {
                "name": "Test Stake",
                "tech_specialist": "test@example.com",
            },
            "channels": [
                {
                    "name": "Test Ward",
                    "channel_id": "UCTestChannelID00000001",
                    "timezone": "America/Denver",
                    "enabled": True,
                    "max_videos_to_check": 50,
                }
            ],
        }
        
        config = AppConfig(**minimal_config)
        
        # Check that default sections are created
        assert config.processing.age_threshold_hours == 24
        assert config.youtube_api.credentials_file == "credentials.json"
        assert config.retry.max_attempts == 3
        assert config.logging.level == "INFO"

    def test_app_config_environment_variable_substitution(self) -> None:
        """Test app config with environment variable substitution."""
        import os
        
        # Set test environment variable
        os.environ["TEST_CREDENTIALS_FILE"] = "test_env_credentials.json"
        
        try:
            config_data = {
                "stake_info": {
                    "name": "Test Stake",
                    "tech_specialist": "test@example.com",
                },
                "channels": [
                    {
                        "name": "Test Ward",
                        "channel_id": "UCTestChannelID00000001",
                        "timezone": "America/Denver",
                        "enabled": True,
                        "max_videos_to_check": 50,
                    }
                ],
                "youtube_api": {
                    "credentials_file": "${TEST_CREDENTIALS_FILE}",
                },
            }
            
            config = AppConfig(**config_data)
            # Note: Environment variable substitution would be handled by the YAML provider
            # This test documents the expected behavior
            assert config.youtube_api.credentials_file == "${TEST_CREDENTIALS_FILE}"
            
        finally:
            # Clean up environment variable
            if "TEST_CREDENTIALS_FILE" in os.environ:
                del os.environ["TEST_CREDENTIALS_FILE"]
