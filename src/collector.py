import logging

logger = logging.getLogger(__name__)


class SongCollector:
    """Collects tracks from multiple Spotify sources."""

    def __init__(self, spotify_client):
        self.sp = spotify_client

    def collect_from_playlist(self, playlist_id: str) -> list[dict]:
        """Fetch all tracks from a playlist. Returns empty list on access error."""
        try:
            tracks = self.sp.get_playlist_tracks(playlist_id)
            logger.info(f"Collected {len(tracks)} tracks from playlist {playlist_id}")
            return tracks
        except Exception as e:
            logger.warning(f"Could not access playlist {playlist_id}: {e}")
            return []

    def collect_from_genre(self, genre: str) -> list[dict]:
        """Search for tracks by genre."""
        tracks = self.sp.search_tracks(q=f"genre:{genre}", limit=50)
        logger.info(f"Collected {len(tracks)} tracks for genre '{genre}'")
        return tracks

    def collect_from_search(self, query: str) -> list[dict]:
        """Search for tracks by free-text query."""
        tracks = self.sp.search_tracks(q=query, limit=50)
        logger.info(f"Collected {len(tracks)} tracks for query '{query}'")
        return tracks

    def collect_from_artist(self, artist_id: str) -> list[dict]:
        """Get top tracks for an artist."""
        tracks = self.sp.get_artist_top_tracks(artist_id)
        logger.info(f"Collected {len(tracks)} tracks from artist {artist_id}")
        return tracks

    def collect_all(self, config: dict) -> list[dict]:
        """Collect tracks from all configured sources and deduplicate.

        Config should have keys: source_playlists, genres, seed_artists
        """
        all_tracks: dict[str, dict] = {}  # track_id -> track

        # Source playlists
        for playlist_id in config.get("source_playlists", []):
            for track in self.collect_from_playlist(playlist_id):
                all_tracks[track["id"]] = track

        # Genre searches
        for genre in config.get("genres", []):
            for track in self.collect_from_genre(genre):
                all_tracks[track["id"]] = track

        # Additional search queries
        for query in config.get("search_queries", []):
            for track in self.collect_from_search(query):
                all_tracks[track["id"]] = track

        # Seed artists
        for artist_id in config.get("seed_artists", []):
            for track in self.collect_from_artist(artist_id):
                all_tracks[track["id"]] = track

        tracks = list(all_tracks.values())
        logger.info(f"Total collected: {len(tracks)} unique tracks")
        return tracks
