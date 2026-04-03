import logging
import random

logger = logging.getLogger(__name__)


class PlaylistBuilder:
    """Assigns tracks to playlists based on energy/mood audio features."""

    def __init__(self, spotify_client):
        self.sp = spotify_client

    def assign_tracks(
        self, tracks: list[dict], playlist_configs: list[dict]
    ) -> dict[str, list[dict]]:
        """Assign tracks to playlists by energy range.

        Each track goes to the playlist whose energy range is the best fit
        (closest to the midpoint). A track appears in at most one playlist.

        Returns: {playlist_name: [track, ...]}
        """
        assignments: dict[str, list[dict]] = {
            cfg["name"]: [] for cfg in playlist_configs
        }

        # Fetch audio features in batches of 100
        track_features: dict[str, dict] = {}
        track_ids = [t["id"] for t in tracks]
        for i in range(0, len(track_ids), 100):
            batch = track_ids[i : i + 100]
            features = self.sp.get_audio_features(batch)
            for feat in features:
                if feat is not None:
                    track_features[feat["id"]] = feat

        # Build a lookup from track id to track dict
        track_map = {t["id"]: t for t in tracks}

        # Shuffle to avoid always picking the same tracks when capping
        shuffled_ids = list(track_features.keys())
        random.shuffle(shuffled_ids)

        assigned_ids: set[str] = set()

        for track_id in shuffled_ids:
            if track_id in assigned_ids:
                continue

            feat = track_features[track_id]
            energy = feat["energy"]

            # Find best-fit playlist
            best_playlist = None
            best_distance = float("inf")

            for cfg in playlist_configs:
                name = cfg["name"]
                e_min = cfg["energy_min"]
                e_max = cfg["energy_max"]

                if e_min <= energy <= e_max and len(assignments[name]) < cfg["max_tracks"]:
                    midpoint = (e_min + e_max) / 2
                    distance = abs(energy - midpoint)
                    if distance < best_distance:
                        best_distance = distance
                        best_playlist = name

            if best_playlist:
                assignments[best_playlist].append(track_map[track_id])
                assigned_ids.add(track_id)

        for name, assigned in assignments.items():
            logger.info(f"Playlist '{name}': {len(assigned)} tracks assigned")

        return assignments
