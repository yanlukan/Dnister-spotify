# src/discover.py
"""Entry point: discover Ukrainian songs and queue for review.

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
from src.language.audio_check import check_audio_language
from src.spotify_client import SpotifyClient
from src.filter import TrackFilter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)
logger = logging.getLogger(__name__)


def deduplicate(songs: list[dict]) -> list[dict]:
    """Deduplicate by (artist, name)."""
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

    # 3. Initialize Spotify + filter
    sp = SpotifyClient()
    track_filter = TrackFilter()

    new_for_review = 0
    skipped = 0
    rejected_text = 0
    rejected_audio = 0
    not_on_spotify = 0

    import time
    total = len(unique_songs)

    for i, song in enumerate(unique_songs):
        name = song["name"]
        artist = song["artist"]

        if (i + 1) % 10 == 0:
            logger.info(f"Progress: {i + 1}/{total}")

        # 4. Text language check (fast pre-filter)
        text = f"{name} {artist}"
        text_result = check_text_language(text)
        if text_result["language"] == "rus" and text_result["confidence"] > 0.8:
            logger.info(f"Rejected (text=rus): {artist} — {name}")
            rejected_text += 1
            continue

        # 5. Find on Spotify (with rate limit delay)
        time.sleep(0.5)
        track = sp.search_track(name, artist)
        if not track:
            not_on_spotify += 1
            continue

        # 6. Audio language check (skip if SKIP_AUDIO_CHECK is set — slow on first run)
        audio_lang = "skipped"
        audio_conf = 0.0
        if not os.environ.get("SKIP_AUDIO_CHECK"):
            preview_url = track.get("preview_url")
            audio_result = check_audio_language(preview_url)
            audio_lang = audio_result["language"]
            audio_conf = audio_result["confidence"]

            if audio_lang == "rus" and audio_conf > 0.7:
                logger.info(f"Rejected (audio=rus): {artist} — {name}")
                rejected_audio += 1
                continue

        # 7. Build track info and classify
        lang_info = f"text={text_result['language']}({text_result['confidence']:.2f}) audio={audio_lang}({audio_conf:.2f})"
        track_info = {
            "id": track["id"],
            "name": track["name"],
            "artist": ", ".join(a["name"] for a in track["artists"]),
            "uri": track["uri"],
            "source": song["source"],
        }

        result = track_filter.classify(track_info, language_info=lang_info)
        if result == "review":
            new_for_review += 1
        elif result == "skip":
            skipped += 1

    logger.info("=== Discovery complete ===")
    logger.info(f"New for review: {new_for_review}")
    logger.info(f"Already known: {skipped}")
    logger.info(f"Rejected (Russian text): {rejected_text}")
    logger.info(f"Rejected (Russian audio): {rejected_audio}")
    logger.info(f"Not on Spotify: {not_on_spotify}")


if __name__ == "__main__":
    main()
