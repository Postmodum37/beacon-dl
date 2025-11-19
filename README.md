# Critical Role BeaconTV Downloader

Automated script to download Critical Role videos from BeaconTV with all subtitle tracks, creating properly formatted MKV files ready for release processing.

## Quick Start

```bash
# Episodic content
./beacon_dl.sh https://beacon.tv/content/c4-e006-knives-and-thorns

# One-shots and specials
./beacon_dl.sh https://beacon.tv/content/critical-role-jester-and-fjords-wedding-live-from-radio-city-music-hall
```

## Features

✅ **Automated Download**: Downloads video in best quality (1080p H.264)
✅ **All Subtitles**: Downloads and embeds 5 language tracks (English, Spanish, French, Italian, Portuguese)
✅ **Universal Support**: Handles both episodic content and one-shots/specials
✅ **Proper Naming**: Follows scene/P2P naming standards
✅ **No Re-encoding**: Direct stream copy (no quality loss)
✅ **Smart Skip**: Detects existing downloads and reuses them
✅ **Ready for Upload-Assistant**: Outputs clean MKV files for release creation

## Output Examples

**Episodic content:**
```
Critical.Role.S04E06.Knives.and.Thorns.1080p.WEB-DL.AAC2.0.H.264-Pawsty.mkv
```

**One-shots/specials:**
```
Critical.Role.Jester.and.Fjords.Wedding.Live.from.Radio.City.Music.Hall.1080p.WEB-DL.AAC2.0.H.264-Pawsty.mkv
```

The script automatically detects the content type and formats the filename appropriately.

## Requirements

```bash
# Required
brew install yt-dlp jq ffmpeg

# For release creation (use Upload-Assistant separately)
# https://github.com/Audionut/Upload-Assistant
```

## Configuration

### Browser Profile

The script needs access to your BeaconTV cookies. Set the browser profile:

```bash
# Default (Zen browser on macOS)
# Automatically used if not specified

# Custom profile
export BROWSER_PROFILE="firefox:~/path/to/your/profile"
./beacon_dl.sh <url>
```

## Release Specifications

- **Video**: H.264 (High Profile), 1920x1080, 30fps, ~2414 kbps
- **Audio**: AAC-LC 2.0, 44.1 kHz, ~120 kbps
- **Container**: Matroska (MKV)
- **Subtitles**: 5 tracks (eng, spa, fre, ita, por) - SRT format, embedded
- **Source**: BeaconTV WEB-DL (no re-encoding)
- **Group**: Pawsty

## Creating Releases

This script outputs MKV files ready for Upload-Assistant processing. Use Upload-Assistant to create complete release packages (NFO, MediaInfo, samples, screenshots, torrents).

```bash
# After downloading the MKV
python3 upload.py /path/to/Critical.Role.*.mkv
```

See [Upload-Assistant documentation](https://github.com/Audionut/Upload-Assistant) for details.

## Troubleshooting

### Subtitle downloads fail

Check if your DNS blocker (Pi-hole) is blocking `assets-jpcust.jwpsrv.com`. Whitelist this domain.

### Browser cookies expired

Log into BeaconTV in your browser, then try again.

### Non-standard video titles

The script automatically handles both episodic format ("C4 E006 | Title") and non-episodic content (one-shots, specials). No special configuration needed.

## See Also

- [CLAUDE.md](CLAUDE.md) - Detailed technical documentation
- [Upload-Assistant](https://github.com/Audionut/Upload-Assistant) - For creating release packages
