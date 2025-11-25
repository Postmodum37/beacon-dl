# BeaconTV Downloader

Download BeaconTV videos with all subtitle tracks. Outputs properly formatted files for media libraries.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Installation

```bash
uv pip install -e .
playwright install chromium
```

**Requirements:** Python 3.10+, ffmpeg (`brew install ffmpeg` on macOS)

## Quick Start

```bash
# Download latest episode (requires auth)
beacon-dl --username user@example.com --password yourpassword

# Download specific episode
beacon-dl https://beacon.tv/content/c4-e007-episode-title -u user@example.com -p pass
```

## Commands

| Command | Description |
|---------|-------------|
| `beacon-dl [URL]` | Download latest episode or specific URL |
| `beacon-dl list-series` | Show all available series |
| `beacon-dl list-episodes <series>` | List episodes in a series |
| `beacon-dl batch-download <series>` | Download multiple episodes |
| `beacon-dl info <episode>` | Show episode details (resolutions, subtitles) |
| `beacon-dl check-new` | Check for new episodes |
| `beacon-dl history` | Show download history |
| `beacon-dl verify` | Verify downloaded files |
| `beacon-dl rename` | Rename files to current schema |

### Examples

```bash
# Browse content
beacon-dl list-series
beacon-dl list-episodes campaign-4
beacon-dl info c4-e007-episode-title

# Download
beacon-dl --series exu-calamity              # Latest from specific series
beacon-dl batch-download campaign-4 --start 1 --end 5   # Episodes 1-5

# Maintenance
beacon-dl history --limit 50
beacon-dl verify --full                      # SHA256 verification
beacon-dl rename --execute                   # Apply naming updates
```

## Authentication

```bash
# Option 1: Command line (recommended)
beacon-dl -u user@example.com -p yourpassword

# Option 2: Environment variables
export BEACON_USERNAME=user@example.com
export BEACON_PASSWORD=yourpassword

# Option 3: Browser cookies (fallback)
beacon-dl --browser firefox
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `BEACON_USERNAME` | - | Account email |
| `BEACON_PASSWORD` | - | Account password |
| `PREFERRED_RESOLUTION` | 1080p | Quality (720p, 1080p, 2160p) |
| `CONTAINER_FORMAT` | mkv | Output format (mkv, mp4) |

## Output Format

```
Critical.Role.S04E07.Episode.Title.1080p.WEB-DL.AAC2.0.H.264.mkv
```

## Docker

```bash
docker build -t beacon-dl .
docker run --rm -e BEACON_USERNAME=... -e BEACON_PASSWORD=... -v $(pwd):/app beacon-dl
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Subtitles fail | Unblock `assets-jpcust.jwpsrv.com` in DNS blocker |
| Auth errors | Check credentials, use `--debug` flag |
| Playwright missing | Run `playwright install chromium` |

## License

MIT
