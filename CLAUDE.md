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

This repository contains a bash script for downloading BeaconTV videos with all subtitle tracks, creating properly formatted video files. The script is fully configurable via environment variables and automatically detects show metadata, video specs, and browser profiles. Originally designed for Critical Role, it now supports any BeaconTV content.

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

All aspects of the script can be customized via environment variables:

**Browser Authentication**:
```bash
# Browser profile for cookie authentication (auto-detected if not specified)
BROWSER_PROFILE="firefox:~/path/to/your/profile" ./beacon_dl.sh <url>
```

**Release Customization**:
```bash
# Release group name (default: Pawsty)
RELEASE_GROUP="MyGroup" ./beacon_dl.sh <url>

# Source type (default: WEB-DL)
SOURCE_TYPE="WEBRip" ./beacon_dl.sh <url>

# Container format (default: mkv)
CONTAINER_FORMAT="mp4" ./beacon_dl.sh <url>
```

**Quality Settings**:
```bash
# Preferred download resolution (default: 1080p)
PREFERRED_RESOLUTION="720p" ./beacon_dl.sh <url>

# Fallback values when metadata is missing
DEFAULT_RESOLUTION="1080p" ./beacon_dl.sh <url>
DEFAULT_VIDEO_CODEC="H.264" ./beacon_dl.sh <url>
DEFAULT_AUDIO_CODEC="AAC" ./beacon_dl.sh <url>
DEFAULT_AUDIO_CHANNELS="2.0" ./beacon_dl.sh <url>
```

**Combined Example**:
```bash
RELEASE_GROUP="CustomGroup" PREFERRED_RESOLUTION="720p" ./beacon_dl.sh <url>
```

## Dependencies

### Required
- **yt-dlp**: Video and subtitle download tool with BeaconTV support
- **jq**: JSON processor for parsing video metadata
- **ffmpeg/ffprobe**: For muxing video and subtitles into MKV container
- **Browser with BeaconTV cookies**: Firefox/Zen browser profile for authentication

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

The script uses `set -euo pipefail` for strict error handling with comprehensive validation:

**Strict Error Modes**:
- `set -e`: Exit on any command failure
- `set -u`: Treat undefined variables as errors
- `set -o pipefail`: Catch errors in pipelines

**Cleanup on Exit**: Trap ensures secure temporary directory is removed even on failure

**Dependency Checking**: Verifies all required commands (yt-dlp, jq, ffmpeg, ffprobe) are installed before proceeding

**Smart Download Skip**: Checks if output file already exists to prevent duplicate downloads

**Input Validation**:
- Environment variables validated for safe characters only (alphanumeric, dots, dashes, underscores)
- URL format strictly validated (HTTPS only, beacon.tv domain, proper content path)
- Browser profile format validated before use
- Container format validated against whitelist
- Filename sanitization with length limits and hidden file prevention

**Security Validations**:
- Prevents path traversal attacks in environment variables
- Blocks command injection attempts
- Enforces HTTPS-only for secure connections
- Validates browser profile format to prevent injection
- Uses secure temporary directory (mktemp) instead of predictable names

**Validation Points**:
- Required URL argument check
- HTTPS and domain validation
- Video metadata extraction with JSON parsing
- Browser profile detection and format validation
- Multi-format title parsing for episodic and non-episodic content
- Video download verification
- Subtitle download verification
- FFmpeg muxing verification
- Final output file verification with size check

**Error Output**: All errors are sent to stderr for proper shell integration

## Key Features

### Dynamic Metadata Extraction
- **Show Name**: Automatically extracted from video metadata instead of hardcoded
- **Video Specs**: Resolution, codecs, and audio channels detected from metadata
- **Fallback Values**: Configurable defaults used when metadata is incomplete

### Multi-Format Episode Detection
Supports multiple episode numbering formats:
- Critical Role format: "C4 E006 | Title"
- Standard format: "S04E06 - Title" or "S04E06: Title"
- Compact format: "S04E06 Title"
- Alternative format: "4x06 - Title"

### Universal Language Support
- Dynamic subtitle language detection from filenames
- ISO 639-2 code mapping for international standards
- Extensible language map supporting 9+ languages
- No hardcoded language list limitations

### Browser Profile Auto-Detection
- Automatically finds Firefox, Zen, or Chrome profiles
- Cross-platform support (macOS, Linux)
- Manual override option available
- Graceful fallback to specified default

## Common Issues

**Subtitle downloads fail**: Check if Pi-hole/DNS blocker is blocking `assets-jpcust.jwpsrv.com`. This domain must be unblocked for subtitle downloads.

**Browser cookies expired**: If downloads fail with authentication errors, log into BeaconTV in your browser and try again.

**Browser profile not detected**: If auto-detection fails, the script will exit with an error. Manually specify your profile:
```bash
BROWSER_PROFILE="firefox:~/path/to/profile" ./beacon_dl.sh <url>
BROWSER_PROFILE="firefox" ./beacon_dl.sh <url>  # Use default profile
```

**Invalid characters in environment variables**: Only alphanumeric characters, dots (`.`), dashes (`-`), and underscores (`_`) are allowed. Path traversal attempts and special characters are blocked:
```bash
# This will fail:
RELEASE_GROUP="../test" ./beacon_dl.sh <url>

# This will work:
RELEASE_GROUP="MyGroup-v2.0" ./beacon_dl.sh <url>
```

**HTTP URLs not accepted**: For security, only HTTPS URLs are accepted. Use `https://` instead of `http://`.

**Wrong show name detected**: Override with environment variable if metadata is incorrect:
```bash
# The script will extract show name from metadata, but you can override it by editing the script
# or by manually renaming the file after download
```

**Non-episodic content**: The script handles all BeaconTV content types. Non-episodic content (one-shots, specials) is automatically detected and formatted without season/episode numbers.

**Custom release requirements**: All filename components can be customized via environment variables. See the Configuration section for details.

**File size warning**: If the output file is less than 1MB, the script will warn that the download may have failed or been incomplete.
