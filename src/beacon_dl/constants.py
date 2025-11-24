"""Constants and configuration values for beacon-tv-downloader.

Centralizes magic strings, mappings, and configuration constants.
"""

# Language to ISO 639-2 code mapping
LANGUAGE_TO_ISO_MAP = {
    "english": "eng",
    "en": "eng",
    "spanish": "spa",
    "es": "spa",
    "español": "spa",
    "french": "fre",
    "fr": "fre",
    "français": "fre",
    "italian": "ita",
    "it": "ita",
    "italiano": "ita",
    "portuguese": "por",
    "pt": "por",
    "português": "por",
    "german": "ger",
    "de": "ger",
    "deutsch": "ger",
    "japanese": "jpn",
    "ja": "jpn",
    "日本語": "jpn",
    "korean": "kor",
    "ko": "kor",
    "한국어": "kor",
    "chinese": "chi",
    "zh": "chi",
    "中文": "chi",
}

# Supported container formats
SUPPORTED_CONTAINER_FORMATS = ["mkv", "mp4", "avi", "mov", "webm", "flv", "m4v"]

# Supported codecs
VIDEO_CODECS = {
    "h264": "H.264",
    "avc": "H.264",
    "x264": "H.264",
    "h265": "H.265",
    "hevc": "H.265",
    "x265": "H.265",
    "vp9": "VP9",
    "av1": "AV1",
}

AUDIO_CODECS = {
    "aac": "AAC",
    "opus": "Opus",
    "vorbis": "Vorbis",
    "ac3": "AC3",
    "eac3": "EAC3",
    "mp3": "MP3",
    "flac": "FLAC",
}

# Default values
DEFAULT_RELEASE_GROUP = "Pawsty"
DEFAULT_SOURCE_TYPE = "WEB-DL"
DEFAULT_CONTAINER_FORMAT = "mkv"
DEFAULT_RESOLUTION = "1080p"
DEFAULT_AUDIO_CODEC = "AAC"
DEFAULT_AUDIO_CHANNELS = "2.0"
DEFAULT_VIDEO_CODEC = "H.264"

# BeaconTV API
BEACON_TV_API_ENDPOINT = "https://beacon.tv/api/graphql"
BEACON_TV_LOGIN_URL = "https://members.beacon.tv/auth/sign_in"
BEACON_TV_BASE_URL = "https://beacon.tv"
BEACON_TV_CONTENT_URL = "https://beacon.tv/content"

# Known collection IDs (cached for performance)
KNOWN_COLLECTIONS = {
    "campaign-4": "68caf69e7a76bce4b7aa689a",
}

# Validation patterns
SLUG_PATTERN = r"^[a-zA-Z0-9_-]+$"
RESOLUTION_PATTERN = r"^\d{3,4}p$"
AUDIO_CHANNELS_PATTERN = r"^\d+\.\d+$"
ALPHANUM_PATTERN = r"^[a-zA-Z0-9._-]+$"

# File permissions (octal)
SECURE_FILE_PERMISSIONS = 0o600  # -rw------- (owner read/write only)
SECURE_DIR_PERMISSIONS = 0o700  # drwx------ (owner full access only)

# Timeouts (in seconds)
DEFAULT_HTTP_TIMEOUT = 10
PLAYWRIGHT_PAGE_TIMEOUT = 30000  # milliseconds
PLAYWRIGHT_NAVIGATION_TIMEOUT = 30000  # milliseconds

# User agents
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
