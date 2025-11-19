# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository contains a bash script for downloading Critical Role videos from BeaconTV with all subtitle tracks, creating properly formatted MKV files. Release creation (NFO, MediaInfo, samples, screenshots) is handled separately using Upload-Assistant.

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

To override the browser profile:
```bash
BROWSER_PROFILE="firefox:~/path/to/your/profile" ./beacon_dl.sh <url>
```

## Dependencies

### Required
- **yt-dlp**: Video and subtitle download tool with BeaconTV support
- **jq**: JSON processor for parsing video metadata
- **ffmpeg/ffprobe**: For muxing video and subtitles into MKV container
- **Browser with BeaconTV cookies**: Firefox/Zen browser profile for authentication

## Architecture

### Download and Muxing Flow

1. **Argument Parsing** (lines 26-30): Validates URL argument
2. **Dependency Checking** (lines 33-39): Verifies all required commands are installed
3. **Metadata Extraction** (lines 44-57): Uses `yt-dlp -j` to extract video title and ID
4. **Technical Specs Extraction** (lines 59-91): Extracts resolution, video codec, and audio codec from metadata
5. **Title Parsing** (lines 93-119): Parses episode or one-shot info
   - **Episodic format** ("C4 E006 | Knives and Thorns"):
     - Season: C4 → S04
     - Episode: E006 → E06
     - Title: "Knives and Thorns" → "Knives.and.Thorns"
     - Output: `Critical.Role.S04E06.Knives.and.Thorns.1080p.WEB-DL.AAC2.0.H.264-Pawsty.mkv`
   - **One-shot/special format** (any other title):
     - Title sanitized and formatted
     - Avoids duplicate "Critical.Role" prefix if already in title
     - Output: `Critical.Role.{Title}.1080p.WEB-DL.AAC2.0.H.264-Pawsty.mkv`
6. **Download Skip Check** (lines 124-128): Checks if MKV already exists to avoid re-downloading
7. **Video Download** (lines 131-140): Downloads best 1080p stream using yt-dlp with browser cookies
8. **Subtitle Download** (lines 143-152): Downloads all 5 subtitle tracks (English, Spanish, French, Italian, Portuguese) as separate VTT files
9. **MKV Muxing** (lines 155-210): Uses ffmpeg to mux video + all subtitles into MKV container with proper language metadata
10. **No Re-encoding**: Video/audio streams are copied (`-c:v copy -c:a copy`), only subtitles converted to SRT format

### Output Format

**Naming Convention**:
- Episodic: `Critical.Role.S{season}E{episode}.{Title}.1080p.WEB-DL.AAC2.0.H.264-Pawsty.mkv`
- One-shot/special: `Critical.Role.{Title}.1080p.WEB-DL.AAC2.0.H.264-Pawsty.mkv`

**Video Specs**:
- Container: Matroska (MKV)
- Video: H.264 (AVC), 1920x1080, 30fps, ~2420kbps
- Audio: AAC 2.0, ~120kbps
- Subtitles: 5 tracks (English, Spanish, French, Italian, Portuguese) with proper language tags

**No encoding required**: BeaconTV source is already H.264/AAC matching torrent release standards.

### Browser Cookie Authentication

The script relies on `--cookies-from-browser` with a configurable Firefox/Zen browser profile path. The default profile is:
```bash
firefox:~/Library/Application Support/zen/Profiles/oc1q8w6o.Default (release)-1
```

**Configuration**: Override using the `BROWSER_PROFILE` environment variable:
```bash
BROWSER_PROFILE="firefox:~/path/to/profile" ./beacon_dl.sh <url>
```

The script requires valid BeaconTV session cookies from the browser.

### Subtitle Handling

BeaconTV provides subtitles as direct VTT URLs in metadata (accessed via `yt-dlp --write-subs --all-subs`):
- Downloads each language track as separate VTT file
- Converts VTT to SRT during muxing (`-c:s srt`)
- Adds proper language metadata tags (eng, spa, fre, ita, por)
- All subtitle tracks embedded in final MKV file

**Note**: The DNS blocker (Pi-hole) may block `assets-jpcust.jwpsrv.com`. Ensure this domain is unblocked for subtitle downloads to work.

### Error Handling

The script uses `set -e` (line 7) for strict error handling with comprehensive validation:

**Cleanup on Exit** (lines 10-13): Trap ensures temporary files (`temp_video.mp4`, `temp_*.vtt`) are removed even on failure

**Dependency Checking** (lines 33-39): Verifies all required commands (yt-dlp, jq, ffmpeg, ffprobe) are installed before proceeding

**Smart Download Skip** (lines 124-128): Checks if output MKV already exists to prevent duplicate downloads

**Validation Points**:
- Required URL argument check (lines 27-29)
- Video metadata extraction with JSON parsing (lines 47-50)
- Title parsing for episodic and non-episodic content (lines 93-119)
- Video download verification (lines 133-140)
- Subtitle download verification (lines 144-152)
- FFmpeg muxing verification (lines 208-211)
- Final output file verification (line 208)

**Error Output**: All errors are sent to stderr for proper shell integration

## Common Issues

**Subtitle downloads fail**: Check if Pi-hole/DNS blocker is blocking `assets-jpcust.jwpsrv.com`. This domain must be unblocked for subtitle downloads.

**Browser cookies expired**: If downloads fail with authentication errors, log into BeaconTV in your browser and try again.

**Non-episodic content**: The script now handles all beacon.tv content, not just episodic Critical Role videos. One-shots, specials, and other content will be automatically detected and formatted appropriately.
