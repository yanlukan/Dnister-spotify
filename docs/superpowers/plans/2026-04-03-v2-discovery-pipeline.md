# Dnister v2 — Discovery + Review Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the playlist system so songs are discovered from Ukrainian music charts, verified by AI language detection, manually reviewed by the owner, and only then pushed to Spotify playlists.

**Architecture:** Three separate commands. `discover` scrapes Hit FM, Last.fm, and kworb.net for Ukrainian songs, finds them on Spotify, runs language detection (glotlid text + mms-lid audio), and queues them for review. `review.py` is an interactive CLI where the owner listens and assigns songs to playlists. `update_playlists` reads the whitelist and pushes to Spotify.

**Tech Stack:** Python 3.12+, Spotipy, requests, BeautifulSoup4, transformers, torchaudio, fasttext, Last.fm API

---

### Task 1: Clean Slate — New Project Structure & Dependencies

**Files:**
- Rewrite: `requirements.txt`
- Rewrite: `config/playlists.yaml`
- Create: `src/scrapers/__init__.py`
- Create: `src/language/__init__.py`
- Reset: `data/whitelist.json`, `data/blacklist.json`, `data/not_sure.json`

- [ ] **Step 1: Update `requirements.txt`**

```
spotipy==2.24.0
requests==2.32.3
beautifulsoup4==4.12.3
PyYAML==6.0.2
pytest==8.3.4
python-dotenv==1.0.1
transformers==4.47.0
torch==2.5.1
torchaudio==2.5.1
fasttext-wheel==0.9.2
huggingface-hub==0.27.0
```

- [ ] **Step 2: Simplify `config/playlists.yaml`**

```yaml
playlists:
  daytime: "2dtGpG8ColpwGLjAIh3h2y"
  evening: "2M199fyV4J4gT1MfusqJxJ"
  folk: "5VcKxY0sYxapLRW1DSUvQr"
  party: "4kn274GiOqPmh6pgwG1nPZ"
  waltz: "5AsuhvTJGEZSNfLi89M3pF"
  rave: "5MwjTAKFh33Qhx8t5JZ2h2"

lastfm_tags:
  - "ukrainian"
  - "ukrainian pop"
  - "ukrainian folk"
  - "ukrainian rock"
  - "ukrainian electronic"
  - "ukrainian hip-hop"
```

- [ ] **Step 3: Create package init files**

Create empty files: `src/scrapers/__init__.py`, `src/language/__init__.py`

- [ ] **Step 4: Reset data files**

Reset `data/whitelist.json`, `data/blacklist.json`, `data/not_sure.json` to:
```json
{
  "tracks": {}
}
```

- [ ] **Step 5: Install dependencies**

Run: `.venv/bin/pip install -r requirements.txt`

Note: `torch` and `transformers` are large downloads (~2GB). This will take a few minutes.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt config/playlists.yaml src/scrapers/__init__.py src/language/__init__.py data/whitelist.json data/blacklist.json data/not_sure.json
git commit -m "feat: v2 project structure with new dependencies"
```

---

### Task 2: Spotify Client (Simplified)

**Files:**
- Rewrite: `src/spotify_client.py`
- Rewrite: `tests/test_spotify_client.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_spotify_client.py
import os
import pytest
from unittest.mock import patch, MagicMock


def test_search_returns_track():
    """search_track should return the first matching track dict."""
    from src.spotify_client import SpotifyClient

    env = {
        "SPOTIFY_CLIENT_ID": "test",
        "SPOTIFY_CLIENT_SECRET": "test",
        "SPOTIFY_REFRESH_TOKEN": "test",
    }
    with patch.dict(os.environ, env), \
         patch("src.spotify_client.SpotifyOAuth"), \
         patch("src.spotify_client.spotipy.Spotify") as MockSp:

        mock_sp = MockSp.return_value
        mock_sp.search.return_value = {
            "tracks": {"items": [
                {
                    "id": "abc",
                    "name": "Stefania",
                    "uri": "spotify:track:abc",
                    "preview_url": "https://example.com/preview.mp3",
                    "artists": [{"name": "Kalush Orchestra"}],
                    "album": {"name": "Album"},
                }
            ]}
        }

        client = SpotifyClient()
        result = client.search_track("Stefania", "Kalush Orchestra")
        assert result is not None
        assert result["id"] == "abc"


def test_search_returns_none_when_not_found():
    from src.spotify_client import SpotifyClient

    env = {
        "SPOTIFY_CLIENT_ID": "test",
        "SPOTIFY_CLIENT_SECRET": "test",
        "SPOTIFY_REFRESH_TOKEN": "test",
    }
    with patch.dict(os.environ, env), \
         patch("src.spotify_client.SpotifyOAuth"), \
         patch("src.spotify_client.spotipy.Spotify") as MockSp:

        mock_sp = MockSp.return_value
        mock_sp.search.return_value = {"tracks": {"items": []}}

        client = SpotifyClient()
        result = client.search_track("Nonexistent", "Nobody")
        assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_spotify_client.py -v`

- [ ] **Step 3: Implement `src/spotify_client.py`**

```python
# src/spotify_client.py
import os
import logging
import requests as http_requests

import spotipy
from spotipy.oauth2 import SpotifyOAuth

logger = logging.getLogger(__name__)


class SpotifyClient:
    """Spotify API client. Only used for search and playlist updates."""

    def __init__(self):
        client_id = os.environ.get("SPOTIFY_CLIENT_ID")
        client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
        refresh_token = os.environ.get("SPOTIFY_REFRESH_TOKEN")

        if not all([client_id, client_secret, refresh_token]):
            raise ValueError(
                "Set SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN"
            )

        self.auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri="http://127.0.0.1:3000/callback",
            scope="playlist-modify-public playlist-modify-private",
        )
        self.auth_manager.refresh_access_token(refresh_token)
        self.sp = spotipy.Spotify(auth_manager=self.auth_manager)
        logger.info("Spotify client initialized")

    def search_track(self, song_name: str, artist_name: str) -> dict | None:
        """Search for a track on Spotify. Returns track dict or None."""
        query = f"{song_name} {artist_name}"
        try:
            results = self.sp.search(q=query, type="track", limit=5, market="UA")
            items = results["tracks"]["items"]
            if not items:
                return None

            # Try exact artist match first
            for track in items:
                track_artists = [a["name"].lower() for a in track["artists"]]
                if artist_name.lower() in track_artists:
                    return track

            # Fall back to first result
            return items[0]
        except Exception as e:
            logger.warning(f"Search failed for '{song_name}' by {artist_name}: {e}")
            return None

    def replace_playlist(self, playlist_id: str, track_uris: list[str]) -> None:
        """Replace all tracks in a playlist using the /items endpoint."""
        token = self.auth_manager.get_access_token(as_dict=False)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        base = "https://api.spotify.com/v1"

        # Clear playlist
        http_requests.put(
            f"{base}/playlists/{playlist_id}/items",
            json={"uris": []},
            headers=headers,
        ).raise_for_status()

        # Add tracks in batches of 100
        for i in range(0, len(track_uris), 100):
            batch = track_uris[i : i + 100]
            http_requests.post(
                f"{base}/playlists/{playlist_id}/items",
                json={"uris": batch},
                headers=headers,
            ).raise_for_status()

        logger.info(f"Updated playlist {playlist_id} with {len(track_uris)} tracks")
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_spotify_client.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/spotify_client.py tests/test_spotify_client.py
git commit -m "feat(v2): simplified Spotify client for search + playlist update"
```

---

### Task 3: Hit FM Scraper

**Files:**
- Create: `src/scrapers/hitfm.py`
- Create: `tests/test_scrapers.py`

- [ ] **Step 1: Write test**

```python
# tests/test_scrapers.py
from unittest.mock import patch, MagicMock
from src.scrapers.hitfm import scrape_hitfm


def test_hitfm_parses_songs():
    html = """
    <html><script>
    var songsFound = [
        {"singer": "KAZKA", "song": "ПЛАКАЛА", "time": "12:00"},
        {"singer": "Океан Ельзи", "song": "Обійми", "time": "12:05"}
    ];
    </script></html>
    """
    with patch("src.scrapers.hitfm.requests.get") as mock_get:
        mock_get.return_value = MagicMock(text=html, status_code=200)
        songs = scrape_hitfm()
        assert len(songs) == 2
        assert songs[0] == {"name": "ПЛАКАЛА", "artist": "KAZKA", "source": "hitfm"}
        assert songs[1] == {"name": "Обійми", "artist": "Океан Ельзи", "source": "hitfm"}


def test_hitfm_returns_empty_on_failure():
    with patch("src.scrapers.hitfm.requests.get") as mock_get:
        mock_get.side_effect = Exception("Connection failed")
        songs = scrape_hitfm()
        assert songs == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_scrapers.py::test_hitfm_parses_songs -v`

- [ ] **Step 3: Implement `src/scrapers/hitfm.py`**

```python
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
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_scrapers.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/scrapers/hitfm.py tests/test_scrapers.py
git commit -m "feat(v2): Hit FM Ukraine playlist scraper"
```

---

### Task 4: Last.fm Scraper

**Files:**
- Create: `src/scrapers/lastfm.py`
- Modify: `tests/test_scrapers.py`

- [ ] **Step 1: Write test**

Append to `tests/test_scrapers.py`:

```python
from src.scrapers.lastfm import scrape_lastfm


def test_lastfm_parses_tracks():
    api_response = {
        "tracks": {
            "track": [
                {
                    "name": "ПЛАКАЛА",
                    "artist": {"name": "KAZKA"},
                },
                {
                    "name": "Stefania",
                    "artist": {"name": "Kalush Orchestra"},
                },
            ]
        }
    }
    with patch("src.scrapers.lastfm.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = api_response
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        songs = scrape_lastfm(api_key="fake_key", tags=["ukrainian"])
        assert len(songs) == 2
        assert songs[0]["name"] == "ПЛАКАЛА"
        assert songs[0]["source"] == "lastfm"


def test_lastfm_returns_empty_without_key():
    songs = scrape_lastfm(api_key="", tags=["ukrainian"])
    assert songs == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_scrapers.py::test_lastfm_parses_tracks -v`

- [ ] **Step 3: Implement `src/scrapers/lastfm.py`**

```python
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
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_scrapers.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/scrapers/lastfm.py tests/test_scrapers.py
git commit -m "feat(v2): Last.fm tag API scraper"
```

---

### Task 5: kworb.net Deezer UA Chart Scraper

**Files:**
- Create: `src/scrapers/kworb.py`
- Modify: `tests/test_scrapers.py`

- [ ] **Step 1: Write test**

Append to `tests/test_scrapers.py`:

```python
from src.scrapers.kworb import scrape_kworb


def test_kworb_parses_chart():
    html = """
    <html><body><table>
    <tr><td>1</td><td></td><td><a>KAZKA</a> - ПЛАКАЛА</td></tr>
    <tr><td>2</td><td></td><td><a>Океан Ельзи</a> - Обійми</td></tr>
    </table></body></html>
    """
    with patch("src.scrapers.kworb.requests.get") as mock_get:
        mock_get.return_value = MagicMock(text=html, status_code=200)
        songs = scrape_kworb()
        assert len(songs) == 2
        assert songs[0]["artist"] == "KAZKA"
        assert songs[0]["name"] == "ПЛАКАЛА"
        assert songs[0]["source"] == "kworb"


def test_kworb_returns_empty_on_failure():
    with patch("src.scrapers.kworb.requests.get") as mock_get:
        mock_get.side_effect = Exception("Timeout")
        songs = scrape_kworb()
        assert songs == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_scrapers.py::test_kworb_parses_chart -v`

- [ ] **Step 3: Implement `src/scrapers/kworb.py`**

```python
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

            # Third cell contains "Artist - Title"
            text = cells[2].get_text(strip=True)
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
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_scrapers.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/scrapers/kworb.py tests/test_scrapers.py
git commit -m "feat(v2): kworb.net Deezer Ukraine chart scraper"
```

---

### Task 6: Text Language Detection (glotlid)

**Files:**
- Create: `src/language/text_check.py`
- Create: `tests/test_language.py`

- [ ] **Step 1: Write test**

```python
# tests/test_language.py
from src.language.text_check import check_text_language


def test_detects_ukrainian_text():
    result = check_text_language("Привіт світе як справи сьогодні")
    assert result["language"] == "ukr"
    assert result["confidence"] > 0.5


def test_detects_russian_text():
    result = check_text_language("Привет мир как дела сегодня")
    assert result["language"] == "rus"
    assert result["confidence"] > 0.5


def test_handles_short_text():
    result = check_text_language("Ой")
    # Short text may not be reliable, but should not crash
    assert "language" in result
    assert "confidence" in result


def test_handles_latin_text():
    result = check_text_language("Hello world")
    assert result["language"] != "ukr"
    assert result["language"] != "rus"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_language.py -v`

- [ ] **Step 3: Implement `src/language/text_check.py`**

```python
# src/language/text_check.py
import logging
import os

import fasttext
from huggingface_hub import hf_hub_download

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    """Lazy-load the glotlid model."""
    global _model
    if _model is None:
        model_path = hf_hub_download(
            repo_id="cis-lmu/glotlid",
            filename="model.bin",
        )
        _model = fasttext.load_model(model_path)
        logger.info("glotlid model loaded")
    return _model


def check_text_language(text: str) -> dict:
    """Detect language of text using glotlid.

    Returns {"language": "ukr"|"rus"|..., "confidence": 0.0-1.0}
    """
    if not text or len(text.strip()) < 2:
        return {"language": "unknown", "confidence": 0.0}

    model = _get_model()
    # fasttext returns (('__label__ukr_Cyrl',), array([0.95]))
    predictions = model.predict(text.replace("\n", " "), k=1)
    label = predictions[0][0].replace("__label__", "").split("_")[0]
    confidence = float(predictions[1][0])

    return {"language": label, "confidence": confidence}
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_language.py -v`
Expected: 4 passed (first run downloads ~1.6GB model, may take a minute)

- [ ] **Step 5: Commit**

```bash
git add src/language/text_check.py tests/test_language.py
git commit -m "feat(v2): glotlid text language detection"
```

---

### Task 7: Audio Language Detection (mms-lid)

**Files:**
- Create: `src/language/audio_check.py`
- Modify: `tests/test_language.py`

- [ ] **Step 1: Write test**

Append to `tests/test_language.py`:

```python
from unittest.mock import patch, MagicMock
from src.language.audio_check import check_audio_language


def test_audio_check_returns_result_for_url():
    """Mock the model and verify the pipeline works."""
    mock_result = {"ukr": 0.92, "rus": 0.05}
    with patch("src.language.audio_check._classify_audio", return_value=mock_result):
        result = check_audio_language("https://example.com/preview.mp3")
        assert result["language"] == "ukr"
        assert result["confidence"] > 0.5


def test_audio_check_returns_unknown_for_none():
    result = check_audio_language(None)
    assert result["language"] == "unknown"
    assert result["confidence"] == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_language.py::test_audio_check_returns_result_for_url -v`

- [ ] **Step 3: Implement `src/language/audio_check.py`**

```python
# src/language/audio_check.py
import io
import logging
import tempfile

import requests
import torch
import torchaudio
from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

logger = logging.getLogger(__name__)

_model = None
_extractor = None
_MODEL_ID = "facebook/mms-lid-4017"


def _load_model():
    """Lazy-load the MMS language identification model."""
    global _model, _extractor
    if _model is None:
        logger.info(f"Loading {_MODEL_ID}...")
        _extractor = AutoFeatureExtractor.from_pretrained(_MODEL_ID)
        _model = AutoModelForAudioClassification.from_pretrained(_MODEL_ID)
        _model.eval()
        logger.info("MMS-LID model loaded")
    return _model, _extractor


def _classify_audio(audio_url: str) -> dict[str, float]:
    """Download audio and classify language. Returns {lang_code: probability}."""
    model, extractor = _load_model()

    # Download preview MP3
    resp = requests.get(audio_url, timeout=15)
    resp.raise_for_status()

    # Save to temp file and load with torchaudio
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as f:
        f.write(resp.content)
        f.flush()
        waveform, sample_rate = torchaudio.load(f.name)

    # Resample to 16kHz if needed
    if sample_rate != 16000:
        resampler = torchaudio.transforms.Resample(sample_rate, 16000)
        waveform = resampler(waveform)

    # Use first channel, limit to 30 seconds
    waveform = waveform[0][:16000 * 30]

    inputs = extractor(waveform.numpy(), sampling_rate=16000, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)

    probs = torch.softmax(outputs.logits, dim=-1)[0]
    id2label = model.config.id2label

    # Get top results
    top_indices = torch.topk(probs, k=5).indices
    results = {}
    for idx in top_indices:
        label = id2label[idx.item()]
        results[label] = float(probs[idx])

    return results


def check_audio_language(preview_url: str | None) -> dict:
    """Check what language a song is sung in.

    Returns {"language": "ukr"|"rus"|..., "confidence": 0.0-1.0}
    """
    if not preview_url:
        return {"language": "unknown", "confidence": 0.0}

    try:
        scores = _classify_audio(preview_url)
        top_lang = max(scores, key=scores.get)
        return {"language": top_lang, "confidence": scores[top_lang]}
    except Exception as e:
        logger.warning(f"Audio language check failed: {e}")
        return {"language": "unknown", "confidence": 0.0}
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_language.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/language/audio_check.py tests/test_language.py
git commit -m "feat(v2): MMS-LID audio language detection"
```

---

### Task 8: Filter (Whitelist/Blacklist/Not-Sure)

**Files:**
- Rewrite: `src/filter.py`
- Create: `tests/test_filter.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_filter.py
import json
import pytest
from src.filter import TrackFilter


@pytest.fixture
def data_dir(tmp_path):
    empty = {"tracks": {}}
    (tmp_path / "whitelist.json").write_text(json.dumps(empty))
    (tmp_path / "blacklist.json").write_text(json.dumps(empty))
    (tmp_path / "not_sure.json").write_text(json.dumps(empty))
    return tmp_path


@pytest.fixture
def filter_instance(data_dir):
    return TrackFilter(
        whitelist_path=str(data_dir / "whitelist.json"),
        blacklist_path=str(data_dir / "blacklist.json"),
        not_sure_path=str(data_dir / "not_sure.json"),
    )


def test_new_track_goes_to_not_sure(filter_instance, data_dir):
    track = {"id": "t1", "name": "Пісня", "artist": "Артист", "uri": "spotify:track:t1"}
    result = filter_instance.classify(track, language_info="ukr (0.9)")
    assert result == "review"

    ns = json.loads((data_dir / "not_sure.json").read_text())
    assert "t1" in ns["tracks"]


def test_whitelisted_track_is_allowed(data_dir):
    wl = {"tracks": {"t1": {"name": "Test", "playlist": "party"}}}
    (data_dir / "whitelist.json").write_text(json.dumps(wl))

    f = TrackFilter(
        whitelist_path=str(data_dir / "whitelist.json"),
        blacklist_path=str(data_dir / "blacklist.json"),
        not_sure_path=str(data_dir / "not_sure.json"),
    )
    track = {"id": "t1", "name": "Test", "artist": "A", "uri": "x"}
    assert f.classify(track) == "allow"


def test_blacklisted_track_is_rejected(data_dir):
    bl = {"tracks": {"t1": {}}}
    (data_dir / "blacklist.json").write_text(json.dumps(bl))

    f = TrackFilter(
        whitelist_path=str(data_dir / "whitelist.json"),
        blacklist_path=str(data_dir / "blacklist.json"),
        not_sure_path=str(data_dir / "not_sure.json"),
    )
    track = {"id": "t1", "name": "Bad", "artist": "A", "uri": "x"}
    assert f.classify(track) == "reject"


def test_already_in_not_sure_skips(data_dir):
    ns = {"tracks": {"t1": {"name": "Old"}}}
    (data_dir / "not_sure.json").write_text(json.dumps(ns))

    f = TrackFilter(
        whitelist_path=str(data_dir / "whitelist.json"),
        blacklist_path=str(data_dir / "blacklist.json"),
        not_sure_path=str(data_dir / "not_sure.json"),
    )
    track = {"id": "t1", "name": "Old", "artist": "A", "uri": "x"}
    assert f.classify(track) == "skip"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_filter.py -v`

- [ ] **Step 3: Implement `src/filter.py`**

```python
# src/filter.py
import json
import logging

logger = logging.getLogger(__name__)


def _load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class TrackFilter:
    """Whitelist-only filter. Every song must be manually approved."""

    def __init__(self, whitelist_path="data/whitelist.json",
                 blacklist_path="data/blacklist.json",
                 not_sure_path="data/not_sure.json"):
        self._wl_path = whitelist_path
        self._bl_path = blacklist_path
        self._ns_path = not_sure_path

        self._whitelist = _load(whitelist_path)
        self._blacklist = _load(blacklist_path)
        self._not_sure = _load(not_sure_path)

        self._wl_ids = set(self._whitelist["tracks"].keys())
        self._bl_ids = set(self._blacklist["tracks"].keys())
        self._ns_ids = set(self._not_sure["tracks"].keys())

        logger.info(
            f"Filter: {len(self._wl_ids)} whitelisted, "
            f"{len(self._bl_ids)} blacklisted, "
            f"{len(self._ns_ids)} pending"
        )

    def classify(self, track: dict, language_info: str = "") -> str:
        """Classify a track: 'allow', 'reject', 'skip', or 'review'.

        - allow: whitelisted
        - reject: blacklisted
        - skip: already in not_sure
        - review: new track, added to not_sure
        """
        track_id = track["id"]

        if track_id in self._wl_ids:
            return "allow"
        if track_id in self._bl_ids:
            return "reject"
        if track_id in self._ns_ids:
            return "skip"

        # New track — add to review queue
        self._not_sure["tracks"][track_id] = {
            "name": track.get("name", ""),
            "artist": track.get("artist", ""),
            "uri": track.get("uri", ""),
            "source": track.get("source", ""),
            "language_check": language_info,
        }
        self._ns_ids.add(track_id)
        _save(self._ns_path, self._not_sure)
        return "review"

    def get_whitelist_by_playlist(self) -> dict[str, list[str]]:
        """Return {playlist_name: [track_uri, ...]} from whitelist."""
        playlists: dict[str, list[str]] = {}
        for track_id, info in self._whitelist["tracks"].items():
            playlist = info.get("playlist", "")
            uri = info.get("uri", "")
            if playlist and uri:
                playlists.setdefault(playlist, []).append(uri)
        return playlists
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_filter.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/filter.py tests/test_filter.py
git commit -m "feat(v2): whitelist-only track filter"
```

---

### Task 9: Discovery Entry Point

**Files:**
- Create: `src/discover.py`

- [ ] **Step 1: Implement `src/discover.py`**

```python
# src/discover.py
"""Entry point: discover Ukrainian songs and queue for review.

Usage: python -m src.discover
"""
import logging
import os
import sys

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
    import yaml
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

    for song in unique_songs:
        name = song["name"]
        artist = song["artist"]

        # 4. Text language check (fast pre-filter)
        text = f"{name} {artist}"
        text_result = check_text_language(text)
        if text_result["language"] == "rus" and text_result["confidence"] > 0.8:
            logger.info(f"Rejected (text=rus): {artist} — {name}")
            rejected_text += 1
            continue

        # 5. Find on Spotify
        track = sp.search_track(name, artist)
        if not track:
            not_on_spotify += 1
            continue

        # 6. Audio language check
        preview_url = track.get("preview_url")
        audio_result = check_audio_language(preview_url)

        if audio_result["language"] == "rus" and audio_result["confidence"] > 0.7:
            logger.info(f"Rejected (audio=rus): {artist} — {name}")
            rejected_audio += 1
            continue

        # 7. Build track info and classify
        lang_info = f"text={text_result['language']}({text_result['confidence']:.2f}) audio={audio_result['language']}({audio_result['confidence']:.2f})"
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
```

- [ ] **Step 2: Commit**

```bash
git add src/discover.py
git commit -m "feat(v2): discovery entry point — scrape + language check + queue"
```

---

### Task 10: Playlist Update Entry Point

**Files:**
- Create: `src/update_playlists.py`

- [ ] **Step 1: Implement `src/update_playlists.py`**

```python
# src/update_playlists.py
"""Entry point: push whitelisted songs to Spotify playlists.

Usage: python -m src.update_playlists
"""
import logging
import sys

import yaml

from src.spotify_client import SpotifyClient
from src.filter import TrackFilter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)
logger = logging.getLogger(__name__)


def main():
    logger.info("=== Updating Spotify playlists ===")

    with open("config/playlists.yaml", "r") as f:
        config = yaml.safe_load(f)

    playlist_ids = config["playlists"]
    sp = SpotifyClient()
    track_filter = TrackFilter()

    playlists = track_filter.get_whitelist_by_playlist()

    for name, spotify_id in playlist_ids.items():
        uris = playlists.get(name, [])
        if uris:
            sp.replace_playlist(spotify_id, uris)
            logger.info(f"Updated '{name}' with {len(uris)} tracks")
        else:
            logger.warning(f"No whitelisted tracks for '{name}' — skipping")

    logger.info("=== Playlists updated ===")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add src/update_playlists.py
git commit -m "feat(v2): playlist update entry point — whitelist → Spotify"
```

---

### Task 11: Review Script

**Files:**
- Rewrite: `scripts/review.py`

- [ ] **Step 1: Implement `scripts/review.py`**

```python
#!/usr/bin/env python3
"""Interactive review of discovered tracks.

For each track in not_sure.json:
- Listen on Spotify
- Assign to a playlist (whitelist) or reject (blacklist)

Usage: python scripts/review.py
"""
import json
import subprocess
import sys

PLAYLIST_KEYS = {
    "d": "daytime",
    "e": "evening",
    "f": "folk",
    "p": "party",
    "w": "waltz",
    "r": "rave",
}


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    not_sure = load("data/not_sure.json")
    whitelist = load("data/whitelist.json")
    blacklist = load("data/blacklist.json")

    tracks = list(not_sure["tracks"].items())
    if not tracks:
        print("No tracks to review!")
        return

    print(f"\n{len(tracks)} tracks to review.\n")
    print("Commands:")
    print("  d=daytime  e=evening  f=folk  p=party  w=waltz  r=rave")
    print("  b=blacklist  s=skip  o=open in Spotify  q=quit\n")

    reviewed = 0
    for track_id, info in tracks:
        artist = info.get("artist", "?")
        name = info.get("name", "?")
        source = info.get("source", "?")
        lang = info.get("language_check", "?")

        print(f"--- {artist} — {name}")
        print(f"    Source: {source} | Language: {lang}")

        while True:
            choice = input("    > ").strip().lower()

            if choice == "o":
                url = f"https://open.spotify.com/track/{track_id}"
                subprocess.run(["open", url], check=False)
                continue
            elif choice == "q":
                save("data/not_sure.json", not_sure)
                save("data/whitelist.json", whitelist)
                save("data/blacklist.json", blacklist)
                print(f"\nSaved. Reviewed {reviewed} tracks.")
                return
            elif choice == "b":
                blacklist["tracks"][track_id] = {}
                del not_sure["tracks"][track_id]
                print(f"    → Blacklisted")
                reviewed += 1
                break
            elif choice == "s":
                print(f"    → Skipped")
                break
            elif choice in PLAYLIST_KEYS:
                playlist = PLAYLIST_KEYS[choice]
                whitelist["tracks"][track_id] = {
                    "name": name,
                    "artist": artist,
                    "uri": info.get("uri", ""),
                    "playlist": playlist,
                }
                del not_sure["tracks"][track_id]
                print(f"    → {playlist}")
                reviewed += 1
                break
            else:
                print("    Invalid. Use d/e/f/p/w/r/b/s/o/q")

    save("data/not_sure.json", not_sure)
    save("data/whitelist.json", whitelist)
    save("data/blacklist.json", blacklist)
    print(f"\nDone! Reviewed {reviewed} tracks.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
chmod +x scripts/review.py
git add scripts/review.py
git commit -m "feat(v2): interactive review script with playlist assignment"
```

---

### Task 12: Clean Up Old Code & Final Verification

**Files:**
- Delete: `src/collector.py`, `src/playlist_builder.py`, `src/lyrics_verifier.py`, `src/discovery.py` (old), `src/main.py`
- Delete: `tests/test_collector.py`, `tests/test_playlist_builder.py`, `tests/test_main.py`
- Delete: `data/russian_artists_blocklist.json`, `data/verified_ukrainian_artists.json`, `data/songs/`
- Update: `.gitignore`

- [ ] **Step 1: Remove old files**

```bash
rm -f src/collector.py src/playlist_builder.py src/lyrics_verifier.py src/main.py
rm -f tests/test_collector.py tests/test_playlist_builder.py tests/test_main.py
rm -f data/russian_artists_blocklist.json data/verified_ukrainian_artists.json
rm -rf data/songs/
```

- [ ] **Step 2: Update `.gitignore`**

Add to `.gitignore`:
```
.venv/
__pycache__/
*.pyc
.cache
*.bin
```

The `*.bin` line prevents accidentally committing the large HuggingFace model files.

- [ ] **Step 3: Run all tests**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: All tests pass (test_spotify_client: 2, test_scrapers: 6, test_language: 6, test_filter: 4 = 18 tests)

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(v2): clean up old v1 code, finalize project structure"
```

- [ ] **Step 5: Push**

```bash
git push
```
