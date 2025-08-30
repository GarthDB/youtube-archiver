"""YAML-based configuration provider implementation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from youtube_archiver.domain.exceptions import ConfigurationError
from youtube_archiver.domain.models.channel import ChannelConfig
from youtube_archiver.domain.services.configuration_provider import ConfigurationProvider
from youtube_archiver.infrastructure.config.models import AppConfig, LoggingConfig, RetrySettings


class YamlConfigurationProvider(ConfigurationProvider):
    """
    Configuration provider that loads settings from YAML files.
    
    This implementation supports loading configuration from YAML files
    with environment variable substitution and validation using Pydantic models.
    """

    def __init__(self, config_path: str | Path) -> None:
        """
        Initialize the YAML configuration provider.
        
        Args:
            config_path: Path to the YAML configuration file
            
        Raises:
            ConfigurationError: If the configuration file cannot be loaded or is invalid
        """
        self.config_path = Path(config_path)
        self._config: AppConfig | None = None
        self._load_config()

    def _load_config(self) -> None:
        """Load and validate configuration from YAML file."""
        try:
            if not self.config_path.exists():
                raise ConfigurationError(f"Configuration file not found: {self.config_path}")
            
            with open(self.config_path, "r", encoding="utf-8") as f:
                raw_config = yaml.safe_load(f)
            
            if not raw_config:
                raise ConfigurationError("Configuration file is empty")
            
            # Perform environment variable substitution
            raw_config = self._substitute_env_vars(raw_config)
            
            # Validate using Pydantic model
            self._config = AppConfig(**raw_config)
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML syntax in configuration file: {e}") from e
        except ValidationError as e:
            raise ConfigurationError(f"Configuration validation failed: {e}") from e
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}") from e

    def _substitute_env_vars(self, obj: Any) -> Any:
        """
        Recursively substitute environment variables in configuration.
        
        Supports ${VAR_NAME} and ${VAR_NAME:default_value} syntax.
        """
        if isinstance(obj, dict):
            return {key: self._substitute_env_vars(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            return self._substitute_string_env_vars(obj)
        else:
            return obj

    def _substitute_string_env_vars(self, value: str) -> str:
        """Substitute environment variables in a string value."""
        import re
        
        # Pattern to match ${VAR_NAME} or ${VAR_NAME:default}
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
        
        def replace_var(match: re.Match[str]) -> str:
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) is not None else ""
            return os.getenv(var_name, default_value)
        
        return re.sub(pattern, replace_var, value)

    @property
    def config(self) -> AppConfig:
        """Get the loaded configuration."""
        if self._config is None:
            raise ConfigurationError("Configuration not loaded")
        return self._config

    def get_channels(self) -> list[ChannelConfig]:
        """Get the list of configured channels to process."""
        return self.config.channels

    def get_age_threshold_hours(self) -> int:
        """Get the age threshold in hours for video processing."""
        return self.config.processing.age_threshold_hours

    def get_target_visibility(self) -> str:
        """Get the target visibility setting for processed videos."""
        return self.config.processing.target_visibility

    def get_dry_run_mode(self) -> bool:
        """Get whether the application should run in dry-run mode."""
        return self.config.processing.dry_run

    def get_max_videos_per_channel(self) -> int:
        """Get the maximum number of videos to check per channel."""
        return self.config.processing.max_videos_per_channel

    def get_stake_info(self) -> dict[str, Any] | None:
        """Get stake information for reporting and identification."""
        return self.config.stake_info.dict()

    def is_channel_enabled(self, channel_id: str) -> bool:
        """Check if a specific channel is enabled for processing."""
        channel = self.config.get_channel_by_id(channel_id)
        return channel is not None and channel.enabled

    def get_retry_settings(self) -> RetrySettings:
        """Get retry configuration for API operations."""
        return self.config.retry_settings

    def get_logging_config(self) -> LoggingConfig:
        """Get logging configuration."""
        return self.config.logging

    def reload(self) -> None:
        """Reload configuration from source."""
        self._config = None
        self._load_config()

    def get_youtube_api_config(self) -> dict[str, Any]:
        """Get YouTube API configuration."""
        return self.config.youtube_api.dict()

    def get_credentials_file(self) -> str | None:
        """Get the path to the OAuth2 credentials file."""
        return self.config.youtube_api.credentials_file

    def get_token_file(self) -> str | None:
        """Get the path to the stored access token file."""
        return self.config.youtube_api.token_file

    def get_oauth_scopes(self) -> list[str]:
        """Get the required OAuth2 scopes."""
        return self.config.youtube_api.scopes
