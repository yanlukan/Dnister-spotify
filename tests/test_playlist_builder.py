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
