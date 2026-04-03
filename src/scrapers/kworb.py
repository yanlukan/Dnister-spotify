# src/scrapers/kworb.py
import logging

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

KWORB_URL = "https://kworb.net/charts/deezer/ua.html"


def scrape_kworb() -> list[dict]:
    """Scrape kworb.net Deezer Ukraine chart. Returns [{name, artist, source}]."""
    try:
        resp = requests.get(KWORB_URL, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        songs = []
        seen = set()

        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 3:
                continue

            text = cells[2].get_text(" ", strip=True)
            if " - " not in text:
                continue

            artist, name = text.split(" - ", 1)
            artist = artist.strip()
            name = name.strip()

            if artist and name:
                key = (artist.lower(), name.lower())
                if key not in seen:
                    seen.add(key)
                    songs.append({"name": name, "artist": artist, "source": "kworb"})

        logger.info(f"kworb.net: found {len(songs)} songs")
        return songs

    except Exception as e:
        logger.error(f"kworb.net scrape failed: {e}")
        return []
