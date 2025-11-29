"""Utility functions for beacon-dl.

This module provides helper functions for filename sanitization,
language mapping, and cookie loading.
"""

import http.cookiejar
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")

from rich.console import Console

from .constants import LANGUAGE_TO_ISO_MAP

console = Console()


def load_cookies(cookie_file: Path) -> dict[str, str]:
    """Load cookies from Netscape format file.

    Args:
        cookie_file: Path to cookie file

    Returns:
        Dictionary of cookie name -> value
    """
    jar = http.cookiejar.MozillaCookieJar(str(cookie_file))
    try:
        jar.load(ignore_discard=True, ignore_expires=True)
    except Exception as e:
        console.print(f"[yellow]⚠️  Could not load cookies: {e}[/yellow]")
        return {}

    cookies = {}
    for cookie in jar:
        cookies[cookie.name] = cookie.value

    return cookies


def sanitize_filename(name: str) -> str:
    """Sanitize filename - remove special chars and convert spaces to dots.

    Args:
        name: Input string to sanitize

    Returns:
        Sanitized string safe for use in filenames

    Example:
        >>> sanitize_filename("C4 E007 | On the Scent")
        'C4.E007.On.the.Scent'
    """
    if not name:
        return "unnamed"

    # Remove non-alphanumeric except spaces
    clean = re.sub(r"[^a-zA-Z0-9 ]", "", name)
    # Convert multiple spaces to single space
    clean = re.sub(r" +", " ", clean)
    # Convert spaces to dots
    clean = clean.replace(" ", ".")
    # Remove leading dots/dashes
    clean = re.sub(r"^[.-]+", "", clean)
    # Limit length
    clean = clean[:200]

    if not clean:
        return "unnamed"

    return clean


def map_language_to_iso(lang: str) -> str:
    """Map language name to ISO 639-2 code.

    Uses the centralized LANGUAGE_TO_ISO_MAP from constants.py.

    Args:
        lang: Language name or code

    Returns:
        ISO 639-2 three-letter language code, or 'und' (undefined) if not found

    Example:
        >>> map_language_to_iso("English")
        'eng'
        >>> map_language_to_iso("español")
        'spa'
    """
    return LANGUAGE_TO_ISO_MAP.get(lang.lower(), "und")


def extract_slug(url_or_slug: str) -> str:
    """Extract slug from URL or return as-is.

    Args:
        url_or_slug: Either a full URL or just the slug

    Returns:
        The extracted slug

    Example:
        >>> extract_slug("https://beacon.tv/content/c4-e007")
        'c4-e007'
        >>> extract_slug("c4-e007")
        'c4-e007'
    """
    if url_or_slug.startswith("http"):
        # Extract from URL like https://beacon.tv/content/c4-e007
        return url_or_slug.split("/content/")[-1].split("?")[0]
    return url_or_slug


def format_duration(seconds: int) -> str:
    """Convert seconds to human-readable duration.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "1h 30m" or "45m"

    Example:
        >>> format_duration(5400)
        '1h 30m'
        >>> format_duration(1800)
        '30m'
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def format_bitrate(kbps: int) -> str:
    """Format bitrate for display.

    Args:
        kbps: Bitrate in kilobits per second

    Returns:
        Formatted string like "5.2 Mbps" or "800 kbps"

    Example:
        >>> format_bitrate(5200)
        '5.2 Mbps'
        >>> format_bitrate(800)
        '800 kbps'
    """
    if kbps >= 1000:
        return f"{kbps / 1000:.1f} Mbps"
    return f"{kbps} kbps"


def format_file_size(size_bytes: int) -> str:
    """Format file size for display.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string like "1.50 GB", "150.0 MB", "500.0 KB", or "0 B"

    Example:
        >>> format_file_size(1_500_000_000)
        '1.50 GB'
        >>> format_file_size(150_000_000)
        '150.0 MB'
        >>> format_file_size(0)
        '0 B'
    """
    if size_bytes <= 0:
        return "0 B"
    if size_bytes < 1_000:
        return f"{size_bytes} B"
    if size_bytes >= 1_000_000_000:
        return f"{size_bytes / 1_000_000_000:.2f} GB"
    elif size_bytes >= 1_000_000:
        return f"{size_bytes / 1_000_000:.1f} MB"
    return f"{size_bytes / 1_000:.1f} KB"


def format_episode_code(season: int | None, episode: int | None) -> str:
    """Format season/episode numbers as 'S##E##' string.

    Args:
        season: Season number (or None)
        episode: Episode number (or None)

    Returns:
        Formatted string like "S04E07", "S?E?", or "-" if both are None

    Example:
        >>> format_episode_code(4, 7)
        'S04E07'
        >>> format_episode_code(None, 5)
        'S?E05'
        >>> format_episode_code(None, None)
        '-'
    """
    if isinstance(season, int) and isinstance(episode, int):
        return f"S{season:02d}E{episode:02d}"
    if season is not None or episode is not None:
        s = f"{season:02d}" if isinstance(season, int) else "?"
        e = f"{episode:02d}" if isinstance(episode, int) else "?"
        return f"S{s}E{e}"
    return "-"


def print_error(msg: str) -> None:
    """Print a standardized error message.

    Args:
        msg: Error message to display
    """
    console.print(f"[red]❌ Error: {msg}[/red]")


def print_warning(msg: str) -> None:
    """Print a standardized warning message.

    Args:
        msg: Warning message to display
    """
    console.print(f"[yellow]⚠️  {msg}[/yellow]")


def print_success(msg: str) -> None:
    """Print a standardized success message.

    Args:
        msg: Success message to display
    """
    console.print(f"[green]✓ {msg}[/green]")


def retry_with_backoff(
    func: Callable[[], T],
    retries: int,
    on_retry: Callable[[int, Exception, float], None] | None = None,
) -> T:
    """Execute function with exponential backoff retry.

    Args:
        func: Function to execute (takes no arguments)
        retries: Number of retry attempts (0 = no retries, just run once)
        on_retry: Optional callback called before each retry with
                  (attempt_number, exception, wait_time)

    Returns:
        Result from successful function call

    Raises:
        Exception: The last exception if all retries fail

    Example:
        >>> def fetch_data():
        ...     return requests.get(url)
        >>> result = retry_with_backoff(fetch_data, retries=3)
    """
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            return func()
        except Exception as e:
            last_error = e
            if attempt < retries:
                wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s, 8s...
                if on_retry:
                    on_retry(attempt, e, wait_time)
                time.sleep(wait_time)

    # This should never happen, but satisfies type checker
    if last_error:
        raise last_error
    raise RuntimeError("Unexpected retry loop exit")
