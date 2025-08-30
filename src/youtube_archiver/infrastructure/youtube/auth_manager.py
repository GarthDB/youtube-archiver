"""YouTube API authentication manager."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource

from youtube_archiver.domain.exceptions import AuthenticationError, ConfigurationError


class YouTubeAuthManager:
    """
    Manages YouTube API authentication using OAuth2.
    
    This class handles the OAuth2 flow, token storage, and refresh logic
    for accessing the YouTube Data API v3.
    """

    def __init__(
        self,
        credentials_file: str | Path,
        token_file: str | Path,
        scopes: list[str],
    ) -> None:
        """
        Initialize the YouTube authentication manager.
        
        Args:
            credentials_file: Path to OAuth2 client credentials JSON file
            token_file: Path to store/load access tokens
            scopes: List of OAuth2 scopes required
            
        Raises:
            ConfigurationError: If credentials file is missing or invalid
        """
        self.credentials_file = Path(credentials_file)
        self.token_file = Path(token_file)
        self.scopes = scopes
        self._credentials: Credentials | None = None
        self._service: Resource | None = None

    def get_authenticated_service(self) -> Resource:
        """
        Get an authenticated YouTube API service instance.
        
        Returns:
            Authenticated YouTube Data API v3 service
            
        Raises:
            AuthenticationError: If authentication fails
            ConfigurationError: If credentials are invalid
        """
        if self._service is None:
            credentials = self._get_credentials()
            self._service = build("youtube", "v3", credentials=credentials)
        
        return self._service

    def _get_credentials(self) -> Credentials:
        """
        Get valid OAuth2 credentials, handling refresh and initial auth flow.
        
        Returns:
            Valid OAuth2 credentials
            
        Raises:
            AuthenticationError: If authentication fails
            ConfigurationError: If credentials file is missing or invalid
        """
        if self._credentials and self._credentials.valid:
            return self._credentials

        # Try to load existing token
        if self.token_file.exists():
            try:
                self._credentials = Credentials.from_authorized_user_file(  # type: ignore[no-untyped-call]
                    str(self.token_file), self.scopes
                )
            except Exception as e:
                raise AuthenticationError(
                    f"Failed to load stored credentials: {e}"
                ) from e

        # Refresh expired token
        if self._credentials and self._credentials.expired and self._credentials.refresh_token:
            try:
                self._credentials.refresh(Request())  # type: ignore[no-untyped-call]
                self._save_credentials()
            except Exception as e:
                raise AuthenticationError(
                    f"Failed to refresh credentials: {e}"
                ) from e

        # Run OAuth2 flow if no valid credentials
        if not self._credentials or not self._credentials.valid:
            self._credentials = self._run_oauth_flow()
            self._save_credentials()

        return self._credentials

    def _run_oauth_flow(self) -> Credentials:
        """
        Run the OAuth2 authorization flow.
        
        Returns:
            New OAuth2 credentials
            
        Raises:
            ConfigurationError: If credentials file is missing or invalid
            AuthenticationError: If OAuth2 flow fails
        """
        if not self.credentials_file.exists():
            raise ConfigurationError(
                f"OAuth2 credentials file not found: {self.credentials_file}\n"
                "Please download your credentials.json file from Google Cloud Console."
            )

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_file), self.scopes
            )
            
            # Try to run local server flow, fallback to console flow
            try:
                credentials = flow.run_local_server(port=0, open_browser=True)
            except Exception:
                # Fallback for headless environments
                credentials = flow.run_console()
                
            return credentials  # type: ignore[no-any-return]
            
        except Exception as e:
            raise AuthenticationError(
                f"OAuth2 flow failed: {e}\n"
                "Please check your credentials file and internet connection."
            ) from e

    def _save_credentials(self) -> None:
        """Save credentials to token file."""
        if not self._credentials:
            return

        try:
            # Ensure token directory exists
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save credentials
            with open(self.token_file, "w", encoding="utf-8") as f:
                f.write(self._credentials.to_json())  # type: ignore[no-untyped-call]
                
        except Exception as e:
            # Don't fail if we can't save, just warn
            print(f"Warning: Could not save credentials to {self.token_file}: {e}")

    def revoke_credentials(self) -> None:
        """
        Revoke stored credentials and remove token file.
        
        This is useful for testing or when switching accounts.
        """
        if self._credentials:
            try:
                # Note: revoke method may not be available on all credential types
                if hasattr(self._credentials, 'revoke'):
                    self._credentials.revoke(Request())  # type: ignore[no-untyped-call]
            except Exception:
                pass  # Ignore revocation errors

        # Remove token file
        if self.token_file.exists():
            try:
                self.token_file.unlink()
            except Exception:
                pass  # Ignore file removal errors

        # Clear cached credentials and service
        self._credentials = None
        self._service = None

    def get_user_info(self) -> dict[str, Any]:
        """
        Get information about the authenticated user.
        
        Returns:
            Dictionary with user information
            
        Raises:
            AuthenticationError: If not authenticated or API call fails
        """
        try:
            service = self.get_authenticated_service()
            
            # Get channel info for the authenticated user
            request = service.channels().list(
                part="snippet,statistics",
                mine=True
            )
            response = request.execute()
            
            if not response.get("items"):
                return {
                    "authenticated": True,
                    "has_channel": False,
                    "message": "Authenticated but no YouTube channel found"
                }
            
            channel = response["items"][0]
            return {
                "authenticated": True,
                "has_channel": True,
                "channel_id": channel["id"],
                "channel_title": channel["snippet"]["title"],
                "subscriber_count": channel["statistics"].get("subscriberCount", "0"),
                "video_count": channel["statistics"].get("videoCount", "0"),
            }
            
        except Exception as e:
            raise AuthenticationError(f"Failed to get user info: {e}") from e

    def test_api_access(self) -> bool:
        """
        Test if we have valid API access.
        
        Returns:
            True if API access is working, False otherwise
        """
        try:
            user_info = self.get_user_info()
            return bool(user_info.get("authenticated", False))
        except Exception:
            return False

    @property
    def is_authenticated(self) -> bool:
        """Check if we have valid authentication."""
        try:
            credentials = self._get_credentials()
            return bool(credentials.valid)
        except Exception:
            return False
