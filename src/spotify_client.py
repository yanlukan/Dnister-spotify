import os
import logging
import requests as http_requests

import spotipy
from spotipy.oauth2 import SpotifyOAuth

logger = logging.getLogger(__name__)


class SpotifyClient:
    """Spotify API client. Only used for search and playlist updates."""

    def __init__(self):
        client_id = os.environ.get("SPOTIFY_CLIENT_ID")
        client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
        refresh_token = os.environ.get("SPOTIFY_REFRESH_TOKEN")

        if not all([client_id, client_secret, refresh_token]):
            raise ValueError(
                "Set SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN"
            )

        self.auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri="http://127.0.0.1:3000/callback",
            scope="playlist-modify-public playlist-modify-private",
        )
        self.auth_manager.refresh_access_token(refresh_token)
        self.sp = spotipy.Spotify(auth_manager=self.auth_manager)
        logger.info("Spotify client initialized")

    def search_track(self, song_name: str, artist_name: str) -> dict | None:
        """Search for a track on Spotify. Returns track dict or None."""
        query = f"{song_name} {artist_name}"
        try:
            results = self.sp.search(q=query, type="track", limit=5, market="UA")
            items = results["tracks"]["items"]
            if not items:
                return None
            for track in items:
                track_artists = [a["name"].lower() for a in track["artists"]]
                if artist_name.lower() in track_artists:
                    return track
            return items[0]
        except Exception as e:
            logger.warning(f"Search failed for '{song_name}' by {artist_name}: {e}")
            return None

    def replace_playlist(self, playlist_id: str, track_uris: list[str]) -> None:
        """Replace all tracks in a playlist using the /items endpoint."""
        token = self.auth_manager.get_access_token(as_dict=False)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        base = "https://api.spotify.com/v1"
        http_requests.put(
            f"{base}/playlists/{playlist_id}/items",
            json={"uris": []},
            headers=headers,
        ).raise_for_status()
        for i in range(0, len(track_uris), 100):
            batch = track_uris[i : i + 100]
            http_requests.post(
                f"{base}/playlists/{playlist_id}/items",
                json={"uris": batch},
                headers=headers,
            ).raise_for_status()
        logger.info(f"Updated playlist {playlist_id} with {len(track_uris)} tracks")
