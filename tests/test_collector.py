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
        "genre:ukrainian pop", limit=50
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
