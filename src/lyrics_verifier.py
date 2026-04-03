import logging
import os
import time

from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

logger = logging.getLogger(__name__)

# Optional: try to import lyricsgenius
try:
    import lyricsgenius
    HAS_GENIUS = True
except ImportError:
    HAS_GENIUS = False


class LyricsVerifier:
    """Verify tracks are Ukrainian by checking lyrics language."""

    def __init__(self):
        genius_token = os.environ.get("GENIUS_ACCESS_TOKEN")
        if HAS_GENIUS and genius_token:
            self.genius = lyricsgenius.Genius(
                genius_token,
                verbose=False,
                remove_section_headers=True,
                retries=1,
                timeout=10,
            )
            logger.info("Genius lyrics API initialized")
        else:
            self.genius = None
            if not genius_token:
                logger.warning("GENIUS_ACCESS_TOKEN not set — lyrics verification disabled")

    def get_lyrics(self, track_name: str, artist_name: str) -> str | None:
        """Fetch lyrics for a track. Returns None if not found."""
        if not self.genius:
            return None

        try:
            # Clean up track name (remove feat., remix, etc.)
            clean_name = track_name.split(" - ")[0].split(" (")[0].strip()
            song = self.genius.search_song(clean_name, artist_name)
            if song and song.lyrics:
                return song.lyrics
        except Exception as e:
            logger.debug(f"Lyrics fetch failed for '{track_name}' by '{artist_name}': {e}")

        return None

    def verify_ukrainian(self, lyrics: str) -> tuple[bool, str]:
        """Check if lyrics are in Ukrainian (not Russian or other).

        Returns (is_ukrainian, detected_language).
        """
        # Clean lyrics — remove common non-lyric text
        lines = lyrics.strip().split("\n")
        # Skip first line (often song title) and last line (often embed info)
        clean_lines = [l for l in lines[1:-1] if l.strip() and not l.startswith("[")]
        text = " ".join(clean_lines)

        if len(text) < 20:
            return True, "too_short"  # Can't reliably detect, allow it

        try:
            lang = detect(text)
            if lang == "uk":
                return True, "uk"
            elif lang == "ru":
                return False, "ru"
            else:
                # Non-Slavic language — could be instrumental or English parts
                # Allow it since our Cyrillic filter already ensures Ukrainian connection
                return True, lang
        except LangDetectException:
            return True, "unknown"

    def check_track(self, track_name: str, artist_name: str) -> tuple[bool, str]:
        """Full verification: fetch lyrics and check language.

        Returns (allowed, reason).
        """
        lyrics = self.get_lyrics(track_name, artist_name)
        if not lyrics:
            return True, "no_lyrics_found"  # Can't verify, allow it

        is_ok, lang = self.verify_ukrainian(lyrics)
        if is_ok:
            return True, f"lyrics_verified_{lang}"
        else:
            return False, f"Lyrics detected as {lang} for '{track_name}' by {artist_name}"
