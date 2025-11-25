"""Tests for CLI commands.

Tests all beacon-dl CLI commands with mocked dependencies.
"""

from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from src.beacon_dl.main import app

runner = CliRunner()


@pytest.fixture
def mock_graphql_client():
    """Mock GraphQL client for testing."""
    with patch("src.beacon_dl.main.BeaconGraphQL") as mock:
        client = Mock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_cookie_file(tmp_path):
    """Mock cookie file."""
    cookie_file = tmp_path / "test_cookies.txt"
    cookie_file.write_text("# Netscape HTTP Cookie File\n")

    with patch("src.beacon_dl.main.get_cookie_file") as mock:
        mock.return_value = cookie_file
        yield cookie_file


class TestListSeriesCommand:
    """Test list-series CLI command."""

    def test_list_series_displays_table(self, mock_graphql_client, mock_cookie_file):
        """Test that list-series displays formatted table."""
        mock_graphql_client.list_collections.return_value = [
            {"name": "Campaign 4", "slug": "campaign-4", "itemCount": 12},
            {"name": "Candela Obscura", "slug": "candela-obscura", "itemCount": 23},
        ]

        result = runner.invoke(app, ["list-series"])

        assert result.exit_code == 0
        assert "Campaign 4" in result.stdout
        assert "campaign-4" in result.stdout
        assert "12" in result.stdout
        assert "Candela Obscura" in result.stdout

    def test_list_series_handles_empty_list(
        self, mock_graphql_client, mock_cookie_file
    ):
        """Test list-series with no series available."""
        mock_graphql_client.list_collections.return_value = []

        result = runner.invoke(app, ["list-series"])

        assert result.exit_code == 0
        assert "No series found" in result.stdout

    def test_list_series_handles_missing_cookies(self):
        """Test list-series without authentication."""
        with patch("src.beacon_dl.main.get_cookie_file") as mock:
            mock.return_value = None

            result = runner.invoke(app, ["list-series"])

            assert result.exit_code == 1
            assert "No cookies found" in result.stdout


class TestListEpisodesCommand:
    """Test list-episodes CLI command."""

    def test_list_episodes_displays_table(self, mock_graphql_client, mock_cookie_file):
        """Test that list-episodes displays formatted table."""
        mock_graphql_client.get_collection_info.return_value = {
            "name": "Campaign 4",
            "itemCount": 7,
        }
        mock_graphql_client.get_series_episodes.return_value = [
            {
                "title": "C4 E001 | The Fall of Thjazi Fang",
                "seasonNumber": 4,
                "episodeNumber": 1,
                "releaseDate": "2025-10-03T00:00:00.000Z",
                "duration": 15138000,
            },
            {
                "title": "C4 E002 | Broken Wing",
                "seasonNumber": 4,
                "episodeNumber": 2,
                "releaseDate": "2025-10-10T00:00:00.000Z",
                "duration": 15459000,
            },
        ]

        result = runner.invoke(app, ["list-episodes", "campaign-4"])

        assert result.exit_code == 0
        assert "Campaign 4" in result.stdout
        assert "S04E01" in result.stdout
        assert "The Fall of Thjazi Fang" in result.stdout

    def test_list_episodes_handles_no_episodes(
        self, mock_graphql_client, mock_cookie_file
    ):
        """Test list-episodes with series that has no episodes."""
        mock_graphql_client.get_series_episodes.return_value = []
        mock_graphql_client.get_collection_info.return_value = (
            None  # No info for empty series
        )

        result = runner.invoke(app, ["list-episodes", "empty-series"])

        assert result.exit_code == 0
        assert "No episodes found" in result.stdout


class TestCheckNewCommand:
    """Test check-new CLI command."""

    def test_check_new_displays_latest_episode(
        self, mock_graphql_client, mock_cookie_file
    ):
        """Test that check-new displays latest episode info."""
        mock_graphql_client.get_latest_episode.return_value = {
            "title": "C4 E007 | On the Scent",
            "slug": "c4-e007-on-the-scent",
            "seasonNumber": 4,
            "episodeNumber": 7,
            "releaseDate": "2025-11-21T00:00:00.000Z",
        }

        result = runner.invoke(app, ["check-new", "--series", "campaign-4"])

        assert result.exit_code == 0
        assert "Latest episode found" in result.stdout
        assert "C4 E007 | On the Scent" in result.stdout
        assert "S04E07" in result.stdout

    def test_check_new_handles_no_episodes(self, mock_graphql_client, mock_cookie_file):
        """Test check-new when no episodes found."""
        mock_graphql_client.get_latest_episode.return_value = None

        result = runner.invoke(app, ["check-new"])

        assert result.exit_code == 0
        assert "No episodes found" in result.stdout


class TestBatchDownloadCommand:
    """Test batch-download CLI command."""

    @patch("src.beacon_dl.main.BeaconDownloader")
    def test_batch_download_all_episodes(
        self, mock_downloader, mock_graphql_client, mock_cookie_file
    ):
        """Test batch downloading all episodes."""
        mock_graphql_client.get_series_episodes.return_value = [
            {
                "slug": "ep1",
                "title": "Episode 1",
                "seasonNumber": 1,
                "episodeNumber": 1,
            },
            {
                "slug": "ep2",
                "title": "Episode 2",
                "seasonNumber": 1,
                "episodeNumber": 2,
            },
        ]

        result = runner.invoke(app, ["batch-download", "test-series"])

        assert result.exit_code == 0
        assert "Found 2 episodes" in result.stdout
        assert mock_downloader.return_value.download_url.call_count == 2

    @patch("src.beacon_dl.main.BeaconDownloader")
    def test_batch_download_with_range(
        self, mock_downloader, mock_graphql_client, mock_cookie_file
    ):
        """Test batch download with episode range."""
        mock_graphql_client.get_series_episodes.return_value = [
            {
                "slug": "ep1",
                "title": "Episode 1",
                "seasonNumber": 1,
                "episodeNumber": 1,
            },
            {
                "slug": "ep2",
                "title": "Episode 2",
                "seasonNumber": 1,
                "episodeNumber": 2,
            },
            {
                "slug": "ep3",
                "title": "Episode 3",
                "seasonNumber": 1,
                "episodeNumber": 3,
            },
        ]

        result = runner.invoke(
            app, ["batch-download", "test-series", "--start", "1", "--end", "2"]
        )

        assert result.exit_code == 0
        assert mock_downloader.return_value.download_url.call_count == 2


class TestDownloadCommand:
    """Test main download command."""

    @patch("src.beacon_dl.main.BeaconDownloader")
    def test_download_without_url_fetches_latest(
        self, mock_downloader, mock_graphql_client, mock_cookie_file
    ):
        """Test download without URL fetches latest episode."""
        mock_graphql_client.get_latest_episode.return_value = {
            "slug": "latest-episode",
            "title": "Latest Episode",
        }

        # Explicitly call "download" command with no URL argument
        result = runner.invoke(app, ["download"])

        assert result.exit_code == 0
        mock_graphql_client.get_latest_episode.assert_called_once()
        mock_downloader.return_value.download_url.assert_called_once()

    @patch("src.beacon_dl.main.BeaconDownloader")
    def test_download_with_url(self, mock_downloader, mock_cookie_file):
        """Test download with specific URL."""
        url = "https://beacon.tv/content/test-episode"

        # Explicitly call "download" command with URL argument
        result = runner.invoke(app, ["download", url])

        assert result.exit_code == 0
        mock_downloader.return_value.download_url.assert_called_once_with(url)

    @patch("src.beacon_dl.main.BeaconDownloader")
    def test_download_with_series_option(
        self, mock_downloader, mock_graphql_client, mock_cookie_file
    ):
        """Test download with series option."""
        mock_graphql_client.get_latest_episode.return_value = {
            "slug": "test-ep",
            "title": "Test Episode",
        }

        result = runner.invoke(app, ["download", "--series", "campaign-4"])

        assert result.exit_code == 0


class TestHelpCommand:
    """Test help and version commands."""

    def test_help_command(self):
        """Test --help flag."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Usage:" in result.stdout or "usage:" in result.stdout.lower()

    def test_download_help(self):
        """Test download command help."""
        result = runner.invoke(app, ["download", "--help"])

        assert result.exit_code == 0
        assert "download" in result.stdout.lower()


class TestListSeriesAdditional:
    """Additional list-series tests."""

    def test_list_series_with_no_auth(self):
        """Test list-series fails gracefully without auth."""
        with patch("src.beacon_dl.main.get_cookie_file") as mock:
            mock.return_value = None

            result = runner.invoke(app, ["list-series"])

            assert result.exit_code == 1


class TestRenameCommand:
    """Test rename command."""

    def test_rename_dry_run_no_files(self, tmp_path):
        """Test rename with no matching files."""
        result = runner.invoke(app, ["rename", str(tmp_path)])

        assert result.exit_code == 0
        assert "No files found" in result.output

    def test_rename_dry_run_with_files(self, tmp_path):
        """Test rename shows what would be renamed."""
        # Create a file with old naming schema (with release group)
        old_file = tmp_path / "Critical.Role.S04E06.Test.1080p.WEB-DL.AAC2.0.H.264-Pawsty.mkv"
        old_file.touch()

        result = runner.invoke(app, ["rename", str(tmp_path)])

        assert result.exit_code == 0
        assert "WOULD RENAME" in result.output
        assert "Pawsty" in result.output

    def test_rename_execute_renames_file(self, tmp_path):
        """Test rename actually renames file with --execute."""
        # Create a file with old naming schema
        old_file = tmp_path / "Critical.Role.S04E06.Test.1080p.WEB-DL.AAC2.0.H.264-Pawsty.mkv"
        old_file.touch()

        result = runner.invoke(app, ["rename", str(tmp_path), "--execute"])

        assert result.exit_code == 0
        assert "RENAMED" in result.output

        # Verify the file was renamed
        new_file = tmp_path / "Critical.Role.S04E06.Test.1080p.WEB-DL.AAC2.0.H.264.mkv"
        assert new_file.exists()
        assert not old_file.exists()

    def test_rename_skips_when_target_exists(self, tmp_path):
        """Test rename skips when target file already exists."""
        # Create both old and new files
        old_file = tmp_path / "Test.File-Group.mkv"
        old_file.touch()
        new_file = tmp_path / "Test.File.mkv"
        new_file.touch()

        result = runner.invoke(app, ["rename", str(tmp_path), "--execute"])

        assert result.exit_code == 0
        assert "SKIP" in result.output
        assert "Target already exists" in result.output
