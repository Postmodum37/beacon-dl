#!/bin/bash

# BeaconTV Downloader - Download Critical Role videos with subtitles
# Usage:
#   ./beacon_dl.sh <url>

set -e

# Cleanup temporary files on exit
cleanup() {
    rm -f temp_video.mp4 temp_*.vtt
}
trap cleanup EXIT

# Show usage
show_usage() {
    echo "Usage:" >&2
    echo "  $0 <beacon_tv_url>" >&2
    echo "" >&2
    echo "Examples:" >&2
    echo "  $0 https://beacon.tv/content/c4-e006-knives-and-thorns" >&2
    echo "  $0 https://beacon.tv/content/critical-role-jester-and-fjords-wedding-live-from-radio-city-music-hall" >&2
    exit 1
}

# Parse arguments
if [ $# -eq 0 ]; then
    show_usage
fi

URL="$1"

# Check for required dependencies
for cmd in yt-dlp jq ffmpeg ffprobe; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "Error: Required command '$cmd' not found" >&2
        echo "Please install $cmd and try again" >&2
        exit 1
    fi
done

# Browser profile - can be overridden with BROWSER_PROFILE env variable
BROWSER_PROFILE="${BROWSER_PROFILE:-firefox:~/Library/Application Support/zen/Profiles/oc1q8w6o.Default (release)-1}"

echo "==> Fetching video metadata..."

# Get video metadata
if ! METADATA=$(yt-dlp --cookies-from-browser "$BROWSER_PROFILE" -j "$URL" 2>/dev/null); then
    echo "Error: Failed to fetch video metadata" >&2
    exit 1
fi

# Extract video information
VIDEO_ID=$(echo "$METADATA" | jq -r '.id')
VIDEO_TITLE=$(echo "$METADATA" | jq -r '.title')

echo "Video: $VIDEO_TITLE"
echo "ID: $VIDEO_ID"

# Extract technical specs from metadata (used for all content types)
# Resolution
HEIGHT=$(echo "$METADATA" | jq -r '.height // empty')
if [ -z "$HEIGHT" ]; then
    RESOLUTION="1080p"
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
    VIDEO_CODEC="H.264"  # Default fallback
fi

# Audio codec and channels
ACODEC=$(echo "$METADATA" | jq -r '.acodec // empty')
if [[ $ACODEC =~ ^mp4a ]]; then
    AUDIO_CODEC="AAC"
elif [[ $ACODEC =~ ^opus ]]; then
    AUDIO_CODEC="Opus"
else
    AUDIO_CODEC="AAC"  # Default fallback
fi

# Audio channels (default to 2.0)
AUDIO_CHANNELS="2.0"

# Parse season and episode from title (e.g., "C4 E006 | Knives and Thorns")
# For episodic content, use SxxExx format. For one-shots/specials, use title only.
if [[ $VIDEO_TITLE =~ C([0-9]+)[[:space:]]+E([0-9]+)[[:space:]]+\|[[:space:]]+(.*) ]]; then
    # Episodic content
    SEASON="${BASH_REMATCH[1]}"
    EPISODE="${BASH_REMATCH[2]}"
    EPISODE_TITLE="${BASH_REMATCH[3]}"

    SEASON_PADDED=$(printf "%02d" "$SEASON")
    EPISODE_PADDED=$(printf "%02d" "$EPISODE")
    # Remove special chars and convert all spaces to dots
    TITLE_FORMATTED=$(echo "$EPISODE_TITLE" | sed 's/[^a-zA-Z0-9 ]//g' | sed 's/  */ /g' | sed 's/ /./g')

    OUTPUT_NAME="Critical.Role.S${SEASON_PADDED}E${EPISODE_PADDED}.${TITLE_FORMATTED}.${RESOLUTION}.WEB-DL.${AUDIO_CODEC}${AUDIO_CHANNELS}.${VIDEO_CODEC}-Pawsty"
else
    # One-shot/special content - use title only
    # Remove special chars and convert all spaces to dots
    TITLE_FORMATTED=$(echo "$VIDEO_TITLE" | sed 's/[^a-zA-Z0-9 ]//g' | sed 's/  */ /g' | sed 's/ /./g')

    # Check if title already starts with "Critical Role" to avoid duplication
    if [[ $TITLE_FORMATTED =~ ^Critical\.Role\. ]]; then
        OUTPUT_NAME="${TITLE_FORMATTED}.${RESOLUTION}.WEB-DL.${AUDIO_CODEC}${AUDIO_CHANNELS}.${VIDEO_CODEC}-Pawsty"
    else
        OUTPUT_NAME="Critical.Role.${TITLE_FORMATTED}.${RESOLUTION}.WEB-DL.${AUDIO_CODEC}${AUDIO_CHANNELS}.${VIDEO_CODEC}-Pawsty"
    fi
fi

echo "Output: ${OUTPUT_NAME}.mkv"
echo ""

# Check if already downloaded
if [ -f "${OUTPUT_NAME}.mkv" ]; then
    echo "✓ Video already downloaded: ${OUTPUT_NAME}.mkv"
    SKIP_DOWNLOAD=true
else
    SKIP_DOWNLOAD=false
fi

# Download if needed
if [ "$SKIP_DOWNLOAD" = false ]; then
    echo "==> Downloading video (1080p)..."
    if ! yt-dlp --cookies-from-browser "$BROWSER_PROFILE" \
        -f 1080p \
        -o "temp_video.mp4" \
        --progress \
        "$URL"; then
        echo "Error: Failed to download video" >&2
        exit 1
    fi

    echo ""
    echo "==> Downloading all subtitle tracks..."
    if ! yt-dlp --cookies-from-browser "$BROWSER_PROFILE" \
        --write-subs \
        --all-subs \
        --skip-download \
        -o "temp_subs" \
        "$URL"; then
        echo "Error: Failed to download subtitles" >&2
        exit 1
    fi

    echo ""
    echo "==> Merging video and subtitles into MKV..."

    # Build ffmpeg command with all subtitle tracks
    SUBTITLE_FILES=(temp_subs.*.vtt)
    FFMPEG_CMD="ffmpeg -i temp_video.mp4"

    # Add subtitle inputs
    for sub in "${SUBTITLE_FILES[@]}"; do
        if [ -f "$sub" ]; then
            FFMPEG_CMD="$FFMPEG_CMD -i $sub"
        fi
    done

    # Add mapping and metadata
    FFMPEG_CMD="$FFMPEG_CMD -map 0:v -map 0:a"

    # Map all subtitle tracks
    SUB_INDEX=1
    for sub in "${SUBTITLE_FILES[@]}"; do
        if [ -f "$sub" ]; then
            FFMPEG_CMD="$FFMPEG_CMD -map $SUB_INDEX"
            ((SUB_INDEX++))
        fi
    done

    # Add codec and metadata options
    FFMPEG_CMD="$FFMPEG_CMD -c:v copy -c:a copy -c:s srt"

    # Add language metadata for each subtitle
    SUB_STREAM=0
    for sub in "${SUBTITLE_FILES[@]}"; do
        if [ -f "$sub" ]; then
            if [[ $sub =~ \.English\. ]]; then
                FFMPEG_CMD="$FFMPEG_CMD -metadata:s:s:$SUB_STREAM language=eng"
            elif [[ $sub =~ \.Spanish\. ]]; then
                FFMPEG_CMD="$FFMPEG_CMD -metadata:s:s:$SUB_STREAM language=spa"
            elif [[ $sub =~ \.French\. ]]; then
                FFMPEG_CMD="$FFMPEG_CMD -metadata:s:s:$SUB_STREAM language=fre"
            elif [[ $sub =~ \.Italian\. ]]; then
                FFMPEG_CMD="$FFMPEG_CMD -metadata:s:s:$SUB_STREAM language=ita"
            elif [[ $sub =~ \.Portuguese\. ]]; then
                FFMPEG_CMD="$FFMPEG_CMD -metadata:s:s:$SUB_STREAM language=por"
            fi
            ((SUB_STREAM++))
        fi
    done

    # Add output file
    FFMPEG_CMD="$FFMPEG_CMD \"${OUTPUT_NAME}.mkv\" -y -hide_banner -loglevel warning -stats"

    # Execute ffmpeg command
    eval $FFMPEG_CMD

    if [ ! -f "${OUTPUT_NAME}.mkv" ]; then
        echo "Error: Failed to create output file" >&2
        exit 1
    fi

    echo ""
    echo "✓ Download complete: ${OUTPUT_NAME}.mkv"
fi

# Display final summary
FILE_SIZE=$(du -h "${OUTPUT_NAME}.mkv" | cut -f1)
echo ""
echo "File: ${OUTPUT_NAME}.mkv ($FILE_SIZE)"
echo ""
