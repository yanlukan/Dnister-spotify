# src/discover.py
"""Discover Ukrainian songs from external sources. No Spotify needed.

Usage: python -m src.discover
"""
import logging
import os
import sys

from dotenv import load_dotenv
load_dotenv()

import yaml

from src.scrapers.hitfm import scrape_hitfm
from src.scrapers.lastfm import scrape_lastfm
from src.scrapers.kworb import scrape_kworb
from src.language.text_check import check_text_language
from src.filter import TrackFilter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)
logger = logging.getLogger(__name__)


def deduplicate(songs: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for song in songs:
        key = (song["artist"].lower(), song["name"].lower())
        if key not in seen:
            seen.add(key)
            unique.append(song)
    return unique


def main():
    logger.info("=== Starting song discovery ===")

    # 1. Scrape external sources
    all_songs = []

    logger.info("--- Scraping Hit FM ---")
    all_songs.extend(scrape_hitfm())

    logger.info("--- Scraping Last.fm ---")
    lastfm_key = os.environ.get("LASTFM_API_KEY", "")
    with open("config/playlists.yaml", "r") as f:
        config = yaml.safe_load(f)
    tags = config.get("lastfm_tags", ["ukrainian"])
    all_songs.extend(scrape_lastfm(api_key=lastfm_key, tags=tags))

    logger.info("--- Scraping kworb.net ---")
    all_songs.extend(scrape_kworb())

    # 2. Deduplicate
    unique_songs = deduplicate(all_songs)
    logger.info(f"Total unique songs: {len(unique_songs)}")

    # 3. Text language filter (no Spotify needed)
    track_filter = TrackFilter()
    new_for_review = 0
    rejected_text = 0
    skipped = 0

    for song in unique_songs:
        name = song["name"]
        artist = song["artist"]

        # Text language check
        text = f"{name} {artist}"
        text_result = check_text_language(text)
        if text_result["language"] == "rus" and text_result["confidence"] > 0.8:
            logger.info(f"Rejected (Russian): {artist} — {name}")
            rejected_text += 1
            continue

        # Use artist+name as ID (no Spotify ID yet)
        song_id = f"{artist}||{name}".lower()
        lang_info = f"{text_result['language']}({text_result['confidence']:.2f})"

        track_info = {
            "id": song_id,
            "name": name,
            "artist": artist,
            "uri": "",  # No Spotify URI yet — resolved at playlist update time
            "source": song["source"],
        }

        result = track_filter.classify(track_info, language_info=lang_info)
        if result == "review":
            new_for_review += 1
        elif result == "skip":
            skipped += 1

    logger.info("=== Discovery complete ===")
    logger.info(f"New for review: {new_for_review}")
    logger.info(f"Already in queue: {skipped}")
    logger.info(f"Rejected (Russian): {rejected_text}")


if __name__ == "__main__":
    main()
