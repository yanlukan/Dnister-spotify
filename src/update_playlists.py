# src/update_playlists.py
"""Search Spotify for whitelisted songs and update playlists.

This is the ONLY step that talks to Spotify.
Songs not found on Spotify are skipped silently.

Usage: python -m src.update_playlists
"""
import json
import logging
import sys
import time

from dotenv import load_dotenv
load_dotenv()

import yaml

from src.spotify_client import SpotifyClient

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

    with open("data/whitelist.json", "r", encoding="utf-8") as f:
        whitelist = json.load(f)

    playlist_ids = config["playlists"]
    sp = SpotifyClient()

    # Group whitelisted songs by playlist
    playlists: dict[str, list[dict]] = {}
    for track_id, info in whitelist["tracks"].items():
        playlist = info.get("playlist", "")
        if playlist:
            playlists.setdefault(playlist, []).append(info)

    # For each playlist, search Spotify for each song and collect URIs
    for name, spotify_id in playlist_ids.items():
        songs = playlists.get(name, [])
        if not songs:
            logger.info(f"'{name}': no songs — skipping")
            continue

        logger.info(f"'{name}': searching Spotify for {len(songs)} songs...")
        uris = []
        not_found = 0

        for song in songs:
            # If we already have a Spotify URI, use it
            if song.get("uri") and song["uri"].startswith("spotify:track:"):
                uris.append(song["uri"])
                continue

            # Otherwise search Spotify
            time.sleep(0.3)
            track = sp.search_track(song["name"], song["artist"])
            if track:
                uris.append(track["uri"])
                logger.info(f"  Found: {song['artist']} — {song['name']}")
            else:
                not_found += 1
                logger.info(f"  Not on Spotify: {song['artist']} — {song['name']}")

        if uris:
            sp.replace_playlist(spotify_id, uris)
            logger.info(f"Updated '{name}' with {len(uris)} tracks ({not_found} not found)")
        else:
            logger.warning(f"No tracks found for '{name}'")

    logger.info("=== Playlists updated ===")


if __name__ == "__main__":
    main()
