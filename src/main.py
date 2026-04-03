import logging
import sys

import yaml

from src.spotify_client import SpotifyClient
from src.collector import SongCollector
from src.filter import RussianContentFilter
from src.playlist_builder import PlaylistBuilder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class PlaylistManager:
    """Main orchestrator: collect -> filter -> build -> update playlists."""

    def __init__(
        self,
        config_path: str = "config/playlists.yaml",
        blocklist_path: str = "data/russian_artists_blocklist.json",
    ):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.sp_client = SpotifyClient()
        self.collector = SongCollector(self.sp_client)
        self.content_filter = RussianContentFilter(blocklist_path)
        self.builder = PlaylistBuilder(self.sp_client)
        self.user_id = self.sp_client.get_current_user_id()

    def _get_or_create_playlist(self, name: str, description: str) -> str:
        """Find an existing playlist by name or create a new one. Returns playlist ID."""
        playlists = self.sp_client.get_user_playlists()
        for pl in playlists:
            if pl["name"] == name and pl["owner"]["id"] == self.user_id:
                logger.info(f"Found existing playlist '{name}' ({pl['id']})")
                return pl["id"]

        playlist_id = self.sp_client.create_playlist(self.user_id, name, description)
        return playlist_id

    def run(self) -> None:
        """Execute the full pipeline: collect -> filter -> assign -> update."""
        playlist_configs = self.config["playlists"]

        # 1. Collect all unique genres across playlists
        all_genres = set()
        for cfg in playlist_configs:
            all_genres.update(cfg["genres"])

        collect_config = {
            "source_playlists": self.config.get("source_playlists", []),
            "genres": list(all_genres),
            "seed_artists": self.config.get("seed_artists", []),
        }

        logger.info("=== Starting playlist update ===")

        # 2. Collect tracks
        all_tracks = self.collector.collect_all(collect_config)
        logger.info(f"Collected {len(all_tracks)} unique tracks")

        # 3. Filter Russian content
        allowed_tracks, excluded = self.content_filter.filter_tracks(all_tracks)
        logger.info(
            f"After filtering: {len(allowed_tracks)} allowed, {len(excluded)} excluded"
        )

        # 4. Assign tracks to playlists by energy
        assignments = self.builder.assign_tracks(allowed_tracks, playlist_configs)

        # 5. Update each playlist on Spotify
        for cfg in playlist_configs:
            name = cfg["name"]
            description = cfg["description"]
            tracks = assignments.get(name, [])

            playlist_id = self._get_or_create_playlist(name, description)
            track_uris = [t["uri"] for t in tracks]

            if track_uris:
                self.sp_client.replace_playlist_tracks(playlist_id, track_uris)
                logger.info(f"Updated '{name}' with {len(track_uris)} tracks")
            else:
                logger.warning(f"No tracks assigned to '{name}' -- skipping update")

        logger.info("=== Playlist update complete ===")


def main():
    try:
        manager = PlaylistManager()
        manager.run()
    except Exception as e:
        logger.error(f"Failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
