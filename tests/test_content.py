"""Tests for content.py - video content fetching and parsing.

This module tests the content fetching and parsing functionality including:
- __NEXT_DATA__ extraction from HTML pages
- Video source and subtitle parsing
- Season/episode number extraction
- Apollo state data traversal
"""

import json

import httpx
import pytest

from src.beacon_dl.content import (
    ContentMetadata,
    SubtitleTrack,
    VideoContent,
    VideoSource,
    _extract_collection_name,
    _label_to_iso,
    _parse_season_episode,
    _safe_int,
    extract_video_content,
    fetch_content_page,
    parse_next_data,
)

pytestmark = pytest.mark.unit  # All tests in this module are unit tests

# =============================================================================
# Dataclass Tests
# =============================================================================


class TestDataclasses:
    """Test dataclass instantiation and attributes."""

    def test_video_source_creation(self):
        """Test VideoSource dataclass creation."""
        source = VideoSource(
            url="https://cdn.example.com/video.mp4",
            label="1080p",
            width=1920,
            height=1080,
            bitrate=5000000,
            file_type="video/mp4",
        )
        assert source.url == "https://cdn.example.com/video.mp4"
        assert source.label == "1080p"
        assert source.width == 1920
        assert source.height == 1080
        assert source.bitrate == 5000000
        assert source.file_type == "video/mp4"

    def test_subtitle_track_creation(self):
        """Test SubtitleTrack dataclass creation."""
        track = SubtitleTrack(
            url="https://cdn.example.com/en.vtt",
            label="English",
            language="eng",
        )
        assert track.url == "https://cdn.example.com/en.vtt"
        assert track.label == "English"
        assert track.language == "eng"

    def test_content_metadata_creation(self):
        """Test ContentMetadata dataclass creation."""
        metadata = ContentMetadata(
            id="test-123",
            title="C4 E007 | On the Scent",
            slug="c4-e007-on-the-scent",
            season_number=4,
            episode_number=7,
            duration=16200000,
            description="Episode description",
            collection_name="Campaign 4",
        )
        assert metadata.id == "test-123"
        assert metadata.title == "C4 E007 | On the Scent"
        assert metadata.slug == "c4-e007-on-the-scent"
        assert metadata.season_number == 4
        assert metadata.episode_number == 7
        assert metadata.duration == 16200000
        assert metadata.description == "Episode description"
        assert metadata.collection_name == "Campaign 4"

    def test_content_metadata_optional_fields(self):
        """Test ContentMetadata with None optional fields."""
        metadata = ContentMetadata(
            id="test-123",
            title="Test Title",
            slug="test-slug",
            season_number=None,
            episode_number=None,
            duration=None,
            description=None,
            collection_name=None,
        )
        assert metadata.season_number is None
        assert metadata.episode_number is None
        assert metadata.duration is None
        assert metadata.description is None
        assert metadata.collection_name is None

    def test_video_content_creation(self):
        """Test VideoContent dataclass creation."""
        metadata = ContentMetadata(
            id="test-123",
            title="Test",
            slug="test",
            season_number=1,
            episode_number=1,
            duration=1000,
            description="desc",
            collection_name="Series",
        )
        source = VideoSource(
            url="https://example.com/video.mp4",
            label="1080p",
            width=1920,
            height=1080,
            bitrate=5000,
            file_type="video/mp4",
        )
        subtitle = SubtitleTrack(
            url="https://example.com/en.vtt",
            label="English",
            language="eng",
        )
        content = VideoContent(
            metadata=metadata,
            sources=[source],
            subtitles=[subtitle],
            hls_url="https://example.com/manifest.m3u8",
        )
        assert content.metadata == metadata
        assert len(content.sources) == 1
        assert len(content.subtitles) == 1
        assert content.hls_url == "https://example.com/manifest.m3u8"


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestSafeInt:
    """Tests for _safe_int helper function."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            (42, 42),
            ("42", 42),
            ("0", 0),
            (0, 0),
            (None, None),
            ("", None),
            ("abc", None),
            ("12.5", None),
            ([], None),
            ({}, None),
        ],
        ids=[
            "int_value",
            "string_int",
            "string_zero",
            "int_zero",
            "none_value",
            "empty_string",
            "non_numeric_string",
            "float_string",
            "empty_list",
            "empty_dict",
        ],
    )
    def test_safe_int(self, value, expected):
        """Test _safe_int with various inputs."""
        assert _safe_int(value) == expected


class TestParseSeasonEpisode:
    """Tests for _parse_season_episode helper function."""

    @pytest.mark.parametrize(
        "title,expected_season,expected_episode",
        [
            # C4 E007 format (Critical Role style)
            ("C4 E007 | On the Scent", 4, 7),
            ("C1 E001 | First Episode", 1, 1),
            ("C10 E100 | Big Episode", 10, 100),
            # S04E07 format (standard TV style)
            ("S04E07 - Title", 4, 7),
            ("S04E07: Title", 4, 7),
            ("S04E07 Title", 4, 7),
            ("S01E01 - Pilot", 1, 1),
            # 4x07 format (alternative style)
            ("4x07 - Title", 4, 7),
            ("1x01 - Pilot", 1, 1),
            # No pattern found
            ("Random Title Without Episode", None, None),
            ("Just A Movie", None, None),
            ("", None, None),
        ],
        ids=[
            "c4_e007_format",
            "c1_e001_format",
            "c10_e100_format",
            "s04e07_dash",
            "s04e07_colon",
            "s04e07_space",
            "s01e01_dash",
            "4x07_format",
            "1x01_format",
            "no_pattern",
            "no_pattern_movie",
            "empty_string",
        ],
    )
    def test_parse_season_episode(self, title, expected_season, expected_episode):
        """Test season/episode parsing from various title formats."""
        season, episode = _parse_season_episode(title)
        assert season == expected_season
        assert episode == expected_episode


class TestLabelToIso:
    """Tests for _label_to_iso helper function."""

    @pytest.mark.parametrize(
        "label,expected",
        [
            ("English", "eng"),
            ("english", "eng"),
            ("ENGLISH", "eng"),
            ("Spanish", "spa"),
            ("French", "fre"),
            ("German", "ger"),
            ("Japanese", "jpn"),
            ("Unknown", "und"),
            ("", "und"),
            ("Klingon", "und"),
        ],
        ids=[
            "english_title",
            "english_lower",
            "english_upper",
            "spanish",
            "french",
            "german",
            "japanese",
            "unknown",
            "empty",
            "fictional",
        ],
    )
    def test_label_to_iso(self, label, expected):
        """Test subtitle label to ISO code conversion."""
        assert _label_to_iso(label) == expected


class TestExtractCollectionName:
    """Tests for _extract_collection_name helper function."""

    def test_extract_direct_collection(self):
        """Test extraction when collection is a direct object."""
        content_data = {
            "primaryCollection": {
                "name": "Campaign 4",
                "slug": "campaign-4",
            }
        }
        apollo = {}
        result = _extract_collection_name(content_data, apollo)
        assert result == "Campaign 4"

    def test_extract_collection_reference(self):
        """Test extraction when collection is an Apollo reference."""
        content_data = {
            "primaryCollection": {"__ref": "Collection:campaign-4"}
        }
        apollo = {
            "Collection:campaign-4": {
                "name": "Campaign 4",
                "slug": "campaign-4",
            }
        }
        result = _extract_collection_name(content_data, apollo)
        assert result == "Campaign 4"

    def test_extract_missing_collection(self):
        """Test extraction when no collection exists."""
        content_data = {}
        apollo = {}
        result = _extract_collection_name(content_data, apollo)
        assert result is None

    def test_extract_null_collection(self):
        """Test extraction when collection is null."""
        content_data = {"primaryCollection": None}
        apollo = {}
        result = _extract_collection_name(content_data, apollo)
        assert result is None

    def test_extract_missing_reference(self):
        """Test extraction when Apollo reference is missing."""
        content_data = {
            "primaryCollection": {"__ref": "Collection:missing"}
        }
        apollo = {}
        result = _extract_collection_name(content_data, apollo)
        assert result is None


# =============================================================================
# parse_next_data Tests
# =============================================================================


class TestParseNextData:
    """Tests for parse_next_data function."""

    def test_parse_valid_html(self):
        """Test parsing valid HTML with __NEXT_DATA__."""
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Test</title></head>
        <body>
        <script id="__NEXT_DATA__" type="application/json">{"props":{"data":"test"}}</script>
        </body>
        </html>
        """
        result = parse_next_data(html)
        assert result == {"props": {"data": "test"}}

    def test_parse_complex_json(self):
        """Test parsing complex nested JSON."""
        data = {
            "props": {
                "pageProps": {
                    "__APOLLO_STATE__": {
                        "MediaItem:123": {
                            "id": "123",
                            "title": "Test",
                        }
                    }
                }
            }
        }
        html = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script>'
        result = parse_next_data(html)
        assert result == data

    def test_parse_missing_script(self):
        """Test parsing HTML without __NEXT_DATA__."""
        html = "<html><body>No data</body></html>"
        result = parse_next_data(html)
        assert result is None

    def test_parse_cloudflare_challenge(self):
        """Test parsing HTML with Cloudflare challenge."""
        html = """
        <html>
        <head><title>Security Check</title></head>
        <body>Please complete the security check</body>
        </html>
        """
        result = parse_next_data(html)
        assert result is None

    def test_parse_cf_chl_marker(self):
        """Test parsing HTML with cf_chl challenge marker."""
        html = """
        <html>
        <body>cf_chl_jschl_tk challenge required</body>
        </html>
        """
        result = parse_next_data(html)
        assert result is None

    def test_parse_invalid_json(self):
        """Test parsing HTML with invalid JSON."""
        html = '<script id="__NEXT_DATA__" type="application/json">{invalid json}</script>'
        result = parse_next_data(html)
        assert result is None

    def test_parse_empty_json(self):
        """Test parsing HTML with empty JSON object."""
        html = '<script id="__NEXT_DATA__" type="application/json">{}</script>'
        result = parse_next_data(html)
        assert result == {}


# =============================================================================
# fetch_content_page Tests
# =============================================================================


class TestFetchContentPage:
    """Tests for fetch_content_page function."""

    def test_fetch_success(self, mock_cookie_file, httpx_mock):
        """Test successful content page fetch."""
        html_content = '<html><script id="__NEXT_DATA__">{"test":"data"}</script></html>'
        httpx_mock.add_response(
            url="https://beacon.tv/content/test-slug",
            text=html_content,
            status_code=200,
        )

        # Add beacon-session cookie to the file
        mock_cookie_file.write_text(
            "# Netscape HTTP Cookie File\n"
            ".beacon.tv\tTRUE\t/\tTRUE\t9999999999\tbeacon-session\ttest_token\n"
        )

        result = fetch_content_page("test-slug", mock_cookie_file)
        assert result == html_content

    def test_fetch_no_session_cookie(self, mock_cookie_file):
        """Test fetch fails when no beacon-session cookie."""
        # Cookie file without beacon-session
        mock_cookie_file.write_text(
            "# Netscape HTTP Cookie File\n"
            ".beacon.tv\tTRUE\t/\tTRUE\t9999999999\tother-cookie\tvalue\n"
        )

        result = fetch_content_page("test-slug", mock_cookie_file)
        assert result is None

    def test_fetch_http_error(self, mock_cookie_file, httpx_mock):
        """Test fetch handles HTTP errors."""
        httpx_mock.add_response(
            url="https://beacon.tv/content/test-slug",
            status_code=404,
        )

        mock_cookie_file.write_text(
            "# Netscape HTTP Cookie File\n"
            ".beacon.tv\tTRUE\t/\tTRUE\t9999999999\tbeacon-session\ttest_token\n"
        )

        result = fetch_content_page("test-slug", mock_cookie_file)
        assert result is None

    def test_fetch_connection_error(self, mock_cookie_file, httpx_mock):
        """Test fetch handles connection errors."""
        httpx_mock.add_exception(
            httpx.ConnectError("Connection failed"),
            url="https://beacon.tv/content/test-slug",
        )

        mock_cookie_file.write_text(
            "# Netscape HTTP Cookie File\n"
            ".beacon.tv\tTRUE\t/\tTRUE\t9999999999\tbeacon-session\ttest_token\n"
        )

        result = fetch_content_page("test-slug", mock_cookie_file)
        assert result is None


# =============================================================================
# extract_video_content Tests
# =============================================================================


class TestExtractVideoContent:
    """Tests for extract_video_content function."""

    @pytest.fixture
    def valid_apollo_data(self):
        """Create valid Apollo state data for testing."""
        return {
            "props": {
                "pageProps": {
                    "__APOLLO_STATE__": {
                        "MediaItem:test-123": {
                            "id": "test-123",
                            "title": "C4 E007 | On the Scent",
                            "slug": "c4-e007-on-the-scent",
                            "seasonNumber": 4,
                            "episodeNumber": 7,
                            "duration": 16200000,
                            "description": "Episode description",
                            "primaryCollection": {
                                "name": "Campaign 4",
                                "slug": "campaign-4",
                            },
                            "contentVideo": {
                                "video": {
                                    "videoData": json.dumps(
                                        {
                                            "playlist": [
                                                {
                                                    "sources": [
                                                        {
                                                            "file": "https://cdn.example.com/1080p.mp4",
                                                            "label": "1080p",
                                                            "type": "video/mp4",
                                                            "width": 1920,
                                                            "height": 1080,
                                                            "bitrate": 5000000,
                                                        },
                                                        {
                                                            "file": "https://cdn.example.com/720p.mp4",
                                                            "label": "720p",
                                                            "type": "video/mp4",
                                                            "width": 1280,
                                                            "height": 720,
                                                            "bitrate": 2500000,
                                                        },
                                                        {
                                                            "file": "https://cdn.example.com/manifest.m3u8",
                                                            "type": "application/vnd.apple.mpegurl",
                                                        },
                                                    ],
                                                    "tracks": [
                                                        {
                                                            "file": "https://cdn.example.com/en.vtt",
                                                            "label": "English",
                                                            "kind": "captions",
                                                        },
                                                        {
                                                            "file": "https://cdn.example.com/es.vtt",
                                                            "label": "Spanish",
                                                            "kind": "captions",
                                                        },
                                                    ],
                                                }
                                            ]
                                        }
                                    )
                                }
                            },
                        }
                    }
                }
            }
        }

    def test_extract_valid_content(self, valid_apollo_data):
        """Test extracting valid video content."""
        result = extract_video_content(valid_apollo_data, "c4-e007-on-the-scent")

        assert result is not None
        assert result.metadata.id == "test-123"
        assert result.metadata.title == "C4 E007 | On the Scent"
        assert result.metadata.season_number == 4
        assert result.metadata.episode_number == 7
        assert result.metadata.collection_name == "Campaign 4"

        # Check sources are sorted by height descending
        assert len(result.sources) == 2
        assert result.sources[0].height == 1080
        assert result.sources[1].height == 720

        # Check subtitles
        assert len(result.subtitles) == 2
        assert result.subtitles[0].label == "English"
        assert result.subtitles[0].language == "eng"

        # Check HLS URL
        assert result.hls_url == "https://cdn.example.com/manifest.m3u8"

    def test_extract_missing_apollo_state(self):
        """Test extraction fails when Apollo state is missing."""
        data = {"props": {"pageProps": {}}}
        result = extract_video_content(data, "test-slug")
        assert result is None

    def test_extract_wrong_slug(self, valid_apollo_data):
        """Test extraction fails when slug doesn't match."""
        result = extract_video_content(valid_apollo_data, "wrong-slug")
        assert result is None

    def test_extract_missing_content_video(self):
        """Test extraction fails when contentVideo is missing."""
        data = {
            "props": {
                "pageProps": {
                    "__APOLLO_STATE__": {
                        "MediaItem:test-123": {
                            "id": "test-123",
                            "title": "Test",
                            "slug": "test-slug",
                            # No contentVideo
                        }
                    }
                }
            }
        }
        result = extract_video_content(data, "test-slug")
        assert result is None

    def test_extract_missing_video_data(self):
        """Test extraction fails when videoData is missing."""
        data = {
            "props": {
                "pageProps": {
                    "__APOLLO_STATE__": {
                        "MediaItem:test-123": {
                            "id": "test-123",
                            "title": "Test",
                            "slug": "test-slug",
                            "contentVideo": {
                                "video": {}  # No videoData
                            },
                        }
                    }
                }
            }
        }
        result = extract_video_content(data, "test-slug")
        assert result is None

    def test_extract_invalid_video_data_json(self):
        """Test extraction fails when videoData is invalid JSON."""
        data = {
            "props": {
                "pageProps": {
                    "__APOLLO_STATE__": {
                        "MediaItem:test-123": {
                            "id": "test-123",
                            "title": "Test",
                            "slug": "test-slug",
                            "contentVideo": {
                                "video": {
                                    "videoData": "{invalid json}"
                                }
                            },
                        }
                    }
                }
            }
        }
        result = extract_video_content(data, "test-slug")
        assert result is None

    def test_extract_empty_playlist(self):
        """Test extraction fails when playlist is empty."""
        data = {
            "props": {
                "pageProps": {
                    "__APOLLO_STATE__": {
                        "MediaItem:test-123": {
                            "id": "test-123",
                            "title": "Test",
                            "slug": "test-slug",
                            "contentVideo": {
                                "video": {
                                    "videoData": json.dumps({"playlist": []})
                                }
                            },
                        }
                    }
                }
            }
        }
        result = extract_video_content(data, "test-slug")
        assert result is None

    def test_extract_parses_title_for_season_episode(self):
        """Test season/episode is parsed from title when not in API."""
        data = {
            "props": {
                "pageProps": {
                    "__APOLLO_STATE__": {
                        "MediaItem:test-123": {
                            "id": "test-123",
                            "title": "C4 E007 | On the Scent",
                            "slug": "c4-e007-on-the-scent",
                            # No seasonNumber/episodeNumber in API
                            "contentVideo": {
                                "video": {
                                    "videoData": json.dumps(
                                        {
                                            "playlist": [
                                                {
                                                    "sources": [
                                                        {
                                                            "file": "https://cdn.example.com/video.mp4",
                                                            "type": "video/mp4",
                                                            "width": 1920,
                                                            "height": 1080,
                                                        }
                                                    ],
                                                    "tracks": [],
                                                }
                                            ]
                                        }
                                    )
                                }
                            },
                        }
                    }
                }
            }
        }
        result = extract_video_content(data, "c4-e007-on-the-scent")

        assert result is not None
        assert result.metadata.season_number == 4
        assert result.metadata.episode_number == 7

    def test_extract_skips_audio_only_sources(self):
        """Test audio-only sources are filtered out."""
        data = {
            "props": {
                "pageProps": {
                    "__APOLLO_STATE__": {
                        "MediaItem:test-123": {
                            "id": "test-123",
                            "title": "Test",
                            "slug": "test-slug",
                            "contentVideo": {
                                "video": {
                                    "videoData": json.dumps(
                                        {
                                            "playlist": [
                                                {
                                                    "sources": [
                                                        {
                                                            "file": "https://cdn.example.com/video.mp4",
                                                            "type": "video/mp4",
                                                            "width": 1920,
                                                            "height": 1080,
                                                        },
                                                        {
                                                            "file": "https://cdn.example.com/audio.mp4",
                                                            "type": "audio/mp4",
                                                        },
                                                    ],
                                                    "tracks": [],
                                                }
                                            ]
                                        }
                                    )
                                }
                            },
                        }
                    }
                }
            }
        }
        result = extract_video_content(data, "test-slug")

        assert result is not None
        assert len(result.sources) == 1
        assert "audio" not in result.sources[0].file_type

    def test_extract_only_caption_tracks(self):
        """Test only caption tracks are included in subtitles."""
        data = {
            "props": {
                "pageProps": {
                    "__APOLLO_STATE__": {
                        "MediaItem:test-123": {
                            "id": "test-123",
                            "title": "Test",
                            "slug": "test-slug",
                            "contentVideo": {
                                "video": {
                                    "videoData": json.dumps(
                                        {
                                            "playlist": [
                                                {
                                                    "sources": [
                                                        {
                                                            "file": "https://cdn.example.com/video.mp4",
                                                            "type": "video/mp4",
                                                            "width": 1920,
                                                            "height": 1080,
                                                        }
                                                    ],
                                                    "tracks": [
                                                        {
                                                            "file": "https://cdn.example.com/en.vtt",
                                                            "label": "English",
                                                            "kind": "captions",
                                                        },
                                                        {
                                                            "file": "https://cdn.example.com/thumb.vtt",
                                                            "label": "Thumbnails",
                                                            "kind": "thumbnails",
                                                        },
                                                    ],
                                                }
                                            ]
                                        }
                                    )
                                }
                            },
                        }
                    }
                }
            }
        }
        result = extract_video_content(data, "test-slug")

        assert result is not None
        assert len(result.subtitles) == 1
        assert result.subtitles[0].label == "English"
