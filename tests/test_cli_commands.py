"""Tests for CLI commands.

Tests all beacon-dl CLI commands with mocked dependencies.
"""

from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from src.beacon_dl.main import app

pytestmark = pytest.mark.integration  # CLI tests are integration tests

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
        # Create a file with old naming schema (without BCTV and release group)
        old_file = tmp_path / "Campaign.4.S04E06.Test.1080p.WEB-DL.AAC2.0.H.264.mkv"
        old_file.touch()

        result = runner.invoke(app, ["rename", str(tmp_path)])

        assert result.exit_code == 0
        assert "WOULD RENAME" in result.output
        assert "Critical.Role" in result.output
        assert "BCTV" in result.output
        assert "Pawsty" in result.output

    def test_rename_execute_renames_file(self, tmp_path):
        """Test rename actually renames file with --execute."""
        # Create a file with old naming schema
        old_file = tmp_path / "Campaign.4.S04E06.Test.1080p.WEB-DL.AAC2.0.H.264.mkv"
        old_file.touch()

        result = runner.invoke(app, ["rename", str(tmp_path), "--execute"])

        assert result.exit_code == 0
        assert "RENAMED" in result.output

        # Verify the file was renamed to new scene format
        new_file = (
            tmp_path / "Critical.Role.S04E06.Test.1080p.BCTV.WEB-DL.AAC2.0.H.264-Pawsty.mkv"
        )
        assert new_file.exists()
        assert not old_file.exists()

    def test_rename_skips_when_target_exists(self, tmp_path):
        """Test rename skips when target file already exists."""
        # Create old file and the target new file
        old_file = tmp_path / "Campaign.4.S04E06.Test.1080p.WEB-DL.AAC2.0.H.264.mkv"
        old_file.touch()
        new_file = (
            tmp_path / "Critical.Role.S04E06.Test.1080p.BCTV.WEB-DL.AAC2.0.H.264-Pawsty.mkv"
        )
        new_file.touch()

        result = runner.invoke(app, ["rename", str(tmp_path), "--execute"])

        assert result.exit_code == 0
        assert "SKIP" in result.output
        assert "Target already exists" in result.output


class TestSearchCommand:
    """Test search CLI command."""

    def test_search_help(self):
        """Test search command has help text."""
        result = runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        assert "search" in result.stdout.lower()


class TestHistoryCommand:
    """Test history CLI command."""

    def test_history_runs(self):
        """Test history command runs successfully."""
        with patch("src.beacon_dl.main.DownloadHistory") as mock_history:
            mock_history.return_value.get_all_downloads.return_value = []
            mock_history.return_value.count_downloads.return_value = 0

            result = runner.invoke(app, ["history"])

            assert result.exit_code == 0

    def test_history_json_format(self):
        """Test history with JSON output format."""
        with patch("src.beacon_dl.main.DownloadHistory") as mock_history:
            mock_history.return_value.get_all_downloads.return_value = []

            result = runner.invoke(app, ["history", "--format", "json"])

            assert result.exit_code == 0
            assert "[]" in result.stdout  # Empty JSON array

    def test_history_csv_format(self):
        """Test history with CSV output format."""
        with patch("src.beacon_dl.main.DownloadHistory") as mock_history:
            mock_history.return_value.get_all_downloads.return_value = []

            result = runner.invoke(app, ["history", "--format", "csv"])

            assert result.exit_code == 0
            assert "content_id" in result.stdout  # CSV header


class TestConfigCommand:
    """Test config CLI command."""

    def test_config_displays_settings(self):
        """Test config displays current settings."""
        result = runner.invoke(app, ["config"])

        assert result.exit_code == 0
        assert "1080p" in result.stdout  # Default resolution
        assert "mkv" in result.stdout  # Default container

    def test_config_shows_all_fields(self):
        """Test config shows all configuration fields."""
        result = runner.invoke(app, ["config"])

        assert result.exit_code == 0
        assert "Resolution" in result.stdout or "resolution" in result.stdout.lower()
        assert "Source" in result.stdout or "source" in result.stdout.lower()


class TestVerifyCommand:
    """Test verify CLI command."""

    def test_verify_runs(self):
        """Test verify command runs successfully."""
        with patch("src.beacon_dl.main.DownloadHistory") as mock_history:
            mock_history.return_value.get_all_downloads.return_value = []

            result = runner.invoke(app, ["verify"])

            assert result.exit_code == 0
            # Verify shows "Verifying X file(s)..." or similar
            assert "Verif" in result.stdout

    def test_verify_with_filter(self):
        """Test verify with status filter."""
        with patch("src.beacon_dl.main.DownloadHistory") as mock_history:
            mock_history.return_value.get_all_downloads.return_value = []

            result = runner.invoke(app, ["verify", "--status", "completed"])

            assert result.exit_code == 0


class TestClearHistoryCommand:
    """Test clear-history CLI command."""

    def test_clear_history_prompts_and_aborts(self):
        """Test clear-history asks for confirmation and aborts on no."""
        with patch("src.beacon_dl.main.DownloadHistory"):
            # Simulate user entering 'n' when prompted
            result = runner.invoke(app, ["clear-history"], input="n\n")

            assert result.exit_code == 0
            assert "Abort" in result.stdout or "cancel" in result.stdout.lower()

    def test_clear_history_force(self):
        """Test clear-history with --force flag runs without prompting."""
        with patch("src.beacon_dl.main.DownloadHistory"):
            result = runner.invoke(app, ["clear-history", "--force"])

            # Should run without prompting and succeed
            assert result.exit_code == 0
            # Should show cleared message
            assert "cleared" in result.stdout.lower() or "History" in result.stdout


class TestInfoCommand:
    """Test info CLI command."""

    @patch("src.beacon_dl.main.get_video_content")
    def test_info_displays_content(self, mock_get_content, mock_cookie_file):
        """Test info displays content information."""
        from src.beacon_dl.content import ContentMetadata, VideoContent, VideoSource

        mock_get_content.return_value = VideoContent(
            metadata=ContentMetadata(
                id="test-123",
                title="C4 E007 | On the Scent",
                slug="c4-e007-on-the-scent",
                season_number=4,
                episode_number=7,
                duration=16200000,
                description="Episode description",
                collection_name="Campaign 4",
            ),
            sources=[
                VideoSource(
                    url="https://cdn.example.com/video.mp4",
                    label="1080p",
                    width=1920,
                    height=1080,
                    bitrate=5000000,
                    file_type="video/mp4",
                )
            ],
            subtitles=[],
            hls_url=None,
        )

        result = runner.invoke(app, ["info", "c4-e007-on-the-scent"])

        assert result.exit_code == 0
        assert "On the Scent" in result.stdout
        assert "1080p" in result.stdout

    @patch("src.beacon_dl.main.get_video_content")
    def test_info_not_found(self, mock_get_content, mock_cookie_file):
        """Test info when content not found."""
        mock_get_content.return_value = None

        result = runner.invoke(app, ["info", "nonexistent-slug"])

        assert result.exit_code == 1

    def test_info_by_episode_number(self, mock_graphql_client, mock_cookie_file):
        """Test info with --series and --episode options."""
        mock_graphql_client.get_series_episodes.return_value = [
            {
                "slug": "c4-e007",
                "title": "Test Episode",
                "seasonNumber": 4,
                "episodeNumber": 7,
            },
        ]

        with patch("src.beacon_dl.main.get_video_content") as mock_get_content:
            from src.beacon_dl.content import ContentMetadata, VideoContent

            mock_get_content.return_value = VideoContent(
                metadata=ContentMetadata(
                    id="test",
                    title="Test",
                    slug="c4-e007",
                    season_number=4,
                    episode_number=7,
                    duration=1000,
                    description="",
                    collection_name="Campaign 4",
                ),
                sources=[],
                subtitles=[],
                hls_url=None,
            )

            result = runner.invoke(
                app, ["info", "--series", "campaign-4", "--episode", "7"]
            )

            assert result.exit_code == 0


class TestCommandHelp:
    """Test help for all commands."""

    @pytest.mark.parametrize(
        "command",
        [
            "download",
            "list-series",
            "list-episodes",
            "search",
            "check-new",
            "batch-download",
            "history",
            "config",
            "verify",
            "clear-history",
            "rename",
            "info",
        ],
    )
    def test_command_help(self, command):
        """Test each command has help text."""
        result = runner.invoke(app, [command, "--help"])

        assert result.exit_code == 0
        assert "Usage:" in result.stdout or "usage:" in result.stdout.lower()
