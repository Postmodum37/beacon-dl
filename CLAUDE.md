# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Project Overview

**beacon-dl** - CLI tool to download BeaconTV videos with subtitles.

- Direct HTTP downloads (no yt-dlp)
- Playwright authentication (Docker-compatible)
- Download history with SHA256 verification
- Scene-style filenames for media libraries
- Auto-installs Chromium browser on first run

## Quick Reference

```bash
# Run directly (no install)
uvx beacon-dl -u user@example.com -p password

# Install as tool
uv tool install beacon-dl

# Development install
uv pip install -e .

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
├── browser.py     # Chromium auto-installation
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

### Browser Auto-Install (browser.py)
- Detects if Chromium is installed in Playwright cache
- Automatically installs Chromium on first run
- Platform-specific cache directory detection

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
| `search <query>` | Search episodes by title/description |
| `batch-download <series>` | Download multiple episodes |
| `check-new` | Check for new episodes |
| `info <slug>` | Show episode details |
| `history` | Show download history |
| `config` | Show current configuration |
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
| `RELEASE_GROUP` | Pawsty | Scene release group tag |
| `DEBUG` | false | Verbose output |

## Output Format

Scene-style naming:
```
{Show}.S{season}E{episode}.{Title}.{resolution}.{service}.{source}.{audio}.{video}-{group}.{format}
```

Example: `Critical.Role.S04E07.On.the.Scent.1080p.BCTV.WEB-DL.AAC2.0.H.264-Pawsty.mkv`

### Service Tag

BCTV identifies BeaconTV as the source (like AMZN for Amazon, NF for Netflix, DSNP for Disney+).

### Show Name Mapping

BeaconTV collection names are mapped to proper show names:

| Collection Name | Display Name |
|-----------------|--------------|
| Campaign 1-4 | Critical.Role |
| Exandria Unlimited | Exandria.Unlimited |
| Candela Obscura | Candela.Obscura |
| 4-Sided Dive | 4-Sided.Dive |
| Midst | Midst |

## Development

```bash
# Setup
uv sync --extra dev
uv run pre-commit install

# Test
uv run pytest                    # All tests (427 tests)
uv run pytest --cov              # With coverage (~74%)
uv run pytest -m unit            # Unit tests only (369 tests)
uv run pytest -m integration     # Integration tests (44 tests)
uv run pytest -m security        # Security tests (14 tests)

# Lint
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

## Test Suite

### Structure

```
tests/
├── conftest.py              # Shared fixtures (cookie files, mock data)
├── test_auth.py             # Authentication and cookie management
├── test_browser.py          # Chromium auto-installation
├── test_cli_commands.py     # CLI command integration tests
├── test_config.py           # Settings validation (82 tests)
├── test_content.py          # Content parsing (63 tests)
├── test_downloader.py       # Download orchestration
├── test_exceptions.py       # Exception hierarchy
├── test_graphql.py          # GraphQL API client
├── test_graphql_security.py # GraphQL injection prevention
├── test_history.py          # Download history tracking
├── test_models.py           # Domain models
└── test_utils.py            # Utility functions (parametrized)
```

### Markers

All tests are tagged with markers for selective execution:

| Marker | Description | Count |
|--------|-------------|-------|
| `unit` | Fast, isolated unit tests | 369 |
| `integration` | Tests with external dependencies | 44 |
| `security` | Input validation and injection prevention | 14 |

### Key Test Patterns

- **Shared fixtures** in `conftest.py` (mock cookies, video sources, API responses)
- **Parametrized tests** for data-driven testing (language mapping, filename sanitization)
- **Module-level markers** via `pytestmark = pytest.mark.unit`
- **httpx_mock** for HTTP request mocking
- **CliRunner** for Typer CLI testing

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
| Chromium install fails | Run `playwright install chromium` manually |
