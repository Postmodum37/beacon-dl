# AI Agent Routing Protocols
You are the **Lead Engineer** and **Orchestrator**. Your goal is NOT to do everything yourself, but to delegate tasks to specialized sub-agents to ensure high-quality output.

## 🚨 Delegation Rules (YOU MUST FOLLOW THESE)

### 1. Architecture & Planning
**Trigger:** User asks for a "new feature," "system design," or "complex refactor."
**Action:** Immediately invoke the `architect` agent.
**Instruction:** "Ask the architect to create a file structure and data flow plan for this request."
**Constraint:** Do NOT write code until the architect's plan is approved.

### 2. UI & Frontend
**Trigger:** User mentions "CSS", "Tailwind", "responsive", "layout", or "make it look good".
**Action:** Delegate the implementation to the `ui-polish` agent.
**Reasoning:** You focus on logic; the `ui-polish` agent focuses on pixel-perfect design and accessibility.

### 3. Security & Sensitivity
**Trigger:** You are touching `auth`, `login`, `API keys`, or `.env` files.
**Action:** Before confirming the task is done, ask the `security` agent to scan the changes.
**Command:** "Have the security agent review these changes for leaks."

### 4. Quality Assurance
**Trigger:** You have finished writing a significant chunk of logic.
**Action:** Delegate to `qa-engineer` to write/run tests.
**Rule:** Never mark a task as "Done" without a passing test result from the QA agent.

---

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

BeaconTV downloader available in two implementations:
1. **Python CLI** (`beacon-dl`) - Modern Python package with Playwright authentication (recommended)
2. **Bash Script** (`beacon_dl.sh`) - Original shell script for simple setups

Both versions support:
- Downloading BeaconTV videos with all subtitle tracks
- Fully configurable via environment variables
- Automatic metadata detection
- All BeaconTV content types (episodic, one-shots, specials)

## Quick Start

### Python CLI (Recommended)

**Installation:**
```bash
# Install with uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .
```

**Usage:**
```bash
# Download latest episode from Campaign 4 (no URL needed!)
beacon-dl

# Download latest episode with credentials (recommended - Playwright auth)
beacon-dl --username user@example.com --password yourpassword

# Download latest from a different series
beacon-dl --series https://beacon.tv/series/exu-calamity --username user@example.com --password yourpassword

# Download specific episode with Playwright authentication (recommended)
beacon-dl https://beacon.tv/content/c4-e006-knives-and-thorns --username user@example.com --password yourpassword

# With browser cookies (fallback method)
beacon-dl https://beacon.tv/content/c4-e006-knives-and-thorns --browser firefox:default

# Debug mode (shows browser window, verbose output)
beacon-dl --username user@example.com --password yourpassword --debug

# Environment variables (Docker-compatible)
BEACON_USERNAME=user@example.com BEACON_PASSWORD=yourpassword beacon-dl
```

### Bash Script

**Usage:**
```bash
# Basic usage (auto-detects browser cookies)
./beacon_dl.sh https://beacon.tv/content/c4-e006-knives-and-thorns

# With environment variables
RELEASE_GROUP="MyGroup" PREFERRED_RESOLUTION="720p" ./beacon_dl.sh <url>
```

**Output examples:**
- Episodic: `Critical.Role.S04E06.Knives.and.Thorns.1080p.WEB-DL.AAC2.0.H.264-Pawsty.mkv`
- One-shot: `Critical.Role.Jester.and.Fjords.Wedding.Live.from.Radio.City.Music.Hall.1080p.WEB-DL.AAC2.0.H.264-Pawsty.mkv`

## Configuration

Both implementations support the same configuration via environment variables or `.env` file:

**Authentication (Python only):**
- `BEACON_USERNAME`: BeaconTV username for Playwright login (primary auth method)
- `BEACON_PASSWORD`: BeaconTV password for Playwright login (primary auth method)
- `BROWSER_PROFILE`: Browser for cookies (fallback: firefox, chrome, etc.)

**Download Settings:**
- `RELEASE_GROUP`: Release group name (default: Pawsty)
- `SOURCE_TYPE`: Source type (default: WEB-DL)
- `CONTAINER_FORMAT`: Output format (default: mkv)
- `PREFERRED_RESOLUTION`: Download quality (default: 1080p)

**Metadata Fallbacks:**
- `DEFAULT_RESOLUTION`: Fallback resolution if not detected
- `DEFAULT_VIDEO_CODEC`: Fallback video codec (default: H.264)
- `DEFAULT_AUDIO_CODEC`: Fallback audio codec (default: AAC)
- `DEFAULT_AUDIO_CHANNELS`: Fallback audio channels (default: 2.0)

**Debug (Python only):**
- `DEBUG`: Enable debug mode (default: false) - shows browser window, verbose output

## Dependencies

### Python CLI
**Required**: Python 3.10+, yt-dlp, playwright, pydantic, rich, typer, ffmpeg

**Installation:**
```bash
# Install package (installs all dependencies)
uv pip install -e .

# Install Playwright browsers (first time only)
playwright install chromium
```

### Bash Script
**Required**: yt-dlp, jq, ffmpeg/ffprobe, browser with BeaconTV cookies (Firefox/Zen/Chrome)

```bash
brew install yt-dlp jq ffmpeg
```

## Architecture

### Python CLI Architecture

The Python implementation (`src/beacon_dl/`) is organized into modular components:

**Package Structure:**
```
src/beacon_dl/
├── __init__.py
├── main.py          # CLI entry point (Typer)
├── config.py        # Configuration (Pydantic Settings)
├── auth.py          # Authentication logic
├── downloader.py    # Download & muxing logic
└── utils.py         # Helper functions
```

**Module Responsibilities:**

1. **config.py** (`src/beacon_dl/config.py:1-29`):
   - Type-safe configuration using Pydantic Settings
   - Reads from environment variables or `.env` file
   - Defines all configurable parameters with defaults
   - Validates configuration values

2. **auth.py** (`src/beacon_dl/auth.py:1-280`):
   - **Playwright login**: Primary authentication method (Docker-optimized, headless by default)
   - **Browser cookie extraction**: Fallback for local development
   - **Cookie management**: Converts Playwright cookies to Netscape format for yt-dlp
   - **Cookie validation**: Validates cookies contain required auth tokens and checks expiration
   - **Authentication priority**: Playwright (username/password) → browser profile (explicit) → browser profile (auto-detect)
   - **Cross-domain handling**: Navigates to both members.beacon.tv and beacon.tv to capture all auth cookies
   - Function `validate_cookies()` checks cookie validity before download
   - Function `login_and_get_cookies()` handles Playwright-based authentication with proper navigation
   - Function `get_auth_args()` returns yt-dlp authentication arguments with correct priority
   - **Debug mode**: Shows browser window when DEBUG=true, headless otherwise

3. **utils.py** (`src/beacon_dl/utils.py:1-137`):
   - **Filename sanitization**: `sanitize_filename()` matches bash script logic
   - **Language mapping**: `map_language_to_iso()` converts language names to ISO 639-2 codes
   - **Browser detection**: `detect_browser_profile()` auto-detects browser profiles on macOS/Linux
   - **Latest episode fetching**: `get_latest_episode_url()` scrapes series page for latest episode
   - Supports 9+ languages for subtitle mapping

4. **downloader.py** (`src/beacon_dl/downloader.py:1-229`):
   - **BeaconDownloader class**: Main download orchestration
   - **Metadata extraction**: Uses yt-dlp Python API to fetch video info
   - **Filename generation**: `_generate_filename()` implements same logic as bash script
     - Supports 4+ episode formats: C4 E006, S04E06, S04E06 Title, 4x06
     - Detects episodic vs non-episodic content
     - Extracts technical specs (resolution, codecs, channels)
   - **Download**: Downloads video and all subtitle tracks using yt-dlp
   - **Muxing**: `_merge_files()` uses ffmpeg to merge video + subtitles
     - Stream copy (no re-encoding)
     - Dynamic language detection from subtitle filenames
     - ISO 639-2 language metadata

5. **main.py** (`src/beacon_dl/main.py:1-70`):
   - **CLI interface**: Typer-based command-line interface
   - **Entry point**: `beacon-dl` command (defined in pyproject.toml)
   - **Arguments**: URL (optional - defaults to latest episode), username, password, browser, series, debug (all optional)
   - **Latest episode mode**: When no URL provided, automatically fetches latest episode
   - **Error handling**: Graceful handling of KeyboardInterrupt and exceptions
   - **Debug mode**: `--debug` flag enables verbose output and shows browser window
   - **Rich console**: Pretty colored terminal output with status indicators

**Key Differences from Bash Script:**
- **Type safety**: Pydantic validates configuration
- **Better UX**: Rich console with colored output
- **Playwright authentication**: Primary auth method (Docker-optimized)
- **Latest episode auto-fetch**: No URL needed - automatically downloads newest episode
- **Series selection**: Can specify different series with `--series` flag
- **Python API**: Uses yt-dlp Python API instead of subprocess
- **Modular**: Separated concerns (auth, download, config, utils)
- **Same output**: Generates identical filenames and video files
- **Docker-ready**: Designed for containerized environments

**Authentication Flow (Docker-optimized):**

The Python CLI prioritizes Playwright authentication as the primary method:

1. **FIRST PRIORITY - Playwright Login** (recommended):
   - If `BEACON_USERNAME` and `BEACON_PASSWORD` provided (via CLI flags or env vars)
   - Launches Chromium in headless mode (visible in debug mode with `--debug`)
   - Logs into members.beacon.tv
   - Navigates to beacon.tv homepage and content page to capture all auth cookies
   - Validates cookies contain required tokens for both domains
   - Saves cookies to Netscape format file for yt-dlp
   - **Ideal for Docker containers** where browser cookies are unavailable

2. **SECOND PRIORITY - Explicit Browser Profile**:
   - If `BROWSER_PROFILE` environment variable or `--browser` flag provided
   - Uses yt-dlp's `--cookies-from-browser` to extract cookies
   - Example: `--browser firefox:default` or `BROWSER_PROFILE=chrome`

3. **THIRD PRIORITY - Auto-detect Browser Profile** (local development fallback):
   - If no credentials or browser profile specified
   - Auto-detects browser profiles in order: Zen → Firefox → Chrome
   - Uses yt-dlp's `--cookies-from-browser` with detected profile
   - **Note**: User must be logged into BeaconTV in their browser

4. **NO AUTHENTICATION**:
   - If none of the above methods available
   - Shows error message with instructions
   - Download will fail for members-only content

**Why Playwright is Primary:**
- **Docker-compatible**: Works in containers without browser cookies
- **Automated**: No manual browser login required
- **Cross-domain**: Properly captures cookies from both members.beacon.tv and beacon.tv
- **Validated**: Checks cookie validity before attempting download
- **Headless**: Runs in background by default (visible with `--debug`)

**Latest Episode Auto-Fetch:**

When no URL is provided, the CLI automatically fetches and downloads the latest episode from Campaign 4:

```bash
# Download latest episode from Campaign 4
beacon-dl

# Download latest from a different series
beacon-dl --series https://beacon.tv/series/exu-calamity
```

**How it works:**
1. Uses Playwright to navigate to the series page (default: `https://beacon.tv/series/campaign-4`)
2. Extracts all episode links from the page
3. Selects the first episode (usually the latest)
4. Downloads that episode automatically

This feature is particularly useful for:
- Docker containers with scheduled downloads (cron jobs)
- Automated setups that always download the newest episode
- Quick downloads without needing to find the episode URL

**Download Flow:**
1. If no URL provided, fetch latest episode URL from series page (using Playwright)
2. Fetch metadata with yt-dlp (`ydl.extract_info(url, download=False)`)
3. Extract show name, title, technical specs from metadata
4. Generate output filename using same logic as bash script
5. Check if file already exists (skip if yes)
6. Download video to `temp_dl/video.mp4`
7. Download all subtitle tracks to `temp_dl/subs.*.vtt`
8. Merge with ffmpeg (stream copy, convert subs to SRT)
9. Cleanup temp directory
10. Report completion with Rich console

### Bash Script Architecture

#### Download and Muxing Flow

1. **Configuration & Validation** (lines 8-48):
   - Sets strict error handling with `set -euo pipefail`
   - Environment-based configuration with sensible defaults
   - Input validation helper function to prevent injection attacks
   - Validates all user-controllable variables (RELEASE_GROUP, CONTAINER_FORMAT, etc.)
   - Creates secure temporary directory using `mktemp`
2. **Helper Functions** (lines 65-160):
   - Enhanced filename sanitization with length limits and hidden file prevention
   - Browser profile detection and language mapping utilities
   - Usage help display
3. **Argument Parsing** (lines 162-179): Validates URL argument with HTTPS enforcement and strict format checking
4. **Dependency Checking** (lines 181-188): Verifies all required commands are installed
5. **Browser Profile Detection & Validation** (lines 190-212):
   - Auto-detects Firefox/Zen/Chrome profiles
   - Validates browser profile format for security
   - Exits with error if auto-detection fails (no hardcoded fallback)
6. **Metadata Extraction** (lines 214-231): Uses `yt-dlp -j` to extract video metadata including:
   - Video title and ID
   - Show/series name (extracted dynamically from metadata)
   - Technical specifications
7. **Technical Specs Extraction** (lines 233-283): Dynamically extracts from metadata:
   - **Resolution**: From metadata height or configurable default
   - **Video Codec**: Detects H.264, H.265, VP9, or uses default
   - **Audio Codec**: Detects AAC, Opus, Vorbis, AC3, EAC3, or uses default
   - **Audio Channels**: Extracted from metadata with proper decimal handling (only appends .0 for integer values)
8. **Title Parsing** (lines 285-347): Multi-format episodic detection:
   - **Format 1**: "C4 E006 | Title" (Critical Role format)
   - **Format 2**: "S04E06 - Title" or "S04E06: Title"
   - **Format 3**: "S04E06 Title" (no separator)
   - **Format 4**: "4x06 - Title"
   - **Non-episodic**: Any title not matching above patterns
   - Uses dynamically detected show name instead of hardcoded "Critical.Role"
   - Fixed regex escaping for proper show name matching
   - Output: `{ShowName}.S{season}E{episode}.{Title}.{specs}-{ReleaseGroup}.{format}`
9. **Download Skip Check** (lines 349-358): Checks if output file already exists
10. **Video Download** (lines 361-371): Downloads video to secure temp directory at configured resolution using browser cookies
11. **Subtitle Download** (lines 373-384): Downloads all available subtitle tracks as VTT files to secure temp directory
12. **Container Muxing** (lines 386-445): Uses ffmpeg to mux video + all subtitles:
    - Secure array-based command construction (no eval)
    - Dynamic subtitle language detection via filename parsing
    - Maps language names to ISO 639-2 codes (supports 9+ languages)
    - Supports any container format (default: MKV)
13. **Output Validation** (lines 447-460): Validates output file exists and checks file size
14. **No Re-encoding**: Video/audio streams are copied (`-c:v copy -c:a copy`), only subtitles converted to SRT format

### Output Format

**Naming Convention** (all components dynamically extracted or configurable):
- Episodic: `{ShowName}.S{season}E{episode}.{Title}.{resolution}.{source}.{audio}{channels}.{video}-{group}.{format}`
- One-shot/special: `{ShowName}.{Title}.{resolution}.{source}.{audio}{channels}.{video}-{group}.{format}`

**Examples** (with defaults):
- `Critical.Role.S04E06.Knives.and.Thorns.1080p.WEB-DL.AAC2.0.H.264-Pawsty.mkv`
- `Critical.Role.Jester.and.Fjords.Wedding.1080p.WEB-DL.AAC2.0.H.264-Pawsty.mkv`

**Dynamic Components**:
- `{ShowName}`: Extracted from metadata (`series` → `uploader` → "Critical.Role")
- `{resolution}`: From video height metadata or `DEFAULT_RESOLUTION`
- `{source}`: Configurable via `SOURCE_TYPE` (default: WEB-DL)
- `{audio}`: Detected codec (AAC, Opus, Vorbis, AC3, EAC3) or `DEFAULT_AUDIO_CODEC`
- `{channels}`: From metadata or `DEFAULT_AUDIO_CHANNELS`
- `{video}`: Detected codec (H.264, H.265, VP9) or `DEFAULT_VIDEO_CODEC`
- `{group}`: Configurable via `RELEASE_GROUP` (default: Pawsty)
- `{format}`: Configurable via `CONTAINER_FORMAT` (default: mkv)

**Video Specs** (for BeaconTV):
- Container: Matroska (MKV) by default, configurable
- Video: H.264 (AVC), 1920x1080, 30fps, ~2420kbps
- Audio: AAC 2.0, ~120kbps
- Subtitles: All available language tracks with proper ISO 639-2 tags

**No encoding required**: BeaconTV source is already H.264/AAC matching torrent release standards.

### Browser Cookie Authentication

The script uses `--cookies-from-browser` to access authentication cookies from your browser.

**Auto-Detection**: The script automatically detects browser profiles in this order:
1. Zen browser on macOS (`~/Library/Application Support/zen/Profiles`)
2. Firefox on macOS (`~/Library/Application Support/Firefox/Profiles`)
3. Firefox on Linux (`~/.mozilla/firefox`)
4. Chrome on macOS (`~/Library/Application Support/Google/Chrome`)
5. Chrome on Linux (`~/.config/google-chrome`)

**Manual Override**: Use the `BROWSER_PROFILE` environment variable:
```bash
BROWSER_PROFILE="firefox:~/path/to/profile" ./beacon_dl.sh <url>
BROWSER_PROFILE="chrome" ./beacon_dl.sh <url>
```

**Security**: Browser profile format is validated before use. Supported browsers: firefox, chrome, chromium, edge, safari, brave, opera.

**No Hardcoded Fallback**: If auto-detection fails, the script exits with an error message instructing the user to set the BROWSER_PROFILE environment variable. This prevents exposure of personal browser profile paths.

The script requires valid BeaconTV session cookies from the browser.

### Subtitle Handling

BeaconTV provides subtitles as direct VTT URLs in metadata (accessed via `yt-dlp --write-subs --all-subs`):
- Downloads all available language tracks as separate VTT files
- Converts VTT to SRT during muxing (`-c:s srt`)
- **Dynamic language detection**: Parses subtitle filenames to extract language names
- **ISO 639-2 mapping**: Maps language names to standard codes via `map_language_to_iso()` function
- **Supported languages**: English, Spanish, French, Italian, Portuguese, German, Japanese, Korean, Chinese, and more
- All subtitle tracks embedded in final container with proper language metadata

**Note**: The DNS blocker (Pi-hole) may block `assets-jpcust.jwpsrv.com`. Ensure this domain is unblocked for subtitle downloads to work.

### Error Handling

**Strict modes**: `set -euo pipefail` (exit on errors, undefined vars, pipeline failures)

**Security validations**:
- Input: alphanumeric, dots, dashes, underscores only
- URLs: HTTPS only, strict format validation
- Browser profile: format validated before use
- Temp files: secure random directories (mktemp)
- Filenames: sanitized, length-limited, no hidden files

**Checks**: Dependencies, existing files, metadata, download success, file size validation

**Cleanup**: Automatic temp directory removal on exit

## Key Features

- **Dynamic metadata**: Auto-extracts show name, resolution, codecs from video
- **Multi-format episodes**: Supports C4 E006, S04E06, 4x06 formats
- **Universal subtitles**: Auto-detects languages, maps to ISO 639-2 codes (9+ languages)
- **Browser auto-detection**: Finds Firefox/Zen/Chrome profiles (macOS/Linux)
- **Security hardened**: Input validation, HTTPS-only, secure temp files, injection prevention

## Common Issues

### Both Implementations
- **Subtitles fail**: Unblock `assets-jpcust.jwpsrv.com` in Pi-hole/DNS blocker
- **Auth errors**: Log into BeaconTV in browser to refresh cookies, or use Playwright login (Python only)
- **Profile not detected**: Set `BROWSER_PROFILE="firefox:~/path/to/profile"` or use `--browser` flag (Python)
- **Wrong metadata**: Edit show name extraction logic or rename file manually
- **File size < 1MB**: Warning indicates incomplete download

### Bash Script Specific
- **Invalid chars**: Use only alphanumeric, dots, dashes, underscores (blocks `../test`, `; rm -rf`)
- **HTTP rejected**: HTTPS required for security

### Python CLI Specific
- **Playwright login fails**: Check username/password, or use browser cookies instead
- **Import errors**: Ensure all dependencies installed: `uv pip install -e .`
- **Playwright not installed**: Run `playwright install chromium`
- **Config not loading**: Create `.env` file in project root or use CLI flags

## Project Structure

```
beacon-tv-downloader/
├── src/beacon_dl/          # Python package
│   ├── __init__.py
│   ├── main.py            # CLI entry point
│   ├── config.py          # Configuration
│   ├── auth.py            # Authentication
│   ├── downloader.py      # Download logic
│   └── utils.py           # Utilities
├── beacon_dl.sh           # Bash script version
├── pyproject.toml         # Python package config
├── uv.lock                # Dependency lock file
├── .env                   # Environment variables (gitignored)
├── .python-version        # Python version (3.14)
├── README.md              # User documentation
└── CLAUDE.md              # This file (AI agent guidance)
```

## Development Notes

**Python Version**: 3.10+ required (project uses 3.14)

**Package Manager**: Uses `uv` for fast dependency management

**Development Setup**:
```bash
# Install in editable mode with dev dependencies
uv sync --extra dev

# Install Playwright browsers
playwright install chromium

# Install pre-commit hooks
uv run pre-commit install
```

**Linting & Formatting (Ruff)**:
```bash
# Check for linting issues
uv run ruff check src/ tests/

# Auto-fix issues
uv run ruff check src/ tests/ --fix

# Format code
uv run ruff format src/ tests/

# Run all pre-commit hooks manually
uv run pre-commit run --all-files
```

**Adding Features**:
- **Configuration**: Add to `Settings` class in `config.py`
- **Authentication**: Modify `auth.py` (prefer browser cookies over Playwright)
- **Download logic**: Update `BeaconDownloader` class in `downloader.py`
- **Filename logic**: Edit `_generate_filename()` method
- **CLI options**: Add to `download()` command in `main.py`

**Testing**:
- Test latest episode auto-fetch: `beacon-dl` (no arguments)
- Test latest from different series: `beacon-dl --series https://beacon.tv/series/exu-calamity`
- Test with episodic content: `beacon-dl https://beacon.tv/content/c4-e006-knives-and-thorns`
- Test with one-shots: `beacon-dl https://beacon.tv/content/critical-role-jester-and-fjords-wedding-live-from-radio-city-music-hall`
- Test different resolutions: `PREFERRED_RESOLUTION="720p" beacon-dl <url>`
- Test authentication methods: Playwright login (primary), browser cookies, auto-detect
- Test Docker compatibility: Use with `BEACON_USERNAME` and `BEACON_PASSWORD` env vars

**Docker Usage**:

The Python CLI is optimized for Docker containers:

```dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install -e .

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Set environment variables
ENV BEACON_USERNAME=""
ENV BEACON_PASSWORD=""
ENV PREFERRED_RESOLUTION="1080p"
ENV RELEASE_GROUP="Pawsty"

# Run command
CMD ["beacon-dl"]
```

**Docker Compose Example:**
```yaml
version: '3.8'
services:
  beacon-dl:
    build: .
    environment:
      - BEACON_USERNAME=${BEACON_USERNAME}
      - BEACON_PASSWORD=${BEACON_PASSWORD}
      - PREFERRED_RESOLUTION=1080p
      - RELEASE_GROUP=Pawsty
    volumes:
      - ./downloads:/app
    command: beacon-dl
```

**Run with Docker:**
```bash
# Build image
docker build -t beacon-dl .

# Download latest episode
docker run --rm \
  -e BEACON_USERNAME=user@example.com \
  -e BEACON_PASSWORD=yourpassword \
  -v $(pwd)/downloads:/app \
  beacon-dl

# Download specific episode
docker run --rm \
  -e BEACON_USERNAME=user@example.com \
  -e BEACON_PASSWORD=yourpassword \
  -v $(pwd)/downloads:/app \
  beacon-dl beacon-dl https://beacon.tv/content/c4-e006-knives-and-thorns
```

**Scheduled Downloads (Cron):**
```bash
# Add to crontab to download latest episode daily at 2 AM
0 2 * * * docker run --rm -e BEACON_USERNAME=user@example.com -e BEACON_PASSWORD=yourpassword -v /path/to/downloads:/app beacon-dl
```

**Security Considerations**:
- Never commit `.env` file (contains credentials)
- Use Docker secrets or environment variables for credentials
- Validate all user inputs (especially environment variables)
- Use HTTPS-only URLs
- Sanitize filenames to prevent directory traversal
- Use secure temp directories
- Don't hardcode personal browser profile paths
