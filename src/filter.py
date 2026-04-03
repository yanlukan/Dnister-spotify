import json
import logging
import re

from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

from src.lyrics_verifier import LyricsVerifier

logger = logging.getLogger(__name__)

CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")


class ContentFilter:
    """Multi-layer filter: verified artists, Cyrillic check, blocklist, language, lyrics."""

    def __init__(self, blocklist_path: str, verified_artists_path: str):
        # Load Russian blocklist
        with open(blocklist_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._blocked_ids: set[str] = {a["id"] for a in data["artists"]}
        self._blocked_names: set[str] = {a["name"].lower() for a in data["artists"]}
        logger.info(f"Loaded {len(self._blocked_ids)} blocked artists")

        # Load verified Ukrainian artists
        with open(verified_artists_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._verified_artists: set[str] = {name.lower() for name in data["artists"]}
        logger.info(f"Loaded {len(self._verified_artists)} verified Ukrainian artists")

        # Lyrics verifier (optional — needs GENIUS_ACCESS_TOKEN)
        self.lyrics_verifier = LyricsVerifier()

    def _has_cyrillic(self, text: str) -> bool:
        return bool(CYRILLIC_RE.search(text))

    def _is_verified_artist(self, track: dict) -> bool:
        """Check if any artist on the track is in the verified Ukrainian list."""
        for artist in track.get("artists", []):
            if artist.get("name", "").lower() in self._verified_artists:
                return True
        return False

    def _is_blocked_artist(self, track: dict) -> tuple[bool, str]:
        """Check if any artist is on the Russian blocklist."""
        for artist in track.get("artists", []):
            if artist["id"] in self._blocked_ids:
                return True, f"Blocklist: artist '{artist['name']}'"
            if artist["name"].lower() in self._blocked_names:
                return True, f"Blocklist: artist '{artist['name']}'"
        return False, ""

    def _has_ukrainian_connection(self, track: dict) -> bool:
        """Check if track has Cyrillic in track/artist/album name."""
        for artist in track.get("artists", []):
            if self._has_cyrillic(artist.get("name", "")):
                return True
        if self._has_cyrillic(track.get("name", "")):
            return True
        if self._has_cyrillic(track.get("album", {}).get("name", "")):
            return True
        return False

    def _check_name_language(self, track: dict) -> tuple[bool, str]:
        """Run language detection on track and album names."""
        track_name = track.get("name", "")
        if self._has_cyrillic(track_name) and len(track_name) >= 3:
            try:
                if detect(track_name) == "ru":
                    return False, f"Track name '{track_name}' detected as Russian"
            except LangDetectException:
                pass

        album_name = track.get("album", {}).get("name", "")
        if self._has_cyrillic(album_name) and len(album_name) >= 3:
            try:
                if detect(album_name) == "ru":
                    return False, f"Album name '{album_name}' detected as Russian"
            except LangDetectException:
                pass

        return True, ""

    def is_allowed(self, track: dict) -> tuple[bool, str]:
        """Full filter pipeline for a single track.

        Pipeline:
        1. Blocked artist? → reject
        2. Verified Ukrainian artist? → accept (skip further checks)
        3. Has Cyrillic connection? → if no, reject
        4. Track/album name language → if Russian, reject
        5. Lyrics check (if available) → if Russian lyrics, reject
        """
        artist_names = ", ".join(a["name"] for a in track.get("artists", []))
        track_name = track.get("name", "")

        # 1. Blocklist check first
        blocked, reason = self._is_blocked_artist(track)
        if blocked:
            return False, reason

        # 2. Verified artist — trust them
        if self._is_verified_artist(track):
            return True, "verified_artist"

        # 3. Must have Cyrillic somewhere
        if not self._has_ukrainian_connection(track):
            return False, f"Non-Ukrainian: '{track_name}' by {artist_names}"

        # 4. Check track/album name language
        ok, reason = self._check_name_language(track)
        if not ok:
            return False, f"Language: {reason}"

        # 5. Lyrics verification (if Genius API available)
        if self.lyrics_verifier.genius:
            ok, reason = self.lyrics_verifier.check_track(track_name, artist_names)
            if not ok:
                return False, f"Lyrics: {reason}"

        return True, ""

    def filter_tracks(self, tracks: list[dict]) -> tuple[list[dict], list[dict]]:
        """Filter a list of tracks. Returns (allowed, excluded)."""
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


# Keep backward-compatible alias
RussianContentFilter = ContentFilter
