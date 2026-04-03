import pytest
from unittest.mock import MagicMock, patch, mock_open

from src.main import PlaylistManager


@pytest.fixture
def mock_config():
    return {
        "playlists": [
            {
                "name": "Test Playlist",
                "spotify_id": "pl_123",
                "description": "Test desc",
                "genres": ["ukrainian pop"],
                "max_tracks": 50,
            }
        ],
        "source_playlists": [],
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

        mgr = PlaylistManager(
            config_path="config/playlists.yaml",
            blocklist_path="data/russian_artists_blocklist.json",
        )

        mgr._mock_collector = MockCollector.return_value
        mgr._mock_filter = MockFilter.return_value
        mgr._mock_builder = MockBuilder.return_value
        mgr._mock_sp = mock_sp
        return mgr


def test_run_updates_playlist_with_assigned_tracks(manager):
    track = {"id": "t1", "uri": "spotify:track:t1", "name": "Song"}
    manager._mock_collector.collect_all.return_value = [track]
    manager._mock_filter.filter_tracks.return_value = ([track], [])
    manager._mock_builder.assign_tracks.return_value = {"Test Playlist": [track]}

    manager.run()

    manager._mock_sp.replace_playlist_tracks.assert_called_once_with(
        "pl_123", ["spotify:track:t1"]
    )


def test_run_skips_empty_playlists(manager):
    manager._mock_collector.collect_all.return_value = []
    manager._mock_filter.filter_tracks.return_value = ([], [])
    manager._mock_builder.assign_tracks.return_value = {"Test Playlist": []}

    manager.run()

    manager._mock_sp.replace_playlist_tracks.assert_not_called()
