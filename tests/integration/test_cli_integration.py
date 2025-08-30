"""Integration tests for CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from youtube_archiver.cli.main import cli
from youtube_archiver.domain.models.processing import BatchProcessingResult, ChannelProcessingResult


class TestCLIIntegration:
    """Integration tests for CLI commands."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """Create a CLI runner for testing."""
        return CliRunner()

    def test_cli_help(self, cli_runner: CliRunner) -> None:
        """Test CLI help command."""
        result = cli_runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "YouTube Archiver" in result.output
        assert "process" in result.output
        assert "auth" in result.output
        assert "validate" in result.output
        assert "summary" in result.output

    def test_cli_version(self, cli_runner: CliRunner) -> None:
        """Test CLI version command."""
        result = cli_runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_validate_command_success(
        self, 
        cli_runner: CliRunner, 
        temp_config_file: Path,
    ) -> None:
        """Test validate command with valid configuration."""
        with patch("youtube_archiver.cli.main.get_youtube_auth_manager") as mock_get_auth:
            mock_auth = Mock()
            mock_auth.is_authenticated = True
            mock_auth.get_user_info.return_value = {
                "authenticated": True,
                "has_channel": True,
                "channel_title": "Test Channel",
                "channel_id": "UCTestChannelID00000001",
                "subscriber_count": "100",
                "video_count": "50",
            }
            mock_get_auth.return_value = mock_auth

            with patch("youtube_archiver.cli.main.asyncio.run") as mock_run:
                mock_run.return_value = None

                result = cli_runner.invoke(cli, [
                    "--config", str(temp_config_file),
                    "validate"
                ])

                assert result.exit_code == 0
                assert "Configuration Check" in result.output
                assert "Found 3 configured channels" in result.output

    def test_validate_command_config_error(self, cli_runner: CliRunner) -> None:
        """Test validate command with configuration error."""
        result = cli_runner.invoke(cli, [
            "--config", "nonexistent.yml",
            "validate"
        ])
        
        assert result.exit_code == 1
        assert "Configuration Error" in result.output

    def test_validate_command_not_authenticated(
        self, 
        cli_runner: CliRunner, 
        temp_config_file: Path,
    ) -> None:
        """Test validate command when not authenticated."""
        with patch("youtube_archiver.cli.main.get_youtube_auth_manager") as mock_get_auth:
            mock_auth = Mock()
            mock_auth.is_authenticated = False
            mock_get_auth.return_value = mock_auth

            result = cli_runner.invoke(cli, [
                "--config", str(temp_config_file),
                "validate"
            ])

            assert result.exit_code == 0
            assert "Not authenticated" in result.output

    def test_auth_status_command_authenticated(
        self, 
        cli_runner: CliRunner, 
        temp_config_file: Path,
    ) -> None:
        """Test auth status command when authenticated."""
        with patch("youtube_archiver.cli.main.get_youtube_auth_manager") as mock_get_auth:
            mock_auth = Mock()
            mock_auth.is_authenticated = True
            mock_auth.get_user_info.return_value = {
                "authenticated": True,
                "has_channel": True,
                "channel_title": "Test Channel",
                "channel_id": "UCTestChannelID00000001",
            }
            mock_get_auth.return_value = mock_auth

            result = cli_runner.invoke(cli, [
                "--config", str(temp_config_file),
                "auth", "status"
            ])

            assert result.exit_code == 0
            assert "Authenticated" in result.output
            assert "Test Channel" in result.output

    def test_auth_status_command_not_authenticated(
        self, 
        cli_runner: CliRunner, 
        temp_config_file: Path,
    ) -> None:
        """Test auth status command when not authenticated."""
        with patch("youtube_archiver.cli.main.get_youtube_auth_manager") as mock_get_auth:
            mock_auth = Mock()
            mock_auth.is_authenticated = False
            mock_get_auth.return_value = mock_auth

            result = cli_runner.invoke(cli, [
                "--config", str(temp_config_file),
                "auth", "status"
            ])

            assert result.exit_code == 0
            assert "Not authenticated" in result.output

    def test_auth_setup_command(
        self, 
        cli_runner: CliRunner, 
        temp_config_file: Path,
    ) -> None:
        """Test auth setup command."""
        with patch("youtube_archiver.cli.main.get_youtube_auth_manager") as mock_get_auth:
            mock_auth = Mock()
            mock_auth.get_user_info.return_value = {
                "authenticated": True,
                "has_channel": True,
                "channel_title": "Test Channel",
                "channel_id": "UCTestChannelID00000001",
            }
            mock_get_auth.return_value = mock_auth

            result = cli_runner.invoke(cli, [
                "--config", str(temp_config_file),
                "auth", "setup"
            ])

            assert result.exit_code == 0
            assert "Authentication Setup" in result.output

    def test_auth_reset_command(
        self, 
        cli_runner: CliRunner, 
        temp_config_file: Path,
    ) -> None:
        """Test auth reset command."""
        with patch("youtube_archiver.cli.main.get_youtube_auth_manager") as mock_get_auth:
            mock_auth = Mock()
            mock_auth.revoke_credentials.return_value = None
            mock_get_auth.return_value = mock_auth

            result = cli_runner.invoke(cli, [
                "--config", str(temp_config_file),
                "auth", "reset"
            ], input="y\n")  # Confirm the reset

            assert result.exit_code == 0
            assert "Authentication reset successfully" in result.output

    def test_summary_command(
        self, 
        cli_runner: CliRunner, 
        temp_config_file: Path,
    ) -> None:
        """Test summary command."""
        mock_summary = {
            "total_channels": 3,
            "enabled_channels": 2,
            "total_videos": 10,
            "eligible_videos": 5,
            "by_channel": {
                "UCTestChannelID00000001": {
                    "name": "Test Ward 1",
                    "total_videos": 5,
                    "eligible_videos": 3,
                    "public_videos": 4,
                    "live_videos": 5,
                    "status": "ready",
                },
                "UCTestChannelID00000002": {
                    "name": "Test Ward 2",
                    "total_videos": 5,
                    "eligible_videos": 2,
                    "public_videos": 3,
                    "live_videos": 5,
                    "status": "ready",
                },
            },
            "generated_at": "2024-01-01T12:00:00",
        }

        with patch("youtube_archiver.cli.main.get_archiving_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_eligible_videos_summary.return_value = mock_summary
            mock_get_service.return_value = mock_service

            result = cli_runner.invoke(cli, [
                "--config", str(temp_config_file),
                "summary"
            ])

            assert result.exit_code == 0
            assert "Video Summary" in result.output
            assert "Test Ward 1" in result.output
            assert "Test Ward 2" in result.output

    def test_process_command_dry_run(
        self, 
        cli_runner: CliRunner, 
        temp_config_file: Path,
    ) -> None:
        """Test process command with dry-run flag."""
        # Create mock batch result
        mock_result = BatchProcessingResult()
        mock_channel_result = ChannelProcessingResult(
            channel_id="UCTestChannelID00000001",
            channel_name="Test Ward 1",
        )
        mock_result.add_channel_result(mock_channel_result)
        mock_result.complete()

        with patch("youtube_archiver.cli.main.get_archiving_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.dry_run_all_channels.return_value = mock_result
            mock_get_service.return_value = mock_service

            result = cli_runner.invoke(cli, [
                "--config", str(temp_config_file),
                "process", "--dry-run"
            ])

            assert result.exit_code == 0
            assert "DRY RUN MODE" in result.output
            assert "Processing Results" in result.output

    def test_process_command_specific_channels(
        self, 
        cli_runner: CliRunner, 
        temp_config_file: Path,
    ) -> None:
        """Test process command with specific channels."""
        # Create mock batch result
        mock_result = BatchProcessingResult()
        mock_channel_result = ChannelProcessingResult(
            channel_id="UCTestChannelID00000001",
            channel_name="Test Ward 1",
        )
        mock_result.add_channel_result(mock_channel_result)
        mock_result.complete()

        with patch("youtube_archiver.cli.main.get_archiving_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.process_specific_channels.return_value = mock_result
            mock_get_service.return_value = mock_service

            result = cli_runner.invoke(cli, [
                "--config", str(temp_config_file),
                "process", 
                "--channels", "UCTestChannelID00000001"
            ])

            assert result.exit_code == 0
            assert "Processing specific channels" in result.output

    def test_process_command_all_channels(
        self, 
        cli_runner: CliRunner, 
        temp_config_file: Path,
    ) -> None:
        """Test process command for all channels."""
        # Create mock batch result
        mock_result = BatchProcessingResult()
        mock_channel_result = ChannelProcessingResult(
            channel_id="UCTestChannelID00000001",
            channel_name="Test Ward 1",
        )
        mock_result.add_channel_result(mock_channel_result)
        mock_result.complete()

        with patch("youtube_archiver.cli.main.get_archiving_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.process_all_channels.return_value = mock_result
            mock_get_service.return_value = mock_service

            result = cli_runner.invoke(cli, [
                "--config", str(temp_config_file),
                "process"
            ])

            assert result.exit_code == 0
            assert "Processing all enabled channels" in result.output

    def test_verbose_flag(
        self, 
        cli_runner: CliRunner, 
        temp_config_file: Path,
    ) -> None:
        """Test verbose flag functionality."""
        with patch("youtube_archiver.cli.main.get_youtube_auth_manager") as mock_get_auth:
            mock_auth = Mock()
            mock_auth.is_authenticated = False
            mock_get_auth.return_value = mock_auth

            result = cli_runner.invoke(cli, [
                "--config", str(temp_config_file),
                "--verbose",
                "auth", "status"
            ])

            assert result.exit_code == 0
            assert f"Using configuration: {temp_config_file}" in result.output

    def test_invalid_config_path(self, cli_runner: CliRunner) -> None:
        """Test CLI with invalid config path."""
        result = cli_runner.invoke(cli, [
            "--config", "nonexistent.yml",
            "auth", "status"
        ])
        
        assert result.exit_code == 2  # Click validation error
        assert "does not exist" in result.output

    def test_auth_help(self, cli_runner: CliRunner, temp_config_file: Path) -> None:
        """Test auth command help."""
        result = cli_runner.invoke(cli, [
            "--config", str(temp_config_file),
            "auth", "--help"
        ])
        
        assert result.exit_code == 0
        assert "Authentication management commands" in result.output
        assert "setup" in result.output
        assert "status" in result.output
        assert "reset" in result.output
