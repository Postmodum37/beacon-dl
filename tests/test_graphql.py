"""Tests for GraphQL client API functionality.

Tests GraphQL queries, error handling, and data parsing.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from src.beacon_dl.graphql import BeaconGraphQL


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
def graphql_client(mock_cookie_file):
    """Create a BeaconGraphQL client for testing."""
    return BeaconGraphQL(mock_cookie_file)


@pytest.fixture
def mock_series_response():
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
def mock_episode_response():
    """Mock successful episode response."""
    return {
        "data": {
            "Contents": {
                "docs": [
                    {
                        "id": "episode-1",
                        "title": "C4 E007 | On the Scent",
                        "slug": "c4-e007-on-the-scent",
                        "seasonNumber": 4,
                        "episodeNumber": 7,
                        "releaseDate": "2025-11-21T03:00:00.000Z",
                        "duration": 13949000,
                        "description": "Test episode description",
                        "primaryCollection": {
                            "id": "collection-1",
                            "name": "Campaign 4",
                            "slug": "campaign-4",
                        },
                    }
                ]
            }
        }
    }


class TestBeaconGraphQLClient:
    """Test BeaconGraphQL client initialization and basic functionality."""

    def test_client_initialization(self, mock_cookie_file):
        """Test that client initializes correctly."""
        client = BeaconGraphQL(mock_cookie_file)

        assert client.endpoint == "https://beacon.tv/api/graphql"
        assert "beacon-session" in client.cookies
        assert client.cookies["beacon-session"] == "test_session_token"

    def test_client_loads_cookies_from_file(self, tmp_path):
        """Test that client loads cookies from Netscape format."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text(
            "# Netscape HTTP Cookie File\n"
            ".beacon.tv\tTRUE\t/\tTRUE\t9999999999\tcookie1\tvalue1\n"
            "beacon.tv\tFALSE\t/\tTRUE\t9999999999\tcookie2\tvalue2\n"
        )

        client = BeaconGraphQL(cookie_file)

        assert "cookie1" in client.cookies
        assert "cookie2" in client.cookies
        assert client.cookies["cookie1"] == "value1"
        assert client.cookies["cookie2"] == "value2"

    def test_client_handles_missing_cookie_file(self, tmp_path):
        """Test that client handles missing cookie file gracefully."""
        missing_file = tmp_path / "nonexistent.txt"

        client = BeaconGraphQL(missing_file)

        # Should create client with empty cookies dict
        assert isinstance(client.cookies, dict)
        assert len(client.cookies) == 0


class TestListSeries:
    """Test list_collections() functionality."""

    @patch('requests.post')
    def test_list_series_success(self, mock_post, graphql_client, mock_series_response):
        """Test successful series listing."""
        mock_response = Mock()
        mock_response.json.return_value = mock_series_response
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        series_list = graphql_client.list_collections(series_only=True)

        assert len(series_list) == 2
        assert series_list[0]["name"] == "Campaign 4"
        assert series_list[0]["slug"] == "campaign-4"
        assert series_list[0]["itemCount"] == 12
        assert series_list[1]["name"] == "Candela Obscura"

    @patch('requests.post')
    def test_list_series_empty_response(self, mock_post, graphql_client):
        """Test handling of empty series list."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": {"Collections": {"docs": []}}}
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        series_list = graphql_client.list_collections()

        assert series_list == []

    @patch('requests.post')
    def test_list_series_graphql_error(self, mock_post, graphql_client):
        """Test handling of GraphQL errors."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "errors": [{"message": "Authentication required"}]
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        series_list = graphql_client.list_collections()

        assert series_list == []

    @patch('requests.post')
    def test_list_series_http_error(self, mock_post, graphql_client):
        """Test handling of HTTP errors."""
        mock_post.side_effect = Exception("Network error")

        series_list = graphql_client.list_collections()

        assert series_list == []


class TestGetLatestEpisode:
    """Test get_latest_episode() functionality."""

    @patch('requests.post')
    def test_get_latest_episode_success(self, mock_post, graphql_client, mock_episode_response):
        """Test successful latest episode retrieval."""
        # campaign-4 is pre-cached, so only ONE API call is made (for episodes)
        mock_response = Mock()
        mock_response.json.return_value = mock_episode_response
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        episode = graphql_client.get_latest_episode("campaign-4")

        assert episode is not None
        assert episode["title"] == "C4 E007 | On the Scent"
        assert episode["slug"] == "c4-e007-on-the-scent"
        assert episode["seasonNumber"] == 4
        assert episode["episodeNumber"] == 7

    @patch('requests.post')
    def test_get_latest_episode_no_episodes(self, mock_post, graphql_client):
        """Test handling when no episodes found."""
        # First call looks up collection ID, second gets episodes
        collection_response = {
            "data": {"Collections": {"docs": [{"id": "col-1", "name": "Test", "slug": "test"}]}}
        }
        empty_response = {"data": {"Contents": {"docs": []}}}

        mock_response = Mock()
        mock_response.json.side_effect = [collection_response, empty_response]
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        episode = graphql_client.get_latest_episode("test")

        assert episode is None

    @patch('requests.post')
    def test_get_latest_episode_collection_not_found(self, mock_post, graphql_client):
        """Test handling when collection doesn't exist."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": {"Collections": {"docs": []}}}
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        episode = graphql_client.get_latest_episode("nonexistent-series")

        assert episode is None


class TestGetContentBySlug:
    """Test get_content_by_slug() functionality."""

    @patch('requests.post')
    def test_get_content_by_slug_success(self, mock_post, graphql_client, mock_episode_response):
        """Test successful content retrieval by slug."""
        mock_response = Mock()
        mock_response.json.return_value = mock_episode_response
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        content = graphql_client.get_content_by_slug("c4-e007-on-the-scent")

        assert content is not None
        assert content["title"] == "C4 E007 | On the Scent"
        assert content["slug"] == "c4-e007-on-the-scent"

    @patch('requests.post')
    def test_get_content_by_slug_not_found(self, mock_post, graphql_client):
        """Test handling when content not found."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": {"Contents": {"docs": []}}}
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        content = graphql_client.get_content_by_slug("nonexistent-slug")

        assert content is None


class TestGetSeriesEpisodes:
    """Test get_series_episodes() functionality."""

    @patch('requests.post')
    def test_get_series_episodes_success(self, mock_post, graphql_client):
        """Test successful retrieval of all episodes in series."""
        # Use unique slug to avoid cache interference from other tests
        unique_slug = "unique-series-episodes-test"

        # Clear cache for this test
        if unique_slug in graphql_client.COLLECTION_CACHE:
            del graphql_client.COLLECTION_CACHE[unique_slug]

        collection_response = {
            "data": {"Collections": {"docs": [{"id": "col-series-ep", "name": "Test", "slug": unique_slug}]}}
        }
        episodes_response = {
            "data": {
                "Contents": {
                    "docs": [
                        {
                            "id": "ep-1",
                            "title": "Episode 1",
                            "slug": "episode-1",
                            "seasonNumber": 1,
                            "episodeNumber": 1,
                            "releaseDate": "2025-01-01T00:00:00.000Z",
                            "duration": 10000000,
                            "description": "Test",
                        },
                        {
                            "id": "ep-2",
                            "title": "Episode 2",
                            "slug": "episode-2",
                            "seasonNumber": 1,
                            "episodeNumber": 2,
                            "releaseDate": "2025-01-08T00:00:00.000Z",
                            "duration": 10000000,
                            "description": "Test",
                        },
                    ]
                }
            }
        }

        mock_response = Mock()
        mock_response.json.side_effect = [collection_response, episodes_response]
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        episodes = graphql_client.get_series_episodes(unique_slug)

        assert len(episodes) == 2
        assert episodes[0]["episodeNumber"] == 1
        assert episodes[1]["episodeNumber"] == 2

    @patch('requests.post')
    def test_get_series_episodes_empty(self, mock_post, graphql_client):
        """Test handling of series with no episodes."""
        collection_response = {
            "data": {"Collections": {"docs": [{"id": "col-1", "name": "Test", "slug": "test-empty"}]}}
        }
        empty_response = {"data": {"Contents": {"docs": []}}}

        mock_response = Mock()
        mock_response.json.side_effect = [collection_response, empty_response]
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        episodes = graphql_client.get_series_episodes("test-empty")

        assert episodes == []


class TestGetCollectionInfo:
    """Test get_collection_info() functionality."""

    @patch('requests.post')
    def test_get_collection_info_success(self, mock_post, graphql_client):
        """Test successful collection info retrieval."""
        # campaign-4 is pre-cached, so only ONE API call is made (for collection info)
        collection_info_response = {
            "data": {
                "Collection": {
                    "id": "68caf69e7a76bce4b7aa689a",
                    "name": "Campaign 4",
                    "slug": "campaign-4",
                    "isSeries": True,
                    "itemCount": 12,
                }
            }
        }

        mock_response = Mock()
        mock_response.json.return_value = collection_info_response
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        info = graphql_client.get_collection_info("campaign-4")

        assert info is not None
        assert info["name"] == "Campaign 4"
        assert info["itemCount"] == 12
        assert info["isSeries"] is True


class TestCollectionCache:
    """Test collection ID caching functionality."""

    @patch('requests.post')
    def test_collection_cache_avoids_redundant_queries(self, mock_post, graphql_client):
        """Test that collection IDs are cached to avoid redundant queries."""
        # Use a unique slug to avoid cache interference from other tests
        unique_slug = "unique-test-slug-for-cache"

        # Clear any existing cache entry for this slug
        if unique_slug in graphql_client.COLLECTION_CACHE:
            del graphql_client.COLLECTION_CACHE[unique_slug]

        collection_response = {
            "data": {"Collections": {"docs": [{"id": "cached-id", "name": "Test", "slug": unique_slug}]}}
        }

        mock_response = Mock()
        mock_response.json.return_value = collection_response
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # First call should query API
        id1 = graphql_client._get_collection_id(unique_slug)
        assert id1 == "cached-id"
        assert mock_post.call_count == 1

        # Second call should use cache
        id2 = graphql_client._get_collection_id(unique_slug)
        assert id2 == "cached-id"
        assert mock_post.call_count == 1  # Still 1, not 2!

    def test_collection_cache_pre_populated(self, graphql_client):
        """Test that cache is pre-populated with known collections."""
        # Should return cached ID without API call
        cached_id = graphql_client.COLLECTION_CACHE.get("campaign-4")
        assert cached_id == "68caf69e7a76bce4b7aa689a"


class TestErrorHandling:
    """Test error handling across all methods."""

    @patch('requests.post')
    def test_handles_network_timeout(self, mock_post, graphql_client):
        """Test handling of network timeouts."""
        mock_post.side_effect = TimeoutError("Connection timed out")

        result = graphql_client.list_collections()

        assert result == []

    @patch('requests.post')
    def test_handles_connection_error(self, mock_post, graphql_client):
        """Test handling of connection errors."""
        mock_post.side_effect = ConnectionError("Cannot connect to server")

        result = graphql_client.get_latest_episode("campaign-4")

        assert result is None

    @patch('requests.post')
    def test_handles_malformed_json(self, mock_post, graphql_client):
        """Test handling of malformed JSON responses."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = graphql_client.list_collections()

        assert result == []

    @patch('requests.post')
    def test_handles_missing_data_field(self, mock_post, graphql_client):
        """Test handling of responses missing expected 'data' field."""
        mock_response = Mock()
        mock_response.json.return_value = {}  # Missing 'data'
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = graphql_client.get_latest_episode("campaign-4")

        assert result is None
