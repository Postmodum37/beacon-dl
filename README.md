# BeaconTV Downloader

Fully configurable script to download BeaconTV videos with all subtitle tracks, creating properly formatted video files ready for release processing. Originally designed for Critical Role, now supports any BeaconTV content with automatic metadata detection.

## Quick Start

```bash
# Episodic content
./beacon_dl.sh https://beacon.tv/content/c4-e006-knives-and-thorns

# One-shots and specials
./beacon_dl.sh https://beacon.tv/content/critical-role-jester-and-fjords-wedding-live-from-radio-city-music-hall
```

## Features

✅ **Fully Configurable**: Every aspect customizable via environment variables
✅ **Dynamic Metadata**: Auto-detects show name, codecs, resolution from video metadata
✅ **Browser Auto-Detection**: Automatically finds Firefox, Zen, or Chrome profiles (macOS/Linux)
✅ **Multi-Format Episodes**: Supports 4+ episode numbering formats (S04E06, C4 E006, 4x06, etc.)
✅ **Universal Subtitles**: Dynamic language detection supporting 9+ languages with ISO 639-2 mapping
✅ **All Content Types**: Handles episodic content, one-shots, and specials automatically
✅ **Quality Options**: Configurable resolution (1080p, 720p, 4K, etc.)
✅ **Custom Releases**: Configure release group, source type, container format
✅ **No Re-encoding**: Direct stream copy (no quality loss)
✅ **Smart Skip**: Detects existing downloads to avoid duplicates
✅ **Ready for Upload-Assistant**: Outputs clean files for release creation
✅ **Security Hardened**: Input validation, HTTPS-only, secure temp files, injection prevention

## Output Examples

**Default output (episodic):**
```
Critical.Role.S04E06.Knives.and.Thorns.1080p.WEB-DL.AAC2.0.H.264-Pawsty.mkv
```

**Default output (one-shots/specials):**
```
Critical.Role.Jester.and.Fjords.Wedding.Live.from.Radio.City.Music.Hall.1080p.WEB-DL.AAC2.0.H.264-Pawsty.mkv
```

**Custom release group:**
```bash
RELEASE_GROUP="MyGroup" ./beacon_dl.sh <url>
# Output: Critical.Role.S04E06.Knives.and.Thorns.1080p.WEB-DL.AAC2.0.H.264-MyGroup.mkv
```

**Different resolution:**
```bash
PREFERRED_RESOLUTION="720p" ./beacon_dl.sh <url>
# Output: Critical.Role.S04E06.Knives.and.Thorns.720p.WEB-DL.AAC2.0.H.264-Pawsty.mkv
```

**All components are automatically detected from metadata or configurable via environment variables.**

## Requirements

```bash
# Required
brew install yt-dlp jq ffmpeg

# For release creation (use Upload-Assistant separately)
# https://github.com/Audionut/Upload-Assistant
```

## Security

- **HTTPS Required**: Only HTTPS URLs accepted for security
- **Input Validation**: Environment variables validated (alphanumeric, dots, dashes, underscores only)
- **Secure Temp Files**: Random temporary directories prevent conflicts
- **No Command Injection**: Blocks path traversal and injection attempts

**Supported browsers**: firefox, chrome, chromium, edge, safari, brave, opera

## Configuration

All aspects of the script can be customized via environment variables. The script auto-detects metadata when possible and uses sensible defaults.

### Browser Authentication

**Auto-Detection (Recommended):**
The script automatically detects browser profiles in this order:
1. Zen browser (macOS)
2. Firefox (macOS/Linux)
3. Chrome (macOS/Linux)

```bash
# Just run the script - browser profile auto-detected
./beacon_dl.sh <url>
```

**Manual Override:**
```bash
# Specify custom browser profile
BROWSER_PROFILE="firefox:~/path/to/your/profile" ./beacon_dl.sh <url>

# Use Chrome
BROWSER_PROFILE="chrome" ./beacon_dl.sh <url>
```

### Release Customization

```bash
# Custom release group (default: Pawsty)
RELEASE_GROUP="MyGroup" ./beacon_dl.sh <url>

# Source type (default: WEB-DL)
SOURCE_TYPE="WEBRip" ./beacon_dl.sh <url>

# Container format (default: mkv)
CONTAINER_FORMAT="mp4" ./beacon_dl.sh <url>
```

### Quality Settings

```bash
# Preferred resolution (default: 1080p)
PREFERRED_RESOLUTION="720p" ./beacon_dl.sh <url>
PREFERRED_RESOLUTION="2160p" ./beacon_dl.sh <url>  # 4K
```

### Metadata Fallbacks

Defaults if metadata extraction fails: 1080p, H.264, AAC 2.0

### Combined Example

```bash
# Custom release with 720p
RELEASE_GROUP="CustomGroup" \
PREFERRED_RESOLUTION="720p" \
SOURCE_TYPE="WEBRip" \
./beacon_dl.sh <url>
```

## Technical Details

**Auto-detected from metadata**: Show name, resolution, video/audio codecs, audio channels, subtitles

**Typical specs**: H.264 1080p 30fps, AAC 2.0, MKV container, no re-encoding

**Episode formats supported**: `C4 E006 | Title`, `S04E06 - Title`, `S04E06 Title`, `4x06 - Title`

Non-episodic content handled automatically.

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

Log into BeaconTV in your browser, then try again. The script will use the updated cookies automatically.

### Browser profile not detected

Set `BROWSER_PROFILE` manually if auto-detection fails:
```bash
# Find profile: ls ~/Library/Application\ Support/Firefox/Profiles/  (macOS)
BROWSER_PROFILE="firefox:~/path/to/profile" ./beacon_dl.sh <url>
BROWSER_PROFILE="firefox" ./beacon_dl.sh <url>  # Use default
```

### Invalid characters error

Only alphanumeric, dots (`.`), dashes (`-`), and underscores (`_`) allowed in environment variables:

```bash
# Wrong: RELEASE_GROUP="../test"
# Right: RELEASE_GROUP="MyGroup-v2.0"
```

### HTTP URL rejected

HTTPS required for security. Use `https://` not `http://`.

### Wrong show name or metadata

The script automatically extracts show name from metadata. If incorrect, you can manually rename the file after download, or edit the show name extraction logic in the script (search for `.series // .uploader`).

### Custom filename format needed

All filename components are configurable:
- Release group: `RELEASE_GROUP="YourGroup"`
- Source type: `SOURCE_TYPE="WEBRip"`
- Container: `CONTAINER_FORMAT="mp4"`

See the Configuration section for all options.

### Multiple episode formats

The script supports 4+ episode numbering formats automatically. Non-episodic content (one-shots, specials) is detected and formatted without season/episode numbers.

## See Also

- [CLAUDE.md](CLAUDE.md) - Detailed technical documentation
- [Upload-Assistant](https://github.com/Audionut/Upload-Assistant) - For creating release packages
