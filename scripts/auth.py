#!/usr/bin/env python3
"""One-time OAuth helper to get a Spotify refresh token.

Usage:
  1. Create a Spotify app at https://developer.spotify.com/dashboard
  2. Set redirect URI to http://127.0.0.1:3000/callback in the app settings
  3. Run: SPOTIFY_CLIENT_ID=xxx SPOTIFY_CLIENT_SECRET=yyy python scripts/auth.py
  4. Open the URL printed in the terminal, authorize, and paste back the redirect URL
  5. Copy the refresh token to your GitHub repo secrets as SPOTIFY_REFRESH_TOKEN
"""
import os
import sys

import spotipy
from spotipy.oauth2 import SpotifyOAuth

REDIRECT_URI = "http://127.0.0.1:3000/callback"
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
        redirect_uri=REDIRECT_URI,
        scope=SCOPES,
        open_browser=False,
    )

    auth_url = auth_manager.get_authorize_url()
    print(f"\n1. Open this URL in your browser:\n")
    print(f"   {auth_url}\n")
    print(f"2. Authorize the app")
    print(f"3. You'll be redirected to a page that won't load (that's OK)")
    print(f"4. Copy the FULL URL from your browser's address bar and paste it here:\n")

    response_url = input("Paste URL here: ").strip()

    code = auth_manager.parse_response_code(response_url)
    token_info = auth_manager.get_access_token(code, as_dict=True)

    if token_info and "refresh_token" in token_info:
        # Verify it works
        sp = spotipy.Spotify(auth=token_info["access_token"])
        user = sp.current_user()
        print(f"\nAuthenticated as: {user['display_name']} ({user['id']})")

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
