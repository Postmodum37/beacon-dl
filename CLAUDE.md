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

Bash script for downloading BeaconTV videos with all subtitle tracks. Fully configurable via environment variables with automatic metadata detection. Supports any BeaconTV content.

## How to Run

Downloads video with all subtitle tracks:
```bash
./beacon_dl.sh <beacon_tv_url>
```

Examples:
```bash
# Episodic content
./beacon_dl.sh https://beacon.tv/content/c4-e006-knives-and-thorns

# One-shots and specials
./beacon_dl.sh https://beacon.tv/content/critical-role-jester-and-fjords-wedding-live-from-radio-city-music-hall
```

Output examples:
- Episodic: `Critical.Role.S04E06.Knives.and.Thorns.1080p.WEB-DL.AAC2.0.H.264-Pawsty.mkv`
- One-shot: `Critical.Role.Jester.and.Fjords.Wedding.Live.from.Radio.City.Music.Hall.1080p.WEB-DL.AAC2.0.H.264-Pawsty.mkv`

### Configuration

Configurable via environment variables:
- `BROWSER_PROFILE`: Browser for cookies (auto-detected: firefox, chrome, etc.)
- `RELEASE_GROUP`: Release group name (default: Pawsty)
- `SOURCE_TYPE`: Source type (default: WEB-DL)
- `CONTAINER_FORMAT`: Output format (default: mkv)
- `PREFERRED_RESOLUTION`: Download quality (default: 1080p)
- Metadata fallbacks: DEFAULT_RESOLUTION, DEFAULT_VIDEO_CODEC, DEFAULT_AUDIO_CODEC, DEFAULT_AUDIO_CHANNELS

## Dependencies

**Required**: yt-dlp, jq, ffmpeg/ffprobe, browser with BeaconTV cookies (Firefox/Zen/Chrome)

## Architecture

### Download and Muxing Flow

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

- **Subtitles fail**: Unblock `assets-jpcust.jwpsrv.com` in Pi-hole/DNS blocker
- **Auth errors**: Log into BeaconTV in browser to refresh cookies
- **Profile not detected**: Set `BROWSER_PROFILE="firefox:~/path/to/profile"`
- **Invalid chars**: Use only alphanumeric, dots, dashes, underscores (blocks `../test`, `; rm -rf`)
- **HTTP rejected**: HTTPS required for security
- **Wrong metadata**: Edit show name extraction logic or rename file manually
- **File size < 1MB**: Warning indicates incomplete download
