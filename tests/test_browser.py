"""Tests for browser installation utilities."""

import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

from beacon_dl.browser import (
    ensure_chromium_installed,
    get_playwright_cache_dir,
    is_chromium_installed,
)

pytestmark = pytest.mark.unit  # All tests in this module are unit tests


class TestGetPlaywrightCacheDir:
    """Tests for get_playwright_cache_dir function."""

    def test_macos_cache_dir(self):
        """Test macOS cache directory path."""
        with patch.object(sys, "platform", "darwin"):
            result = get_playwright_cache_dir()
            assert "Library/Caches/ms-playwright" in str(result)

    def test_linux_cache_dir(self):
        """Test Linux cache directory path."""
        with patch.object(sys, "platform", "linux"):
            result = get_playwright_cache_dir()
            assert ".cache/ms-playwright" in str(result)

    def test_windows_cache_dir(self):
        """Test Windows cache directory path."""
        with patch.object(sys, "platform", "win32"):
            result = get_playwright_cache_dir()
            assert "AppData" in str(result) and "ms-playwright" in str(result)


class TestIsChromiumInstalled:
    """Tests for is_chromium_installed function."""

    def test_chromium_not_installed_empty_cache(self, tmp_path):
        """Test returns False when cache dir is empty."""
        with patch(
            "beacon_dl.browser.get_playwright_cache_dir"
        ) as mock_cache:
            mock_cache.return_value = tmp_path
            assert not is_chromium_installed()

    def test_chromium_not_installed_no_cache(self, tmp_path):
        """Test returns False when cache dir doesn't exist."""
        with patch(
            "beacon_dl.browser.get_playwright_cache_dir"
        ) as mock_cache:
            mock_cache.return_value = tmp_path / "nonexistent"
            assert not is_chromium_installed()

    def test_chromium_installed(self, tmp_path):
        """Test returns True when chromium directory exists."""
        # Create mock chromium directory
        (tmp_path / "chromium-1120").mkdir()

        with patch(
            "beacon_dl.browser.get_playwright_cache_dir"
        ) as mock_cache:
            mock_cache.return_value = tmp_path
            assert is_chromium_installed()

    def test_chromium_installed_multiple_versions(self, tmp_path):
        """Test returns True with multiple chromium versions."""
        (tmp_path / "chromium-1119").mkdir()
        (tmp_path / "chromium-1120").mkdir()

        with patch(
            "beacon_dl.browser.get_playwright_cache_dir"
        ) as mock_cache:
            mock_cache.return_value = tmp_path
            assert is_chromium_installed()


class TestEnsureChromiumInstalled:
    """Tests for ensure_chromium_installed function."""

    def test_already_installed_skips_install(self, tmp_path):
        """Test returns True immediately if chromium already installed."""
        (tmp_path / "chromium-1120").mkdir()

        with patch(
            "beacon_dl.browser.get_playwright_cache_dir"
        ) as mock_cache:
            mock_cache.return_value = tmp_path

            with patch("subprocess.run") as mock_run:
                result = ensure_chromium_installed()

                assert result is True
                mock_run.assert_not_called()  # Should not call install

    def test_installs_if_missing(self, tmp_path):
        """Test runs installation when chromium is missing."""
        with patch(
            "beacon_dl.browser.get_playwright_cache_dir"
        ) as mock_cache:
            mock_cache.return_value = tmp_path

            with patch("beacon_dl.browser.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stderr="")

                result = ensure_chromium_installed()

                assert result is True
                mock_run.assert_called_once()
                call_args = mock_run.call_args[0][0]
                assert "playwright" in str(call_args)
                assert "chromium" in str(call_args)

    def test_raises_on_install_failure(self, tmp_path):
        """Test raises RuntimeError when installation fails."""
        with patch(
            "beacon_dl.browser.get_playwright_cache_dir"
        ) as mock_cache:
            mock_cache.return_value = tmp_path

            with patch("beacon_dl.browser.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1, stderr="Installation failed: disk full"
                )

                with pytest.raises(RuntimeError, match="installation failed"):
                    ensure_chromium_installed()

    def test_raises_on_timeout(self, tmp_path):
        """Test raises RuntimeError when installation times out."""
        with patch(
            "beacon_dl.browser.get_playwright_cache_dir"
        ) as mock_cache:
            mock_cache.return_value = tmp_path

            with patch("beacon_dl.browser.subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired(cmd="", timeout=300)

                with pytest.raises(RuntimeError, match="timed out"):
                    ensure_chromium_installed()

    def test_raises_on_missing_playwright(self, tmp_path):
        """Test raises RuntimeError when playwright module not found."""
        with patch(
            "beacon_dl.browser.get_playwright_cache_dir"
        ) as mock_cache:
            mock_cache.return_value = tmp_path

            with patch("beacon_dl.browser.subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError()

                with pytest.raises(RuntimeError, match="not found"):
                    ensure_chromium_installed()
