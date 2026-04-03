# src/update_playlists.py
"""Entry point: push whitelisted songs to Spotify playlists.

Usage: python -m src.update_playlists
"""
import logging
import sys

import yaml

from src.spotify_client import SpotifyClient
from src.filter import TrackFilter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)
logger = logging.getLogger(__name__)


def main():
    logger.info("=== Updating Spotify playlists ===")

    with open("config/playlists.yaml", "r") as f:
        config = yaml.safe_load(f)

    playlist_ids = config["playlists"]
    sp = SpotifyClient()
    track_filter = TrackFilter()

    playlists = track_filter.get_whitelist_by_playlist()

    for name, spotify_id in playlist_ids.items():
        uris = playlists.get(name, [])
        if uris:
            sp.replace_playlist(spotify_id, uris)
            logger.info(f"Updated '{name}' with {len(uris)} tracks")
        else:
            logger.warning(f"No whitelisted tracks for '{name}' — skipping")

    logger.info("=== Playlists updated ===")


if __name__ == "__main__":
    main()
