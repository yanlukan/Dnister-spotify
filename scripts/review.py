#!/usr/bin/env python3
"""Interactive review of discovered tracks.

For each track in not_sure.json:
- Listen on Spotify
- Assign to a playlist (whitelist) or reject (blacklist)

Usage: python scripts/review.py
"""
import json
import subprocess
import sys

PLAYLIST_KEYS = {
    "d": "daytime",
    "e": "evening",
    "f": "folk",
    "p": "party",
    "w": "waltz",
    "r": "rave",
}


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    not_sure = load("data/not_sure.json")
    whitelist = load("data/whitelist.json")
    blacklist = load("data/blacklist.json")

    tracks = list(not_sure["tracks"].items())
    if not tracks:
        print("No tracks to review!")
        return

    print(f"\n{len(tracks)} tracks to review.\n")
    print("Commands:")
    print("  d=daytime  e=evening  f=folk  p=party  w=waltz  r=rave")
    print("  b=blacklist  s=skip  o=open in Spotify  q=quit\n")

    reviewed = 0
    for track_id, info in tracks:
        artist = info.get("artist", "?")
        name = info.get("name", "?")
        source = info.get("source", "?")
        lang = info.get("language_check", "?")

        print(f"--- {artist} — {name}")
        print(f"    Source: {source} | Language: {lang}")

        while True:
            choice = input("    > ").strip().lower()

            if choice == "o":
                url = f"https://open.spotify.com/track/{track_id}"
                subprocess.run(["open", url], check=False)
                continue
            elif choice == "q":
                save("data/not_sure.json", not_sure)
                save("data/whitelist.json", whitelist)
                save("data/blacklist.json", blacklist)
                print(f"\nSaved. Reviewed {reviewed} tracks.")
                return
            elif choice == "b":
                blacklist["tracks"][track_id] = {}
                del not_sure["tracks"][track_id]
                print(f"    → Blacklisted")
                reviewed += 1
                break
            elif choice == "s":
                print(f"    → Skipped")
                break
            elif choice in PLAYLIST_KEYS:
                playlist = PLAYLIST_KEYS[choice]
                whitelist["tracks"][track_id] = {
                    "name": name,
                    "artist": artist,
                    "uri": info.get("uri", ""),
                    "playlist": playlist,
                }
                del not_sure["tracks"][track_id]
                print(f"    → {playlist}")
                reviewed += 1
                break
            else:
                print("    Invalid. Use d/e/f/p/w/r/b/s/o/q")

    save("data/not_sure.json", not_sure)
    save("data/whitelist.json", whitelist)
    save("data/blacklist.json", blacklist)
    print(f"\nDone! Reviewed {reviewed} tracks.")


if __name__ == "__main__":
    main()
