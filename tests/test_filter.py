import json
import pytest
from langdetect import DetectorFactory

DetectorFactory.seed = 0

from src.filter import ContentFilter


@pytest.fixture
def data_dir(tmp_path):
    """Create all required data files."""
    blocklist = {
        "artists": [
            {"name": "Русский Артист", "id": "russian_id_1"},
            {"name": "Другой Русский", "id": "russian_id_2"},
        ]
    }
    (tmp_path / "blocklist.json").write_text(json.dumps(blocklist))

    verified = {"artists": ["KAZKA", "Калуш Оркестра"]}
    (tmp_path / "verified.json").write_text(json.dumps(verified))

    empty_list = {"tracks": {}}
    (tmp_path / "whitelist.json").write_text(json.dumps(empty_list))
    (tmp_path / "blacklist.json").write_text(json.dumps(empty_list))
    (tmp_path / "not_sure.json").write_text(json.dumps(empty_list))

    return tmp_path


@pytest.fixture
def filter_instance(data_dir):
    return ContentFilter(
        blocklist_path=str(data_dir / "blocklist.json"),
        verified_artists_path=str(data_dir / "verified.json"),
        whitelist_path=str(data_dir / "whitelist.json"),
        blacklist_path=str(data_dir / "blacklist.json"),
        not_sure_path=str(data_dir / "not_sure.json"),
    )


def _make_track(track_name, artist_id, artist_name, album_name=None):
    return {
        "id": f"track_{track_name}",
        "name": track_name,
        "uri": f"spotify:track:track_{track_name}",
        "album": {"name": album_name or f"Альбом {track_name}"},
        "artists": [{"id": artist_id, "name": artist_name}],
    }


def test_allows_verified_artist(filter_instance):
    track = _make_track("Стефанія", "uid", "Калуш Оркестра")
    decision, _ = filter_instance.classify(track)
    assert decision == "allow"


def test_rejects_blocklisted_artist(filter_instance):
    track = _make_track("Пісня", "russian_id_1", "Русский Артист")
    decision, reason = filter_instance.classify(track)
    assert decision == "reject"
    assert "blocklist" in reason.lower()


def test_rejects_featured_russian_artist(filter_instance):
    track = _make_track("Колаб", "uid", "Українець")
    track["artists"].append({"id": "russian_id_2", "name": "Другой Русский"})
    decision, _ = filter_instance.classify(track)
    assert decision == "reject"


def test_rejects_non_cyrillic_track(filter_instance):
    track = _make_track("Good Vibes", "sid", "Some Artist", "Some Album")
    decision, reason = filter_instance.classify(track)
    assert decision == "reject"
    assert "non-ukrainian" in reason.lower()


def test_not_sure_for_unknown_artist(filter_instance):
    """Unknown Cyrillic artist goes to not-sure, not auto-approved."""
    track = _make_track("Гарна Пісня", "uid", "Невідомий Гурт")
    decision, reason = filter_instance.classify(track)
    assert decision == "not_sure"
    assert "review" in reason.lower()


def test_whitelisted_track_always_allowed(data_dir):
    # Pre-populate whitelist
    wl = {"tracks": {"track_123": {"name": "Test", "artists": "Test"}}}
    (data_dir / "whitelist.json").write_text(json.dumps(wl))

    f = ContentFilter(
        blocklist_path=str(data_dir / "blocklist.json"),
        verified_artists_path=str(data_dir / "verified.json"),
        whitelist_path=str(data_dir / "whitelist.json"),
        blacklist_path=str(data_dir / "blacklist.json"),
        not_sure_path=str(data_dir / "not_sure.json"),
    )
    track = {"id": "track_123", "name": "Test", "artists": [], "album": {"name": ""}}
    decision, _ = f.classify(track)
    assert decision == "allow"


def test_blacklisted_track_always_rejected(data_dir):
    bl = {"tracks": {"track_456": {"name": "Bad", "artists": "Bad"}}}
    (data_dir / "blacklist.json").write_text(json.dumps(bl))

    f = ContentFilter(
        blocklist_path=str(data_dir / "blocklist.json"),
        verified_artists_path=str(data_dir / "verified.json"),
        whitelist_path=str(data_dir / "whitelist.json"),
        blacklist_path=str(data_dir / "blacklist.json"),
        not_sure_path=str(data_dir / "not_sure.json"),
    )
    track = {"id": "track_456", "name": "Bad", "artists": [], "album": {"name": ""}}
    decision, _ = f.classify(track)
    assert decision == "reject"


def test_filter_tracks_saves_not_sure(filter_instance, data_dir):
    tracks = [_make_track("Щось Таке", "uid", "Невідомий Співак")]
    allowed, excluded = filter_instance.filter_tracks(tracks)
    assert len(allowed) == 0
    assert len(excluded) == 1

    # Check not_sure.json was updated
    ns = json.loads((data_dir / "not_sure.json").read_text())
    assert len(ns["tracks"]) == 1
