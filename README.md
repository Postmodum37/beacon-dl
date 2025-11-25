# BeaconTV Downloader

Download BeaconTV videos with all subtitle tracks. Outputs properly formatted video files ready for release processing.

## Installation

```bash
# Install with uv (recommended)
uv pip install -e .

# Install Playwright browser (first time only)
playwright install chromium
```

**Requirements:** Python 3.10+, ffmpeg

```bash
brew install ffmpeg  # macOS
```

## Quick Start

```bash
# Download latest episode from Campaign 4
beacon-dl --username user@example.com --password yourpassword

# Download specific episode
beacon-dl https://beacon.tv/content/c4-e007-knives-and-thorns --username user@example.com --password yourpassword
```

## Commands

### Download (default)

```bash
# Latest episode from Campaign 4
beacon-dl

# Latest from a different series
beacon-dl --series exu-calamity

# Specific episode by URL
beacon-dl https://beacon.tv/content/c4-e007-knives-and-thorns

# With debug output
beacon-dl --debug
```

### List Series

```bash
# Show all available series on Beacon TV
beacon-dl list-series
```

### List Episodes

```bash
# List all episodes in a series
beacon-dl list-episodes campaign-4
beacon-dl list-episodes exu-calamity
```

### Check for New Episodes

```bash
# Check latest episode in Campaign 4
beacon-dl check-new

# Check a specific series
beacon-dl check-new --series exu-calamity
```

### Episode Info

```bash
# Show detailed info about an episode (resolutions, subtitles, metadata)
beacon-dl info c4-e007-on-the-scent

# Also accepts full URLs
beacon-dl info https://beacon.tv/content/c4-e007-on-the-scent
```

Shows:
- Episode metadata (title, series, duration, description)
- All available resolutions with bitrates
- Available subtitle languages
- Download history status (if previously downloaded)

### Batch Download

```bash
# Download all episodes from a series
beacon-dl batch-download campaign-4

# Download episodes 1-5
beacon-dl batch-download campaign-4 --start 1 --end 5

# Download from episode 10 onwards
beacon-dl batch-download campaign-4 --start 10
```

### Download History

```bash
# Show recent downloads
beacon-dl history

# Show more entries
beacon-dl history --limit 50
```

### Verify Downloads

```bash
# Quick verify (file size check)
beacon-dl verify

# Full verify with SHA256 checksums
beacon-dl verify --full

# Verify specific file
beacon-dl verify "Critical.Role.S04E07.*.mkv"
```

### Clear History

```bash
# Clear download history (with confirmation)
beacon-dl clear-history

# Skip confirmation
beacon-dl clear-history --force
```

### Rename Files

Rename existing files to match the current naming schema (useful after updates):

```bash
# Dry-run: show what would be renamed
beacon-dl rename

# Rename files in a specific directory
beacon-dl rename ./downloads

# Actually rename files
beacon-dl rename --execute

# Only rename mp4 files
beacon-dl rename --pattern "*.mp4" --execute
```

## Authentication

### Username/Password (Recommended)

```bash
# Via command line flags
beacon-dl --username user@example.com --password yourpassword

# Via environment variables
export BEACON_USERNAME=user@example.com
export BEACON_PASSWORD=yourpassword
beacon-dl
```

### Browser Cookies (Fallback)

```bash
# Auto-detect browser (Firefox, Chrome)
beacon-dl --browser firefox

# Specific profile
beacon-dl --browser "firefox:default"
```

## Configuration

All settings can be configured via environment variables or a `.env` file.

### Download Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `PREFERRED_RESOLUTION` | 1080p | Download quality (720p, 1080p, 2160p) |
| `SOURCE_TYPE` | WEB-DL | Source type in filename |
| `CONTAINER_FORMAT` | mkv | Output format (mkv, mp4) |

### Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `BEACON_USERNAME` | - | Beacon TV username |
| `BEACON_PASSWORD` | - | Beacon TV password |
| `BROWSER_PROFILE` | - | Browser for cookie extraction |

### Example `.env` file

```bash
BEACON_USERNAME=user@example.com
BEACON_PASSWORD=yourpassword
PREFERRED_RESOLUTION=1080p
```

### Custom Settings Examples

```bash
# 720p quality
PREFERRED_RESOLUTION="720p" beacon-dl

# MP4 container
CONTAINER_FORMAT="mp4" beacon-dl

# Combined
PREFERRED_RESOLUTION="720p" CONTAINER_FORMAT="mp4" beacon-dl
```

## Output Format

**Episodic content:**
```
Critical.Role.S04E07.Knives.and.Thorns.1080p.WEB-DL.AAC2.0.H.264.mkv
```

**One-shots/specials:**
```
Critical.Role.Jester.and.Fjords.Wedding.1080p.WEB-DL.AAC2.0.H.264.mkv
```

## Docker

```bash
# Build
docker build -t beacon-dl .

# Download latest episode
docker run --rm \
  -e BEACON_USERNAME=user@example.com \
  -e BEACON_PASSWORD=yourpassword \
  -v $(pwd)/downloads:/app \
  beacon-dl

# Scheduled downloads (cron)
0 2 * * * docker run --rm -e BEACON_USERNAME=... -e BEACON_PASSWORD=... -v /downloads:/app beacon-dl
```

## Troubleshooting

### Subtitle downloads fail
Unblock `assets-jpcust.jwpsrv.com` in your DNS blocker (Pi-hole).

### Authentication errors
Verify credentials are correct. Try `--debug` for verbose output.

### Playwright not installed
Run `playwright install chromium` after installing the package.

## See Also

- [CLAUDE.md](CLAUDE.md) - Technical documentation
- [Upload-Assistant](https://github.com/Audionut/Upload-Assistant) - For creating release packages
