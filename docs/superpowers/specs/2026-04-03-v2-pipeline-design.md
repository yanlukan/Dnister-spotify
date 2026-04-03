# Dnister Spotify v2 — Discovery + Review Pipeline

## Overview

Complete rebuild of the playlist system. External sources discover Ukrainian songs, AI verifies language, human reviews every track, Spotify only used for playback.

## Goals

- Every song in a playlist is manually approved — zero auto-approves
- Song discovery from Ukrainian music charts, not Spotify search
- AI language detection filters out Russian before human review
- Each song assigned to a specific playlist by the reviewer
- Three separate commands: discover, review, update

## Architecture

```
DISCOVERY (python -m src.discover):
  Hit FM scraper ──┐
  Last.fm API ─────┤──→ Deduplicate ──→ Language Check ──→ not_sure.json
  kworb.net chart ─┘    (by artist+      (glotlid text +
                          track name)      mms-lid audio)

REVIEW (python scripts/review.py):
  not_sure.json ──→ Interactive CLI ──→ whitelist.json OR blacklist.json
                    (listen on Spotify,
                     assign to playlist)

UPDATE (python -m src.update_playlists):
  whitelist.json ──→ Group by playlist ──→ Spotify /items API ──→ Done
```

## Song Discovery Sources

### Hit FM Ukraine
- URL: `https://www.hitfm.ua/playlist/`
- Method: Scrape embedded `songsFound` JSON from page source
- Fields: `singer`, `song`
- Frequency: Daily playlist data

### Last.fm API
- Endpoint: `tag.getTopTracks`
- Tags: `ukrainian`, `ukrainian pop`, `ukrainian folk`, `ukrainian rock`, `ukrainian electronic`, `ukrainian hip-hop`
- Returns: Top 50 tracks per tag with artist + track name
- Auth: Free API key from https://www.last.fm/api

### kworb.net Deezer UA Chart
- URL: `https://kworb.net/charts/deezer/ua.html`
- Method: Scrape HTML table
- Fields: Artist, Title
- Returns: Ukraine top 100

### Deduplication
All sources merge into one list. Deduplicate by normalized `(artist_name.lower(), track_name.lower())`.

## Language Verification

### Layer 1 — Text (fast)
- Model: `cis-lmu/glotlid` (FastText, 2102 languages)
- Input: Track name + artist name concatenated
- If Russian (`rus`) with high confidence → auto-reject
- Otherwise → proceed to Layer 2

### Layer 2 — Audio (definitive)
- Model: `facebook/mms-lid-4017` (Wav2Vec2, 4017 languages)
- Input: Spotify 30-second preview MP3 (free, URL in track metadata)
- If Ukrainian (`ukr`) → queue for review
- If Russian (`rus`) → auto-reject
- If instrumental/no preview → queue for review with note

## Data Files

### `data/not_sure.json` — Review Queue
```json
{
  "tracks": {
    "spotify_track_id": {
      "name": "Song Name",
      "artist": "Artist Name",
      "uri": "spotify:track:xxx",
      "source": "hitfm|lastfm|kworb",
      "language_check": "uk (0.94)",
      "playlist_suggestion": "party"
    }
  }
}
```

### `data/whitelist.json` — Approved Songs
```json
{
  "tracks": {
    "spotify_track_id": {
      "name": "Song Name",
      "artist": "Artist Name",
      "uri": "spotify:track:xxx",
      "playlist": "daytime|evening|folk|party|waltz|rave"
    }
  }
}
```

### `data/blacklist.json` — Rejected Songs
```json
{
  "tracks": {
    "spotify_track_id": {}
  }
}
```

## Review Script (`scripts/review.py`)

Interactive CLI that iterates through `not_sure.json`:

- Shows: track name, artist, source, language confidence
- Commands:
  - `o` — open track in Spotify (listen to it)
  - `d` — whitelist → Daytime playlist
  - `e` — whitelist → Evening playlist
  - `f` — whitelist → Folk playlist
  - `p` — whitelist → Party playlist
  - `w` — whitelist → Waltz playlist
  - `r` — whitelist → Rave playlist
  - `b` — blacklist (never show again)
  - `s` — skip (stay in not_sure for later)
  - `q` — quit and save

## Playlist Update (`src/update_playlists.py`)

1. Load `whitelist.json`
2. Group tracks by `playlist` field
3. Load playlist IDs from `config/playlists.yaml`
4. For each playlist: replace all tracks via Spotify `/items` API

## Playlist Config (`config/playlists.yaml`)

```yaml
playlists:
  daytime: "2dtGpG8ColpwGLjAIh3h2y"
  evening: "2M199fyV4J4gT1MfusqJxJ"
  folk: "5VcKxY0sYxapLRW1DSUvQr"
  party: "4kn274GiOqPmh6pgwG1nPZ"
  waltz: "5AsuhvTJGEZSNfLi89M3pF"
  rave: "5MwjTAKFh33Qhx8t5JZ2h2"
```

## Commands

```bash
# Discover new songs from external sources
python -m src.discover

# Review discovered songs (interactive)
python scripts/review.py

# Push approved songs to Spotify playlists
python -m src.update_playlists
```

## Tech Stack

- Python 3.12+
- Spotipy (Spotify API — search + playlist update only)
- requests + BeautifulSoup (web scraping)
- HuggingFace transformers (mms-lid-4017)
- FastText via HuggingFace (glotlid)
- Last.fm API (free key)

## Project Structure

```
src/
  discover.py          # Entry point: run all scrapers + language check
  update_playlists.py  # Entry point: whitelist → Spotify playlists
  scrapers/
    hitfm.py           # Hit FM Ukraine scraper
    lastfm.py          # Last.fm tag API
    kworb.py           # kworb.net Deezer UA chart scraper
  language/
    text_check.py      # glotlid text language detection
    audio_check.py     # mms-lid-4017 audio language detection
  spotify_client.py    # Spotipy wrapper (search + playlist update)
  filter.py            # Whitelist/blacklist/not-sure logic
scripts/
  review.py            # Interactive review CLI
data/
  whitelist.json
  blacklist.json
  not_sure.json
config/
  playlists.yaml       # Playlist name → Spotify ID mapping
```
