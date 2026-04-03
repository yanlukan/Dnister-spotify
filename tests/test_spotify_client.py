import os
import pytest
from unittest.mock import patch, MagicMock


def test_search_returns_track():
    from src.spotify_client import SpotifyClient
    env = {
        "SPOTIFY_CLIENT_ID": "test",
        "SPOTIFY_CLIENT_SECRET": "test",
        "SPOTIFY_REFRESH_TOKEN": "test",
    }
    with patch.dict(os.environ, env), \
         patch("src.spotify_client.SpotifyOAuth"), \
         patch("src.spotify_client.spotipy.Spotify") as MockSp:
        mock_sp = MockSp.return_value
        mock_sp.search.return_value = {
            "tracks": {"items": [
                {
                    "id": "abc",
                    "name": "Stefania",
                    "uri": "spotify:track:abc",
                    "preview_url": "https://example.com/preview.mp3",
                    "artists": [{"name": "Kalush Orchestra"}],
                    "album": {"name": "Album"},
                }
            ]}
        }
        client = SpotifyClient()
        result = client.search_track("Stefania", "Kalush Orchestra")
        assert result is not None
        assert result["id"] == "abc"


def test_search_returns_none_when_not_found():
    from src.spotify_client import SpotifyClient
    env = {
        "SPOTIFY_CLIENT_ID": "test",
        "SPOTIFY_CLIENT_SECRET": "test",
        "SPOTIFY_REFRESH_TOKEN": "test",
    }
    with patch.dict(os.environ, env), \
         patch("src.spotify_client.SpotifyOAuth"), \
         patch("src.spotify_client.spotipy.Spotify") as MockSp:
        mock_sp = MockSp.return_value
        mock_sp.search.return_value = {"tracks": {"items": []}}
        client = SpotifyClient()
        result = client.search_track("Nonexistent", "Nobody")
        assert result is None
