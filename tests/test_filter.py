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
            {"name": "Русский Артист", "id": "russian_id_1"},
            {"name": "Другой Русский", "id": "russian_id_2"},
        ]
    }
    path = tmp_path / "blocklist.json"
    path.write_text(json.dumps(blocklist))
    return str(path)


@pytest.fixture
def filter_instance(blocklist_path):
    return RussianContentFilter(blocklist_path)


def _make_track(track_name, artist_id, artist_name, album_name=None):
    """Helper to create a mock track dict."""
    return {
        "id": f"track_{track_name}",
        "name": track_name,
        "uri": f"spotify:track:track_{track_name}",
        "album": {"name": album_name or f"Альбом {track_name}"},
        "artists": [{"id": artist_id, "name": artist_name}],
    }


def test_allows_ukrainian_track(filter_instance):
    track = _make_track("Стефанія", "ukrainian_id", "Калуш Оркестра")
    allowed, reason = filter_instance.is_allowed(track)
    assert allowed is True


def test_blocks_blocklisted_artist(filter_instance):
    track = _make_track("Пісня", "russian_id_1", "Русский Артист")
    allowed, reason = filter_instance.is_allowed(track)
    assert allowed is False
    assert "blocklist" in reason.lower()


def test_blocks_featured_russian_artist(filter_instance):
    track = _make_track("Колаб", "ukrainian_id", "Українець")
    track["artists"].append({"id": "russian_id_2", "name": "Другой Русский"})
    allowed, reason = filter_instance.is_allowed(track)
    assert allowed is False


def test_blocks_russian_language_track_name(filter_instance):
    track = _make_track("Привет мир как дела сегодня", "unknown_id", "Невідомий")
    allowed, reason = filter_instance.is_allowed(track)
    assert allowed is False


def test_allows_ukrainian_language_track_name(filter_instance):
    track = _make_track("Привіт світе як справи сьогодні", "unknown_id", "Невідомий")
    allowed, reason = filter_instance.is_allowed(track)
    assert allowed is True


def test_blocks_non_ukrainian_track(filter_instance):
    """Tracks with no Cyrillic at all should be excluded."""
    track = _make_track("Good Vibes Only", "some_id", "Some Artist", "Some Album")
    allowed, reason = filter_instance.is_allowed(track)
    assert allowed is False
    assert "non-ukrainian" in reason.lower()


def test_filter_tracks_returns_allowed_only(filter_instance):
    tracks = [
        _make_track("Гарна Пісня", "uk_id", "Українська Співачка"),
        _make_track("Пісня", "russian_id_1", "Русский Артист"),
        _make_track("Ще Одна Пісня", "uk_id_2", "Український Гурт", "Збірка Хітів"),
    ]
    allowed, excluded = filter_instance.filter_tracks(tracks)
    assert len(allowed) == 2
    assert len(excluded) == 1
    assert excluded[0]["track"]["name"] == "Пісня"


def test_excluded_tracks_include_reason(filter_instance):
    tracks = [_make_track("Пісня", "russian_id_1", "Русский Артист")]
    _, excluded = filter_instance.filter_tracks(tracks)
    assert "reason" in excluded[0]
    assert "blocklist" in excluded[0]["reason"].lower()
