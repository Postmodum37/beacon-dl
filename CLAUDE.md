# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Project Overview

**beacon-tv-downloader** - CLI tool to download BeaconTV videos with subtitles.

- Direct HTTP downloads (no yt-dlp)
- Playwright authentication (Docker-compatible)
- Download history with SHA256 verification
- Scene-style filenames for media libraries

## Quick Reference

```bash
# Install
uv pip install -e . && playwright install chromium

# Download latest episode
beacon-dl -u user@example.com -p password

# Other commands
beacon-dl list-series                    # Show all series
beacon-dl list-episodes campaign-4       # List episodes
beacon-dl batch-download campaign-4      # Download all
beacon-dl history                        # Show downloads
beacon-dl verify --full                  # Verify files
```

## Architecture

```
src/beacon_dl/
├── main.py        # CLI commands (Typer)
├── auth.py        # Playwright login, cookie management
├── downloader.py  # Download orchestration, FFmpeg muxing
├── content.py     # Fetch video metadata from beacon.tv
├── graphql.py     # GraphQL API client for browsing
├── config.py      # Pydantic settings
├── history.py     # SQLite download tracking
├── models.py      # Data models (Episode, Collection)
├── utils.py       # Helpers (filename sanitization, language mapping)
├── constants.py   # Default values, codec mappings
└── exceptions.py  # Custom exceptions
```

## Key Components

### Authentication (auth.py)
- Playwright launches Chromium, logs into members.beacon.tv
- Captures cookies from both members.beacon.tv and beacon.tv
- Saves as Netscape format for HTTP client
- Validates expiration with configurable buffer

### Download Flow (downloader.py)
1. Fetch metadata via `content.py`
2. Select best resolution matching preference
3. Check history (skip if already downloaded)
4. Download video + subtitles via HTTP
5. Merge with FFmpeg (stream copy)
6. Record in history with SHA256

### Content Parsing (content.py)
- Fetches `https://beacon.tv/content/{slug}`
- Extracts `__NEXT_DATA__` JSON from page
- Parses video sources, subtitles, metadata

### GraphQL API (graphql.py)
- Endpoint: `https://cms.beacon.tv/graphql`
- Used for: listing series, episodes, searching
- Methods: `get_latest_episode()`, `get_series_episodes()`, `list_collections()`

### History (history.py)
- SQLite database (`.beacon-dl-history.db`)
- Tracks: content_id, filename, SHA256, timestamps
- Prevents re-downloading same content

## CLI Commands

| Command | Description |
|---------|-------------|
| `beacon-dl [URL]` | Download (default: latest Campaign 4) |
| `list-series` | Show all series |
| `list-episodes <series>` | List episodes in series |
| `batch-download <series>` | Download multiple episodes |
| `check-new` | Check for new episodes |
| `info <slug>` | Show episode details |
| `history` | Show download history |
| `verify` | Verify downloaded files |
| `rename` | Rename files to current schema |
| `clear-history` | Clear history database |

## Configuration

Environment variables or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `BEACON_USERNAME` | - | Login email |
| `BEACON_PASSWORD` | - | Login password |
| `PREFERRED_RESOLUTION` | 1080p | Video quality |
| `CONTAINER_FORMAT` | mkv | Output format |
| `SOURCE_TYPE` | WEB-DL | Source tag |
| `DEBUG` | false | Verbose output |

## Output Format

```
{Collection}.S{season}E{episode}.{Title}.{resolution}.{source}.{audio}.{video}.{format}
```

Example: `Campaign.4.S04E07.On.the.Scent.1080p.WEB-DL.AAC2.0.H.264.mkv`

## Development

```bash
# Setup
uv sync --extra dev
playwright install chromium
uv run pre-commit install

# Test
uv run pytest                    # All tests
uv run pytest --cov              # With coverage
uv run pytest -m unit            # Unit tests only

# Lint
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

## Dependencies

- **httpx**: HTTP client
- **playwright**: Browser automation
- **pydantic**: Configuration validation
- **rich**: Console output
- **typer**: CLI framework
- **ffmpeg**: Video muxing (system)

## Common Issues

| Issue | Solution |
|-------|----------|
| Subtitles fail | Unblock `assets-jpcust.jwpsrv.com` |
| Auth errors | Check credentials |
| Playwright missing | `playwright install chromium` |
