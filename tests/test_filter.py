import json
import pytest
from unittest.mock import MagicMock, patch
from langdetect import DetectorFactory

DetectorFactory.seed = 0

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
