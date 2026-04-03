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


def test_distributes_tracks_across_playlists(mock_spotify_client, playlist_config):
    tracks = [_make_track(f"t{i}") for i in range(6)]

    builder = PlaylistBuilder(mock_spotify_client)
    assignments = builder.assign_tracks(tracks, playlist_config)

    assert len(assignments["Chill"]) == 3
    assert len(assignments["Party"]) == 3


def test_respects_max_tracks(mock_spotify_client, playlist_config):
    tracks = [_make_track(f"t{i}") for i in range(10)]

    builder = PlaylistBuilder(mock_spotify_client)
    assignments = builder.assign_tracks(tracks, playlist_config)

    assert len(assignments["Chill"]) <= 3
    assert len(assignments["Party"]) <= 3


def test_track_assigned_to_one_playlist_only(mock_spotify_client, playlist_config):
    tracks = [_make_track(f"t{i}") for i in range(4)]

    builder = PlaylistBuilder(mock_spotify_client)
    assignments = builder.assign_tracks(tracks, playlist_config)

    all_ids = []
    for assigned in assignments.values():
        all_ids.extend(t["id"] for t in assigned)
    assert len(all_ids) == len(set(all_ids))


def test_handles_empty_tracks(mock_spotify_client, playlist_config):
    builder = PlaylistBuilder(mock_spotify_client)
    assignments = builder.assign_tracks([], playlist_config)

    assert len(assignments["Chill"]) == 0
    assert len(assignments["Party"]) == 0
