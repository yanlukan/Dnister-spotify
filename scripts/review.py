#!/usr/bin/env python3
"""Review tracks in the not-sure list.

For each track, opens it in Spotify and asks: whitelist, blacklist, or skip.
Approved tracks go to whitelist.json, rejected to blacklist.json.

Usage: python scripts/review.py
"""
import json
import subprocess
import sys


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    not_sure = load_json("data/not_sure.json")
    whitelist = load_json("data/whitelist.json")
    blacklist = load_json("data/blacklist.json")

    tracks = list(not_sure["tracks"].items())
    if not tracks:
        print("No tracks to review!")
        return

    print(f"\n{len(tracks)} tracks to review.\n")
    print("Commands: [w] whitelist  [b] blacklist  [s] skip  [o] open in Spotify  [q] quit\n")

    reviewed = 0
    for track_id, info in tracks:
        print(f"--- {info['artists']}")
        print(f"    Reason: {info['reason']}")
        print(f"    URI: {info['uri']}")

        while True:
            choice = input("    [w/b/s/o/q]: ").strip().lower()

            if choice == "o":
                # Open in Spotify
                url = f"https://open.spotify.com/track/{track_id}"
                subprocess.run(["open", url], check=False)
                continue
            elif choice == "w":
                whitelist["tracks"][track_id] = info
                del not_sure["tracks"][track_id]
                print("    → Whitelisted")
                reviewed += 1
                break
            elif choice == "b":
                blacklist["tracks"][track_id] = info
                del not_sure["tracks"][track_id]
                print("    → Blacklisted")
                reviewed += 1
                break
            elif choice == "s":
                print("    → Skipped")
                break
            elif choice == "q":
                print(f"\nReviewed {reviewed} tracks.")
                save_json("data/not_sure.json", not_sure)
                save_json("data/whitelist.json", whitelist)
                save_json("data/blacklist.json", blacklist)
                return
            else:
                print("    Invalid choice. Use w/b/s/o/q")

    print(f"\nDone! Reviewed {reviewed} tracks.")
    save_json("data/not_sure.json", not_sure)
    save_json("data/whitelist.json", whitelist)
    save_json("data/blacklist.json", blacklist)


if __name__ == "__main__":
    main()
