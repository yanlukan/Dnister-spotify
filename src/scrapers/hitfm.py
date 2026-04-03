# src/scrapers/hitfm.py
import json
import logging
import re

import requests

logger = logging.getLogger(__name__)

HITFM_URL = "https://www.hitfm.ua/playlist/"


def scrape_hitfm() -> list[dict]:
    """Scrape Hit FM Ukraine playlist. Returns [{name, artist, source}]."""
    try:
        resp = requests.get(HITFM_URL, timeout=15)
        resp.raise_for_status()

        match = re.search(r"var\s+songsFound\s*=\s*(\[.*?\]);", resp.text, re.DOTALL)
        if not match:
            logger.warning("Could not find songsFound in Hit FM page")
            return []

        songs_data = json.loads(match.group(1))
        songs = []
        seen = set()
        for item in songs_data:
            artist = item.get("singer", "").strip()
            name = item.get("song", "").strip()
            if artist and name:
                key = (artist.lower(), name.lower())
                if key not in seen:
                    seen.add(key)
                    songs.append({"name": name, "artist": artist, "source": "hitfm"})

        logger.info(f"Hit FM: found {len(songs)} songs")
        return songs

    except Exception as e:
        logger.error(f"Hit FM scrape failed: {e}")
        return []
