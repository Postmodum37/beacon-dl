"""Shared pytest fixtures for beacon-dl tests.

This module provides common fixtures used across multiple test files,
reducing duplication and ensuring consistent test data.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.beacon_dl.content import (
    ContentMetadata,
    SubtitleTrack,
    VideoContent,
    VideoSource,
)

# =============================================================================
# Cookie Fixtures
# =============================================================================


@pytest.fixture
def mock_cookie_file(tmp_path: Path) -> Path:
    """Create a temporary cookie file for testing.

    This fixture is used across multiple test files:
    - test_graphql.py
    - test_downloader.py
    - test_cli_commands.py
    """
    cookie_file = tmp_path / "test_cookies.txt"
    cookie_file.write_text(
        "# Netscape HTTP Cookie File\n"
        ".beacon.tv\tTRUE\t/\tTRUE\t9999999999\tbeacon-session\ttest_session_token\n"
    )
    return cookie_file


@pytest.fixture
def expired_cookie_file(tmp_path: Path) -> Path:
    """Create a cookie file with expired cookies."""
    cookie_file = tmp_path / "expired_cookies.txt"
    cookie_file.write_text(
        "# Netscape HTTP Cookie File\n"
        ".beacon.tv\tTRUE\t/\tTRUE\t0\tbeacon-session\texpired_token\n"
    )
    return cookie_file


# =============================================================================
# Video Content Fixtures
# =============================================================================


@pytest.fixture
def sample_video_source() -> VideoSource:
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
def sample_video_source_720p() -> VideoSource:
    """Create a 720p video source for testing resolution selection."""
    return VideoSource(
        url="https://cdn.jwplayer.com/videos/test-720p.mp4",
        label="720p",
        width=1280,
        height=720,
        bitrate=1200000,
        file_type="video/mp4",
    )


@pytest.fixture
def sample_metadata() -> ContentMetadata:
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
def sample_subtitle() -> SubtitleTrack:
    """Create a sample subtitle track for testing."""
    return SubtitleTrack(
        url="https://cdn.jwplayer.com/tracks/test-en.vtt",
        label="English",
        language="eng",
    )


@pytest.fixture
def sample_video_content(
    sample_metadata: ContentMetadata,
    sample_video_source: VideoSource,
    sample_subtitle: SubtitleTrack,
) -> VideoContent:
    """Create sample video content for testing."""
    return VideoContent(
        metadata=sample_metadata,
        sources=[sample_video_source],
        subtitles=[sample_subtitle],
        hls_url=None,
    )


# =============================================================================
# GraphQL Response Fixtures
# =============================================================================


@pytest.fixture
def mock_series_response() -> dict:
    """Mock successful series list response."""
    return {
        "data": {
            "Collections": {
                "docs": [
                    {
                        "id": "collection-1",
                        "name": "Campaign 4",
                        "slug": "campaign-4",
                        "isSeries": True,
                        "itemCount": 12,
                    },
                    {
                        "id": "collection-2",
                        "name": "Candela Obscura",
                        "slug": "candela-obscura",
                        "isSeries": True,
                        "itemCount": 23,
                    },
                ]
            }
        }
    }


@pytest.fixture
def mock_episode_response() -> dict:
    """Mock successful episode response."""
    return {
        "data": {
            "MediaItems": {
                "docs": [
                    {
                        "id": "episode-1",
                        "title": "C4 E001 | The Fall of Thjazi Fang",
                        "slug": "c4-e001-the-fall-of-thjazi-fang",
                        "seasonNumber": 4,
                        "episodeNumber": 1,
                        "releaseDate": "2025-10-03T00:00:00.000Z",
                        "duration": 15138000,
                        "primaryCollection": {
                            "name": "Campaign 4",
                            "slug": "campaign-4",
                        },
                    },
                    {
                        "id": "episode-2",
                        "title": "C4 E002 | Broken Wing",
                        "slug": "c4-e002-broken-wing",
                        "seasonNumber": 4,
                        "episodeNumber": 2,
                        "releaseDate": "2025-10-10T00:00:00.000Z",
                        "duration": 15459000,
                        "primaryCollection": {
                            "name": "Campaign 4",
                            "slug": "campaign-4",
                        },
                    },
                ]
            }
        }
    }


@pytest.fixture
def mock_latest_episode_response() -> dict:
    """Mock response for latest episode query."""
    return {
        "data": {
            "MediaItems": {
                "docs": [
                    {
                        "id": "latest-episode",
                        "title": "C4 E007 | On the Scent",
                        "slug": "c4-e007-on-the-scent",
                        "seasonNumber": 4,
                        "episodeNumber": 7,
                        "releaseDate": "2025-11-07T00:00:00.000Z",
                        "duration": 16200000,
                        "primaryCollection": {
                            "name": "Campaign 4",
                            "slug": "campaign-4",
                        },
                    }
                ]
            }
        }
    }


@pytest.fixture
def mock_search_response() -> dict:
    """Mock search response for content search."""
    return {
        "data": {
            "MediaItems": {
                "docs": [
                    {
                        "id": "search-result-1",
                        "title": "C4 E007 | On the Scent",
                        "slug": "c4-e007-on-the-scent",
                        "seasonNumber": 4,
                        "episodeNumber": 7,
                        "releaseDate": "2025-11-07T00:00:00.000Z",
                        "duration": 16200000,
                        "primaryCollection": {
                            "name": "Campaign 4",
                            "slug": "campaign-4",
                        },
                    }
                ]
            }
        }
    }


# =============================================================================
# CLI Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_graphql_client():
    """Mock BeaconGraphQL client for CLI testing."""
    with patch("src.beacon_dl.main.BeaconGraphQL") as mock:
        client = Mock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_get_cookie_file(mock_cookie_file: Path):
    """Mock get_cookie_file to return the test cookie file."""
    with patch("src.beacon_dl.main.get_cookie_file") as mock:
        mock.return_value = mock_cookie_file
        yield mock


@pytest.fixture
def mock_downloader():
    """Mock BeaconDownloader for CLI testing."""
    with patch("src.beacon_dl.main.BeaconDownloader") as mock:
        downloader = Mock()
        mock.return_value = downloader
        yield downloader


@pytest.fixture
def mock_history(tmp_path: Path):
    """Mock DownloadHistory for CLI testing."""
    with patch("src.beacon_dl.main.DownloadHistory") as mock:
        history = Mock()
        mock.return_value = history
        # Default behaviors
        history.get_all_downloads.return_value = []
        history.get_download.return_value = None
        history.get_download_by_slug.return_value = None
        yield history


# =============================================================================
# Content Parsing Fixtures (for test_content.py)
# =============================================================================


@pytest.fixture
def sample_next_data() -> dict:
    """Sample __NEXT_DATA__ structure from beacon.tv page."""
    return {
        "props": {
            "pageProps": {
                "content": {
                    "id": "test-content-id",
                    "title": "C4 E007 | On the Scent",
                    "slug": "c4-e007-on-the-scent",
                    "description": "Episode description here",
                    "seasonNumber": 4,
                    "episodeNumber": 7,
                    "duration": 16200,
                    "primaryCollection": {
                        "name": "Campaign 4",
                        "slug": "campaign-4",
                    },
                    "video": {
                        "playlist": [
                            {
                                "sources": [
                                    {
                                        "file": "https://cdn.jwplayer.com/videos/test-1080p.mp4",
                                        "label": "1080p",
                                        "type": "video/mp4",
                                        "width": 1920,
                                        "height": 1080,
                                        "bitrate": 5000000,
                                    },
                                    {
                                        "file": "https://cdn.jwplayer.com/videos/test-720p.mp4",
                                        "label": "720p",
                                        "type": "video/mp4",
                                        "width": 1280,
                                        "height": 720,
                                        "bitrate": 2500000,
                                    },
                                ],
                                "tracks": [
                                    {
                                        "file": "https://cdn.jwplayer.com/tracks/en.vtt",
                                        "label": "English",
                                        "kind": "captions",
                                    },
                                    {
                                        "file": "https://cdn.jwplayer.com/tracks/es.vtt",
                                        "label": "Spanish",
                                        "kind": "captions",
                                    },
                                ],
                            }
                        ]
                    },
                }
            }
        }
    }


@pytest.fixture
def sample_html_page(sample_next_data: dict) -> str:
    """Sample HTML page with embedded __NEXT_DATA__."""
    import json

    return f"""<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body>
<script id="__NEXT_DATA__" type="application/json">{json.dumps(sample_next_data)}</script>
</body>
</html>"""
