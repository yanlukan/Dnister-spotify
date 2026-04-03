import os
from unittest.mock import patch, MagicMock
import pytest


def test_spotify_client_initializes_with_env_vars():
    """SpotifyClient should initialize Spotipy with credentials from env vars."""
    env = {
        "SPOTIFY_CLIENT_ID": "test_id",
        "SPOTIFY_CLIENT_SECRET": "test_secret",
        "SPOTIFY_REFRESH_TOKEN": "test_token",
    }
    with patch.dict(os.environ, env):
        with patch("src.spotify_client.SpotifyOAuth") as mock_oauth:
            with patch("src.spotify_client.spotipy.Spotify") as mock_spotify:
                from src.spotify_client import SpotifyClient

                client = SpotifyClient()
                assert client.sp is not None


def test_spotify_client_raises_without_credentials():
    """SpotifyClient should raise ValueError if credentials are missing."""
    with patch.dict(os.environ, {}, clear=True):
        from src.spotify_client import SpotifyClient

        with pytest.raises(ValueError, match="Missing Spotify credentials"):
            SpotifyClient()
