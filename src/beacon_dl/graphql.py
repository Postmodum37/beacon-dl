"""GraphQL client for BeaconTV API.

This module provides a client for querying the beacon.tv GraphQL API to fetch
content metadata, series information, and episode listings. This replaces
slower Playwright-based web scraping with fast, structured API calls.

API Endpoint: https://beacon.tv/api/graphql
Authentication: beacon-session cookie (obtained via Playwright login)

Discovered Schema (2025-11-24):
    - Contents: Episodes, articles, one-shots with metadata
    - Collections: Series and collection groupings
    - search: Powerful custom query with filtering and pagination
    - Categories, Tags: Content categorization
    - Videos: Video metadata (but playlistUrl not accessible via API)

Limitations:
    - Video URLs (playlistUrl) return null - still need yt-dlp for downloads
    - ViewHistories returns 403 Forbidden - watch progress not accessible
    - meMember.user returns null - member profile not accessible
    - API requires literal values in where clauses, not GraphQL variables

Content Types:
    - videoPodcast: Video content with podcast feed
    - article: Text-based content
    - livestream: Live streaming content
"""

import re
from pathlib import Path
from typing import Any

import httpx
from rich.console import Console

from .exceptions import GraphQLError, ValidationError
from .utils import load_cookies

console = Console()

# HTTP client with retry support
DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
DEFAULT_TRANSPORT = httpx.HTTPTransport(retries=3)


def validate_slug(slug: str, field_name: str = "slug") -> str:
    """
    Validate and sanitize a slug to prevent GraphQL injection.

    Beacon TV API requires literal values in GraphQL queries (doesn't support
    variables in where clauses), so we must validate inputs before interpolation.

    Args:
        slug: The slug to validate (series slug, episode slug, etc.)
        field_name: Name of the field for error messages

    Returns:
        The validated slug

    Raises:
        ValidationError: If slug is empty, contains invalid characters, or is too long

    Security:
        Only allows alphanumeric characters, hyphens, and underscores.
        Prevents GraphQL injection attacks via malicious slugs.
    """
    if not slug:
        raise ValidationError(f"{field_name} cannot be empty")

    # Only allow alphanumeric, hyphens, and underscores
    if not re.match(r"^[a-zA-Z0-9_-]+$", slug):
        raise ValidationError(
            f"Invalid {field_name}: '{slug}'. "
            f"Only alphanumeric characters, hyphens, and underscores are allowed."
        )

    # Prevent excessively long slugs (DoS protection)
    if len(slug) > 200:
        raise ValidationError(f"{field_name} too long (max 200 characters)")

    return slug


class BeaconGraphQL:
    """GraphQL client for beacon.tv API.

    Provides methods to query content metadata, series information, and episode
    listings using the beacon.tv GraphQL API. Authenticates using cookies from
    a Netscape HTTP Cookie File.

    Supports context manager protocol for proper resource cleanup.

    Example:
        >>> with BeaconGraphQL(cookie_file="beacon_cookies.txt") as client:
        ...     latest = client.get_latest_episode("campaign-4")
        ...     print(latest["title"])
        'C4 E007 | On the Scent'
    """

    # Known collection slugs to IDs (cached for performance)
    # Discovered via GraphQL introspection on 2025-11-24
    COLLECTION_CACHE: dict[str, str] = {
        "4-sided-dive": "65b254ac78f89be87b4dbeb8",
        "age-of-umbra": "6827b1bed18cf5fdafa5e57e",
        "all-work-no-play": "66067c5dc1ffa829c389b7aa",
        "campaign-1-infinights-tales-from-the-stinky-dragon": "66f36f993b411022057dc8fb",
        "campaign-2-grotethe-tales-from-the-stinky-dragon": "66f36ff55bdb51837c543cd2",
        "campaign-2-the-mighty-nein": "660676d5c1ffa829c389a4c7",
        "campaign-3-bells-hells": "65b2548e78f89be87b4dbe9a",
        "campaign-3-kanon-tales-from-the-stinky-dragon": "66f3708e91e18e3e38b3b460",
        "campaign-4": "68caf69e7a76bce4b7aa689a",
        "candela-obscura": "66067a09c1ffa829c389a65e",
        "crit-recap-animated": "663588c574598feedb62290f",
        "critical-cooldown": "663012bf624e86a8e0a20a11",
        "critical-role-abridged": "6616fa3b1fa3e938e56cf5ee",
        "exandria-unlimited": "662c3b58fd8fbf1731b32f48",
        "fireside-chat": "6632a932c7641d946e1e9e41",
        "midst": "65b25a0478f89be87b4dc1d4",
        "moonward": "66a194d052248ebdd8d22ae1",
        "narrative-telephone": "6616ff227fdbd0e3fc6ae1c0",
        "re-slayers-take": "663b31be33a09eef3a773b5a",
        "thresher": "6802a0a9d2fad35616589918",
        "unend": "66f34b7397a421f24c60213e",
        "weird-kids": "67c4212a45894204e65efaf0",
        "wildemount-wildlings": "67e46b7b00458864a1e0b8c8",
    }

    def __init__(self, cookie_file: Path | str):
        """Initialize GraphQL client.

        Args:
            cookie_file: Path to Netscape HTTP Cookie File containing beacon-session cookie
        """
        self.endpoint = "https://beacon.tv/api/graphql"
        self.cookies = load_cookies(Path(cookie_file))
        self.client = httpx.Client(
            timeout=DEFAULT_TIMEOUT,
            transport=DEFAULT_TRANSPORT,
            cookies=self.cookies,
        )

    def __enter__(self) -> "BeaconGraphQL":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager, closing HTTP client."""
        self.close()

    def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self.client:
            self.client.close()

    def _query(
        self, query: str, variables: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a GraphQL query.

        Args:
            query: GraphQL query string
            variables: Optional query variables

        Returns:
            GraphQL response data

        Raises:
            GraphQLError: If the query fails or returns errors
        """
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = self.client.post(
                self.endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            raise GraphQLError(
                f"GraphQL request failed (HTTP {e.response.status_code})"
            ) from e
        except httpx.RequestError as e:
            raise GraphQLError(f"GraphQL request failed: {e}") from e

        # Check for GraphQL errors
        if "errors" in data:
            errors = data["errors"]
            error_msgs = [e.get("message", str(e)) for e in errors]
            raise GraphQLError(f"GraphQL errors: {', '.join(error_msgs)}")

        return data

    def _get_collection_id(self, collection_slug: str) -> str:
        """Get collection ID from slug.

        First checks cache, then queries API if not found.

        Args:
            collection_slug: Collection slug (e.g., "campaign-4")

        Returns:
            Collection ID

        Raises:
            ValidationError: If slug is invalid
            GraphQLError: If collection not found or query fails
        """
        # Validate slug to prevent GraphQL injection
        validated_slug = validate_slug(collection_slug, "collection_slug")

        # Check cache first
        if validated_slug in self.COLLECTION_CACHE:
            return self.COLLECTION_CACHE[validated_slug]

        # Query API - safe to interpolate after validation
        query = f"""
        query GetCollection {{
          Collections(where: {{ slug: {{ equals: "{validated_slug}" }} }}, limit: 1) {{
            docs {{
              id
              name
              slug
            }}
          }}
        }}
        """

        response = self._query(query)
        docs = response.get("data", {}).get("Collections", {}).get("docs", [])

        if not docs:
            raise GraphQLError(f"Collection not found: {collection_slug}")

        collection_id = docs[0]["id"]

        # Cache for future use
        self.COLLECTION_CACHE[collection_slug] = collection_id

        return collection_id

    def get_latest_episode(
        self, collection_slug: str = "campaign-4"
    ) -> dict[str, Any] | None:
        """Get the latest episode from a series.

        Args:
            collection_slug: Series slug (default: "campaign-4")

        Returns:
            Episode metadata dict with keys: id, title, slug, seasonNumber,
            episodeNumber, releaseDate, duration, primaryCollection

        Example:
            >>> client.get_latest_episode("campaign-4")
            {
                "id": "691f59778e6c004863e24ba1",
                "title": "C4 E007 | On the Scent",
                "slug": "c4-e007-on-the-scent",
                "seasonNumber": 4,
                "episodeNumber": 7,
                ...
            }
        """
        try:
            collection_id = self._get_collection_id(collection_slug)
        except (ValidationError, GraphQLError) as e:
            console.print(f"[yellow]⚠️  {e}[/yellow]")
            return None

        # Note: Beacon API requires literal values in where clauses, not variables
        query = f"""
        query GetLatestEpisode {{
          Contents(
            where: {{
              primaryCollection: {{ equals: "{collection_id}" }}
              seasonNumber: {{ not_equals: null }}
              episodeNumber: {{ not_equals: null }}
            }}
            sort: "-releaseDate"
            limit: 1
          ) {{
            docs {{
              id
              title
              slug
              seasonNumber
              episodeNumber
              releaseDate
              duration
              description
              contentType
              primaryCollection {{
                id
                name
                slug
              }}
            }}
          }}
        }}
        """

        try:
            response = self._query(query)
            docs = response.get("data", {}).get("Contents", {}).get("docs", [])
            return docs[0] if docs else None
        except Exception as e:
            console.print(f"[yellow]⚠️  GraphQL query failed: {e}[/yellow]")
            return None

    def get_content_by_slug(self, slug: str) -> dict[str, Any] | None:
        """Get content metadata by URL slug.

        Args:
            slug: Content slug from URL (e.g., "c4-e006-knives-and-thorns")

        Returns:
            Content metadata dict

        Raises:
            ValueError: If slug contains invalid characters

        Example:
            >>> client.get_content_by_slug("c4-e006-knives-and-thorns")
            {
                "id": "6914e32be6f4eb512d3a61f4",
                "title": "C4 E006 | Knives and Thorns",
                "slug": "c4-e006-knives-and-thorns",
                ...
            }
        """
        # Validate slug to prevent GraphQL injection
        validated_slug = validate_slug(slug, "content_slug")

        # Use f-string interpolation (API doesn't support variables in where clauses)
        query = f"""
        query GetContentBySlug {{
          Contents(where: {{ slug: {{ equals: "{validated_slug}" }} }}, limit: 1) {{
            docs {{
              id
              title
              slug
              seasonNumber
              episodeNumber
              releaseDate
              duration
              description
              contentType
              primaryCollection {{
                id
                name
                slug
              }}
            }}
          }}
        }}
        """

        try:
            response = self._query(query)
            docs = response.get("data", {}).get("Contents", {}).get("docs", [])
            return docs[0] if docs else None
        except Exception as e:
            console.print(f"[yellow]⚠️  GraphQL query failed: {e}[/yellow]")
            return None

    def get_series_episodes(
        self, collection_slug: str, episodic_only: bool = True, limit: int = 200
    ) -> list[dict[str, Any]]:
        """Get all episodes in a series.

        Args:
            collection_slug: Series slug (e.g., "campaign-4")
            episodic_only: Only return content with season/episode numbers (default: True)
            limit: Maximum number of episodes to return (default: 200)

        Returns:
            List of episode metadata dicts, sorted by season/episode number

        Example:
            >>> episodes = client.get_series_episodes("campaign-4")
            >>> len(episodes)
            7
            >>> episodes[0]["title"]
            'C4 E001 | The Fall of Thjazi Fang'
        """
        try:
            collection_id = self._get_collection_id(collection_slug)
        except (ValidationError, GraphQLError) as e:
            console.print(f"[yellow]⚠️  {e}[/yellow]")
            return []

        # Build where clause for episodic_only filter
        episodic_filter = ""
        if episodic_only:
            episodic_filter = """
              seasonNumber: { not_equals: null }
              episodeNumber: { not_equals: null }
            """

        query = f"""
        query GetSeriesEpisodes {{
          Contents(
            where: {{
              primaryCollection: {{ equals: "{collection_id}" }}
              {episodic_filter}
            }}
            sort: "seasonNumber,episodeNumber"
            limit: {limit}
          ) {{
            docs {{
              id
              title
              slug
              seasonNumber
              episodeNumber
              releaseDate
              duration
              description
              contentType
            }}
          }}
        }}
        """

        try:
            response = self._query(query)
            return response.get("data", {}).get("Contents", {}).get("docs", [])
        except Exception as e:
            console.print(f"[yellow]⚠️  GraphQL query failed: {e}[/yellow]")
            return []

    def list_collections(self, series_only: bool = True) -> list[dict[str, Any]]:
        """List all available collections/series.

        Args:
            series_only: Only return series (not one-shots/podcasts) (default: True)

        Returns:
            List of collection metadata dicts with keys: id, name, slug, isSeries, itemCount

        Example:
            >>> collections = client.list_collections()
            >>> for c in collections:
            ...     print(f"{c['name']} ({c['itemCount']} episodes)")
        """
        where_clause = ""
        if series_only:
            where_clause = "where: { isSeries: { equals: true } }"

        query = f"""
        query GetCollections {{
          Collections({where_clause} sort: "name", limit: 100) {{
            docs {{
              id
              name
              slug
              isSeries
              isPodcast
              itemCount
              releaseDate
            }}
            totalDocs
          }}
        }}
        """

        try:
            response = self._query(query)
            return response.get("data", {}).get("Collections", {}).get("docs", [])
        except Exception as e:
            console.print(f"[yellow]⚠️  GraphQL query failed: {e}[/yellow]")
            return []

    def get_collection_info(self, collection_slug: str) -> dict[str, Any] | None:
        """Get collection/series metadata.

        Args:
            collection_slug: Collection slug (e.g., "campaign-4")

        Returns:
            Collection metadata dict with keys: id, name, slug, isSeries, itemCount

        Example:
            >>> info = client.get_collection_info("campaign-4")
            >>> print(f"{info['name']}: {info['itemCount']} episodes")
            'Campaign 4: 12 episodes'
        """
        try:
            collection_id = self._get_collection_id(collection_slug)
        except (ValidationError, GraphQLError) as e:
            console.print(f"[yellow]⚠️  {e}[/yellow]")
            return None

        query = f"""
        query GetCollection {{
          Collection(id: "{collection_id}") {{
            id
            name
            slug
            isSeries
            isPodcast
            itemCount
            episodeSortPreference
            releaseDate
          }}
        }}
        """

        try:
            response = self._query(query)
            return response.get("data", {}).get("Collection")
        except Exception as e:
            console.print(f"[yellow]⚠️  GraphQL query failed: {e}[/yellow]")
            return None

    def search(
        self,
        collection_slug: str | None = None,
        content_types: list[str] | None = None,
        search_text: str | None = None,
        sort: str = "-releaseDate",
        limit: int = 20,
        page: int = 1,
    ) -> dict[str, Any]:
        """Search for content with flexible filters.

        This uses the custom `search` query endpoint which provides powerful
        filtering and pagination capabilities.

        Args:
            collection_slug: Optional collection slug to filter by (e.g., "campaign-4")
            content_types: Optional list of content types (e.g., ["videoPodcast", "article"])
            search_text: Optional text to search for in titles/descriptions
            sort: Sort order (default: "-releaseDate" for newest first)
            limit: Maximum results per page (default: 20)
            page: Page number for pagination (default: 1)

        Returns:
            Dict with keys: docs (list of content), totalDocs, page, totalPages

        Example:
            >>> result = client.search(collection_slug="campaign-4", limit=5)
            >>> print(f"Found {result['totalDocs']} episodes")
            >>> for ep in result['docs']:
            ...     print(f"  {ep['title']}")
        """
        # Build query arguments
        args = [f'sort: "{sort}"', f"limit: {limit}", f"page: {page}"]

        if collection_slug:
            try:
                collection_id = self._get_collection_id(collection_slug)
                args.append(f'collection: "{collection_id}"')
            except (ValidationError, GraphQLError) as e:
                console.print(f"[yellow]⚠️  {e}[/yellow]")
                return {"docs": [], "totalDocs": 0, "page": 1, "totalPages": 0}

        if content_types:
            types_str = ", ".join(f'"{t}"' for t in content_types)
            args.append(f"contentTypes: [{types_str}]")

        if search_text:
            # Escape quotes in search text
            escaped_text = search_text.replace('"', '\\"')
            args.append(f'search: "{escaped_text}"')

        args_str = ", ".join(args)

        query = f"""
        query Search {{
          search({args_str}) {{
            docs {{
              id
              title
              slug
              seasonNumber
              episodeNumber
              releaseDate
              duration
              contentType
              description
              primaryCollection {{
                id
                name
                slug
              }}
            }}
            totalDocs
            page
            totalPages
          }}
        }}
        """

        try:
            response = self._query(query)
            return response.get("data", {}).get(
                "search", {"docs": [], "totalDocs": 0, "page": 1, "totalPages": 0}
            )
        except Exception as e:
            console.print(f"[yellow]⚠️  GraphQL search failed: {e}[/yellow]")
            return {"docs": [], "totalDocs": 0, "page": 1, "totalPages": 0}

    def get_latest_content(
        self,
        limit: int = 10,
        episodic_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Get the latest content across all collections.

        Args:
            limit: Maximum number of results (default: 10)
            episodic_only: Only return episodic content with season/episode numbers

        Returns:
            List of content metadata dicts sorted by release date (newest first)

        Example:
            >>> latest = client.get_latest_content(limit=5)
            >>> for content in latest:
            ...     print(f"{content['title']} - {content['primaryCollection']['name']}")
        """
        episodic_filter = ""
        if episodic_only:
            episodic_filter = """
              seasonNumber: { not_equals: null }
              episodeNumber: { not_equals: null }
            """

        where_clause = f"where: {{ {episodic_filter} }}" if episodic_filter else ""

        query = f"""
        query GetLatestContent {{
          Contents(
            {where_clause}
            sort: "-releaseDate"
            limit: {limit}
          ) {{
            docs {{
              id
              title
              slug
              seasonNumber
              episodeNumber
              releaseDate
              duration
              contentType
              primaryCollection {{
                id
                name
                slug
              }}
            }}
          }}
        }}
        """

        try:
            response = self._query(query)
            return response.get("data", {}).get("Contents", {}).get("docs", [])
        except Exception as e:
            console.print(f"[yellow]⚠️  GraphQL query failed: {e}[/yellow]")
            return []

    def count_collection_items(self, collection_slug: str) -> int:
        """Get the number of items in a collection.

        Args:
            collection_slug: Collection slug (e.g., "campaign-4")

        Returns:
            Number of items in the collection

        Example:
            >>> count = client.count_collection_items("campaign-4")
            >>> print(f"Campaign 4 has {count} episodes")
        """
        info = self.get_collection_info(collection_slug)
        if info and "itemCount" in info:
            return int(info["itemCount"])
        return 0
