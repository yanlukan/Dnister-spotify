import json
import logging
import re

from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

logger = logging.getLogger(__name__)

# Cyrillic character range
CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")


class RussianContentFilter:
    """Filter to exclude Russian content and non-Ukrainian tracks."""

    # Known Ukrainian artist IDs that should always be allowed
    _known_ukrainian: set[str] = set()

    def __init__(self, blocklist_path: str):
        with open(blocklist_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._blocked_ids: set[str] = {a["id"] for a in data["artists"]}
        self._blocked_names: set[str] = {a["name"].lower() for a in data["artists"]}
        logger.info(f"Loaded {len(self._blocked_ids)} blocked artists")

    def _has_cyrillic(self, text: str) -> bool:
        """Check if text contains Cyrillic characters."""
        return bool(CYRILLIC_RE.search(text))

    def _looks_ukrainian(self, track: dict) -> bool:
        """Check if a track has any Ukrainian connection.

        Returns True if the track/artist/album name contains Cyrillic,
        or if the artist is in our known Ukrainian set.
        """
        # Check artist names for Cyrillic
        for artist in track.get("artists", []):
            if self._has_cyrillic(artist.get("name", "")):
                return True
            if artist["id"] in self._known_ukrainian:
                return True

        # Check track name for Cyrillic
        if self._has_cyrillic(track.get("name", "")):
            return True

        # Check album name for Cyrillic
        if self._has_cyrillic(track.get("album", {}).get("name", "")):
            return True

        return False

    def is_allowed(self, track: dict) -> tuple[bool, str]:
        """Check if a track passes all filter layers.

        Returns (allowed: bool, reason: str). Reason is empty if allowed.
        """
        # Layer 0: Must look Ukrainian (has Cyrillic somewhere)
        if not self._looks_ukrainian(track):
            artist_names = ", ".join(a["name"] for a in track.get("artists", []))
            return False, f"Non-Ukrainian: '{track.get('name', '')}' by {artist_names}"

        # Layer 1 + 3: Check all artists (primary + featured) against blocklist
        for artist in track.get("artists", []):
            if artist["id"] in self._blocked_ids:
                return False, f"Blocklist: artist '{artist['name']}' is blocked"
            if artist["name"].lower() in self._blocked_names:
                return False, f"Blocklist: artist name '{artist['name']}' matches"

        # Layer 2: Language detection on track name
        track_name = track.get("name", "")
        if CYRILLIC_RE.search(track_name) and len(track_name) >= 3:
            try:
                lang = detect(track_name)
                if lang == "ru":
                    return False, f"Language: track name '{track_name}' detected as Russian"
            except LangDetectException:
                pass  # Can't detect — allow by default

        # Layer 2b: Language detection on album name
        album_name = track.get("album", {}).get("name", "")
        if CYRILLIC_RE.search(album_name) and len(album_name) >= 3:
            try:
                lang = detect(album_name)
                if lang == "ru":
                    return False, f"Language: album name '{album_name}' detected as Russian"
            except LangDetectException:
                pass

        return True, ""

    def filter_tracks(self, tracks: list[dict]) -> tuple[list[dict], list[dict]]:
        """Filter a list of tracks. Returns (allowed, excluded) lists.

        Excluded items include the track and the reason for exclusion.
        """
        allowed = []
        excluded = []
        for track in tracks:
            is_ok, reason = self.is_allowed(track)
            if is_ok:
                allowed.append(track)
            else:
                excluded.append({"track": track, "reason": reason})
                logger.info(f"Excluded: {track['name']} — {reason}")
        logger.info(
            f"Filter result: {len(allowed)} allowed, {len(excluded)} excluded"
        )
        return allowed, excluded
