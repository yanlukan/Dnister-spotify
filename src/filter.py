import json
import logging

logger = logging.getLogger(__name__)


def _load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class TrackFilter:
    """Whitelist-only filter. Every song must be manually approved."""

    def __init__(self, whitelist_path="data/whitelist.json",
                 blacklist_path="data/blacklist.json",
                 not_sure_path="data/not_sure.json"):
        self._wl_path = whitelist_path
        self._bl_path = blacklist_path
        self._ns_path = not_sure_path

        self._whitelist = _load(whitelist_path)
        self._blacklist = _load(blacklist_path)
        self._not_sure = _load(not_sure_path)

        self._wl_ids = set(self._whitelist["tracks"].keys())
        self._bl_ids = set(self._blacklist["tracks"].keys())
        self._ns_ids = set(self._not_sure["tracks"].keys())

        logger.info(
            f"Filter: {len(self._wl_ids)} whitelisted, "
            f"{len(self._bl_ids)} blacklisted, "
            f"{len(self._ns_ids)} pending"
        )

    def classify(self, track: dict, language_info: str = "") -> str:
        """Classify a track: 'allow', 'reject', 'skip', or 'review'."""
        track_id = track["id"]

        if track_id in self._wl_ids:
            return "allow"
        if track_id in self._bl_ids:
            return "reject"
        if track_id in self._ns_ids:
            return "skip"

        self._not_sure["tracks"][track_id] = {
            "name": track.get("name", ""),
            "artist": track.get("artist", ""),
            "uri": track.get("uri", ""),
            "source": track.get("source", ""),
            "language_check": language_info,
        }
        self._ns_ids.add(track_id)
        _save(self._ns_path, self._not_sure)
        return "review"

    def get_whitelist_by_playlist(self) -> dict[str, list[str]]:
        """Return {playlist_name: [track_uri, ...]} from whitelist."""
        playlists: dict[str, list[str]] = {}
        for track_id, info in self._whitelist["tracks"].items():
            playlist = info.get("playlist", "")
            uri = info.get("uri", "")
            if playlist and uri:
                playlists.setdefault(playlist, []).append(uri)
        return playlists
