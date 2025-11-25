"""Tests for downloader module."""

from unittest.mock import patch

import pytest

from src.beacon_dl.content import (
    ContentMetadata,
    SubtitleTrack,
    VideoContent,
    VideoSource,
)
from src.beacon_dl.downloader import BeaconDownloader


@pytest.fixture
def mock_cookie_file(tmp_path):
    """Create a temporary cookie file for testing."""
    cookie_file = tmp_path / "test_cookies.txt"
    cookie_file.write_text(
        "# Netscape HTTP Cookie File\n"
        ".beacon.tv\tTRUE\t/\tTRUE\t9999999999\tbeacon-session\ttest_session_token\n"
    )
    return cookie_file


@pytest.fixture
def downloader(mock_cookie_file):
    """Create a BeaconDownloader instance."""
    return BeaconDownloader(mock_cookie_file)


@pytest.fixture
def sample_video_source():
    """Create a sample video source for testing."""
    return VideoSource(
        url="https://cdn.jwplayer.com/videos/test.mp4",
        label="1080p",
        width=1920,
        height=1080,
        bitrate=2420000,
        file_type="video/mp4",
    )


@pytest.fixture
def sample_metadata():
    """Create sample content metadata for testing."""
    return ContentMetadata(
        id="test-id",
        title="C4 E006 | Knives and Thorns",
        slug="c4-e006-knives-and-thorns",
        season_number=4,
        episode_number=6,
        duration=13949,
        description="Test episode description",
        collection_name="Campaign 4",
    )


@pytest.fixture
def sample_video_content(sample_metadata, sample_video_source):
    """Create sample video content for testing."""
    return VideoContent(
        metadata=sample_metadata,
        sources=[sample_video_source],
        subtitles=[
            SubtitleTrack(
                url="https://cdn.jwplayer.com/tracks/test-en.vtt",
                label="English",
                language="eng",
            ),
        ],
        hls_url=None,
    )


class TestFilenameGeneration:
    """Tests for filename generation logic."""

    def test_generate_filename_episodic_c4_format(
        self, downloader, sample_video_content, sample_video_source
    ):
        """Test filename generation for C4 E006 format."""
        filename = downloader._generate_filename(
            sample_video_content, sample_video_source
        )

        assert filename.startswith("Campaign.4.S04E06")
        assert "Knives.and.Thorns" in filename
        assert "1080p" in filename
        assert "H.264" in filename
        assert "AAC" in filename

    def test_generate_filename_episodic_s04e06_format(
        self, downloader, sample_video_source
    ):
        """Test filename generation for S04E06 - Title format."""
        metadata = ContentMetadata(
            id="test-id",
            title="S04E06 - Knives and Thorns",
            slug="s04e06-knives-and-thorns",
            season_number=4,
            episode_number=6,
            duration=13949,
            description="Test",
            collection_name="Critical Role",
        )
        content = VideoContent(
            metadata=metadata,
            sources=[sample_video_source],
            subtitles=[],
            hls_url=None,
        )

        # Modify source to 720p for this test
        source_720 = VideoSource(
            url="https://cdn.jwplayer.com/videos/test.mp4",
            label="720p",
            width=1280,
            height=720,
            bitrate=1420000,
            file_type="video/mp4",
        )

        filename = downloader._generate_filename(content, source_720)

        assert "S04E06" in filename
        assert "Knives.and.Thorns" in filename
        assert "720p" in filename

    def test_generate_filename_non_episodic(self, downloader, sample_video_source):
        """Test filename generation for non-episodic content."""
        metadata = ContentMetadata(
            id="test-id",
            title="Jester and Fjords Wedding",
            slug="jester-and-fjords-wedding",
            season_number=None,
            episode_number=None,
            duration=13949,
            description="Test",
            collection_name="Critical Role",
        )
        content = VideoContent(
            metadata=metadata,
            sources=[sample_video_source],
            subtitles=[],
            hls_url=None,
        )

        filename = downloader._generate_filename(content, sample_video_source)

        assert filename.startswith("Critical.Role.Jester")
        assert "Wedding" in filename
        assert "1080p" in filename

    def test_generate_filename_h265_codec(self, downloader, sample_video_content):
        """Test filename generation with H.265 codec detection."""
        source = VideoSource(
            url="https://cdn.jwplayer.com/videos/test-hevc.mp4",
            label="1080p",
            width=1920,
            height=1080,
            bitrate=2420000,
            file_type="video/mp4",
        )

        filename = downloader._generate_filename(sample_video_content, source)

        assert "H.265" in filename

    def test_generate_filename_default_collection_name(
        self, downloader, sample_video_source
    ):
        """Test filename generation when collection_name is None."""
        metadata = ContentMetadata(
            id="test-id",
            title="S01E01 - Test Episode",
            slug="test-episode",
            season_number=1,
            episode_number=1,
            duration=1000,
            description="Test",
            collection_name=None,
        )
        content = VideoContent(
            metadata=metadata,
            sources=[sample_video_source],
            subtitles=[],
            hls_url=None,
        )

        filename = downloader._generate_filename(content, sample_video_source)

        # Should use default "Critical Role" when collection_name is None
        assert filename.startswith("Critical.Role")


class TestEpisodeTitleExtraction:
    """Tests for episode title extraction from full titles."""

    def test_extract_episode_title_c4_format(self, downloader):
        """Test extracting title from C4 E006 | format."""
        title = downloader._extract_episode_title("C4 E006 | Knives and Thorns")
        assert title == "Knives and Thorns"

    def test_extract_episode_title_s04e06_dash(self, downloader):
        """Test extracting title from S04E06 - format."""
        title = downloader._extract_episode_title("S04E06 - Knives and Thorns")
        assert title == "Knives and Thorns"

    def test_extract_episode_title_s04e06_colon(self, downloader):
        """Test extracting title from S04E06: format."""
        title = downloader._extract_episode_title("S04E06: Knives and Thorns")
        assert title == "Knives and Thorns"

    def test_extract_episode_title_s04e06_space(self, downloader):
        """Test extracting title from S04E06 Title format (no separator)."""
        title = downloader._extract_episode_title("S04E06 Knives and Thorns")
        assert title == "Knives and Thorns"

    def test_extract_episode_title_4x06_format(self, downloader):
        """Test extracting title from 4x06 - format."""
        title = downloader._extract_episode_title("4x06 - Knives and Thorns")
        assert title == "Knives and Thorns"

    def test_extract_episode_title_fallback(self, downloader):
        """Test fallback when no pattern matches."""
        title = downloader._extract_episode_title("Just a Regular Title")
        assert title == "Just a Regular Title"


class TestSlugExtraction:
    """Tests for URL slug extraction."""

    def test_extract_slug_valid_url(self, downloader):
        """Test extracting slug from valid beacon.tv URL."""
        slug = downloader._extract_slug(
            "https://beacon.tv/content/c4-e006-knives-and-thorns"
        )
        assert slug == "c4-e006-knives-and-thorns"

    def test_extract_slug_with_query_params(self, downloader):
        """Test extracting slug from URL with query parameters."""
        # The regex matches up to the slug, query params should not affect it
        slug = downloader._extract_slug("https://beacon.tv/content/test-slug?foo=bar")
        assert slug == "test-slug"

    def test_extract_slug_invalid_url(self, downloader):
        """Test extracting slug from invalid URL returns None."""
        slug = downloader._extract_slug("https://youtube.com/watch?v=abc123")
        assert slug is None


class TestSourceSelection:
    """Tests for video source selection."""

    def test_select_source_exact_match(self, downloader):
        """Test selecting source with exact resolution match."""
        sources = [
            VideoSource("url1", "720p", 1280, 720, 1000000, "video/mp4"),
            VideoSource("url2", "1080p", 1920, 1080, 2000000, "video/mp4"),
            VideoSource("url3", "540p", 960, 540, 500000, "video/mp4"),
        ]

        # Default preferred resolution is 1080p
        selected = downloader._select_source(sources)

        assert selected.height == 1080
        assert selected.label == "1080p"

    def test_select_source_fallback_to_lower(self, downloader):
        """Test selecting source falls back to lower resolution."""
        sources = [
            VideoSource("url1", "720p", 1280, 720, 1000000, "video/mp4"),
            VideoSource("url2", "540p", 960, 540, 500000, "video/mp4"),
        ]

        # Preferred is 1080p, but not available - should get 720p
        selected = downloader._select_source(sources)

        assert selected.height == 720

    def test_select_source_empty_list(self, downloader):
        """Test selecting source from empty list returns None."""
        selected = downloader._select_source([])
        assert selected is None


class TestMergeFiles:
    """Tests for file merging logic."""

    @patch("subprocess.run")
    def test_merge_files_no_subtitles(self, mock_run, downloader, tmp_path):
        """Test merging video with no subtitles."""
        video_path = tmp_path / "video.mp4"
        video_path.touch()
        output_path = tmp_path / "output.mkv"

        downloader._merge_files(video_path, [], output_path)

        # Check ffmpeg was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]

        assert "ffmpeg" in args[0]
        assert "-i" in args
        assert str(output_path) in args

    @patch("subprocess.run")
    def test_merge_files_with_subtitles(self, mock_run, downloader, tmp_path):
        """Test merging video with subtitle files."""
        video_path = tmp_path / "video.mp4"
        video_path.touch()
        output_path = tmp_path / "output.mkv"

        # Create subtitle files info
        sub1 = tmp_path / "subs.eng.English.vtt"
        sub1.touch()
        sub2 = tmp_path / "subs.spa.Spanish.vtt"
        sub2.touch()

        subtitle_files = [
            (sub1, "eng", "English"),
            (sub2, "spa", "Spanish"),
        ]

        downloader._merge_files(video_path, subtitle_files, output_path)

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]

        # Should have multiple -i flags for subtitles
        input_count = args.count("-i")
        assert input_count == 3  # video + 2 subtitles


class TestDownloadFlow:
    """Tests for the download flow."""

    @patch.object(BeaconDownloader, "_download_file")
    @patch.object(BeaconDownloader, "_merge_files")
    @patch("src.beacon_dl.downloader.get_video_content")
    def test_download_slug_skips_existing_file(
        self,
        mock_get_content,
        mock_merge,
        mock_download,
        downloader,
        tmp_path,
        monkeypatch,
        sample_video_content,
    ):
        """Test that existing files are skipped."""
        mock_get_content.return_value = sample_video_content

        # Change to tmp_path directory
        monkeypatch.chdir(tmp_path)

        # Create a file that matches the expected output pattern
        expected_file = (
            tmp_path
            / "Campaign.4.S04E06.Knives.and.Thorns.1080p.WEB-DL.AAC2.0.H.264.mkv"
        )
        expected_file.touch()

        # Process slug - should skip
        downloader.download_slug("c4-e006-knives-and-thorns")

        # Should not call download or merge since file exists
        mock_download.assert_not_called()
        mock_merge.assert_not_called()

    @patch.object(BeaconDownloader, "_download_file")
    @patch.object(BeaconDownloader, "_merge_files")
    @patch("src.beacon_dl.downloader.get_video_content")
    def test_download_slug_downloads_new_file(
        self,
        mock_get_content,
        mock_merge,
        mock_download,
        downloader,
        tmp_path,
        monkeypatch,
        sample_video_content,
    ):
        """Test that new files are downloaded."""
        mock_get_content.return_value = sample_video_content

        # Change to tmp_path directory
        monkeypatch.chdir(tmp_path)

        # Make merge create the output file (needed for SHA256 calculation)
        def create_output_file(video_path, subtitle_files, output_path):
            output_path.write_bytes(b"test video content")

        mock_merge.side_effect = create_output_file

        # Process slug - should download
        downloader.download_slug("c4-e006-knives-and-thorns")

        # Should call download and merge
        assert mock_download.call_count >= 1  # At least video
        mock_merge.assert_called_once()
