# Dnister Spotify Playlist Automation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an automated system that creates and maintains 4 mood-based Ukrainian music playlists on Spotify, with Russian content filtering, running weekly via GitHub Actions.

**Architecture:** Python application using Spotipy for Spotify API access. A collector gathers songs from charts, editorial playlists, and genre searches. A filter excludes Russian content via artist blocklist + language detection. A builder assigns tracks to playlists by energy/mood using Spotify audio features. GitHub Actions runs the pipeline weekly.

**Tech Stack:** Python 3.12+, Spotipy, langdetect, PyYAML, pytest, GitHub Actions

---

### Task 1: Project Scaffolding & Config

**Files:**
- Create: `requirements.txt`
- Create: `config/playlists.yaml`
- Create: `data/russian_artists_blocklist.json`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create `requirements.txt`**

```
spotipy==2.24.0
langdetect==1.0.9
PyYAML==6.0.2
pytest==8.3.4
python-dotenv==1.0.1
```

- [ ] **Step 2: Create `config/playlists.yaml`**

```yaml
playlists:
  - name: "Dnister Daytime"
    description: "Chill Ukrainian sounds for a relaxed lunch"
    genres:
      - "ukrainian indie"
      - "ukrainian acoustic"
      - "ukrainian jazz"
    energy_min: 0.0
    energy_max: 0.4
    max_tracks: 50

  - name: "Dnister Evening"
    description: "Modern Ukrainian hits for dinner"
    genres:
      - "ukrainian pop"
      - "ukrainian r&b"
      - "ukrainian indie"
    energy_min: 0.4
    energy_max: 0.65
    max_tracks: 50

  - name: "Dnister Folk"
    description: "Traditional Ukrainian folk & bandura classics"
    genres:
      - "ukrainian folk"
      - "ukrainian traditional"
    energy_min: 0.2
    energy_max: 0.55
    max_tracks: 50

  - name: "Dnister Party"
    description: "Upbeat Ukrainian bangers for weekends"
    genres:
      - "ukrainian pop"
      - "ukrainian hip hop"
      - "ukrainian rock"
    energy_min: 0.65
    energy_max: 1.0
    max_tracks: 50

# Source playlists to pull tracks from (Spotify playlist IDs)
source_playlists:
  - "37i9dQZEVXbKkidEfWYRuD"  # Top 50 Ukraine
  # Add more editorial playlist IDs as discovered

# Seed artists (Spotify artist IDs) — known Ukrainian artists
seed_artists: []
```

- [ ] **Step 3: Create `data/russian_artists_blocklist.json`**

```json
{
  "artists": [
    {
      "name": "Филипп Киркоров",
      "id": "0GnTcERehXfOi6kahqNJzq"
    },
    {
      "name": "Егор Крид",
      "id": "4F5Bh6TswDB0G5MjGLyGn0"
    },
    {
      "name": "Баста",
      "id": "1WaFQSHVGZQRlqMdMnrGMO"
    },
    {
      "name": "Тимати",
      "id": "2p4FRSqX3mYFGoJpmrmfaI"
    },
    {
      "name": "Мот",
      "id": "4Kp0OAUjBMbm8i85Lrc2Rb"
    },
    {
      "name": "Miyagi",
      "id": "4LZ4DcEMFJKPJqK3M0OLJQ"
    },
    {
      "name": "Скриптонит",
      "id": "1pBLC0qVIN5KMQEG4FCq9F"
    },
    {
      "name": "Макс Корж",
      "id": "5S3KPmEv3tJOjYMpEHTkHt"
    },
    {
      "name": "Zivert",
      "id": "4bCv4FxN1G0hNKMPPjdafT"
    },
    {
      "name": "Мальбэк",
      "id": "4G5jPSMI9EGBdQ5MYGkHGS"
    }
  ],
  "_comment": "Add Spotify artist IDs of known Russian artists. This list should be expanded over time."
}
```

- [ ] **Step 4: Create empty `__init__.py` files**

Create empty files at `src/__init__.py` and `tests/__init__.py`.

- [ ] **Step 5: Install dependencies and verify**

Run: `pip install -r requirements.txt`
Expected: All packages install successfully.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt config/ data/ src/__init__.py tests/__init__.py
git commit -m "feat: project scaffolding with config and dependencies"
```

---

### Task 2: Spotify Client Wrapper

**Files:**
- Create: `src/spotify_client.py`
- Create: `tests/test_spotify_client.py`

- [ ] **Step 1: Write the failing test for SpotifyClient initialization**

```python
# tests/test_spotify_client.py
import os
from unittest.mock import patch, MagicMock
import pytest


def test_spotify_client_initializes_with_env_vars():
    """SpotifyClient should initialize Spotipy with credentials from env vars."""
    env = {
        "SPOTIFY_CLIENT_ID": "test_id",
        "SPOTIFY_CLIENT_SECRET": "test_secret",
        "SPOTIFY_REFRESH_TOKEN": "test_token",
    }
    with patch.dict(os.environ, env):
        with patch("src.spotify_client.spotipy.Spotify") as mock_spotify:
            from src.spotify_client import SpotifyClient

            client = SpotifyClient()
            assert client.sp is not None


def test_spotify_client_raises_without_credentials():
    """SpotifyClient should raise ValueError if credentials are missing."""
    with patch.dict(os.environ, {}, clear=True):
        from src.spotify_client import SpotifyClient

        with pytest.raises(ValueError, match="Missing Spotify credentials"):
            SpotifyClient()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_spotify_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.spotify_client'`

- [ ] **Step 3: Implement `src/spotify_client.py`**

```python
# src/spotify_client.py
import os
import logging
from typing import Optional

import spotipy
from spotipy.oauth2 import SpotifyOAuth

logger = logging.getLogger(__name__)


class SpotifyClient:
    """Wrapper around Spotipy for authenticated Spotify API access."""

    SCOPES = "playlist-modify-public playlist-modify-private"

    def __init__(self):
        client_id = os.environ.get("SPOTIFY_CLIENT_ID")
        client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
        refresh_token = os.environ.get("SPOTIFY_REFRESH_TOKEN")

        if not all([client_id, client_secret, refresh_token]):
            raise ValueError(
                "Missing Spotify credentials. Set SPOTIFY_CLIENT_ID, "
                "SPOTIFY_CLIENT_SECRET, and SPOTIFY_REFRESH_TOKEN env vars."
            )

        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri="http://localhost:8888/callback",
            scope=self.SCOPES,
        )
        # Inject the refresh token directly
        auth_manager.refresh_access_token(refresh_token)

        self.sp = spotipy.Spotify(auth_manager=auth_manager)
        logger.info("Spotify client initialized successfully")

    def get_playlist_tracks(self, playlist_id: str) -> list[dict]:
        """Fetch all tracks from a playlist."""
        tracks = []
        results = self.sp.playlist_tracks(playlist_id)
        while results:
            for item in results["items"]:
                if item["track"] is not None:
                    tracks.append(item["track"])
            results = self.sp.next(results) if results["next"] else None
        return tracks

    def search_tracks(self, query: str, limit: int = 50) -> list[dict]:
        """Search for tracks by query string."""
        results = self.sp.search(q=query, type="track", limit=limit, market="UA")
        return results["tracks"]["items"]

    def get_artist(self, artist_id: str) -> dict:
        """Get artist details by ID."""
        return self.sp.artist(artist_id)

    def get_artists(self, artist_ids: list[str]) -> list[dict]:
        """Get multiple artists in one call (max 50)."""
        results = self.sp.artists(artist_ids)
        return results["artists"]

    def get_artist_top_tracks(self, artist_id: str, market: str = "UA") -> list[dict]:
        """Get an artist's top tracks in a market."""
        results = self.sp.artist_top_tracks(artist_id, country=market)
        return results["tracks"]

    def get_audio_features(self, track_ids: list[str]) -> list[Optional[dict]]:
        """Get audio features for multiple tracks (max 100)."""
        return self.sp.audio_features(track_ids)

    def replace_playlist_tracks(self, playlist_id: str, track_uris: list[str]) -> None:
        """Replace all tracks in a playlist."""
        # Spotify API allows max 100 tracks per request
        self.sp.playlist_replace_items(playlist_id, track_uris[:100])
        # Add remaining tracks in batches
        for i in range(100, len(track_uris), 100):
            self.sp.playlist_add_items(playlist_id, track_uris[i : i + 100])
        logger.info(f"Replaced playlist {playlist_id} with {len(track_uris)} tracks")

    def create_playlist(self, user_id: str, name: str, description: str) -> str:
        """Create a new playlist and return its ID."""
        result = self.sp.user_playlist_create(
            user_id, name, public=True, description=description
        )
        logger.info(f"Created playlist '{name}' with ID {result['id']}")
        return result["id"]

    def get_current_user_id(self) -> str:
        """Get the authenticated user's Spotify ID."""
        return self.sp.current_user()["id"]

    def get_user_playlists(self) -> list[dict]:
        """Get all playlists owned by the current user."""
        playlists = []
        results = self.sp.current_user_playlists()
        while results:
            playlists.extend(results["items"])
            results = self.sp.next(results) if results["next"] else None
        return playlists
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_spotify_client.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/spotify_client.py tests/test_spotify_client.py
git commit -m "feat: add Spotify client wrapper with auth and API methods"
```

---

### Task 3: Russian Content Filter

**Files:**
- Create: `src/filter.py`
- Create: `tests/test_filter.py`

- [ ] **Step 1: Write failing tests for the filter**

```python
# tests/test_filter.py
import json
import pytest
from unittest.mock import MagicMock, patch

from src.filter import RussianContentFilter


@pytest.fixture
def blocklist_path(tmp_path):
    """Create a temporary blocklist file."""
    blocklist = {
        "artists": [
            {"name": "Russian Artist", "id": "russian_id_1"},
            {"name": "Another Russian", "id": "russian_id_2"},
        ]
    }
    path = tmp_path / "blocklist.json"
    path.write_text(json.dumps(blocklist))
    return str(path)


@pytest.fixture
def filter_instance(blocklist_path):
    return RussianContentFilter(blocklist_path)


def _make_track(track_name, artist_id, artist_name):
    """Helper to create a mock track dict."""
    return {
        "id": f"track_{track_name}",
        "name": track_name,
        "uri": f"spotify:track:track_{track_name}",
        "album": {"name": f"Album of {track_name}"},
        "artists": [{"id": artist_id, "name": artist_name}],
    }


def test_allows_ukrainian_track(filter_instance):
    track = _make_track("Stefania", "ukrainian_id", "Kalush Orchestra")
    assert filter_instance.is_allowed(track) is True


def test_blocks_blocklisted_artist(filter_instance):
    track = _make_track("Some Song", "russian_id_1", "Russian Artist")
    assert filter_instance.is_allowed(track) is False


def test_blocks_featured_russian_artist(filter_instance):
    track = _make_track("Collab Song", "ukrainian_id", "Ukrainian Artist")
    track["artists"].append({"id": "russian_id_2", "name": "Another Russian"})
    assert filter_instance.is_allowed(track) is False


def test_blocks_russian_language_track_name(filter_instance):
    track = _make_track("Привет мир как дела сегодня", "unknown_id", "Unknown Artist")
    assert filter_instance.is_allowed(track) is False


def test_allows_ukrainian_language_track_name(filter_instance):
    track = _make_track("Привіт світе як справи сьогодні", "unknown_id", "Unknown Artist")
    assert filter_instance.is_allowed(track) is True


def test_allows_english_track_name(filter_instance):
    track = _make_track("Good Vibes Only", "some_id", "Some Artist")
    assert filter_instance.is_allowed(track) is True


def test_filter_tracks_returns_allowed_only(filter_instance):
    tracks = [
        _make_track("Good Song", "uk_id", "Ukrainian Singer"),
        _make_track("Bad Song", "russian_id_1", "Russian Artist"),
        _make_track("Another Good", "uk_id_2", "Ukrainian Band"),
    ]
    allowed, excluded = filter_instance.filter_tracks(tracks)
    assert len(allowed) == 2
    assert len(excluded) == 1
    assert excluded[0]["track"]["name"] == "Bad Song"


def test_excluded_tracks_include_reason(filter_instance):
    tracks = [_make_track("Song", "russian_id_1", "Russian Artist")]
    _, excluded = filter_instance.filter_tracks(tracks)
    assert "reason" in excluded[0]
    assert "blocklist" in excluded[0]["reason"].lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_filter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.filter'`

- [ ] **Step 3: Implement `src/filter.py`**

```python
# src/filter.py
import json
import logging
import re

from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

logger = logging.getLogger(__name__)

# Cyrillic character range
CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")


class RussianContentFilter:
    """Three-layer filter to exclude Russian content from track lists."""

    def __init__(self, blocklist_path: str):
        with open(blocklist_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._blocked_ids: set[str] = {a["id"] for a in data["artists"]}
        self._blocked_names: set[str] = {a["name"].lower() for a in data["artists"]}
        logger.info(f"Loaded {len(self._blocked_ids)} blocked artists")

    def is_allowed(self, track: dict) -> tuple[bool, str]:
        """Check if a track passes all three filter layers.

        Returns (allowed: bool, reason: str). Reason is empty if allowed.
        """
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
```

**Note:** The `is_allowed` method signature returns a tuple. Update the tests to unpack correctly:

- [ ] **Step 4: Update tests to match tuple return**

Replace the simple `assert filter_instance.is_allowed(track) is True/False` calls:

```python
# In tests/test_filter.py — update these test functions:

def test_allows_ukrainian_track(filter_instance):
    track = _make_track("Stefania", "ukrainian_id", "Kalush Orchestra")
    allowed, reason = filter_instance.is_allowed(track)
    assert allowed is True


def test_blocks_blocklisted_artist(filter_instance):
    track = _make_track("Some Song", "russian_id_1", "Russian Artist")
    allowed, reason = filter_instance.is_allowed(track)
    assert allowed is False
    assert "blocklist" in reason.lower()


def test_blocks_featured_russian_artist(filter_instance):
    track = _make_track("Collab Song", "ukrainian_id", "Ukrainian Artist")
    track["artists"].append({"id": "russian_id_2", "name": "Another Russian"})
    allowed, reason = filter_instance.is_allowed(track)
    assert allowed is False


def test_blocks_russian_language_track_name(filter_instance):
    track = _make_track("Привет мир как дела сегодня", "unknown_id", "Unknown Artist")
    allowed, reason = filter_instance.is_allowed(track)
    assert allowed is False


def test_allows_ukrainian_language_track_name(filter_instance):
    track = _make_track("Привіт світе як справи сьогодні", "unknown_id", "Unknown Artist")
    allowed, reason = filter_instance.is_allowed(track)
    assert allowed is True


def test_allows_english_track_name(filter_instance):
    track = _make_track("Good Vibes Only", "some_id", "Some Artist")
    allowed, reason = filter_instance.is_allowed(track)
    assert allowed is True
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_filter.py -v`
Expected: 8 passed

- [ ] **Step 6: Commit**

```bash
git add src/filter.py tests/test_filter.py
git commit -m "feat: add Russian content filter with blocklist and language detection"
```

---

### Task 4: Song Collector

**Files:**
- Create: `src/collector.py`
- Create: `tests/test_collector.py`

- [ ] **Step 1: Write failing tests for the collector**

```python
# tests/test_collector.py
import pytest
from unittest.mock import MagicMock

from src.collector import SongCollector


def _make_track(track_id, name="Test Track"):
    return {
        "id": track_id,
        "name": name,
        "uri": f"spotify:track:{track_id}",
        "album": {"name": "Test Album"},
        "artists": [{"id": "artist_1", "name": "Test Artist"}],
    }


@pytest.fixture
def mock_spotify_client():
    return MagicMock()


@pytest.fixture
def collector(mock_spotify_client):
    return SongCollector(mock_spotify_client)


def test_collect_from_playlist(collector, mock_spotify_client):
    mock_spotify_client.get_playlist_tracks.return_value = [
        _make_track("t1"),
        _make_track("t2"),
    ]
    tracks = collector.collect_from_playlist("playlist_123")
    assert len(tracks) == 2
    mock_spotify_client.get_playlist_tracks.assert_called_once_with("playlist_123")


def test_collect_from_genre_search(collector, mock_spotify_client):
    mock_spotify_client.search_tracks.return_value = [
        _make_track("t1", "Ukrainian Song"),
    ]
    tracks = collector.collect_from_genre("ukrainian pop")
    assert len(tracks) == 1
    mock_spotify_client.search_tracks.assert_called_once_with(
        q="genre:ukrainian pop", limit=50
    )


def test_collect_from_artist(collector, mock_spotify_client):
    mock_spotify_client.get_artist_top_tracks.return_value = [
        _make_track("t1"),
        _make_track("t2"),
        _make_track("t3"),
    ]
    tracks = collector.collect_from_artist("artist_abc")
    assert len(tracks) == 3


def test_collect_all_deduplicates(collector, mock_spotify_client):
    """Same track from multiple sources should appear only once."""
    same_track = _make_track("t1", "Same Song")
    mock_spotify_client.get_playlist_tracks.return_value = [same_track]
    mock_spotify_client.search_tracks.return_value = [same_track]
    mock_spotify_client.get_artist_top_tracks.return_value = []

    config = {
        "source_playlists": ["playlist_1"],
        "genres": ["ukrainian pop"],
        "seed_artists": [],
    }
    tracks = collector.collect_all(config)
    assert len(tracks) == 1


def test_collect_all_combines_sources(collector, mock_spotify_client):
    mock_spotify_client.get_playlist_tracks.return_value = [_make_track("t1")]
    mock_spotify_client.search_tracks.return_value = [_make_track("t2")]
    mock_spotify_client.get_artist_top_tracks.return_value = [_make_track("t3")]

    config = {
        "source_playlists": ["playlist_1"],
        "genres": ["ukrainian pop"],
        "seed_artists": ["artist_1"],
    }
    tracks = collector.collect_all(config)
    assert len(tracks) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_collector.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.collector'`

- [ ] **Step 3: Implement `src/collector.py`**

```python
# src/collector.py
import logging

logger = logging.getLogger(__name__)


class SongCollector:
    """Collects tracks from multiple Spotify sources."""

    def __init__(self, spotify_client):
        self.sp = spotify_client

    def collect_from_playlist(self, playlist_id: str) -> list[dict]:
        """Fetch all tracks from a Spotify playlist."""
        tracks = self.sp.get_playlist_tracks(playlist_id)
        logger.info(f"Collected {len(tracks)} tracks from playlist {playlist_id}")
        return tracks

    def collect_from_genre(self, genre: str) -> list[dict]:
        """Search for tracks by genre."""
        tracks = self.sp.search_tracks(q=f"genre:{genre}", limit=50)
        logger.info(f"Collected {len(tracks)} tracks for genre '{genre}'")
        return tracks

    def collect_from_artist(self, artist_id: str) -> list[dict]:
        """Get top tracks for an artist."""
        tracks = self.sp.get_artist_top_tracks(artist_id)
        logger.info(f"Collected {len(tracks)} tracks from artist {artist_id}")
        return tracks

    def collect_all(self, config: dict) -> list[dict]:
        """Collect tracks from all configured sources and deduplicate.

        Config should have keys: source_playlists, genres, seed_artists
        """
        all_tracks: dict[str, dict] = {}  # track_id -> track

        # Source playlists
        for playlist_id in config.get("source_playlists", []):
            for track in self.collect_from_playlist(playlist_id):
                all_tracks[track["id"]] = track

        # Genre searches
        for genre in config.get("genres", []):
            for track in self.collect_from_genre(genre):
                all_tracks[track["id"]] = track

        # Seed artists
        for artist_id in config.get("seed_artists", []):
            for track in self.collect_from_artist(artist_id):
                all_tracks[track["id"]] = track

        tracks = list(all_tracks.values())
        logger.info(f"Total collected: {len(tracks)} unique tracks")
        return tracks
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_collector.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/collector.py tests/test_collector.py
git commit -m "feat: add song collector with playlist, genre, and artist sources"
```

---

### Task 5: Playlist Builder

**Files:**
- Create: `src/playlist_builder.py`
- Create: `tests/test_playlist_builder.py`

- [ ] **Step 1: Write failing tests for the playlist builder**

```python
# tests/test_playlist_builder.py
import pytest
from unittest.mock import MagicMock

from src.playlist_builder import PlaylistBuilder


def _make_track(track_id, name="Track"):
    return {
        "id": track_id,
        "name": name,
        "uri": f"spotify:track:{track_id}",
        "artists": [{"id": "a1", "name": "Artist"}],
    }


@pytest.fixture
def mock_spotify_client():
    return MagicMock()


@pytest.fixture
def playlist_config():
    return [
        {
            "name": "Chill",
            "description": "Low energy",
            "genres": ["ukrainian indie"],
            "energy_min": 0.0,
            "energy_max": 0.4,
            "max_tracks": 3,
        },
        {
            "name": "Party",
            "description": "High energy",
            "genres": ["ukrainian pop"],
            "energy_min": 0.7,
            "energy_max": 1.0,
            "max_tracks": 3,
        },
    ]


def test_assigns_tracks_by_energy(mock_spotify_client, playlist_config):
    tracks = [_make_track("t1"), _make_track("t2"), _make_track("t3")]

    # t1: low energy, t2: high energy, t3: medium (no match for either)
    mock_spotify_client.get_audio_features.return_value = [
        {"id": "t1", "energy": 0.2},
        {"id": "t2", "energy": 0.85},
        {"id": "t3", "energy": 0.5},
    ]

    builder = PlaylistBuilder(mock_spotify_client)
    assignments = builder.assign_tracks(tracks, playlist_config)

    assert "t1" in [t["id"] for t in assignments["Chill"]]
    assert "t2" in [t["id"] for t in assignments["Party"]]


def test_respects_max_tracks(mock_spotify_client, playlist_config):
    tracks = [_make_track(f"t{i}") for i in range(10)]
    mock_spotify_client.get_audio_features.return_value = [
        {"id": f"t{i}", "energy": 0.2} for i in range(10)
    ]

    builder = PlaylistBuilder(mock_spotify_client)
    assignments = builder.assign_tracks(tracks, playlist_config)

    assert len(assignments["Chill"]) <= 3


def test_track_assigned_to_best_fit_only(mock_spotify_client):
    """A track should only appear in one playlist, even if energy overlaps."""
    config = [
        {
            "name": "A",
            "description": "d",
            "genres": [],
            "energy_min": 0.0,
            "energy_max": 0.5,
            "max_tracks": 50,
        },
        {
            "name": "B",
            "description": "d",
            "genres": [],
            "energy_min": 0.3,
            "energy_max": 0.8,
            "max_tracks": 50,
        },
    ]
    tracks = [_make_track("t1")]
    mock_spotify_client.get_audio_features.return_value = [
        {"id": "t1", "energy": 0.4}
    ]

    builder = PlaylistBuilder(mock_spotify_client)
    assignments = builder.assign_tracks(tracks, config)

    total = sum(len(v) for v in assignments.values())
    assert total == 1  # Track appears in exactly one playlist


def test_handles_missing_audio_features(mock_spotify_client, playlist_config):
    """Tracks with no audio features should be skipped."""
    tracks = [_make_track("t1")]
    mock_spotify_client.get_audio_features.return_value = [None]

    builder = PlaylistBuilder(mock_spotify_client)
    assignments = builder.assign_tracks(tracks, playlist_config)

    total = sum(len(v) for v in assignments.values())
    assert total == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_playlist_builder.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `src/playlist_builder.py`**

```python
# src/playlist_builder.py
import logging
import random

logger = logging.getLogger(__name__)


class PlaylistBuilder:
    """Assigns tracks to playlists based on energy/mood audio features."""

    def __init__(self, spotify_client):
        self.sp = spotify_client

    def assign_tracks(
        self, tracks: list[dict], playlist_configs: list[dict]
    ) -> dict[str, list[dict]]:
        """Assign tracks to playlists by energy range.

        Each track goes to the playlist whose energy range is the best fit
        (closest to the midpoint). A track appears in at most one playlist.

        Returns: {playlist_name: [track, ...]}
        """
        assignments: dict[str, list[dict]] = {
            cfg["name"]: [] for cfg in playlist_configs
        }

        # Fetch audio features in batches of 100
        track_features: dict[str, dict] = {}
        track_ids = [t["id"] for t in tracks]
        for i in range(0, len(track_ids), 100):
            batch = track_ids[i : i + 100]
            features = self.sp.get_audio_features(batch)
            for feat in features:
                if feat is not None:
                    track_features[feat["id"]] = feat

        # Build a lookup from track id to track dict
        track_map = {t["id"]: t for t in tracks}

        # Shuffle to avoid always picking the same tracks when capping
        shuffled_ids = list(track_features.keys())
        random.shuffle(shuffled_ids)

        assigned_ids: set[str] = set()

        for track_id in shuffled_ids:
            if track_id in assigned_ids:
                continue

            feat = track_features[track_id]
            energy = feat["energy"]

            # Find best-fit playlist
            best_playlist = None
            best_distance = float("inf")

            for cfg in playlist_configs:
                name = cfg["name"]
                e_min = cfg["energy_min"]
                e_max = cfg["energy_max"]

                if e_min <= energy <= e_max and len(assignments[name]) < cfg["max_tracks"]:
                    midpoint = (e_min + e_max) / 2
                    distance = abs(energy - midpoint)
                    if distance < best_distance:
                        best_distance = distance
                        best_playlist = name

            if best_playlist:
                assignments[best_playlist].append(track_map[track_id])
                assigned_ids.add(track_id)

        for name, assigned in assignments.items():
            logger.info(f"Playlist '{name}': {len(assigned)} tracks assigned")

        return assignments
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_playlist_builder.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/playlist_builder.py tests/test_playlist_builder.py
git commit -m "feat: add playlist builder with energy-based track assignment"
```

---

### Task 6: Main Orchestrator

**Files:**
- Create: `src/main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: Write failing tests for the orchestrator**

```python
# tests/test_main.py
import pytest
from unittest.mock import MagicMock, patch, mock_open

from src.main import PlaylistManager


@pytest.fixture
def mock_config():
    return {
        "playlists": [
            {
                "name": "Test Playlist",
                "description": "Test desc",
                "genres": ["ukrainian pop"],
                "energy_min": 0.0,
                "energy_max": 1.0,
                "max_tracks": 50,
            }
        ],
        "source_playlists": ["playlist_1"],
        "seed_artists": [],
    }


@pytest.fixture
def manager(mock_config):
    with patch("src.main.SpotifyClient") as MockClient, \
         patch("src.main.yaml.safe_load", return_value=mock_config), \
         patch("builtins.open", mock_open()), \
         patch("src.main.RussianContentFilter") as MockFilter, \
         patch("src.main.SongCollector") as MockCollector, \
         patch("src.main.PlaylistBuilder") as MockBuilder:

        mock_sp = MockClient.return_value
        mock_sp.get_current_user_id.return_value = "user_123"
        mock_sp.get_user_playlists.return_value = []

        mgr = PlaylistManager(
            config_path="config/playlists.yaml",
            blocklist_path="data/russian_artists_blocklist.json",
        )

        # Store mocks for assertions
        mgr._mock_collector = MockCollector.return_value
        mgr._mock_filter = MockFilter.return_value
        mgr._mock_builder = MockBuilder.return_value
        mgr._mock_sp = mock_sp
        return mgr


def test_run_creates_missing_playlists(manager):
    manager._mock_collector.collect_all.return_value = []
    manager._mock_filter.filter_tracks.return_value = ([], [])
    manager._mock_builder.assign_tracks.return_value = {"Test Playlist": []}
    manager._mock_sp.get_user_playlists.return_value = []
    manager._mock_sp.create_playlist.return_value = "new_playlist_id"

    manager.run()

    manager._mock_sp.create_playlist.assert_called_once_with(
        "user_123", "Test Playlist", "Test desc"
    )


def test_run_reuses_existing_playlists(manager):
    manager._mock_collector.collect_all.return_value = []
    manager._mock_filter.filter_tracks.return_value = ([], [])
    manager._mock_builder.assign_tracks.return_value = {"Test Playlist": []}
    manager._mock_sp.get_user_playlists.return_value = [
        {"name": "Test Playlist", "id": "existing_id", "owner": {"id": "user_123"}}
    ]

    manager.run()

    manager._mock_sp.create_playlist.assert_not_called()


def test_run_calls_replace_with_assigned_tracks(manager):
    track = {"id": "t1", "uri": "spotify:track:t1", "name": "Song"}
    manager._mock_collector.collect_all.return_value = [track]
    manager._mock_filter.filter_tracks.return_value = ([track], [])
    manager._mock_builder.assign_tracks.return_value = {"Test Playlist": [track]}
    manager._mock_sp.get_user_playlists.return_value = [
        {"name": "Test Playlist", "id": "pl_id", "owner": {"id": "user_123"}}
    ]

    manager.run()

    manager._mock_sp.replace_playlist_tracks.assert_called_once_with(
        "pl_id", ["spotify:track:t1"]
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_main.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `src/main.py`**

```python
# src/main.py
import logging
import sys

import yaml

from src.spotify_client import SpotifyClient
from src.collector import SongCollector
from src.filter import RussianContentFilter
from src.playlist_builder import PlaylistBuilder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class PlaylistManager:
    """Main orchestrator: collect → filter → build → update playlists."""

    def __init__(
        self,
        config_path: str = "config/playlists.yaml",
        blocklist_path: str = "data/russian_artists_blocklist.json",
    ):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.sp_client = SpotifyClient()
        self.collector = SongCollector(self.sp_client)
        self.content_filter = RussianContentFilter(blocklist_path)
        self.builder = PlaylistBuilder(self.sp_client)
        self.user_id = self.sp_client.get_current_user_id()

    def _get_or_create_playlist(self, name: str, description: str) -> str:
        """Find an existing playlist by name or create a new one. Returns playlist ID."""
        playlists = self.sp_client.get_user_playlists()
        for pl in playlists:
            if pl["name"] == name and pl["owner"]["id"] == self.user_id:
                logger.info(f"Found existing playlist '{name}' ({pl['id']})")
                return pl["id"]

        playlist_id = self.sp_client.create_playlist(self.user_id, name, description)
        return playlist_id

    def run(self) -> None:
        """Execute the full pipeline: collect → filter → assign → update."""
        playlist_configs = self.config["playlists"]

        # 1. Collect all unique genres across playlists
        all_genres = set()
        for cfg in playlist_configs:
            all_genres.update(cfg["genres"])

        collect_config = {
            "source_playlists": self.config.get("source_playlists", []),
            "genres": list(all_genres),
            "seed_artists": self.config.get("seed_artists", []),
        }

        logger.info("=== Starting playlist update ===")

        # 2. Collect tracks
        all_tracks = self.collector.collect_all(collect_config)
        logger.info(f"Collected {len(all_tracks)} unique tracks")

        # 3. Filter Russian content
        allowed_tracks, excluded = self.content_filter.filter_tracks(all_tracks)
        logger.info(
            f"After filtering: {len(allowed_tracks)} allowed, {len(excluded)} excluded"
        )

        # 4. Assign tracks to playlists by energy
        assignments = self.builder.assign_tracks(allowed_tracks, playlist_configs)

        # 5. Update each playlist on Spotify
        for cfg in playlist_configs:
            name = cfg["name"]
            description = cfg["description"]
            tracks = assignments.get(name, [])

            playlist_id = self._get_or_create_playlist(name, description)
            track_uris = [t["uri"] for t in tracks]

            if track_uris:
                self.sp_client.replace_playlist_tracks(playlist_id, track_uris)
                logger.info(f"Updated '{name}' with {len(track_uris)} tracks")
            else:
                logger.warning(f"No tracks assigned to '{name}' — skipping update")

        logger.info("=== Playlist update complete ===")


def main():
    try:
        manager = PlaylistManager()
        manager.run()
    except Exception as e:
        logger.error(f"Failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_main.py -v`
Expected: 3 passed

- [ ] **Step 5: Run all tests to verify nothing is broken**

Run: `python -m pytest tests/ -v`
Expected: All tests pass (12+ tests)

- [ ] **Step 6: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: add main orchestrator for collect-filter-assign-update pipeline"
```

---

### Task 7: OAuth Helper Script

**Files:**
- Create: `scripts/auth.py`

- [ ] **Step 1: Create `scripts/auth.py`**

```python
#!/usr/bin/env python3
"""One-time OAuth helper to get a Spotify refresh token.

Usage:
  1. Create a Spotify app at https://developer.spotify.com/dashboard
  2. Set redirect URI to http://localhost:8888/callback
  3. Run: SPOTIFY_CLIENT_ID=xxx SPOTIFY_CLIENT_SECRET=yyy python scripts/auth.py
  4. Follow the browser prompt to authorize
  5. Copy the refresh token to your GitHub repo secrets as SPOTIFY_REFRESH_TOKEN
"""
import os
import sys

import spotipy
from spotipy.oauth2 import SpotifyOAuth

SCOPES = "playlist-modify-public playlist-modify-private"


def main():
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("Error: Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET env vars.")
        print()
        print("Example:")
        print(
            "  SPOTIFY_CLIENT_ID=abc SPOTIFY_CLIENT_SECRET=xyz python scripts/auth.py"
        )
        sys.exit(1)

    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="http://localhost:8888/callback",
        scope=SCOPES,
        open_browser=True,
    )

    # This triggers the OAuth flow — opens browser, waits for callback
    sp = spotipy.Spotify(auth_manager=auth_manager)
    user = sp.current_user()
    print(f"\nAuthenticated as: {user['display_name']} ({user['id']})")

    token_info = auth_manager.get_cached_token()
    if token_info and "refresh_token" in token_info:
        print(f"\n{'=' * 60}")
        print("Your refresh token (add this to GitHub secrets):")
        print(f"{'=' * 60}")
        print(token_info["refresh_token"])
        print(f"{'=' * 60}")
        print("\nGitHub secret name: SPOTIFY_REFRESH_TOKEN")
    else:
        print("Error: Could not retrieve refresh token.")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add scripts/auth.py
git commit -m "feat: add OAuth helper script for one-time Spotify auth"
```

---

### Task 8: GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/update-playlists.yml`

- [ ] **Step 1: Create the workflow file**

```yaml
# .github/workflows/update-playlists.yml
name: Update Dnister Playlists

on:
  schedule:
    # Every Monday at 6:00 AM UTC
    - cron: "0 6 * * 1"
  workflow_dispatch: # Allow manual runs

jobs:
  update-playlists:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Update playlists
        env:
          SPOTIFY_CLIENT_ID: ${{ secrets.SPOTIFY_CLIENT_ID }}
          SPOTIFY_CLIENT_SECRET: ${{ secrets.SPOTIFY_CLIENT_SECRET }}
          SPOTIFY_REFRESH_TOKEN: ${{ secrets.SPOTIFY_REFRESH_TOKEN }}
        run: python -m src.main

      - name: Report result
        if: failure()
        run: echo "::error::Playlist update failed. Check logs above."
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/update-playlists.yml
git commit -m "feat: add GitHub Actions workflow for weekly playlist updates"
```

---

### Task 9: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create `README.md`**

```markdown
# Dnister Spotify Playlist Automation

Automated weekly Spotify playlist management for **Dnister** Ukrainian restaurant. Creates and maintains 4 mood-based playlists with Ukrainian music, filtering out all Russian content.

## Playlists

| Playlist | Vibe | Energy |
|----------|------|--------|
| Dnister Daytime | Chill indie/acoustic/jazz for lunch | Low |
| Dnister Evening | Modern pop & indie for dinner | Medium |
| Dnister Folk | Traditional folk & bandura | Low-Medium |
| Dnister Party | Upbeat hits for weekends | High |

## How It Works

1. **Collects** songs from Spotify Ukraine charts, editorial playlists, and genre searches
2. **Filters** out Russian content (artist blocklist + language detection)
3. **Assigns** tracks to playlists by energy level using Spotify audio features
4. **Updates** all 4 playlists on Spotify

Runs automatically every Monday via GitHub Actions.

## Setup

### 1. Create a Spotify App

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Set redirect URI to `http://localhost:8888/callback`
4. Note your Client ID and Client Secret

### 2. Get a Refresh Token

```bash
SPOTIFY_CLIENT_ID=your_id SPOTIFY_CLIENT_SECRET=your_secret python scripts/auth.py
```

Follow the browser prompt. Copy the refresh token from the output.

### 3. Add GitHub Secrets

In your repo: Settings → Secrets and variables → Actions → New repository secret

- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `SPOTIFY_REFRESH_TOKEN`

### 4. Run

The workflow runs automatically every Monday. To run manually:

Actions → Update Dnister Playlists → Run workflow

## Development

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

## Updating the Blocklist

Edit `data/russian_artists_blocklist.json` to add or remove artists. Each entry needs a `name` and Spotify `id`.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup and usage instructions"
```

---

### Task 10: Integration Test & Final Verification

**Files:**
- Modify: `tests/test_main.py`

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 2: Verify project structure**

Run: `find . -type f -not -path './.git/*' | sort`

Expected output:
```
./.github/workflows/update-playlists.yml
./README.md
./config/playlists.yaml
./data/russian_artists_blocklist.json
./docs/superpowers/plans/2026-04-03-dnister-spotify-playlist.md
./docs/superpowers/specs/2026-04-03-dnister-spotify-playlist-design.md
./requirements.txt
./scripts/auth.py
./src/__init__.py
./src/collector.py
./src/filter.py
./src/main.py
./src/playlist_builder.py
./src/spotify_client.py
./tests/__init__.py
./tests/test_collector.py
./tests/test_filter.py
./tests/test_main.py
./tests/test_playlist_builder.py
```

- [ ] **Step 3: Verify linting (optional)**

Run: `python -m py_compile src/main.py && python -m py_compile src/collector.py && python -m py_compile src/filter.py && python -m py_compile src/playlist_builder.py && python -m py_compile src/spotify_client.py`
Expected: No errors

- [ ] **Step 4: Final commit if any cleanup was needed**

```bash
git add -A
git commit -m "chore: final cleanup and verification"
```
