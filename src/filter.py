import json
import logging
import re

from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

from src.lyrics_verifier import LyricsVerifier

logger = logging.getLogger(__name__)

CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class ContentFilter:
    """Track filter with whitelist/blacklist/not-sure lists."""

    def __init__(
        self,
        blocklist_path: str,
        verified_artists_path: str,
        whitelist_path: str = "data/whitelist.json",
        blacklist_path: str = "data/blacklist.json",
        not_sure_path: str = "data/not_sure.json",
    ):
        # Russian artist blocklist
        data = _load_json(blocklist_path)
        self._blocked_ids: set[str] = {a["id"] for a in data["artists"]}
        self._blocked_names: set[str] = {a["name"].lower() for a in data["artists"]}

        # Verified Ukrainian artists
        data = _load_json(verified_artists_path)
        self._verified_artists: set[str] = {name.lower() for name in data["artists"]}

        # Track lists (keyed by Spotify track ID)
        self._whitelist_path = whitelist_path
        self._blacklist_path = blacklist_path
        self._not_sure_path = not_sure_path

        self._whitelist = _load_json(whitelist_path)
        self._blacklist = _load_json(blacklist_path)
        self._not_sure = _load_json(not_sure_path)

        self._whitelisted_ids: set[str] = set(self._whitelist["tracks"].keys())
        self._blacklisted_ids: set[str] = set(self._blacklist["tracks"].keys())
        self._not_sure_ids: set[str] = set(self._not_sure["tracks"].keys())

        # Lyrics verifier
        self.lyrics_verifier = LyricsVerifier()

        logger.info(
            f"Loaded {len(self._whitelisted_ids)} whitelisted, "
            f"{len(self._blacklisted_ids)} blacklisted, "
            f"{len(self._not_sure_ids)} not-sure tracks"
        )

    def _has_cyrillic(self, text: str) -> bool:
        return bool(CYRILLIC_RE.search(text))

    def _is_verified_artist(self, track: dict) -> bool:
        for artist in track.get("artists", []):
            if artist.get("name", "").lower() in self._verified_artists:
                return True
        return False

    def _is_blocked_artist(self, track: dict) -> tuple[bool, str]:
        for artist in track.get("artists", []):
            if artist["id"] in self._blocked_ids:
                return True, f"Blocklist artist: '{artist['name']}'"
            if artist["name"].lower() in self._blocked_names:
                return True, f"Blocklist artist: '{artist['name']}'"
        return False, ""

    def _has_ukrainian_connection(self, track: dict) -> bool:
        for artist in track.get("artists", []):
            if self._has_cyrillic(artist.get("name", "")):
                return True
        if self._has_cyrillic(track.get("name", "")):
            return True
        if self._has_cyrillic(track.get("album", {}).get("name", "")):
            return True
        return False

    def _check_name_language(self, track: dict) -> tuple[bool, str]:
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

    def _track_summary(self, track: dict) -> str:
        """Human-readable summary for the review lists."""
        artists = ", ".join(a["name"] for a in track.get("artists", []))
        return f"{artists} — {track.get('name', '?')}"

    def _add_to_not_sure(self, track: dict, reason: str) -> None:
        """Add a track to the not-sure list for manual review."""
        track_id = track["id"]
        if track_id not in self._not_sure_ids:
            self._not_sure["tracks"][track_id] = {
                "name": track.get("name", ""),
                "artists": self._track_summary(track),
                "uri": track.get("uri", ""),
                "reason": reason,
            }
            self._not_sure_ids.add(track_id)

    def classify(self, track: dict) -> tuple[str, str]:
        """Classify a track as 'allow', 'reject', or 'not_sure'.

        Returns (decision, reason).
        """
        track_id = track.get("id", "")

        # 1. Already manually reviewed?
        if track_id in self._whitelisted_ids:
            return "allow", "whitelisted"
        if track_id in self._blacklisted_ids:
            return "reject", "blacklisted"

        # 2. Blocked Russian artist?
        blocked, reason = self._is_blocked_artist(track)
        if blocked:
            return "reject", reason

        # 3. Verified Ukrainian artist?
        if self._is_verified_artist(track):
            return "allow", "verified_artist"

        # 4. No Cyrillic at all? → definitely not Ukrainian
        if not self._has_ukrainian_connection(track):
            artists = ", ".join(a["name"] for a in track.get("artists", []))
            return "reject", f"Non-Ukrainian: '{track.get('name', '')}' by {artists}"

        # 5. Track/album name detected as Russian?
        ok, reason = self._check_name_language(track)
        if not ok:
            return "not_sure", f"Language: {reason}"

        # 6. Lyrics check if available
        if self.lyrics_verifier.genius:
            artists = ", ".join(a["name"] for a in track.get("artists", []))
            ok, reason = self.lyrics_verifier.check_track(track.get("name", ""), artists)
            if not ok:
                return "not_sure", f"Lyrics: {reason}"

        # 7. Has Cyrillic but not verified — mark as not sure
        if not self._is_verified_artist(track):
            return "not_sure", "Unknown artist, needs review"

        return "allow", ""

    def filter_tracks(self, tracks: list[dict]) -> tuple[list[dict], list[dict]]:
        """Filter tracks. Returns (allowed, excluded).

        Tracks classified as 'not_sure' are excluded but saved
        to not_sure.json for manual review.
        """
        allowed = []
        excluded = []
        new_not_sure = 0

        for track in tracks:
            decision, reason = self.classify(track)

            if decision == "allow":
                allowed.append(track)
            elif decision == "reject":
                excluded.append({"track": track, "reason": reason})
                logger.info(f"Rejected: {self._track_summary(track)} — {reason}")
            else:  # not_sure
                excluded.append({"track": track, "reason": f"NOT SURE: {reason}"})
                self._add_to_not_sure(track, reason)
                new_not_sure += 1
                logger.info(f"Not sure: {self._track_summary(track)} — {reason}")

        # Save updated not-sure list
        if new_not_sure > 0:
            _save_json(self._not_sure_path, self._not_sure)
            logger.info(f"Added {new_not_sure} tracks to not-sure list for review")

        logger.info(
            f"Filter: {len(allowed)} allowed, {len(excluded)} excluded "
            f"({new_not_sure} need review)"
        )
        return allowed, excluded


# Backward-compatible alias
RussianContentFilter = ContentFilter
