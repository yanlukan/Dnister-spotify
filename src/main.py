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
        verified_artists_path: str = "data/verified_ukrainian_artists.json",
    ):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.sp_client = SpotifyClient()
        self.collector = SongCollector(self.sp_client)
        self.content_filter = RussianContentFilter(blocklist_path, verified_artists_path)
        self.builder = PlaylistBuilder(self.sp_client)
        self.user_id = self.sp_client.get_current_user_id()

    def _collect_for_playlist(self, cfg: dict) -> list[dict]:
        """Collect tracks for a single playlist using its own config."""
        collect_config = {
            "source_playlists": cfg.get("source_playlists", []),
            "genres": cfg.get("genres", []),
            "search_queries": cfg.get("search_queries", []),
            "seed_artists": cfg.get("seed_artists", []),
        }
        return self.collector.collect_all(collect_config)

    def _collect_general(self, playlist_configs: list[dict]) -> list[dict]:
        """Collect tracks from the global config sources."""
        all_genres = set()
        for cfg in playlist_configs:
            if not cfg.get("dedicated"):
                all_genres.update(cfg.get("genres", []))

        collect_config = {
            "source_playlists": self.config.get("source_playlists", []),
            "genres": list(all_genres),
            "search_queries": self.config.get("search_queries", []),
            "seed_artists": self.config.get("seed_artists", []),
        }
        return self.collector.collect_all(collect_config)

    def run(self) -> None:
        """Execute the full pipeline: collect -> filter -> assign -> update."""
        playlist_configs = self.config["playlists"]
        import random

        logger.info("=== Starting playlist update ===")

        # Split playlists into dedicated (own sources) and general (shared pool)
        dedicated = [cfg for cfg in playlist_configs if cfg.get("dedicated")]
        general = [cfg for cfg in playlist_configs if not cfg.get("dedicated")]

        # Handle dedicated playlists — each gets its own collection
        for cfg in dedicated:
            name = cfg["name"]
            playlist_id = cfg["spotify_id"]
            max_tracks = cfg.get("max_tracks", 50)

            logger.info(f"--- Collecting for dedicated playlist '{name}' ---")
            tracks = self._collect_for_playlist(cfg)
            allowed, excluded = self.content_filter.filter_tracks(tracks)
            logger.info(f"'{name}': {len(allowed)} allowed, {len(excluded)} excluded")

            random.shuffle(allowed)
            track_uris = [t["uri"] for t in allowed[:max_tracks]]

            if track_uris:
                self.sp_client.replace_playlist_tracks(playlist_id, track_uris)
                logger.info(f"Updated '{name}' with {len(track_uris)} tracks")
            else:
                logger.warning(f"No tracks for '{name}' -- skipping update")

        # Handle general playlists — shared pool, distributed
        if general:
            logger.info("--- Collecting for general playlists ---")
            all_tracks = self._collect_general(playlist_configs)
            logger.info(f"Collected {len(all_tracks)} unique tracks")

            allowed_tracks, excluded = self.content_filter.filter_tracks(all_tracks)
            logger.info(
                f"After filtering: {len(allowed_tracks)} allowed, {len(excluded)} excluded"
            )

            assignments = self.builder.assign_tracks(allowed_tracks, general)

            for cfg in general:
                name = cfg["name"]
                playlist_id = cfg["spotify_id"]
                tracks = assignments.get(name, [])
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
