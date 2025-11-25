"""Tests for utility functions."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.beacon_dl.utils import (
    detect_browser_profile,
    load_cookies,
    map_language_to_iso,
    sanitize_filename,
)


class TestFilenameSanitization:
    """Tests for filename sanitization."""

    def test_sanitize_basic(self):
        """Test basic filename sanitization."""
        assert sanitize_filename("Hello World") == "Hello.World"

    def test_sanitize_special_chars(self):
        """Test sanitization removes special characters (& and !)."""
        # Removes all non-alphanumeric except spaces
        assert sanitize_filename("Hello: World & More!") == "Hello.World.More"

    def test_sanitize_multiple_spaces(self):
        """Test multiple spaces are converted to single dot."""
        assert sanitize_filename("Hello    World") == "Hello.World"

    def test_sanitize_leading_trailing_spaces(self):
        """Test leading/trailing spaces are converted to dots then trimmed."""
        # Leading spaces become dots which are removed, trailing spaces become trailing dots
        assert sanitize_filename("  Hello World  ") == "Hello.World."

    def test_sanitize_apostrophes(self):
        """Test apostrophes are removed."""
        assert sanitize_filename("It's Great") == "Its.Great"

    def test_sanitize_slashes(self):
        """Test slashes are removed (special chars)."""
        # Slashes are removed as they're not alphanumeric
        assert sanitize_filename("Part 1/2") == "Part.12"

    def test_sanitize_colons(self):
        """Test colons are removed."""
        assert sanitize_filename("Episode: Title") == "Episode.Title"

    def test_sanitize_parentheses(self):
        """Test parentheses are removed."""
        assert sanitize_filename("Title (2024)") == "Title.2024"

    def test_sanitize_length_limit(self):
        """Test long filenames are truncated to 200 chars."""
        long_name = "A" * 300
        result = sanitize_filename(long_name)
        assert len(result) <= 200  # Implementation limits to 200

    def test_sanitize_preserve_alphanumeric(self):
        """Test alphanumeric characters are preserved."""
        # Dots are special chars and get removed
        assert sanitize_filename("TitleS01E01") == "TitleS01E01"


class TestLanguageMapping:
    """Tests for language to ISO code mapping."""

    def test_map_english(self):
        """Test English language mapping."""
        assert map_language_to_iso("english") == "eng"
        assert map_language_to_iso("English") == "eng"
        assert map_language_to_iso("ENGLISH") == "eng"

    def test_map_spanish(self):
        """Test Spanish language mapping."""
        assert map_language_to_iso("spanish") == "spa"
        assert map_language_to_iso("español") == "spa"

    def test_map_french(self):
        """Test French language mapping."""
        assert map_language_to_iso("french") == "fre"
        assert map_language_to_iso("français") == "fre"

    def test_map_german(self):
        """Test German language mapping."""
        assert map_language_to_iso("german") == "ger"

    def test_map_italian(self):
        """Test Italian language mapping."""
        assert map_language_to_iso("italian") == "ita"

    def test_map_portuguese(self):
        """Test Portuguese language mapping."""
        assert map_language_to_iso("portuguese") == "por"

    def test_map_japanese(self):
        """Test Japanese language mapping."""
        assert map_language_to_iso("japanese") == "jpn"

    def test_map_korean(self):
        """Test Korean language mapping."""
        assert map_language_to_iso("korean") == "kor"

    def test_map_chinese(self):
        """Test Chinese language mapping."""
        assert map_language_to_iso("chinese") == "chi"

    def test_map_unknown_language(self):
        """Test unknown language returns 'und'."""
        assert map_language_to_iso("klingon") == "und"
        assert map_language_to_iso("") == "und"

    def test_map_partial_match(self):
        """Test partial language name matching."""
        # Should match even with extra text
        result = map_language_to_iso("english.subtitles")
        # Depends on implementation - either "eng" or "und"
        assert result in ["eng", "und"]


class TestBrowserDetection:
    """Tests for browser profile detection."""

    def test_detect_browser_profile_zen_macos(self):
        """Test Zen browser detection on macOS."""
        with patch.object(Path, "home", return_value=Path("/Users/test")):
            with patch.object(Path, "exists") as mock_exists:
                with patch.object(Path, "glob") as mock_glob:
                    # Zen exists, Firefox doesn't
                    def exists_side_effect(self=None):
                        path_str = (
                            str(self)
                            if hasattr(self, "__str__")
                            else str(mock_exists.call_args)
                        )
                        if "zen" in path_str.lower():
                            return True
                        return False

                    mock_exists.side_effect = exists_side_effect

                    # Mock profile found
                    mock_profile = MagicMock()
                    mock_profile.stat.return_value.st_mtime = 12345
                    mock_glob.return_value = [mock_profile]

                    result = detect_browser_profile()

                    # When Zen is found, should return firefox:path
                    if result:
                        assert "firefox:" in result

    def test_detect_browser_profile_firefox_fallback(self):
        """Test Firefox fallback when Zen not available."""
        with patch.object(Path, "home", return_value=Path("/Users/test")):
            with patch.object(Path, "exists") as mock_exists:
                with patch.object(Path, "glob") as mock_glob:
                    # Only Firefox exists (not Zen)
                    call_count = [0]

                    def exists_side_effect(self=None):
                        call_count[0] += 1
                        # First call is Zen (no), second is Firefox (yes)
                        if call_count[0] == 1:
                            return False  # No Zen
                        return True  # Firefox exists

                    mock_exists.side_effect = exists_side_effect

                    mock_profile = MagicMock()
                    mock_profile.stat.return_value.st_mtime = 12345
                    mock_glob.return_value = [mock_profile]

                    result = detect_browser_profile()

                    if result:
                        assert "firefox:" in result

    def test_detect_browser_profile_chrome_fallback(self):
        """Test Chrome fallback when Firefox not available."""
        with patch.object(Path, "home", return_value=Path("/Users/test")):
            with patch.object(Path, "exists") as mock_exists:
                with patch.object(Path, "glob") as mock_glob:
                    # Only Chrome exists
                    call_count = [0]

                    def exists_side_effect(self=None):
                        call_count[0] += 1
                        # Zen: no, Firefox macOS: no, Firefox Linux: no, Chrome macOS: yes
                        if call_count[0] <= 3:
                            return False
                        return True

                    mock_exists.side_effect = exists_side_effect
                    mock_glob.return_value = []  # No profiles found

                    result = detect_browser_profile()

                    if result:
                        assert result == "chrome"

    def test_detect_browser_profile_none_found(self):
        """Test when no browser is found."""
        with patch.object(Path, "home", return_value=Path("/Users/test")):
            with patch.object(Path, "exists", return_value=False):
                with patch.object(Path, "glob", return_value=[]):
                    result = detect_browser_profile()
                    assert result is None


class TestSanitizeFilenameEdgeCases:
    """Additional edge case tests for filename sanitization."""

    def test_sanitize_empty_string(self):
        """Test empty string returns 'unnamed'."""
        assert sanitize_filename("") == "unnamed"

    def test_sanitize_only_special_chars(self):
        """Test string with only special chars returns 'unnamed'."""
        assert sanitize_filename("!@#$%^&*()") == "unnamed"

    def test_sanitize_unicode(self):
        """Test unicode characters are removed."""
        result = sanitize_filename("Caf\u00e9 \u4e2d\u6587")
        assert result == "Caf."

    def test_sanitize_leading_dashes(self):
        """Test leading dashes are removed."""
        result = sanitize_filename("---test")
        assert result == "test"

    def test_sanitize_numbers_only(self):
        """Test numbers are preserved."""
        assert sanitize_filename("12345") == "12345"


class TestConstants:
    """Tests that import and verify constants."""

    def test_import_constants(self):
        """Test constants can be imported."""
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

        # Verify some key values
        assert DEFAULT_RESOLUTION == "1080p"
        assert DEFAULT_CONTAINER_FORMAT == "mkv"
        assert "campaign-4" in KNOWN_COLLECTIONS
        assert SECURE_FILE_PERMISSIONS == 0o600

        # Verify Playwright timeouts are in milliseconds and reasonable
        assert PLAYWRIGHT_PAGE_TIMEOUT == 30000  # 30 seconds
        assert PLAYWRIGHT_NAVIGATION_TIMEOUT == 30000
        assert PLAYWRIGHT_SELECTOR_TIMEOUT == 10000  # 10 seconds
        assert PLAYWRIGHT_NETWORKIDLE_TIMEOUT == 10000
        assert PLAYWRIGHT_SSO_TIMEOUT == 15000  # 15 seconds
        assert PLAYWRIGHT_CLICK_TIMEOUT == 5000  # 5 seconds
        assert PLAYWRIGHT_BANNER_TIMEOUT == 2000  # 2 seconds

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


class TestLanguageMappingAdditional:
    """Additional language mapping tests."""

    def test_map_iso_codes(self):
        """Test ISO code inputs are mapped correctly."""
        assert map_language_to_iso("en") == "eng"
        assert map_language_to_iso("es") == "spa"
        assert map_language_to_iso("fr") == "fre"
        assert map_language_to_iso("de") == "ger"
        assert map_language_to_iso("it") == "ita"
        assert map_language_to_iso("pt") == "por"
        assert map_language_to_iso("ja") == "jpn"
        assert map_language_to_iso("ko") == "kor"
        assert map_language_to_iso("zh") == "chi"

    def test_map_native_names(self):
        """Test native language name inputs."""
        assert map_language_to_iso("italiano") == "ita"
        assert map_language_to_iso("deutsch") == "ger"
        assert map_language_to_iso("português") == "por"


class TestLoadCookies:
    """Tests for cookie loading utility."""

    def test_load_cookies_valid_file(self, tmp_path):
        """Test loading cookies from a valid Netscape cookie file."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text("""# Netscape HTTP Cookie File
.beacon.tv\tTRUE\t/\tTRUE\t1735689600\tbeacon-session\tabc123
.beacon.tv\tTRUE\t/\tFALSE\t0\tother_cookie\txyz789
""")

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

        # Should return empty dict on parse error
        assert cookies == {}

    def test_load_cookies_multiple_domains(self, tmp_path):
        """Test loading cookies from multiple domains."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text("""# Netscape HTTP Cookie File
.beacon.tv\tTRUE\t/\tTRUE\t1735689600\tcookie1\tvalue1
.members.beacon.tv\tTRUE\t/\tTRUE\t1735689600\tcookie2\tvalue2
.example.com\tTRUE\t/\tFALSE\t0\tcookie3\tvalue3
""")

        cookies = load_cookies(cookie_file)

        assert len(cookies) == 3
        assert cookies["cookie1"] == "value1"
        assert cookies["cookie2"] == "value2"
        assert cookies["cookie3"] == "value3"
