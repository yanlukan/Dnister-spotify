# src/scrapers/lastfm.py
import logging

import requests

logger = logging.getLogger(__name__)

LASTFM_API_URL = "http://ws.audioscrobbler.com/2.0/"


def scrape_lastfm(api_key: str, tags: list[str]) -> list[dict]:
    """Fetch top tracks for Ukrainian tags from Last.fm. Returns [{name, artist, source}]."""
    if not api_key:
        logger.warning("No Last.fm API key — skipping")
        return []

    songs = []
    seen = set()

    for tag in tags:
        try:
            resp = requests.get(
                LASTFM_API_URL,
                params={
                    "method": "tag.getTopTracks",
                    "tag": tag,
                    "api_key": api_key,
                    "format": "json",
                    "limit": 50,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            for track in data.get("tracks", {}).get("track", []):
                name = track.get("name", "").strip()
                artist = track.get("artist", {}).get("name", "").strip()
                if name and artist:
                    key = (artist.lower(), name.lower())
                    if key not in seen:
                        seen.add(key)
                        songs.append({"name": name, "artist": artist, "source": "lastfm"})

            logger.info(f"Last.fm tag '{tag}': {len(data.get('tracks', {}).get('track', []))} tracks")

        except Exception as e:
            logger.warning(f"Last.fm tag '{tag}' failed: {e}")

    logger.info(f"Last.fm total: {len(songs)} unique songs")
    return songs
