import os
import logging
from typing import Optional

import spotipy
from spotipy.oauth2 import SpotifyOAuth

logger = logging.getLogger(__name__)


class SpotifyClient:
    """Wrapper around Spotipy for authenticated Spotify API access."""

    SCOPES = "playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private"

    def __init__(self):
        client_id = os.environ.get("SPOTIFY_CLIENT_ID")
        client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
        refresh_token = os.environ.get("SPOTIFY_REFRESH_TOKEN")

        if not all([client_id, client_secret, refresh_token]):
            raise ValueError(
                "Missing Spotify credentials. Set SPOTIFY_CLIENT_ID, "
                "SPOTIFY_CLIENT_SECRET, and SPOTIFY_REFRESH_TOKEN env vars."
            )

        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri="http://127.0.0.1:3000/callback",
            scope=self.SCOPES,
        )
        # Inject the refresh token directly
        auth_manager.refresh_access_token(refresh_token)

        self.sp = spotipy.Spotify(auth_manager=auth_manager)
        logger.info("Spotify client initialized successfully")

    def get_playlist_tracks(self, playlist_id: str) -> list[dict]:
        """Fetch all tracks from a playlist."""
        tracks = []
        results = self.sp.playlist_tracks(playlist_id)
        while results:
            for item in results["items"]:
                if item["track"] is not None:
                    tracks.append(item["track"])
            results = self.sp.next(results) if results["next"] else None
        return tracks

    def search_tracks(self, query: str, limit: int = 10) -> list[dict]:
        """Search for tracks by query string. Dev mode caps limit at 10."""
        results = self.sp.search(q=query, type="track", limit=min(limit, 10), market="UA")
        return results["tracks"]["items"]

    def get_artist(self, artist_id: str) -> dict:
        """Get artist details by ID."""
        return self.sp.artist(artist_id)

    def get_artists(self, artist_ids: list[str]) -> list[dict]:
        """Get multiple artists in one call (max 50)."""
        results = self.sp.artists(artist_ids)
        return results["artists"]

    def get_artist_top_tracks(self, artist_id: str, market: str = "UA") -> list[dict]:
        """Get an artist's top tracks in a market."""
        results = self.sp.artist_top_tracks(artist_id, country=market)
        return results["tracks"]

    def get_audio_features(self, track_ids: list[str]) -> list[Optional[dict]]:
        """Get audio features for multiple tracks (max 100)."""
        return self.sp.audio_features(track_ids)

    def replace_playlist_tracks(self, playlist_id: str, track_uris: list[str]) -> None:
        """Replace all tracks in a playlist using the non-deprecated /items endpoint."""
        import requests

        # Clear playlist first
        self._api_put(f"playlists/{playlist_id}/items", {"uris": []})

        # Add tracks in batches of 100
        for i in range(0, len(track_uris), 100):
            batch = track_uris[i : i + 100]
            self._api_post(f"playlists/{playlist_id}/items", {"uris": batch})

        logger.info(f"Replaced playlist {playlist_id} with {len(track_uris)} tracks")

    def _api_post(self, endpoint: str, data: dict) -> dict:
        """Make a POST request to the Spotify API."""
        import requests
        token = self.sp.auth_manager.get_access_token(as_dict=False)
        resp = requests.post(
            f"https://api.spotify.com/v1/{endpoint}",
            json=data,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    def _api_put(self, endpoint: str, data: dict) -> dict:
        """Make a PUT request to the Spotify API."""
        import requests
        token = self.sp.auth_manager.get_access_token(as_dict=False)
        resp = requests.put(
            f"https://api.spotify.com/v1/{endpoint}",
            json=data,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    def create_playlist(self, user_id: str, name: str, description: str) -> str:
        """Create a new playlist and return its ID."""
        result = self.sp.user_playlist_create(
            user_id, name, public=True, description=description
        )
        logger.info(f"Created playlist '{name}' with ID {result['id']}")
        return result["id"]

    def get_current_user_id(self) -> str:
        """Get the authenticated user's Spotify ID."""
        return self.sp.current_user()["id"]

    def get_user_playlists(self) -> list[dict]:
        """Get all playlists owned by the current user."""
        playlists = []
        results = self.sp.current_user_playlists()
        while results:
            playlists.extend(results["items"])
            results = self.sp.next(results) if results["next"] else None
        return playlists
