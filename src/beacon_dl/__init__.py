"""Beacon TV Downloader - Download videos from beacon.tv.

This package provides a CLI and Python API for downloading videos from
beacon.tv using direct HTTP requests. No yt-dlp required for downloading.

Key features:
- Direct HTTP downloads (fast, reliable)
- GraphQL API integration for metadata
- Playwright for authentication only (Cloudflare bypass)
- Multiple subtitle tracks support
- Automatic filename generation

Example usage:
    from beacon_dl.downloader import BeaconDownloader
    from beacon_dl.auth import get_cookie_file

    cookie_file = get_cookie_file()
    downloader = BeaconDownloader(cookie_file)
    downloader.download_url("https://beacon.tv/content/c4-e007-on-the-scent")
"""

__version__ = "0.2.0"
