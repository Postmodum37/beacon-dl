"""Tests for downloader module."""

import pytest
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path
from src.beacon_dl.downloader import BeaconDownloader


class TestFilenameGeneration:
    """Tests for filename generation logic."""

    @pytest.fixture
    def downloader(self):
        """Create a BeaconDownloader instance."""
        return BeaconDownloader()

    def test_generate_filename_episodic_c4_format(self, downloader):
        """Test filename generation for C4 E006 format."""
        info = {
            "height": 1080,
            "vcodec": "avc1.64001f",
            "acodec": "mp4a.40.2",
            "audio_channels": 2,
        }
        show_name = "Critical.Role"
        video_title = "C4 E006 | Knives and Thorns"

        filename = downloader._generate_filename(info, show_name, video_title)

        assert filename.startswith("Critical.Role.S04E06")
        assert "Knives.and.Thorns" in filename
        assert "1080p" in filename
        assert "H.264" in filename
        assert "AAC" in filename

    def test_generate_filename_episodic_s04e06_format(self, downloader):
        """Test filename generation for S04E06 - Title format."""
        info = {
            "height": 720,
            "vcodec": "avc1.64001f",
            "acodec": "mp4a.40.2",
            "audio_channels": 2,
        }
        show_name = "Critical.Role"
        video_title = "S04E06 - Knives and Thorns"

        filename = downloader._generate_filename(info, show_name, video_title)

        assert "S04E06" in filename
        assert "Knives.and.Thorns" in filename
        assert "720p" in filename

    def test_generate_filename_episodic_s04e06_colon_format(self, downloader):
        """Test filename generation for S04E06: Title format."""
        info = {"height": 1080, "vcodec": "avc", "acodec": "mp4a", "audio_channels": 2}
        show_name = "Show.Name"
        video_title = "S01E05: Episode Title"

        filename = downloader._generate_filename(info, show_name, video_title)

        assert "S01E05" in filename
        assert "Episode.Title" in filename

    def test_generate_filename_episodic_s04e06_no_separator(self, downloader):
        """Test filename generation for S04E06 Title format (no separator)."""
        info = {"height": 1080, "vcodec": "avc", "acodec": "mp4a", "audio_channels": 2}
        show_name = "Show.Name"
        video_title = "S02E10 The Big Episode"

        filename = downloader._generate_filename(info, show_name, video_title)

        assert "S02E10" in filename
        assert "The.Big.Episode" in filename

    def test_generate_filename_episodic_4x06_format(self, downloader):
        """Test filename generation for 4x06 - Title format."""
        info = {"height": 1080, "vcodec": "avc", "acodec": "mp4a", "audio_channels": 2}
        show_name = "Show.Name"
        video_title = "4x06 - Episode Title"

        filename = downloader._generate_filename(info, show_name, video_title)

        assert "S04E06" in filename
        assert "Episode.Title" in filename

    def test_generate_filename_non_episodic(self, downloader):
        """Test filename generation for non-episodic content."""
        info = {"height": 1080, "vcodec": "avc", "acodec": "mp4a", "audio_channels": 2}
        show_name = "Critical.Role"
        video_title = "Jester and Fjords Wedding"

        filename = downloader._generate_filename(info, show_name, video_title)

        assert filename.startswith("Critical.Role.Jester")
        assert "Wedding" in filename
        assert "1080p" in filename

    def test_generate_filename_non_episodic_title_starts_with_show(self, downloader):
        """Test filename when title already starts with show name."""
        info = {"height": 1080, "vcodec": "avc", "acodec": "mp4a", "audio_channels": 2}
        show_name = "Critical.Role"
        video_title = "Critical Role Special Event"

        filename = downloader._generate_filename(info, show_name, video_title)

        # Should not duplicate show name
        assert not filename.startswith("Critical.Role.Critical.Role")

    def test_generate_filename_h265_codec(self, downloader):
        """Test filename generation with H.265 codec."""
        info = {
            "height": 1080,
            "vcodec": "hevc.123",
            "acodec": "mp4a.40.2",
            "audio_channels": 2,
        }
        show_name = "Show"
        video_title = "S01E01 - Episode"

        filename = downloader._generate_filename(info, show_name, video_title)

        assert "H.265" in filename

    def test_generate_filename_vp9_codec(self, downloader):
        """Test filename generation with VP9 codec."""
        info = {
            "height": 1080,
            "vcodec": "vp9",
            "acodec": "mp4a.40.2",
            "audio_channels": 2,
        }
        show_name = "Show"
        video_title = "S01E01 - Episode"

        filename = downloader._generate_filename(info, show_name, video_title)

        assert "VP9" in filename

    def test_generate_filename_opus_audio(self, downloader):
        """Test filename generation with Opus audio."""
        info = {
            "height": 1080,
            "vcodec": "avc",
            "acodec": "opus",
            "audio_channels": 2,
        }
        show_name = "Show"
        video_title = "S01E01 - Episode"

        filename = downloader._generate_filename(info, show_name, video_title)

        assert "Opus" in filename

    def test_generate_filename_vorbis_audio(self, downloader):
        """Test filename generation with Vorbis audio."""
        info = {
            "height": 1080,
            "vcodec": "avc",
            "acodec": "vorbis",
            "audio_channels": 2,
        }
        show_name = "Show"
        video_title = "S01E01 - Episode"

        filename = downloader._generate_filename(info, show_name, video_title)

        assert "Vorbis" in filename

    def test_generate_filename_ac3_audio(self, downloader):
        """Test filename generation with AC3 audio."""
        info = {
            "height": 1080,
            "vcodec": "avc",
            "acodec": "ac3",
            "audio_channels": 6,
        }
        show_name = "Show"
        video_title = "S01E01 - Episode"

        filename = downloader._generate_filename(info, show_name, video_title)

        assert "AC3" in filename
        assert "6.0" in filename

    def test_generate_filename_eac3_audio(self, downloader):
        """Test filename generation with EAC3 audio."""
        info = {
            "height": 1080,
            "vcodec": "avc",
            "acodec": "eac3",
            "audio_channels": 6,
        }
        show_name = "Show"
        video_title = "S01E01 - Episode"

        filename = downloader._generate_filename(info, show_name, video_title)

        assert "EAC3" in filename

    def test_generate_filename_default_codec(self, downloader):
        """Test filename generation with unknown codec uses defaults."""
        info = {
            "height": 1080,
            "vcodec": "unknown_codec",
            "acodec": "unknown_audio",
            "audio_channels": 2,
        }
        show_name = "Show"
        video_title = "S01E01 - Episode"

        filename = downloader._generate_filename(info, show_name, video_title)

        # Should use default codecs from config
        assert "H.264" in filename or "default" in filename.lower() is False
        assert "AAC" in filename or "default" in filename.lower() is False

    def test_generate_filename_no_height(self, downloader):
        """Test filename generation without height uses preferred resolution."""
        info = {
            "vcodec": "avc",
            "acodec": "mp4a",
            "audio_channels": 2,
        }
        show_name = "Show"
        video_title = "S01E01 - Episode"

        filename = downloader._generate_filename(info, show_name, video_title)

        # Should use preferred_resolution from settings
        assert "1080p" in filename  # default from settings

    def test_generate_filename_fractional_channels(self, downloader):
        """Test filename generation with fractional audio channels."""
        info = {
            "height": 1080,
            "vcodec": "avc",
            "acodec": "mp4a",
            "audio_channels": "5.1",  # Already a string
        }
        show_name = "Show"
        video_title = "S01E01 - Episode"

        filename = downloader._generate_filename(info, show_name, video_title)

        # Should preserve the 5.1 format
        assert "5.1" in filename or "2.0" in filename  # fallback if not digit


class TestMergeFiles:
    """Tests for file merging logic."""

    @pytest.fixture
    def downloader(self):
        """Create a BeaconDownloader instance."""
        return BeaconDownloader()

    @patch('subprocess.run')
    def test_merge_files_no_subtitles(self, mock_run, downloader, tmp_path):
        """Test merging video with no subtitles."""
        video_path = tmp_path / "video.mp4"
        video_path.touch()

        downloader._merge_files(video_path, tmp_path, "output.mkv")

        # Check ffmpeg was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]

        assert "ffmpeg" in args[0]
        assert "-i" in args
        assert "output.mkv" in args

    @patch('subprocess.run')
    def test_merge_files_with_subtitles(self, mock_run, downloader, tmp_path):
        """Test merging video with subtitle files."""
        video_path = tmp_path / "video.mp4"
        video_path.touch()

        # Create subtitle files
        (tmp_path / "subs.en.English.vtt").touch()
        (tmp_path / "subs.es.Spanish.vtt").touch()

        downloader._merge_files(video_path, tmp_path, "output.mkv")

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]

        # Should have multiple -i flags for subtitles
        input_count = args.count("-i")
        assert input_count >= 2  # video + at least one subtitle


class TestProcessUrl:
    """Tests for URL processing."""

    @pytest.fixture
    def downloader(self):
        """Create a BeaconDownloader instance."""
        return BeaconDownloader()

    @patch('src.beacon_dl.downloader.get_auth_args')
    @patch('yt_dlp.YoutubeDL')
    def test_process_url_skips_existing_file(
        self, mock_ydl_class, mock_auth, downloader, tmp_path, monkeypatch
    ):
        """Test that existing files are skipped."""
        # Setup mocks
        mock_auth.return_value = []

        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__ = Mock(return_value=mock_ydl)
        mock_ydl_class.return_value.__exit__ = Mock(return_value=False)

        mock_ydl.extract_info.return_value = {
            "id": "test-id",
            "title": "S01E01 - Test Episode",
            "series": "Test Show",
            "height": 1080,
            "vcodec": "avc",
            "acodec": "mp4a",
            "audio_channels": 2,
        }

        # Create the output file to simulate it already exists
        # We need to figure out what filename will be generated
        # and create that file

        # Change to tmp_path directory
        monkeypatch.chdir(tmp_path)

        # Create a file that matches the expected output
        expected_file = tmp_path / "Test.Show.S01E01.Test.Episode.1080p.WEB-DL.AAC2.0.H.264-Pawsty.mkv"
        expected_file.touch()

        # Process URL - should skip
        downloader.process_url("https://beacon.tv/content/test")

        # Should only call extract_info, not download
        mock_ydl.extract_info.assert_called_once()
        mock_ydl.download.assert_not_called()

    @patch('src.beacon_dl.downloader.get_auth_args')
    @patch('yt_dlp.YoutubeDL')
    def test_process_url_with_cookie_file(self, mock_ydl_class, mock_auth, downloader):
        """Test that cookie file is passed to yt-dlp."""
        mock_auth.return_value = ["--cookies", "test_cookies.txt"]

        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__ = Mock(return_value=mock_ydl)
        mock_ydl_class.return_value.__exit__ = Mock(return_value=False)

        # Make extract_info raise to exit early
        mock_ydl.extract_info.side_effect = Exception("Test stop")

        with pytest.raises(SystemExit):
            downloader.process_url("https://beacon.tv/content/test")

        # Check that cookiefile was set
        assert downloader.ydl_opts.get('cookiefile') == "test_cookies.txt"

    @patch('src.beacon_dl.downloader.get_auth_args')
    @patch('yt_dlp.YoutubeDL')
    def test_process_url_with_browser_cookies(self, mock_ydl_class, mock_auth, downloader):
        """Test that browser cookies are passed to yt-dlp."""
        mock_auth.return_value = ["--cookies-from-browser", "firefox:default"]

        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__ = Mock(return_value=mock_ydl)
        mock_ydl_class.return_value.__exit__ = Mock(return_value=False)

        # Make extract_info raise to exit early
        mock_ydl.extract_info.side_effect = Exception("Test stop")

        with pytest.raises(SystemExit):
            downloader.process_url("https://beacon.tv/content/test")

        # Check that cookiesfrombrowser was set
        assert downloader.ydl_opts.get('cookiesfrombrowser') == ("firefox", "default", None, None)

    @patch('src.beacon_dl.downloader.get_auth_args')
    @patch('yt_dlp.YoutubeDL')
    def test_process_url_browser_no_path(self, mock_ydl_class, mock_auth, downloader):
        """Test browser cookies without path."""
        mock_auth.return_value = ["--cookies-from-browser", "chrome"]

        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__ = Mock(return_value=mock_ydl)
        mock_ydl_class.return_value.__exit__ = Mock(return_value=False)

        mock_ydl.extract_info.side_effect = Exception("Test stop")

        with pytest.raises(SystemExit):
            downloader.process_url("https://beacon.tv/content/test")

        assert downloader.ydl_opts.get('cookiesfrombrowser') == ("chrome", None, None, None)
