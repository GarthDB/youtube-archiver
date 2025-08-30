"""Use case for validating application configuration."""

from __future__ import annotations

from youtube_archiver.domain.services.configuration_provider import ConfigurationProvider


class ValidateConfigUseCase:
    """
    Use case for validating the application configuration.
    
    This use case performs comprehensive validation of the configuration
    including channel accessibility, API connectivity, and settings validation.
    """

    def __init__(self, config_provider: ConfigurationProvider) -> None:
        """
        Initialize the validation use case.
        
        Args:
            config_provider: Configuration provider to validate
        """
        self.config_provider = config_provider

    def execute(self) -> list[str]:
        """
        Execute configuration validation.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []

        try:
            # Validate basic configuration loading
            channels = self.config_provider.get_channels()
            if not channels:
                errors.append("No channels configured")

            # Validate processing settings
            age_threshold = self.config_provider.get_age_threshold_hours()
            if age_threshold < 1 or age_threshold > 168:  # 1 hour to 1 week
                errors.append(f"Invalid age threshold: {age_threshold} hours (must be 1-168)")

            target_visibility = self.config_provider.get_target_visibility()
            if target_visibility not in ["unlisted", "private"]:
                errors.append(f"Invalid target visibility: {target_visibility}")

            max_videos = self.config_provider.get_max_videos_per_channel()
            if max_videos < 1 or max_videos > 200:
                errors.append(f"Invalid max videos per channel: {max_videos} (must be 1-200)")

            # Validate channel configurations
            for channel in channels:
                if not channel.channel_id.startswith(("UC", "UU", "UL")):
                    errors.append(f"Invalid channel ID format: {channel.channel_id}")
                
                if len(channel.channel_id) != 24:
                    errors.append(f"Invalid channel ID length: {channel.channel_id}")

            # Validate retry settings
            retry_settings = self.config_provider.get_retry_settings()
            max_attempts = retry_settings.get("max_attempts", 0)
            if max_attempts < 1 or max_attempts > 10:
                errors.append(f"Invalid max retry attempts: {max_attempts} (must be 1-10)")

            # Validate logging configuration
            logging_config = self.config_provider.get_logging_config()
            log_level = logging_config.get("level", "").upper()
            valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
            if log_level not in valid_levels:
                errors.append(f"Invalid log level: {log_level} (must be one of {valid_levels})")

        except Exception as e:
            errors.append(f"Configuration validation failed: {e}")

        return errors

    def validate_channel_access(self, channel_id: str) -> str | None:
        """
        Validate access to a specific channel.
        
        Args:
            channel_id: YouTube channel ID to validate
            
        Returns:
            Error message if validation fails, None if successful
            
        Note:
            This is a placeholder for future implementation that would
            actually test API access to the channel.
        """
        # TODO: Implement actual channel access validation
        # This would require YouTube API integration
        if not channel_id or len(channel_id) != 24:
            return f"Invalid channel ID: {channel_id}"
        
        if not channel_id.startswith(("UC", "UU", "UL")):
            return f"Invalid channel ID format: {channel_id}"
        
        return None

    def validate_api_connectivity(self) -> str | None:
        """
        Validate YouTube API connectivity and authentication.
        
        Returns:
            Error message if validation fails, None if successful
            
        Note:
            This is a placeholder for future implementation that would
            actually test YouTube API connectivity.
        """
        # TODO: Implement actual API connectivity validation
        # This would require YouTube API integration
        return None
