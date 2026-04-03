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
