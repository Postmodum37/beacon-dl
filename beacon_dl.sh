#!/bin/bash

# BeaconTV Downloader - Download BeaconTV videos with subtitles
# Usage:
#   ./beacon_dl.sh <url>
#   ./beacon_dl.sh -h|--help

set -euo pipefail

# Validation helper function
validate_alphanum() {
    local value="$1"
    local varname="$2"
    if [[ ! "$value" =~ ^[a-zA-Z0-9._-]+$ ]]; then
        echo "Error: Invalid characters in $varname: $value" >&2
        echo "Only alphanumeric characters, dots, dashes, and underscores are allowed" >&2
        exit 1
    fi
}

# Configuration - can be overridden with environment variables
RELEASE_GROUP="${RELEASE_GROUP:-Pawsty}"
validate_alphanum "$RELEASE_GROUP" "RELEASE_GROUP"

PREFERRED_RESOLUTION="${PREFERRED_RESOLUTION:-1080p}"
validate_alphanum "$PREFERRED_RESOLUTION" "PREFERRED_RESOLUTION"

SOURCE_TYPE="${SOURCE_TYPE:-WEB-DL}"
validate_alphanum "$SOURCE_TYPE" "SOURCE_TYPE"

CONTAINER_FORMAT="${CONTAINER_FORMAT:-mkv}"
validate_alphanum "$CONTAINER_FORMAT" "CONTAINER_FORMAT"

DEFAULT_RESOLUTION="${DEFAULT_RESOLUTION:-1080p}"
DEFAULT_VIDEO_CODEC="${DEFAULT_VIDEO_CODEC:-H.264}"
DEFAULT_AUDIO_CODEC="${DEFAULT_AUDIO_CODEC:-AAC}"
DEFAULT_AUDIO_CHANNELS="${DEFAULT_AUDIO_CHANNELS:-2.0}"

# Validate container format
CONTAINER_LOWER=$(echo "$CONTAINER_FORMAT" | tr '[:upper:]' '[:lower:]')
case "$CONTAINER_LOWER" in
    mkv|mp4|avi|mov|webm) ;;
    *)
        echo "Error: Unsupported container format: $CONTAINER_FORMAT" >&2
        echo "Supported formats: mkv, mp4, avi, mov, webm" >&2
        exit 1
        ;;
esac

# Create secure temporary directory
TEMP_DIR=$(mktemp -d) || {
    echo "Error: Failed to create temporary directory" >&2
    exit 1
}

# Cleanup temporary files on exit
cleanup() {
    if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
}
trap cleanup EXIT

# Sanitize filename - remove special chars and convert spaces to dots
sanitize_filename() {
    local clean
    # Remove non-alphanumeric except spaces
    clean=$(echo "$1" | sed -e 's/[^a-zA-Z0-9 ]//g' -e 's/  */ /g' -e 's/ /./g')
    # Remove leading dots/dashes to prevent hidden files and argument injection
    clean=$(echo "$clean" | sed 's/^[.-]*//')
    # Limit length to 200 characters for filesystem compatibility
    clean="${clean:0:200}"
    # Ensure not empty
    if [ -z "$clean" ]; then
        clean="unnamed"
    fi
    echo "$clean"
}

# Show usage
show_usage() {
    echo "Usage:" >&2
    echo "  $0 <beacon_tv_url>" >&2
    echo "  $0 -h|--help" >&2
    echo "" >&2
    echo "Examples:" >&2
    echo "  $0 https://beacon.tv/content/c4-e006-knives-and-thorns" >&2
    echo "  $0 https://beacon.tv/content/critical-role-jester-and-fjords-wedding-live-from-radio-city-music-hall" >&2
    echo "" >&2
    echo "Configuration via environment variables:" >&2
    echo "  RELEASE_GROUP, PREFERRED_RESOLUTION, SOURCE_TYPE, CONTAINER_FORMAT" >&2
    echo "  See README.md for details" >&2
    exit 1
}

# Auto-detect browser profile
detect_browser_profile() {
    local profile=""

    # Check for Zen browser (Firefox fork) on macOS
    if [ -d "$HOME/Library/Application Support/zen/Profiles" ]; then
        profile=$(find "$HOME/Library/Application Support/zen/Profiles" -maxdepth 1 \( -name "*.default*" -o -name "*.Default*" \) | head -n 1)
        if [ -n "$profile" ]; then
            echo "firefox:$profile"
            return 0
        fi
    fi

    # Check for Firefox on macOS
    if [ -d "$HOME/Library/Application Support/Firefox/Profiles" ]; then
        profile=$(find "$HOME/Library/Application Support/Firefox/Profiles" -maxdepth 1 \( -name "*.default*" -o -name "*.Default*" \) | head -n 1)
        if [ -n "$profile" ]; then
            echo "firefox:$profile"
            return 0
        fi
    fi

    # Check for Firefox on Linux
    if [ -d "$HOME/.mozilla/firefox" ]; then
        profile=$(find "$HOME/.mozilla/firefox" -maxdepth 1 \( -name "*.default*" -o -name "*.Default*" \) | head -n 1)
        if [ -n "$profile" ]; then
            echo "firefox:$profile"
            return 0
        fi
    fi

    # Check for Chrome on macOS
    if [ -d "$HOME/Library/Application Support/Google/Chrome" ]; then
        echo "chrome"
        return 0
    fi

    # Check for Chrome on Linux
    if [ -d "$HOME/.config/google-chrome" ]; then
        echo "chrome"
        return 0
    fi

    # Fallback: return empty, let user specify
    return 1
}

# Map language name to ISO 639-2 code
map_language_to_iso() {
    local lang="$1"
    local lang_lower=$(echo "$lang" | tr '[:upper:]' '[:lower:]')
    case "$lang_lower" in
        english|en) echo "eng" ;;
        spanish|es|español) echo "spa" ;;
        french|fr|français) echo "fre" ;;
        italian|it|italiano) echo "ita" ;;
        portuguese|pt|português) echo "por" ;;
        german|de|deutsch) echo "ger" ;;
        japanese|ja|日本語) echo "jpn" ;;
        korean|ko|한국어) echo "kor" ;;
        chinese|zh|中文) echo "chi" ;;
        *) echo "und" ;;  # undefined
    esac
}

# Parse arguments
if [ $# -eq 0 ]; then
    show_usage
fi

# Check for help flag
if [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    show_usage
fi

URL="$1"

# Validate URL is from beacon.tv (HTTPS only for security)
if [[ ! $URL =~ ^https://beacon\.tv/content/[a-zA-Z0-9._-]+$ ]]; then
    echo "Error: Invalid BeaconTV URL" >&2
    echo "Expected format: https://beacon.tv/content/<content-id>" >&2
    echo "Note: HTTPS is required for security" >&2
    exit 1
fi

# Check for required dependencies
for cmd in yt-dlp jq ffmpeg ffprobe; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "Error: Required command '$cmd' not found" >&2
        echo "Please install $cmd and try again" >&2
        exit 1
    fi
done

# Browser profile - can be overridden with BROWSER_PROFILE env variable
if [ -z "${BROWSER_PROFILE:-}" ]; then
    DETECTED_PROFILE=$(detect_browser_profile)
    if [ -n "$DETECTED_PROFILE" ]; then
        BROWSER_PROFILE="$DETECTED_PROFILE"
        echo "Using detected browser profile: $BROWSER_PROFILE" >&2
    else
        # No hardcoded fallback - require user to specify
        echo "Error: Could not auto-detect browser profile" >&2
        echo "Please set BROWSER_PROFILE environment variable" >&2
        echo "Example: BROWSER_PROFILE=\"firefox\" ./beacon_dl.sh <url>" >&2
        echo "         BROWSER_PROFILE=\"firefox:/path/to/profile\" ./beacon_dl.sh <url>" >&2
        exit 1
    fi
fi

# Validate browser profile format for security
if [[ ! "$BROWSER_PROFILE" =~ ^(firefox|chrome|chromium|edge|safari|brave|opera)(:.*)?$ ]]; then
    echo "Error: Invalid BROWSER_PROFILE format: $BROWSER_PROFILE" >&2
    echo "Expected format: browser[:path]" >&2
    echo "Supported browsers: firefox, chrome, chromium, edge, safari, brave, opera" >&2
    exit 1
fi

echo "==> Fetching video metadata..."

# Get video metadata
if ! METADATA=$(yt-dlp --cookies-from-browser "$BROWSER_PROFILE" -j "$URL"); then
    echo "Error: Failed to fetch video metadata" >&2
    exit 1
fi

# Extract video information
VIDEO_ID=$(echo "$METADATA" | jq -r '.id')
VIDEO_TITLE=$(echo "$METADATA" | jq -r '.title')

# Extract show/series name (fallback to uploader, then "Critical.Role")
SHOW_NAME=$(echo "$METADATA" | jq -r '.series // .uploader // "Critical Role"')
# Sanitize show name for filename
SHOW_NAME=$(sanitize_filename "$SHOW_NAME")

echo "Show: $SHOW_NAME"
echo "Video: $VIDEO_TITLE"
echo "ID: $VIDEO_ID"

# Extract technical specs from metadata (used for all content types)
# Resolution
HEIGHT=$(echo "$METADATA" | jq -r '.height // empty')
if [ -z "$HEIGHT" ]; then
    RESOLUTION="$DEFAULT_RESOLUTION"
else
    RESOLUTION="${HEIGHT}p"
fi

# Video codec
VCODEC=$(echo "$METADATA" | jq -r '.vcodec // empty')
if [[ $VCODEC =~ ^avc ]]; then
    VIDEO_CODEC="H.264"
elif [[ $VCODEC =~ ^hevc ]]; then
    VIDEO_CODEC="H.265"
elif [[ $VCODEC =~ ^vp9 ]]; then
    VIDEO_CODEC="VP9"
else
    VIDEO_CODEC="$DEFAULT_VIDEO_CODEC"
fi

# Audio codec and channels
ACODEC=$(echo "$METADATA" | jq -r '.acodec // empty')
if [[ $ACODEC =~ ^mp4a ]]; then
    AUDIO_CODEC="AAC"
elif [[ $ACODEC =~ ^opus ]]; then
    AUDIO_CODEC="Opus"
elif [[ $ACODEC =~ ^vorbis ]]; then
    AUDIO_CODEC="Vorbis"
elif [[ $ACODEC =~ ^ac3 ]]; then
    AUDIO_CODEC="AC3"
elif [[ $ACODEC =~ ^eac3 ]]; then
    AUDIO_CODEC="EAC3"
else
    AUDIO_CODEC="$DEFAULT_AUDIO_CODEC"
fi

# Audio channels - extract from metadata or use default
CHANNELS=$(echo "$METADATA" | jq -r '.audio_channels // empty')
if [ -n "$CHANNELS" ] && [ "$CHANNELS" != "null" ]; then
    # Only append .0 if not already present (e.g., for stereo "2" -> "2.0")
    if [[ "$CHANNELS" =~ ^[0-9]+$ ]]; then
        AUDIO_CHANNELS="${CHANNELS}.0"
    else
        AUDIO_CHANNELS="$CHANNELS"
    fi
else
    AUDIO_CHANNELS="$DEFAULT_AUDIO_CHANNELS"
fi

# Parse season and episode from title - supports multiple formats
# Formats: "C4 E006 | Title", "S04E06 - Title", "4x06 - Title", etc.
IS_EPISODIC=false
SEASON=""
EPISODE=""
EPISODE_TITLE=""

# Try format: "C4 E006 | Title" (Critical Role format)
if [[ $VIDEO_TITLE =~ C([0-9]+)[[:space:]]+E([0-9]+)[[:space:]]+\|[[:space:]]+(.*) ]]; then
    IS_EPISODIC=true
    SEASON="${BASH_REMATCH[1]}"
    EPISODE="${BASH_REMATCH[2]}"
    EPISODE_TITLE="${BASH_REMATCH[3]}"
# Try format: "S04E06 - Title" or "S04E06: Title"
elif [[ $VIDEO_TITLE =~ S([0-9]+)E([0-9]+)[[:space:]]*[-:][[:space:]]*(.*) ]]; then
    IS_EPISODIC=true
    SEASON="${BASH_REMATCH[1]}"
    EPISODE="${BASH_REMATCH[2]}"
    EPISODE_TITLE="${BASH_REMATCH[3]}"
# Try format: "S04E06 Title" (no separator)
elif [[ $VIDEO_TITLE =~ S([0-9]+)E([0-9]+)[[:space:]]+(.*) ]]; then
    IS_EPISODIC=true
    SEASON="${BASH_REMATCH[1]}"
    EPISODE="${BASH_REMATCH[2]}"
    EPISODE_TITLE="${BASH_REMATCH[3]}"
# Try format: "4x06 - Title"
elif [[ $VIDEO_TITLE =~ ([0-9]+)x([0-9]+)[[:space:]]*[-:][[:space:]]*(.*) ]]; then
    IS_EPISODIC=true
    SEASON="${BASH_REMATCH[1]}"
    EPISODE="${BASH_REMATCH[2]}"
    EPISODE_TITLE="${BASH_REMATCH[3]}"
fi

if [ "$IS_EPISODIC" = true ]; then
    # Episodic content - validate season and episode numbers
    if [[ ! $SEASON =~ ^[0-9]+$ ]]; then
        echo "Error: Invalid season number: $SEASON" >&2
        exit 1
    fi
    if [[ ! $EPISODE =~ ^[0-9]+$ ]]; then
        echo "Error: Invalid episode number: $EPISODE" >&2
        exit 1
    fi

    SEASON_PADDED=$(printf "%02d" "$SEASON")
    EPISODE_PADDED=$(printf "%02d" "$EPISODE")
    # Sanitize title
    TITLE_FORMATTED=$(sanitize_filename "$EPISODE_TITLE")

    OUTPUT_NAME="${SHOW_NAME}.S${SEASON_PADDED}E${EPISODE_PADDED}.${TITLE_FORMATTED}.${RESOLUTION}.${SOURCE_TYPE}.${AUDIO_CODEC}${AUDIO_CHANNELS}.${VIDEO_CODEC}-${RELEASE_GROUP}"
else
    # One-shot/special content - use title only
    TITLE_FORMATTED=$(sanitize_filename "$VIDEO_TITLE")

    # Check if title already starts with show name to avoid duplication
    # Escape regex metacharacters in SHOW_NAME (including backslash itself)
    ESCAPED_SHOW_NAME=$(printf '%s\n' "$SHOW_NAME" | sed 's/[]\.*^$[(){}+?|\/]/\\&/g')
    if [[ $TITLE_FORMATTED =~ ^${ESCAPED_SHOW_NAME}\. ]]; then
        OUTPUT_NAME="${TITLE_FORMATTED}.${RESOLUTION}.${SOURCE_TYPE}.${AUDIO_CODEC}${AUDIO_CHANNELS}.${VIDEO_CODEC}-${RELEASE_GROUP}"
    else
        OUTPUT_NAME="${SHOW_NAME}.${TITLE_FORMATTED}.${RESOLUTION}.${SOURCE_TYPE}.${AUDIO_CODEC}${AUDIO_CHANNELS}.${VIDEO_CODEC}-${RELEASE_GROUP}"
    fi
fi

echo "Output: ${OUTPUT_NAME}.${CONTAINER_FORMAT}"
echo ""

# Check if already downloaded
if [ -f "${OUTPUT_NAME}.${CONTAINER_FORMAT}" ]; then
    echo "✓ Video already downloaded: ${OUTPUT_NAME}.${CONTAINER_FORMAT}"
    SKIP_DOWNLOAD=true
else
    SKIP_DOWNLOAD=false
fi

# Download if needed
if [ "$SKIP_DOWNLOAD" = false ]; then
    echo "==> Downloading video (${PREFERRED_RESOLUTION})..."
    TEMP_VIDEO="$TEMP_DIR/video.mp4"
    if ! yt-dlp --cookies-from-browser "$BROWSER_PROFILE" \
        -f "$PREFERRED_RESOLUTION" \
        -o "$TEMP_VIDEO" \
        --progress \
        "$URL"; then
        echo "Error: Failed to download video" >&2
        exit 1
    fi

    echo ""
    echo "==> Downloading all subtitle tracks..."
    TEMP_SUBS="$TEMP_DIR/subs"
    if ! yt-dlp --cookies-from-browser "$BROWSER_PROFILE" \
        --write-subs \
        --all-subs \
        --skip-download \
        -o "$TEMP_SUBS" \
        "$URL"; then
        echo "Error: Failed to download subtitles" >&2
        exit 1
    fi

    echo ""
    CONTAINER_UPPER=$(echo "$CONTAINER_FORMAT" | tr '[:lower:]' '[:upper:]')
    echo "==> Merging video and subtitles into ${CONTAINER_UPPER}..."

    # Build ffmpeg command with all subtitle tracks using array (secure)
    shopt -s nullglob
    SUBTITLE_FILES=("$TEMP_DIR"/subs.*.vtt)
    shopt -u nullglob

    # Start building ffmpeg arguments array
    ffmpeg_args=(-i "$TEMP_VIDEO")

    # Add subtitle inputs
    for sub in "${SUBTITLE_FILES[@]}"; do
        if [ -f "$sub" ]; then
            ffmpeg_args+=(-i "$sub")
        fi
    done

    # Add mapping for video and audio
    ffmpeg_args+=(-map 0:v -map 0:a)

    # Map all subtitle tracks
    SUB_INDEX=1
    for sub in "${SUBTITLE_FILES[@]}"; do
        if [ -f "$sub" ]; then
            ffmpeg_args+=(-map "$SUB_INDEX")
            ((SUB_INDEX++))
        fi
    done

    # Add codec options
    ffmpeg_args+=(-c:v copy -c:a copy -c:s srt)

    # Add language metadata for each subtitle (dynamic detection)
    SUB_STREAM=0
    for sub in "${SUBTITLE_FILES[@]}"; do
        if [ -f "$sub" ]; then
            # Extract language from filename (e.g., temp_subs.en.English.vtt -> English)
            # Try to match pattern: .{lang_code}.{language_name}.vtt (case-insensitive)
            if [[ $sub =~ \.([a-zA-Z]{2,3})\.([^.]+)\.vtt$ ]]; then
                LANG_NAME="${BASH_REMATCH[2]}"
            elif [[ $sub =~ \.([^.]+)\.vtt$ ]]; then
                LANG_NAME="${BASH_REMATCH[1]}"
            else
                LANG_NAME="unknown"
            fi

            # Map language name to ISO code
            LANG_CODE=$(map_language_to_iso "$LANG_NAME")
            ffmpeg_args+=(-metadata:s:s:"$SUB_STREAM" language="$LANG_CODE")
            ((SUB_STREAM++))
        fi
    done

    # Add output file and options
    ffmpeg_args+=("${OUTPUT_NAME}.${CONTAINER_FORMAT}" -y -hide_banner -loglevel warning -stats)

    # Execute ffmpeg command (safe - no eval)
    ffmpeg "${ffmpeg_args[@]}"

    if [ ! -f "${OUTPUT_NAME}.${CONTAINER_FORMAT}" ]; then
        echo "Error: Failed to create output file" >&2
        exit 1
    fi

    # Validate output file size
    if command -v stat &> /dev/null; then
        # Try BSD stat (macOS) first, then GNU stat (Linux)
        FILE_SIZE_BYTES=$(stat -f%z "${OUTPUT_NAME}.${CONTAINER_FORMAT}" 2>/dev/null || stat -c%s "${OUTPUT_NAME}.${CONTAINER_FORMAT}" 2>/dev/null || echo "0")
        if [ "$FILE_SIZE_BYTES" -lt 1048576 ]; then  # Less than 1MB
            echo "Warning: Output file is suspiciously small (${FILE_SIZE_BYTES} bytes)" >&2
            echo "The download may have failed or been incomplete" >&2
        fi
    fi

    echo ""
    echo "✓ Download complete: ${OUTPUT_NAME}.${CONTAINER_FORMAT}"
fi

# Display final summary
FILE_SIZE=$(du -h "${OUTPUT_NAME}.${CONTAINER_FORMAT}" | cut -f1)
echo ""
echo "File: ${OUTPUT_NAME}.${CONTAINER_FORMAT} ($FILE_SIZE)"
echo ""
