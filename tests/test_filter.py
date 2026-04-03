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
