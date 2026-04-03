#!/usr/bin/env python3
"""One-time OAuth helper to get a Spotify refresh token.

Usage:
  1. Create a Spotify app at https://developer.spotify.com/dashboard
  2. Set redirect URI to http://localhost:8888/callback
  3. Run: SPOTIFY_CLIENT_ID=xxx SPOTIFY_CLIENT_SECRET=yyy python scripts/auth.py
  4. Follow the browser prompt to authorize
  5. Copy the refresh token to your GitHub repo secrets as SPOTIFY_REFRESH_TOKEN
"""
import os
import sys

import spotipy
from spotipy.oauth2 import SpotifyOAuth

SCOPES = "playlist-modify-public playlist-modify-private"


def main():
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("Error: Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET env vars.")
        print()
        print("Example:")
        print(
            "  SPOTIFY_CLIENT_ID=abc SPOTIFY_CLIENT_SECRET=xyz python scripts/auth.py"
        )
        sys.exit(1)

    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="http://localhost:8888/callback",
        scope=SCOPES,
        open_browser=True,
    )

    # This triggers the OAuth flow — opens browser, waits for callback
    sp = spotipy.Spotify(auth_manager=auth_manager)
    user = sp.current_user()
    print(f"\nAuthenticated as: {user['display_name']} ({user['id']})")

    token_info = auth_manager.get_cached_token()
    if token_info and "refresh_token" in token_info:
        print(f"\n{'=' * 60}")
        print("Your refresh token (add this to GitHub secrets):")
        print(f"{'=' * 60}")
        print(token_info["refresh_token"])
        print(f"{'=' * 60}")
        print("\nGitHub secret name: SPOTIFY_REFRESH_TOKEN")
    else:
        print("Error: Could not retrieve refresh token.")
        sys.exit(1)


if __name__ == "__main__":
    main()
