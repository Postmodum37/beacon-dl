"""GraphQL client for BeaconTV API.

This module provides a client for querying the beacon.tv GraphQL API to fetch
content metadata, series information, and episode listings. This replaces
slower Playwright-based web scraping with fast, structured API calls.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import http.cookiejar
import re
import requests
from rich.console import Console

console = Console()


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
        ValueError: If slug contains invalid characters

    Security:
        Only allows alphanumeric characters, hyphens, and underscores.
        Prevents GraphQL injection attacks via malicious slugs.
    """
    if not slug:
        raise ValueError(f"{field_name} cannot be empty")

    # Only allow alphanumeric, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', slug):
        raise ValueError(
            f"Invalid {field_name}: '{slug}'. "
            f"Only alphanumeric characters, hyphens, and underscores are allowed."
        )

    # Prevent excessively long slugs (DoS protection)
    if len(slug) > 200:
        raise ValueError(f"{field_name} too long (max 200 characters)")

    return slug


class BeaconGraphQL:
    """GraphQL client for beacon.tv API.

    Provides methods to query content metadata, series information, and episode
    listings using the beacon.tv GraphQL API. Authenticates using cookies from
    a Netscape HTTP Cookie File.

    Example:
        >>> client = BeaconGraphQL(cookie_file="beacon_cookies.txt")
        >>> latest = client.get_latest_episode("campaign-4")
        >>> print(latest["title"])
        'C4 E007 | On the Scent'
    """

    # Known collection slugs to IDs (cached for performance)
    COLLECTION_CACHE: Dict[str, str] = {
        "campaign-4": "68caf69e7a76bce4b7aa689a",
    }

    def __init__(self, cookie_file: Path | str):
        """Initialize GraphQL client.

        Args:
            cookie_file: Path to Netscape HTTP Cookie File containing beacon-session cookie
        """
        self.endpoint = "https://beacon.tv/api/graphql"
        self.cookies = self._load_cookies(Path(cookie_file))

    def _load_cookies(self, cookie_file: Path) -> Dict[str, str]:
        """Load cookies from Netscape HTTP Cookie File.

        Args:
            cookie_file: Path to cookie file

        Returns:
            Dictionary of cookie name -> value pairs
        """
        jar = http.cookiejar.MozillaCookieJar(str(cookie_file))
        try:
            jar.load(ignore_discard=True, ignore_expires=True)
        except Exception as e:
            console.print(f"[yellow]⚠️  Could not load cookies: {e}[/yellow]")
            return {}

        # Convert cookie jar to dict
        cookies = {}
        for cookie in jar:
            cookies[cookie.name] = cookie.value

        return cookies

    def _query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a GraphQL query.

        Args:
            query: GraphQL query string
            variables: Optional query variables

        Returns:
            GraphQL response data

        Raises:
            requests.HTTPError: If the request fails
        """
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        response = requests.post(
            self.endpoint,
            json=payload,
            cookies=self.cookies,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()

        # Check for GraphQL errors
        if "errors" in data:
            errors = data["errors"]
            error_msgs = [e.get("message", str(e)) for e in errors]
            raise ValueError(f"GraphQL errors: {', '.join(error_msgs)}")

        return data

    def _get_collection_id(self, collection_slug: str) -> str:
        """Get collection ID from slug.

        First checks cache, then queries API if not found.

        Args:
            collection_slug: Collection slug (e.g., "campaign-4")

        Returns:
            Collection ID

        Raises:
            ValueError: If collection not found or slug invalid
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
            raise ValueError(f"Collection not found: {collection_slug}")

        collection_id = docs[0]["id"]

        # Cache for future use
        self.COLLECTION_CACHE[collection_slug] = collection_id

        return collection_id

    def get_latest_episode(self, collection_slug: str = "campaign-4") -> Optional[Dict[str, Any]]:
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
        except ValueError as e:
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

    def get_content_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
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
        self,
        collection_slug: str,
        episodic_only: bool = True,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
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
        except ValueError as e:
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

    def list_collections(self, series_only: bool = True) -> List[Dict[str, Any]]:
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
            where_clause = 'where: { isSeries: { equals: true } }'

        query = f"""
        query GetCollections {{
          Collections({where_clause} sort: "name", limit: 100) {{
            docs {{
              id
              name
              slug
              isSeries
              itemCount
            }}
          }}
        }}
        """

        try:
            response = self._query(query)
            return response.get("data", {}).get("Collections", {}).get("docs", [])
        except Exception as e:
            console.print(f"[yellow]⚠️  GraphQL query failed: {e}[/yellow]")
            return []

    def get_collection_info(self, collection_slug: str) -> Optional[Dict[str, Any]]:
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
        except ValueError as e:
            console.print(f"[yellow]⚠️  {e}[/yellow]")
            return None

        query = f"""
        query GetCollection {{
          Collection(id: "{collection_id}") {{
            id
            name
            slug
            isSeries
            itemCount
          }}
        }}
        """

        try:
            response = self._query(query)
            return response.get("data", {}).get("Collection")
        except Exception as e:
            console.print(f"[yellow]⚠️  GraphQL query failed: {e}[/yellow]")
            return None
