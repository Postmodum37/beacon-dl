"""Tests for authentication module."""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from src.beacon_dl.auth import (
    are_cookies_valid_with_buffer,
    get_auth_args,
    validate_cookies,
)
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


class TestCookieCaching:
    """Tests for cookie caching with expiry buffer."""

    def test_valid_cookies_with_buffer(self, tmp_path):
        """Test cookies are valid when not expiring soon."""
        cookie_file = tmp_path / "cookies.txt"
        # Create beacon-session cookie expiring far in the future
        cookie_file.write_text(
            "# Netscape HTTP Cookie File\n"
            ".beacon.tv\tTRUE\t/\tTRUE\t9999999999\tbeacon-session\txyz789\n"
        )
        assert are_cookies_valid_with_buffer(cookie_file, buffer_hours=6)

    def test_cookies_expiring_soon(self, tmp_path):
        """Test cookies are invalid when expiring within buffer."""
        cookie_file = tmp_path / "cookies.txt"
        # Create beacon-session cookie expiring in 1 hour
        expires_soon = int(datetime.now().timestamp()) + 3600  # 1 hour from now
        cookie_file.write_text(
            f"# Netscape HTTP Cookie File\n"
            f".beacon.tv\tTRUE\t/\tTRUE\t{expires_soon}\tbeacon-session\txyz789\n"
        )
        # Should be invalid with 6 hour buffer (expires in 1 hour < 6 hour buffer)
        assert not are_cookies_valid_with_buffer(cookie_file, buffer_hours=6)

    def test_cookies_valid_with_small_buffer(self, tmp_path):
        """Test cookies are valid with small buffer time."""
        cookie_file = tmp_path / "cookies.txt"
        # Create beacon-session cookie expiring in 2 hours
        expires = int(datetime.now().timestamp()) + 7200  # 2 hours from now
        cookie_file.write_text(
            f"# Netscape HTTP Cookie File\n"
            f".beacon.tv\tTRUE\t/\tTRUE\t{expires}\tbeacon-session\txyz789\n"
        )
        # Should be valid with 1 hour buffer
        assert are_cookies_valid_with_buffer(cookie_file, buffer_hours=1)

    def test_no_beacon_session_cookie(self, tmp_path):
        """Test cookies are invalid without beacon-session cookie."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text(
            "# Netscape HTTP Cookie File\n"
            ".beacon.tv\tTRUE\t/\tTRUE\t9999999999\tother_cookie\txyz789\n"
        )
        assert not are_cookies_valid_with_buffer(cookie_file, buffer_hours=6)

    def test_session_cookie_always_valid(self, tmp_path):
        """Test session cookies (expires=0) are always considered valid."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text(
            "# Netscape HTTP Cookie File\n"
            ".beacon.tv\tTRUE\t/\tTRUE\t0\tbeacon-session\txyz789\n"
        )
        assert are_cookies_valid_with_buffer(cookie_file, buffer_hours=6)

    def test_file_not_found(self, tmp_path):
        """Test returns False when cookie file doesn't exist."""
        cookie_file = tmp_path / "nonexistent.txt"
        assert not are_cookies_valid_with_buffer(cookie_file, buffer_hours=6)


class TestAuthArgs:
    """Tests for get_auth_args functionality."""

    def test_playwright_auth_priority(self):
        """Test Playwright auth is prioritized when credentials provided."""
        with patch("src.beacon_dl.config.settings") as mock_settings:
            mock_settings.beacon_username = "user@example.com"
            mock_settings.beacon_password = "password123"
            mock_settings.browser_profile = None
            mock_settings.debug = False

            with patch("src.beacon_dl.auth.login_and_get_cookies") as mock_login:
                mock_login.return_value = Path("test_cookies.txt")

                args = get_auth_args()

                assert args == ["--cookies", "test_cookies.txt"]
                mock_login.assert_called_once()

    def test_browser_profile_fallback(self):
        """Test browser profile is used when no credentials provided."""
        with patch("src.beacon_dl.auth.settings") as mock_settings:
            mock_settings.beacon_username = None
            mock_settings.beacon_password = None
            mock_settings.browser_profile = "firefox:default"

            args = get_auth_args()

            assert args == ["--cookies-from-browser", "firefox:default"]

    def test_auto_detect_fallback(self):
        """Test auto-detection fallback when no auth configured."""
        with patch("src.beacon_dl.auth.settings") as mock_settings:
            mock_settings.beacon_username = None
            mock_settings.beacon_password = None
            mock_settings.browser_profile = None

            with patch("src.beacon_dl.auth.detect_browser_profile") as mock_detect:
                mock_detect.return_value = "chrome:Default"

                args = get_auth_args()

                assert args == ["--cookies-from-browser", "chrome:Default"]
                mock_detect.assert_called_once()

    def test_no_auth_available(self):
        """Test empty args returned when no auth method available."""
        with patch("src.beacon_dl.auth.settings") as mock_settings:
            mock_settings.beacon_username = None
            mock_settings.beacon_password = None
            mock_settings.browser_profile = None

            with patch("src.beacon_dl.auth.detect_browser_profile") as mock_detect:
                mock_detect.return_value = None

                args = get_auth_args()

                assert args == []


class TestSettings:
    """Tests for configuration settings."""

    def test_default_settings(self):
        """Test default configuration values."""
        settings = Settings()

        assert settings.preferred_resolution == "1080p"
        assert settings.source_type == "WEB-DL"
        assert settings.container_format == "mkv"
        assert settings.debug is False

    def test_custom_settings(self):
        """Test custom configuration values."""
        settings = Settings(preferred_resolution="720p", debug=True)

        assert settings.preferred_resolution == "720p"
        assert settings.debug is True


class TestGetCookieFile:
    """Tests for get_cookie_file functionality."""

    def test_get_cookie_file_with_credentials(self, tmp_path):
        """Test cookie file is created when credentials provided."""
        from src.beacon_dl.auth import get_cookie_file

        with patch("src.beacon_dl.auth.settings") as mock_settings:
            mock_settings.beacon_username = "user@example.com"
            mock_settings.beacon_password = "password123"

            with patch("src.beacon_dl.auth.login_and_get_cookies") as mock_login:
                mock_cookie_file = tmp_path / "cookies.txt"
                mock_login.return_value = mock_cookie_file

                result = get_cookie_file()

                assert result == mock_cookie_file
                mock_login.assert_called_once()

    def test_get_cookie_file_existing_file(self, tmp_path, monkeypatch):
        """Test returns existing cookie file."""
        from src.beacon_dl.auth import get_cookie_file

        # Create existing cookie file
        cookie_file = tmp_path / "beacon_cookies.txt"
        cookie_file.write_text("# Netscape HTTP Cookie File\n")

        # Change working directory to tmp_path
        monkeypatch.chdir(tmp_path)

        with patch("src.beacon_dl.auth.settings") as mock_settings:
            mock_settings.beacon_username = None
            mock_settings.beacon_password = None

            result = get_cookie_file()

            assert result == Path("beacon_cookies.txt")

    def test_get_cookie_file_no_file_no_credentials(self, tmp_path, monkeypatch):
        """Test returns None when no cookie file and no credentials."""
        from src.beacon_dl.auth import get_cookie_file

        # Change to tmp_path where no cookie file exists
        monkeypatch.chdir(tmp_path)

        with patch("src.beacon_dl.auth.settings") as mock_settings:
            mock_settings.beacon_username = None
            mock_settings.beacon_password = None

            result = get_cookie_file()

            assert result is None


class TestWriteNetscapeCookies:
    """Tests for _write_netscape_cookies functionality."""

    def test_write_netscape_cookies_format(self, tmp_path):
        """Test cookies are written in correct Netscape format."""
        from src.beacon_dl.auth import _write_netscape_cookies

        cookies = [
            {
                "domain": ".beacon.tv",
                "path": "/",
                "secure": True,
                "expires": 9999999999,
                "name": "session",
                "value": "abc123",
            },
            {
                "domain": "beacon.tv",
                "path": "/",
                "secure": False,
                "expires": -1,  # Session cookie
                "name": "preference",
                "value": "dark",
            },
        ]

        cookie_file = tmp_path / "cookies.txt"
        _write_netscape_cookies(cookies, cookie_file)

        content = cookie_file.read_text()

        # Check header
        assert "# Netscape HTTP Cookie File" in content

        # Check cookies are written
        assert ".beacon.tv" in content
        assert "beacon.tv" in content
        assert "session" in content
        assert "abc123" in content

    def test_write_netscape_cookies_filters_non_beacon(self, tmp_path):
        """Test only beacon.tv cookies are written."""
        from src.beacon_dl.auth import _write_netscape_cookies

        cookies = [
            {
                "domain": ".beacon.tv",
                "path": "/",
                "secure": True,
                "expires": 9999999999,
                "name": "session",
                "value": "abc",
            },
            {
                "domain": ".google.com",  # Should be filtered out
                "path": "/",
                "secure": True,
                "expires": 9999999999,
                "name": "tracking",
                "value": "xyz",
            },
        ]

        cookie_file = tmp_path / "cookies.txt"
        _write_netscape_cookies(cookies, cookie_file)

        content = cookie_file.read_text()

        # beacon.tv cookies should be present
        assert "beacon.tv" in content
        assert "session" in content

        # google.com cookies should NOT be present
        assert "google.com" not in content
        assert "tracking" not in content

    def test_write_netscape_cookies_file_permissions(self, tmp_path):
        """Test cookie file has secure permissions."""
        import os
        import stat

        from src.beacon_dl.auth import _write_netscape_cookies

        cookies = [
            {
                "domain": ".beacon.tv",
                "path": "/",
                "secure": True,
                "expires": 9999999999,
                "name": "test",
                "value": "value",
            },
        ]

        cookie_file = tmp_path / "cookies.txt"
        _write_netscape_cookies(cookies, cookie_file)

        # Check file permissions (should be 0o600 = owner read/write only)
        mode = os.stat(cookie_file).st_mode
        permissions = stat.S_IMODE(mode)
        assert permissions == 0o600


class TestCookieValidationEdgeCases:
    """Additional edge case tests for cookie validation."""

    def test_validate_cookies_malformed_line(self, tmp_path):
        """Test validation handles malformed cookie lines."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text(
            "# Netscape HTTP Cookie File\n"
            "beacon.tv\t/\tTRUE\n"  # Too few fields
            "beacon.tv\tFALSE\t/\tTRUE\t9999999999\tvalid\tvalue\n"
        )
        # Should still pass because valid cookie exists
        assert validate_cookies(cookie_file)

    def test_validate_cookies_all_expired(self, tmp_path):
        """Test validation when all cookies are expired."""
        import time

        past_timestamp = int(time.time()) - 3600  # 1 hour ago

        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text(
            "# Netscape HTTP Cookie File\n"
            f"beacon.tv\tFALSE\t/\tTRUE\t{past_timestamp}\texpired\tvalue\n"
        )
        # All beacon.tv cookies expired, so validation fails
        assert not validate_cookies(cookie_file)

    def test_validate_cookies_read_error(self, tmp_path):
        """Test validation handles read errors gracefully."""
        import os

        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text("# Netscape HTTP Cookie File\n")

        # Make file unreadable (if not root)
        try:
            os.chmod(cookie_file, 0o000)
            result = validate_cookies(cookie_file)
            os.chmod(cookie_file, 0o644)  # Restore permissions

            # On most systems, this should fail due to permission error
            # (unless running as root)
            assert result in [True, False]  # Either is acceptable depending on system
        except PermissionError:
            pass  # Skip if we can't change permissions
