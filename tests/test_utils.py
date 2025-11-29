"""Tests for utility functions.

This module uses pytest.mark.parametrize for efficient testing of
multiple input/output combinations.
"""

import pytest

pytestmark = pytest.mark.unit  # All tests in this module are unit tests

from src.beacon_dl.utils import (
    extract_slug,
    format_bitrate,
    format_duration,
    format_episode_code,
    format_file_size,
    load_cookies,
    map_language_to_iso,
    sanitize_filename,
)


# =============================================================================
# Filename Sanitization Tests
# =============================================================================


class TestFilenameSanitization:
    """Tests for filename sanitization function."""

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            # Basic transformations
            ("Hello World", "Hello.World"),
            ("Hello: World & More!", "Hello.World.More"),
            ("Hello    World", "Hello.World"),
            ("It's Great", "Its.Great"),
            ("Part 1/2", "Part.12"),
            ("Episode: Title", "Episode.Title"),
            ("Title (2024)", "Title.2024"),
            ("TitleS01E01", "TitleS01E01"),
            # Edge cases
            ("", "unnamed"),
            ("!@#$%^&*()", "unnamed"),
            ("---test", "test"),
            ("12345", "12345"),
        ],
        ids=[
            "basic_spaces",
            "special_chars",
            "multiple_spaces",
            "apostrophes",
            "slashes",
            "colons",
            "parentheses",
            "alphanumeric",
            "empty_string",
            "only_special_chars",
            "leading_dashes",
            "numbers_only",
        ],
    )
    def test_sanitize_filename(self, input_name: str, expected: str):
        """Test filename sanitization with various inputs."""
        assert sanitize_filename(input_name) == expected

    def test_sanitize_trailing_spaces(self):
        """Test leading/trailing spaces are converted to dots then trimmed."""
        # Leading spaces become dots which are removed, trailing spaces become trailing dots
        assert sanitize_filename("  Hello World  ") == "Hello.World."

    def test_sanitize_length_limit(self):
        """Test long filenames are truncated to 200 chars."""
        long_name = "A" * 300
        result = sanitize_filename(long_name)
        assert len(result) <= 200

    def test_sanitize_unicode(self):
        """Test unicode characters are removed."""
        result = sanitize_filename("Café 中文")
        assert result == "Caf."


# =============================================================================
# Language Mapping Tests
# =============================================================================


class TestLanguageMapping:
    """Tests for language to ISO code mapping."""

    @pytest.mark.parametrize(
        "language,expected",
        [
            # English variations
            ("english", "eng"),
            ("English", "eng"),
            ("ENGLISH", "eng"),
            ("en", "eng"),
            # Spanish variations
            ("spanish", "spa"),
            ("español", "spa"),
            ("es", "spa"),
            # French variations
            ("french", "fre"),
            ("français", "fre"),
            ("fr", "fre"),
            # German variations
            ("german", "ger"),
            ("deutsch", "ger"),
            ("de", "ger"),
            # Italian variations
            ("italian", "ita"),
            ("italiano", "ita"),
            ("it", "ita"),
            # Portuguese variations
            ("portuguese", "por"),
            ("português", "por"),
            ("pt", "por"),
            # Asian languages
            ("japanese", "jpn"),
            ("ja", "jpn"),
            ("korean", "kor"),
            ("ko", "kor"),
            ("chinese", "chi"),
            ("zh", "chi"),
            # Unknown/undefined
            ("klingon", "und"),
            ("", "und"),
            ("xyz123", "und"),
        ],
        ids=[
            "english_lower",
            "english_title",
            "english_upper",
            "english_code",
            "spanish_lower",
            "spanish_native",
            "spanish_code",
            "french_lower",
            "french_native",
            "french_code",
            "german_lower",
            "german_native",
            "german_code",
            "italian_lower",
            "italian_native",
            "italian_code",
            "portuguese_lower",
            "portuguese_native",
            "portuguese_code",
            "japanese_lower",
            "japanese_code",
            "korean_lower",
            "korean_code",
            "chinese_lower",
            "chinese_code",
            "unknown_klingon",
            "empty_string",
            "unknown_random",
        ],
    )
    def test_map_language_to_iso(self, language: str, expected: str):
        """Test language to ISO code mapping."""
        assert map_language_to_iso(language) == expected

    def test_map_partial_match(self):
        """Test partial language name matching returns undefined."""
        result = map_language_to_iso("english.subtitles")
        assert result in ["eng", "und"]


# =============================================================================
# Format Functions Tests
# =============================================================================


class TestFormatDuration:
    """Tests for duration formatting function."""

    @pytest.mark.parametrize(
        "seconds,expected",
        [
            (0, "0m"),
            (30, "0m"),
            (60, "1m"),
            (90, "1m"),
            (1800, "30m"),
            (3600, "1h 0m"),
            (3660, "1h 1m"),
            (5400, "1h 30m"),
            (7200, "2h 0m"),
            (9000, "2h 30m"),
        ],
        ids=[
            "zero",
            "30_seconds",
            "1_minute",
            "90_seconds",
            "30_minutes",
            "1_hour",
            "1h_1m",
            "1h_30m",
            "2_hours",
            "2h_30m",
        ],
    )
    def test_format_duration(self, seconds: int, expected: str):
        """Test duration formatting."""
        assert format_duration(seconds) == expected


class TestFormatBitrate:
    """Tests for bitrate formatting function."""

    @pytest.mark.parametrize(
        "kbps,expected",
        [
            (100, "100 kbps"),
            (800, "800 kbps"),
            (999, "999 kbps"),
            (1000, "1.0 Mbps"),
            (2500, "2.5 Mbps"),
            (5000, "5.0 Mbps"),
            (5200, "5.2 Mbps"),
        ],
        ids=[
            "100kbps",
            "800kbps",
            "999kbps",
            "1mbps",
            "2.5mbps",
            "5mbps",
            "5.2mbps",
        ],
    )
    def test_format_bitrate(self, kbps: int, expected: str):
        """Test bitrate formatting."""
        assert format_bitrate(kbps) == expected


class TestFormatFileSize:
    """Tests for file size formatting function."""

    @pytest.mark.parametrize(
        "size_bytes,expected",
        [
            (0, "0 B"),
            (-100, "0 B"),
            (500, "500 B"),
            (1_000, "1.0 KB"),
            (150_000, "150.0 KB"),
            (1_000_000, "1.0 MB"),
            (150_000_000, "150.0 MB"),
            (1_000_000_000, "1.00 GB"),
            (1_500_000_000, "1.50 GB"),
            (2_500_000_000, "2.50 GB"),
        ],
        ids=[
            "zero",
            "negative",
            "500_bytes",
            "1kb",
            "150kb",
            "1mb",
            "150mb",
            "1gb",
            "1.5gb",
            "2.5gb",
        ],
    )
    def test_format_file_size(self, size_bytes: int, expected: str):
        """Test file size formatting."""
        assert format_file_size(size_bytes) == expected


class TestFormatEpisodeCode:
    """Tests for episode code formatting function."""

    @pytest.mark.parametrize(
        "season,episode,expected",
        [
            (4, 7, "S04E07"),
            (1, 1, "S01E01"),
            (10, 25, "S10E25"),
            (None, 5, "S?E05"),
            (4, None, "S04E?"),
            (None, None, "-"),
        ],
        ids=[
            "s04e07",
            "s01e01",
            "s10e25",
            "unknown_season",
            "unknown_episode",
            "both_unknown",
        ],
    )
    def test_format_episode_code(
        self, season: int | None, episode: int | None, expected: str
    ):
        """Test episode code formatting."""
        assert format_episode_code(season, episode) == expected


# =============================================================================
# URL/Slug Extraction Tests
# =============================================================================


class TestExtractSlug:
    """Tests for URL slug extraction."""

    @pytest.mark.parametrize(
        "input_url,expected",
        [
            ("https://beacon.tv/content/c4-e007", "c4-e007"),
            ("https://beacon.tv/content/c4-e007?ref=home", "c4-e007"),
            ("c4-e007", "c4-e007"),
            ("some-random-slug", "some-random-slug"),
        ],
        ids=[
            "full_url",
            "url_with_query",
            "slug_only",
            "random_slug",
        ],
    )
    def test_extract_slug(self, input_url: str, expected: str):
        """Test slug extraction from URLs."""
        assert extract_slug(input_url) == expected


# =============================================================================
# Constants Tests
# =============================================================================


class TestConstants:
    """Tests that import and verify constants."""

    def test_import_constants(self):
        """Test constants can be imported and have expected values."""
        from src.beacon_dl.constants import (
            DEFAULT_CONTAINER_FORMAT,
            DEFAULT_RESOLUTION,
            KNOWN_COLLECTIONS,
            PLAYWRIGHT_BANNER_TIMEOUT,
            PLAYWRIGHT_CLICK_TIMEOUT,
            PLAYWRIGHT_NAVIGATION_TIMEOUT,
            PLAYWRIGHT_NETWORKIDLE_TIMEOUT,
            PLAYWRIGHT_PAGE_TIMEOUT,
            PLAYWRIGHT_SELECTOR_TIMEOUT,
            PLAYWRIGHT_SSO_TIMEOUT,
            SECURE_FILE_PERMISSIONS,
        )

        assert DEFAULT_RESOLUTION == "1080p"
        assert DEFAULT_CONTAINER_FORMAT == "mkv"
        assert "campaign-4" in KNOWN_COLLECTIONS
        assert SECURE_FILE_PERMISSIONS == 0o600

        # Playwright timeouts in milliseconds
        assert PLAYWRIGHT_PAGE_TIMEOUT == 30000
        assert PLAYWRIGHT_NAVIGATION_TIMEOUT == 30000
        assert PLAYWRIGHT_SELECTOR_TIMEOUT == 10000
        assert PLAYWRIGHT_NETWORKIDLE_TIMEOUT == 10000
        assert PLAYWRIGHT_SSO_TIMEOUT == 15000
        assert PLAYWRIGHT_CLICK_TIMEOUT == 5000
        assert PLAYWRIGHT_BANNER_TIMEOUT == 2000

    def test_language_map_completeness(self):
        """Test language map has expected entries."""
        from src.beacon_dl.constants import LANGUAGE_TO_ISO_MAP

        assert "english" in LANGUAGE_TO_ISO_MAP
        assert "spanish" in LANGUAGE_TO_ISO_MAP
        assert LANGUAGE_TO_ISO_MAP["english"] == "eng"
        assert LANGUAGE_TO_ISO_MAP["spanish"] == "spa"

    def test_container_formats(self):
        """Test supported container formats."""
        from src.beacon_dl.constants import SUPPORTED_CONTAINER_FORMATS

        assert "mkv" in SUPPORTED_CONTAINER_FORMATS
        assert "mp4" in SUPPORTED_CONTAINER_FORMATS
        assert len(SUPPORTED_CONTAINER_FORMATS) >= 5

    def test_codec_mappings(self):
        """Test codec mappings."""
        from src.beacon_dl.constants import AUDIO_CODECS, VIDEO_CODECS

        assert VIDEO_CODECS["h264"] == "H.264"
        assert VIDEO_CODECS["hevc"] == "H.265"
        assert AUDIO_CODECS["aac"] == "AAC"
        assert AUDIO_CODECS["opus"] == "Opus"


# =============================================================================
# Cookie Loading Tests
# =============================================================================


class TestLoadCookies:
    """Tests for cookie loading utility."""

    def test_load_cookies_valid_file(self, tmp_path):
        """Test loading cookies from a valid Netscape cookie file."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text(
            "# Netscape HTTP Cookie File\n"
            ".beacon.tv\tTRUE\t/\tTRUE\t1735689600\tbeacon-session\tabc123\n"
            ".beacon.tv\tTRUE\t/\tFALSE\t0\tother_cookie\txyz789\n"
        )

        cookies = load_cookies(cookie_file)

        assert "beacon-session" in cookies
        assert cookies["beacon-session"] == "abc123"
        assert "other_cookie" in cookies
        assert cookies["other_cookie"] == "xyz789"

    def test_load_cookies_empty_file(self, tmp_path):
        """Test loading from an empty cookie file."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text("# Netscape HTTP Cookie File\n")

        cookies = load_cookies(cookie_file)
        assert cookies == {}

    def test_load_cookies_file_not_found(self, tmp_path):
        """Test loading from non-existent file returns empty dict."""
        cookie_file = tmp_path / "nonexistent.txt"

        cookies = load_cookies(cookie_file)
        assert cookies == {}

    def test_load_cookies_invalid_format(self, tmp_path):
        """Test loading from file with invalid format returns empty dict."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text("this is not a valid cookie file\nrandom content")

        cookies = load_cookies(cookie_file)
        assert cookies == {}

    def test_load_cookies_multiple_domains(self, tmp_path):
        """Test loading cookies from multiple domains."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text(
            "# Netscape HTTP Cookie File\n"
            ".beacon.tv\tTRUE\t/\tTRUE\t1735689600\tcookie1\tvalue1\n"
            ".members.beacon.tv\tTRUE\t/\tTRUE\t1735689600\tcookie2\tvalue2\n"
            ".example.com\tTRUE\t/\tFALSE\t0\tcookie3\tvalue3\n"
        )

        cookies = load_cookies(cookie_file)

        assert len(cookies) == 3
        assert cookies["cookie1"] == "value1"
        assert cookies["cookie2"] == "value2"
        assert cookies["cookie3"] == "value3"
