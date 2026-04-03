# Dnister Spotify Playlist Automation

Automated weekly Spotify playlist management for **Dnister** Ukrainian restaurant. Creates and maintains 4 mood-based playlists with Ukrainian music, filtering out all Russian content.

## Playlists

| Playlist | Vibe | Energy |
|----------|------|--------|
| Dnister Daytime | Chill indie/acoustic/jazz for lunch | Low |
| Dnister Evening | Modern pop & indie for dinner | Medium |
| Dnister Folk | Traditional folk & bandura | Low-Medium |
| Dnister Party | Upbeat hits for weekends | High |

## How It Works

1. **Collects** songs from Spotify Ukraine charts, editorial playlists, and genre searches
2. **Filters** out Russian content (artist blocklist + language detection)
3. **Assigns** tracks to playlists by energy level using Spotify audio features
4. **Updates** all 4 playlists on Spotify

Runs automatically every Monday via GitHub Actions.

## Setup

### 1. Create a Spotify App

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Set redirect URI to `http://localhost:8888/callback`
4. Note your Client ID and Client Secret

### 2. Get a Refresh Token

```bash
SPOTIFY_CLIENT_ID=your_id SPOTIFY_CLIENT_SECRET=your_secret python scripts/auth.py
```

Follow the browser prompt. Copy the refresh token from the output.

### 3. Add GitHub Secrets

In your repo: Settings > Secrets and variables > Actions > New repository secret

- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `SPOTIFY_REFRESH_TOKEN`

### 4. Run

The workflow runs automatically every Monday. To run manually:

Actions > Update Dnister Playlists > Run workflow

## Development

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

## Updating the Blocklist

Edit `data/russian_artists_blocklist.json` to add or remove artists. Each entry needs a `name` and Spotify `id`.
