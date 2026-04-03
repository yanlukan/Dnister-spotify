# Dnister Spotify Playlist Automation

## Overview

Automated weekly Spotify playlist management for Dnister, a Ukrainian restaurant. The system creates and maintains 4 mood-based playlists populated with Ukrainian music, with robust filtering to exclude all Russian content due to the ongoing war in Ukraine.

## Goals

- Fully automatic playlist updates on a weekly schedule
- Multiple playlists matching different restaurant moods/times
- Broad song discovery via charts, editorial playlists, and genre search
- Reliable Russian content filtering (artist-level + language detection)
- Zero infrastructure cost (GitHub Actions)

## Architecture

```
GitHub Actions (weekly cron — Mondays 6:00 AM UTC)
    |
    v
+------------------------+
|   Playlist Manager     |  <- main orchestrator
|   (Python + Spotipy)   |
+--------+---------------+
         |
         +-- Song Collector -- pulls from Spotify charts, editorial playlists, genre searches
         |
         +-- Russian Filter -- artist origin check + language detection on track names
         |
         +-- Playlist Builder -- assigns songs to playlists by mood/genre using audio features
         |
         +-- Spotify Updater -- creates/updates the 4 Dnister playlists
```

Config-driven via YAML. Spotify credentials stored as GitHub Actions secrets.

## Song Collection

### Sources (queried in parallel)
- Spotify "Top 50 Ukraine" chart playlist
- Spotify editorial playlists (e.g., "Ukrainian Hits", "Ukrainian Indie")
- Genre-based search queries: "ukrainian pop", "ukrainian folk", "ukrainian indie", "ukrainian hip hop", "ukrainian rock"
- Artist top tracks from a seed list of known Ukrainian artists

### Processing
- Deduplicate by Spotify track ID before filtering
- Each playlist gets a configurable max track count (default: 50)
- Full replacement each week — no rotation logic needed

## Russian Content Filtering

Three layers of defense:

### Layer 1 — Artist origin check
- Check Spotify artist metadata for market/country info
- Cross-reference against a maintained blocklist of known Russian artists (stored as `data/russian_artists_blocklist.json` in the repo)

### Layer 2 — Language detection
- Use `langdetect` library on track names and album names
- Flag anything detected as Russian (`ru`) for exclusion
- For Cyrillic text: run Ukrainian (`uk`) vs Russian (`ru`) classifier to distinguish

### Layer 3 — Collaboration filter
- Check ALL artists on a track (primary + featured)
- If any artist is on the Russian blocklist, exclude the entire track

### Edge cases
- Belarusian artists singing in Ukrainian: allowed
- Ukrainian artist with a Russian-language track: excluded (language filter catches it)
- Instrumental tracks: allowed (no language to flag)

### Logging
Every excluded track is logged with the reason for review and blocklist tuning.

## Playlist Profiles

Defined in `config/playlists.yaml`:

### Dnister Daytime
- **Vibe:** Chill Ukrainian sounds for a relaxed lunch
- **Genres:** ukrainian indie, ukrainian acoustic, ukrainian jazz
- **Energy:** low
- **Max tracks:** 50

### Dnister Evening
- **Vibe:** Modern Ukrainian hits for dinner
- **Genres:** ukrainian pop, ukrainian r&b, ukrainian indie
- **Energy:** medium
- **Max tracks:** 50

### Dnister Folk
- **Vibe:** Traditional Ukrainian folk & bandura classics
- **Genres:** ukrainian folk, ukrainian traditional
- **Energy:** low-medium
- **Max tracks:** 50

### Dnister Party
- **Vibe:** Upbeat Ukrainian bangers for weekends
- **Genres:** ukrainian pop, ukrainian hip hop, ukrainian rock
- **Energy:** high
- **Max tracks:** 50

Energy filtering uses Spotify's audio features API (`energy`, `valence`, `tempo`) to match songs to the right playlist mood.

## GitHub Actions & Deployment

### Workflow: `.github/workflows/update-playlists.yml`
- **Schedule:** Every Monday at 6:00 AM UTC via cron
- **Manual trigger:** `workflow_dispatch` for on-demand runs
- **Steps:**
  1. Checkout repo
  2. Set up Python + install dependencies
  3. Run playlist manager script
  4. Log results (tracks added/removed/filtered per playlist)

### Secrets (stored in GitHub repo settings)
- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `SPOTIFY_REFRESH_TOKEN`

### Initial setup
One-time OAuth flow via `scripts/auth.py` helper script. Run locally once, copy the refresh token to GitHub secrets.

### Error handling
If Spotify API fails, workflow retries once. On second failure, existing playlists stay untouched (no empty playlist risk).

## Tech Stack

- **Language:** Python 3.12+
- **Spotify API:** Spotipy library
- **Language detection:** langdetect library
- **CI/CD:** GitHub Actions
- **Config:** YAML (playlist definitions)
- **Data:** JSON (Russian artists blocklist)

## Project Structure

```
Dnister-spotify/
  config/
    playlists.yaml          # Playlist definitions
  data/
    russian_artists_blocklist.json  # Known Russian artists to exclude
  src/
    main.py                 # Entry point / orchestrator
    collector.py            # Song collection from multiple sources
    filter.py               # Russian content filtering (3 layers)
    playlist_builder.py     # Assign songs to playlists by mood/audio features
    spotify_client.py       # Spotipy wrapper / auth handling
  scripts/
    auth.py                 # One-time OAuth helper for getting refresh token
  tests/
    test_collector.py
    test_filter.py
    test_playlist_builder.py
  .github/
    workflows/
      update-playlists.yml  # Weekly cron workflow
  requirements.txt
  README.md
```
