"""Utility functions for beacon-dl.

This module provides helper functions for filename sanitization,
language mapping, and cookie loading.
"""

import http.cookiejar
import re
from pathlib import Path

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
