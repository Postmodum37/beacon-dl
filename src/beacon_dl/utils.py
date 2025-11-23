import re
from pathlib import Path
from typing import Optional
from playwright.sync_api import sync_playwright
from rich.console import Console

console = Console()

def sanitize_filename(name: str) -> str:
    """
    Sanitize filename - remove special chars and convert spaces to dots.
    Matches the bash script's logic.
    """
    if not name:
        return "unnamed"
    
    # Remove non-alphanumeric except spaces
    clean = re.sub(r'[^a-zA-Z0-9 ]', '', name)
    # Convert multiple spaces to single space
    clean = re.sub(r' +', ' ', clean)
    # Convert spaces to dots
    clean = clean.replace(' ', '.')
    # Remove leading dots/dashes
    clean = re.sub(r'^[.-]+', '', clean)
    # Limit length
    clean = clean[:200]
    
    if not clean:
        return "unnamed"
        
    return clean

def map_language_to_iso(lang: str) -> str:
    """Map language name to ISO 639-2 code."""
    lang_lower = lang.lower()
    mapping = {
        "english": "eng", "en": "eng",
        "spanish": "spa", "es": "spa", "español": "spa",
        "french": "fre", "fr": "fre", "français": "fre",
        "italian": "ita", "it": "ita", "italiano": "ita",
        "portuguese": "por", "pt": "por", "português": "por",
        "german": "ger", "de": "ger", "deutsch": "ger",
        "japanese": "jpn", "ja": "jpn", "日本語": "jpn",
        "korean": "kor", "ko": "kor", "한국어": "kor",
        "chinese": "chi", "zh": "chi", "中文": "chi",
    }
    return mapping.get(lang_lower, "und")

def detect_browser_profile() -> Optional[str]:
    """Auto-detect browser profile path."""
    home = Path.home()
    
    # Check for Zen browser (Firefox fork) on macOS
    zen_path = home / "Library/Application Support/zen/Profiles"
    if zen_path.exists():
        profiles = list(zen_path.glob("*.default*")) + list(zen_path.glob("*.Default*"))
        if profiles:
            # Sort by modification time, most recent first
            profiles.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return f"firefox:{profiles[0]}"

    # Check for Firefox on macOS
    firefox_path = home / "Library/Application Support/Firefox/Profiles"
    if firefox_path.exists():
        profiles = list(firefox_path.glob("*.default*")) + list(firefox_path.glob("*.Default*"))
        if profiles:
            # Sort by modification time, most recent first
            profiles.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return f"firefox:{profiles[0]}"

    # Check for Chrome on macOS
    chrome_path = home / "Library/Application Support/Google/Chrome"
    if chrome_path.exists():
        return "chrome"

    return None

def get_latest_episode_url(series_url: str = "https://beacon.tv/series/campaign-4") -> str:
    """
    Fetch the latest episode URL from a Beacon TV series page.

    Args:
        series_url: URL of the series page (default: Campaign 4)

    Returns:
        URL of the latest episode
    """
    console.print(f"[blue]Fetching latest episode from {series_url}...[/blue]")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Navigate to series page
            page.goto(series_url, wait_until="domcontentloaded", timeout=30000)

            # Wait for content to load
            page.wait_for_timeout(3000)

            # Find all episode links
            # Beacon TV episode URLs follow the pattern: /content/{slug}
            episode_links = page.locator('a[href^="/content/"]').all()

            if not episode_links:
                raise ValueError(f"No episodes found on {series_url}")

            # Get the first episode link (usually the latest)
            latest_link = episode_links[0]
            href = latest_link.get_attribute("href")

            if not href:
                raise ValueError("Could not extract episode URL")

            # Construct full URL
            if href.startswith("/"):
                latest_url = f"https://beacon.tv{href}"
            else:
                latest_url = href

            # Try to get episode title for confirmation
            try:
                title = latest_link.text_content() or "Unknown"
                console.print(f"[green]Found latest episode: {title}[/green]")
            except:
                pass

            console.print(f"[green]Latest episode URL: {latest_url}[/green]")
            return latest_url

        except Exception as e:
            console.print(f"[red]Error fetching latest episode: {e}[/red]")
            raise
        finally:
            browser.close()
