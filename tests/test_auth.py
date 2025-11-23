"""Tests for authentication module."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.beacon_dl.auth import validate_cookies, get_auth_args
from src.beacon_dl.config import Settings


class TestCookieValidation:
    """Tests for cookie validation functionality."""

    def test_validate_cookies_file_not_found(self, tmp_path):
        """Test validation fails when cookie file doesn't exist."""
        cookie_file = tmp_path / "nonexistent.txt"
        assert not validate_cookies(cookie_file)

    def test_validate_cookies_empty_file(self, tmp_path):
        """Test validation fails when cookie file is empty."""
        cookie_file = tmp_path / "empty.txt"
        cookie_file.write_text("# Netscape HTTP Cookie File\n# Comments only\n")
        assert not validate_cookies(cookie_file)

    def test_validate_cookies_no_beacon_tv_cookies(self, tmp_path):
        """Test validation fails when no beacon.tv cookies present."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text(
            "# Netscape HTTP Cookie File\n"
            "members.beacon.tv\tFALSE\t/\tTRUE\t9999999999\tsession\tabc123\n"
        )
        assert not validate_cookies(cookie_file)

    def test_validate_cookies_valid_beacon_tv_cookies(self, tmp_path):
        """Test validation passes with valid beacon.tv cookies."""
        cookie_file = tmp_path / "cookies.txt"
        # Create cookies with far future expiration
        cookie_file.write_text(
            "# Netscape HTTP Cookie File\n"
            "beacon.tv\tFALSE\t/\tTRUE\t9999999999\tauth_token\txyz789\n"
            "members.beacon.tv\tFALSE\t/\tTRUE\t9999999999\tsession\tabc123\n"
        )
        assert validate_cookies(cookie_file)

    def test_validate_cookies_with_domain_prefix(self, tmp_path):
        """Test validation passes with .beacon.tv domain cookies."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text(
            "# Netscape HTTP Cookie File\n"
            ".beacon.tv\tTRUE\t/\tTRUE\t9999999999\tauth_token\txyz789\n"
        )
        assert validate_cookies(cookie_file)

    def test_validate_cookies_expired(self, tmp_path):
        """Test validation handles expired cookies gracefully."""
        cookie_file = tmp_path / "cookies.txt"
        # Create cookies with past expiration (timestamp 0)
        cookie_file.write_text(
            "# Netscape HTTP Cookie File\n"
            ".beacon.tv\tTRUE\t/\tTRUE\t0\told_token\tabc\n"
            ".beacon.tv\tTRUE\t/\tTRUE\t9999999999\tvalid_token\txyz\n"
        )
        # Should pass because at least one valid cookie exists
        assert validate_cookies(cookie_file)


class TestAuthArgs:
    """Tests for get_auth_args functionality."""

    def test_playwright_auth_priority(self):
        """Test Playwright auth is prioritized when credentials provided."""
        with patch('src.beacon_dl.config.settings') as mock_settings:
            mock_settings.beacon_username = "user@example.com"
            mock_settings.beacon_password = "password123"
            mock_settings.browser_profile = None
            mock_settings.debug = False

            with patch('src.beacon_dl.auth.login_and_get_cookies') as mock_login:
                mock_login.return_value = Path("test_cookies.txt")

                args = get_auth_args()

                assert args == ["--cookies", "test_cookies.txt"]
                mock_login.assert_called_once()

    def test_browser_profile_fallback(self):
        """Test browser profile is used when no credentials provided."""
        with patch('src.beacon_dl.auth.settings') as mock_settings:
            mock_settings.beacon_username = None
            mock_settings.beacon_password = None
            mock_settings.browser_profile = "firefox:default"

            args = get_auth_args()

            assert args == ["--cookies-from-browser", "firefox:default"]

    def test_auto_detect_fallback(self):
        """Test auto-detection fallback when no auth configured."""
        with patch('src.beacon_dl.auth.settings') as mock_settings:
            mock_settings.beacon_username = None
            mock_settings.beacon_password = None
            mock_settings.browser_profile = None

            with patch('src.beacon_dl.auth.detect_browser_profile') as mock_detect:
                mock_detect.return_value = "chrome:Default"

                args = get_auth_args()

                assert args == ["--cookies-from-browser", "chrome:Default"]
                mock_detect.assert_called_once()

    def test_no_auth_available(self):
        """Test empty args returned when no auth method available."""
        with patch('src.beacon_dl.auth.settings') as mock_settings:
            mock_settings.beacon_username = None
            mock_settings.beacon_password = None
            mock_settings.browser_profile = None

            with patch('src.beacon_dl.auth.detect_browser_profile') as mock_detect:
                mock_detect.return_value = None

                args = get_auth_args()

                assert args == []


class TestSettings:
    """Tests for configuration settings."""

    def test_default_settings(self):
        """Test default configuration values."""
        settings = Settings()

        assert settings.release_group == "Pawsty"
        assert settings.preferred_resolution == "1080p"
        assert settings.source_type == "WEB-DL"
        assert settings.container_format == "mkv"
        assert settings.debug is False

    def test_custom_settings(self):
        """Test custom configuration values."""
        settings = Settings(
            release_group="CustomGroup",
            preferred_resolution="720p",
            debug=True
        )

        assert settings.release_group == "CustomGroup"
        assert settings.preferred_resolution == "720p"
        assert settings.debug is True
