"""Content fetching and parsing for beacon.tv.

This module handles fetching content pages and extracting video/subtitle URLs
from the embedded __NEXT_DATA__ JSON. This replaces the yt-dlp-based metadata
extraction with direct HTTP requests.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

import httpx
from rich.console import Console

from .config import settings
from .constants import LANGUAGE_TO_ISO_MAP
from .utils import load_cookies

console = Console()

# HTTP client with retry support
DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
DEFAULT_TRANSPORT = httpx.HTTPTransport(retries=3)


@dataclass
class VideoSource:
    """A video source with URL and metadata."""

    url: str
    label: str  # e.g., "1080p", "720p"
    width: int
    height: int
    bitrate: int
    file_type: str  # e.g., "video/mp4"


@dataclass
class SubtitleTrack:
    """A subtitle track with URL and metadata."""

    url: str
    label: str  # e.g., "English", "Spanish"
    language: str  # ISO code derived from label


@dataclass
class ContentMetadata:
    """Metadata for a piece of content."""

    id: str
    title: str
    slug: str
    season_number: int | None
    episode_number: int | None
    duration: int | None  # milliseconds
    description: str | None
    collection_name: str | None  # Series name


@dataclass
class VideoContent:
    """Complete video content with all sources and subtitles."""

    metadata: ContentMetadata
    sources: list[VideoSource]
    subtitles: list[SubtitleTrack]
    hls_url: str | None  # M3U8 manifest URL


def fetch_content_page(slug: str, cookie_file: Path) -> str | None:
    """Fetch a content page from beacon.tv.

    Args:
        slug: Content slug (e.g., "c4-e007-on-the-scent")
        cookie_file: Path to Netscape format cookie file

    Returns:
        HTML content of the page, or None if fetch failed
    """
    cookies = load_cookies(cookie_file)

    if not cookies.get("beacon-session"):
        console.print("[red]❌ No beacon-session cookie found![/red]")
        console.print(
            "[yellow]Please authenticate first with --username and --password[/yellow]"
        )
        return None

    url = f"https://beacon.tv/content/{slug}"
    console.print(f"[dim]Fetching {url}...[/dim]")

    try:
        with httpx.Client(
            timeout=DEFAULT_TIMEOUT,
            transport=DEFAULT_TRANSPORT,
            cookies=cookies,
            headers={"User-Agent": settings.user_agent},
            follow_redirects=True,
        ) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.text
    except httpx.HTTPStatusError as e:
        console.print(
            f"[red]❌ Failed to fetch content page (HTTP {e.response.status_code}): {e}[/red]"
        )
        return None
    except httpx.RequestError as e:
        console.print(f"[red]❌ Failed to fetch content page: {e}[/red]")
        return None


def parse_next_data(html: str) -> dict | None:
    """Extract and parse __NEXT_DATA__ from HTML.

    Args:
        html: HTML content of the page

    Returns:
        Parsed JSON data, or None if not found
    """
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
        html,
    )

    if not match:
        # Check for Cloudflare challenge
        if "security check" in html.lower() or "cf_chl" in html:
            console.print("[red]❌ Cloudflare challenge detected![/red]")
            console.print(
                "[yellow]Your session may have expired. Please re-authenticate.[/yellow]"
            )
        else:
            console.print("[red]❌ __NEXT_DATA__ not found in page[/red]")
        return None

    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as e:
        console.print(f"[red]❌ Failed to parse __NEXT_DATA__: {e}[/red]")
        return None


def extract_video_content(next_data: dict, slug: str) -> VideoContent | None:
    """Extract video content from parsed __NEXT_DATA__.

    Args:
        next_data: Parsed __NEXT_DATA__ JSON
        slug: Content slug to find

    Returns:
        VideoContent with all sources and subtitles, or None if not found
    """
    page_props = next_data.get("props", {}).get("pageProps", {})
    apollo = page_props.get("__APOLLO_STATE__", {})

    if not apollo:
        console.print("[red]❌ Apollo state not found in page data[/red]")
        return None

    # Find the content by slug
    content_data = None
    for _key, value in apollo.items():
        if isinstance(value, dict) and value.get("slug") == slug:
            content_data = value
            break

    if not content_data:
        console.print(f"[red]❌ Content with slug '{slug}' not found[/red]")
        return None

    # Extract metadata
    title = content_data.get("title", "")

    # Try to get season/episode from API, fallback to parsing title
    season_number = _safe_int(content_data.get("seasonNumber"))
    episode_number = _safe_int(content_data.get("episodeNumber"))

    if season_number is None or episode_number is None:
        parsed_season, parsed_episode = _parse_season_episode(title)
        if season_number is None:
            season_number = parsed_season
        if episode_number is None:
            episode_number = parsed_episode

    metadata = ContentMetadata(
        id=content_data.get("id", ""),
        title=title,
        slug=slug,
        season_number=season_number,
        episode_number=episode_number,
        duration=_safe_int(content_data.get("duration")),
        description=content_data.get("description"),
        collection_name=_extract_collection_name(content_data, apollo),
    )

    # Extract video data from contentVideo
    content_video = content_data.get("contentVideo")
    if not content_video:
        console.print("[red]❌ No video data found for this content[/red]")
        return None

    video = content_video.get("video")
    if not video:
        console.print("[red]❌ Video object is empty[/red]")
        return None

    # Parse videoData JSON string
    video_data_str = video.get("videoData")
    if not video_data_str:
        console.print("[red]❌ videoData is empty[/red]")
        return None

    try:
        video_data = json.loads(video_data_str)
    except json.JSONDecodeError as e:
        console.print(f"[red]❌ Failed to parse videoData: {e}[/red]")
        return None

    # Extract sources and subtitles from playlist
    playlist = video_data.get("playlist", [])
    if not playlist:
        console.print("[red]❌ No playlist found in video data[/red]")
        return None

    playlist_item = playlist[0]

    # Parse sources
    sources = []
    hls_url = None
    for source in playlist_item.get("sources", []):
        file_type = source.get("type", "")

        # HLS manifest
        if "mpegurl" in file_type.lower():
            hls_url = source.get("file")
            continue

        # Skip audio-only
        if file_type == "audio/mp4":
            continue

        # Video source
        if source.get("file") and source.get("width"):
            sources.append(
                VideoSource(
                    url=source["file"],
                    label=source.get("label", ""),
                    width=source.get("width", 0),
                    height=source.get("height", 0),
                    bitrate=source.get("bitrate", 0),
                    file_type=file_type,
                )
            )

    # Sort by height (resolution) descending
    sources.sort(key=lambda s: s.height, reverse=True)

    # Parse subtitles
    subtitles = []
    for track in playlist_item.get("tracks", []):
        if track.get("kind") == "captions":
            label = track.get("label", "Unknown")
            subtitles.append(
                SubtitleTrack(
                    url=track.get("file", ""),
                    label=label,
                    language=_label_to_iso(label),
                )
            )

    return VideoContent(
        metadata=metadata,
        sources=sources,
        subtitles=subtitles,
        hls_url=hls_url,
    )


def get_video_content(slug: str, cookie_file: Path) -> VideoContent | None:
    """Fetch and parse video content for a given slug.

    This is the main entry point for getting video content.

    Args:
        slug: Content slug (e.g., "c4-e007-on-the-scent")
        cookie_file: Path to Netscape format cookie file

    Returns:
        VideoContent with all sources and subtitles, or None if failed
    """
    html = fetch_content_page(slug, cookie_file)
    if not html:
        return None

    next_data = parse_next_data(html)
    if not next_data:
        return None

    return extract_video_content(next_data, slug)


def _safe_int(value) -> int | None:
    """Safely convert a value to int."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _parse_season_episode(title: str) -> tuple[int | None, int | None]:
    """Parse season and episode numbers from title.

    Handles formats like:
    - "C4 E007 | On the Scent" -> (4, 7)
    - "S04E07 - Title" -> (4, 7)
    - "S04E07: Title" -> (4, 7)
    - "S04E07 Title" -> (4, 7)
    - "4x07 - Title" -> (4, 7)

    Args:
        title: Video title

    Returns:
        Tuple of (season_number, episode_number), either may be None
    """
    # "C4 E007 | Title"
    match = re.match(r"C(\d+)\s+E(\d+)", title)
    if match:
        return int(match.group(1)), int(match.group(2))

    # "S04E07" formats
    match = re.match(r"S(\d+)E(\d+)", title)
    if match:
        return int(match.group(1)), int(match.group(2))

    # "4x07" format
    match = re.match(r"(\d+)x(\d+)", title)
    if match:
        return int(match.group(1)), int(match.group(2))

    return None, None


def _extract_collection_name(content_data: dict, apollo: dict) -> str | None:
    """Extract collection/series name from content data."""
    collection = content_data.get("primaryCollection")
    if not collection:
        return None

    # Could be a direct object or a reference
    if isinstance(collection, dict):
        if "__ref" in collection:
            # Follow reference
            ref_key = collection["__ref"]
            ref_data = apollo.get(ref_key, {})
            return ref_data.get("name")
        return collection.get("name")

    return None


def _label_to_iso(label: str) -> str:
    """Convert subtitle label to ISO 639-2 language code.

    Uses the centralized LANGUAGE_TO_ISO_MAP from constants.py.
    """
    return LANGUAGE_TO_ISO_MAP.get(label.lower(), "und")
