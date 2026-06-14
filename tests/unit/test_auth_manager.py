"""Unit tests for YouTubeAuthManager."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from youtube_archiver.domain.exceptions import AuthenticationError, ConfigurationError
from youtube_archiver.infrastructure.youtube.auth_manager import YouTubeAuthManager


class TestYouTubeAuthManagerInit:
    """Tests for YouTubeAuthManager initialisation."""

    def test_init_stores_paths_and_scopes(self, tmp_path: Path) -> None:
        """Constructor stores credentials_file, token_file, and scopes as Paths."""
        creds = tmp_path / "credentials.json"
        token = tmp_path / "token.json"
        scopes = ["https://www.googleapis.com/auth/youtube"]

        manager = YouTubeAuthManager(str(creds), str(token), scopes)

        assert manager.credentials_file == creds
        assert manager.token_file == token
        assert manager.scopes == scopes
        assert manager._credentials is None
        assert manager._service is None


class TestRunOAuthFlow:
    """Tests for _run_oauth_flow — the OAuth 2 browser/headless path."""

    def test_missing_credentials_file_raises(self, tmp_path: Path) -> None:
        """Raises ConfigurationError when credentials.json is absent."""
        manager = YouTubeAuthManager(
            credentials_file=str(tmp_path / "missing.json"),
            token_file=str(tmp_path / "token.json"),
            scopes=["https://www.googleapis.com/auth/youtube"],
        )

        with pytest.raises(ConfigurationError, match="credentials file not found"):
            manager._run_oauth_flow()

    def test_browser_flow_success(self, tmp_path: Path) -> None:
        """run_local_server path succeeds and returns credentials."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text("{}")  # must exist

        mock_credentials = Mock()
        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = mock_credentials

        manager = YouTubeAuthManager(
            credentials_file=str(creds_file),
            token_file=str(tmp_path / "token.json"),
            scopes=["https://www.googleapis.com/auth/youtube"],
        )

        with patch(
            "youtube_archiver.infrastructure.youtube.auth_manager.InstalledAppFlow"
            ".from_client_secrets_file",
            return_value=mock_flow,
        ):
            result = manager._run_oauth_flow()

        assert result is mock_credentials
        mock_flow.run_local_server.assert_called_once_with(port=0, open_browser=True)

    def test_headless_fallback_when_local_server_fails(self, tmp_path: Path) -> None:
        """When run_local_server raises, falls back to manual code exchange."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text("{}")

        mock_credentials = Mock()
        mock_flow = MagicMock()
        mock_flow.run_local_server.side_effect = OSError("no display")
        mock_flow.authorization_url.return_value = ("https://auth.example.com", "state")
        mock_flow.credentials = mock_credentials

        manager = YouTubeAuthManager(
            credentials_file=str(creds_file),
            token_file=str(tmp_path / "token.json"),
            scopes=["https://www.googleapis.com/auth/youtube"],
        )

        with (
            patch(
                "youtube_archiver.infrastructure.youtube.auth_manager.InstalledAppFlow"
                ".from_client_secrets_file",
                return_value=mock_flow,
            ),
            patch("builtins.input", return_value="fake-auth-code"),
        ):
            result = manager._run_oauth_flow()

        # Verify the manual exchange happened
        mock_flow.authorization_url.assert_called_once_with(prompt="consent")
        mock_flow.fetch_token.assert_called_once_with(code="fake-auth-code")
        assert result is mock_credentials

    def test_headless_fallback_prints_url(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Headless fallback prints the authorization URL to stdout."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text("{}")

        mock_flow = MagicMock()
        mock_flow.run_local_server.side_effect = OSError("no display")
        mock_flow.authorization_url.return_value = (
            "https://auth.example.com/oauth",
            "s",
        )
        mock_flow.credentials = Mock()

        manager = YouTubeAuthManager(
            credentials_file=str(creds_file),
            token_file=str(tmp_path / "token.json"),
            scopes=["https://www.googleapis.com/auth/youtube"],
        )

        with (
            patch(
                "youtube_archiver.infrastructure.youtube.auth_manager.InstalledAppFlow"
                ".from_client_secrets_file",
                return_value=mock_flow,
            ),
            patch("builtins.input", return_value="code"),
        ):
            manager._run_oauth_flow()

        captured = capsys.readouterr()
        assert "https://auth.example.com/oauth" in captured.out

    def test_oauth_flow_failure_raises_auth_error(self, tmp_path: Path) -> None:
        """An unexpected exception from InstalledAppFlow is wrapped in AuthenticationError."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text("{}")

        manager = YouTubeAuthManager(
            credentials_file=str(creds_file),
            token_file=str(tmp_path / "token.json"),
            scopes=["https://www.googleapis.com/auth/youtube"],
        )

        with patch(
            "youtube_archiver.infrastructure.youtube.auth_manager.InstalledAppFlow"
            ".from_client_secrets_file",
            side_effect=ValueError("bad secrets file"),
        ):
            with pytest.raises(AuthenticationError, match="OAuth2 flow failed"):
                manager._run_oauth_flow()


class TestIsAuthenticated:
    """Tests for the is_authenticated property."""

    def test_is_authenticated_returns_false_when_no_credentials(
        self, tmp_path: Path
    ) -> None:
        """Returns False when token file absent and credentials file absent."""
        manager = YouTubeAuthManager(
            credentials_file=str(tmp_path / "missing_creds.json"),
            token_file=str(tmp_path / "missing_token.json"),
            scopes=["https://www.googleapis.com/auth/youtube"],
        )

        assert manager.is_authenticated is False

    def test_is_authenticated_returns_false_when_get_credentials_raises(
        self, tmp_path: Path
    ) -> None:
        """is_authenticated swallows exceptions and returns False."""
        manager = YouTubeAuthManager(
            credentials_file=str(tmp_path / "missing_creds.json"),
            token_file=str(tmp_path / "missing_token.json"),
            scopes=["https://www.googleapis.com/auth/youtube"],
        )

        # Even with a mocked internal raise, the property is safe
        with patch.object(
            type(manager),
            "_get_credentials",
            side_effect=AuthenticationError("no token"),
        ):
            assert manager.is_authenticated is False


class TestSaveCredentials:
    """Tests for _save_credentials."""

    def test_save_credentials_creates_parent_dirs(self, tmp_path: Path) -> None:
        """_save_credentials creates parent directories if they don't exist."""
        nested_token = tmp_path / "sub" / "dir" / "token.json"
        manager = YouTubeAuthManager(
            credentials_file=str(tmp_path / "creds.json"),
            token_file=str(nested_token),
            scopes=[],
        )

        mock_creds = MagicMock()
        mock_creds.to_json.return_value = '{"token": "fake"}'
        manager._credentials = mock_creds  # type: ignore[assignment]

        manager._save_credentials()

        assert nested_token.exists()
        assert nested_token.read_text() == '{"token": "fake"}'

    def test_save_credentials_is_noop_without_credentials(self, tmp_path: Path) -> None:
        """_save_credentials does nothing when _credentials is None."""
        token_path = tmp_path / "token.json"
        manager = YouTubeAuthManager(
            credentials_file=str(tmp_path / "creds.json"),
            token_file=str(token_path),
            scopes=[],
        )
        manager._save_credentials()  # should not raise or create file
        assert not token_path.exists()
