import logging
import random

logger = logging.getLogger(__name__)


class PlaylistBuilder:
    """Assigns tracks to playlists by shuffling and distributing evenly."""

    def __init__(self, spotify_client):
        self.sp = spotify_client

    def assign_tracks(
        self, tracks: list[dict], playlist_configs: list[dict]
    ) -> dict[str, list[dict]]:
        """Distribute tracks across playlists randomly.

        Shuffles all tracks and deals them out to playlists up to each
        playlist's max_tracks limit. Each track appears in at most one playlist.

        Returns: {playlist_name: [track, ...]}
        """
        assignments: dict[str, list[dict]] = {
            cfg["name"]: [] for cfg in playlist_configs
        }

        shuffled = list(tracks)
        random.shuffle(shuffled)

        # Round-robin distribute tracks across playlists
        playlist_idx = 0
        for track in shuffled:
            # Try each playlist starting from current index
            for attempt in range(len(playlist_configs)):
                idx = (playlist_idx + attempt) % len(playlist_configs)
                cfg = playlist_configs[idx]
                name = cfg["name"]
                if len(assignments[name]) < cfg["max_tracks"]:
                    assignments[name].append(track)
                    playlist_idx = (idx + 1) % len(playlist_configs)
                    break

        for name, assigned in assignments.items():
            logger.info(f"Playlist '{name}': {len(assigned)} tracks assigned")

        return assignments
