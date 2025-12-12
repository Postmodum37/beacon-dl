"""Browser installation utilities for automatic Chromium setup.

This module handles automatic detection and installation of Playwright
browsers (specifically Chromium) for uvx/pip users who haven't run
'playwright install chromium' manually.
"""

import subprocess
import sys
from pathlib import Path

from rich.console import Console

console = Console()


def get_playwright_cache_dir() -> Path:
    """Get the platform-specific Playwright browser cache directory.

    Returns:
        Path to the ms-playwright cache directory for the current platform
    """
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "ms-playwright"
    elif sys.platform == "win32":
        return Path.home() / "AppData" / "Local" / "ms-playwright"
    else:  # Linux and others
        return Path.home() / ".cache" / "ms-playwright"


def is_chromium_installed() -> bool:
    """Check if Playwright Chromium browser is installed for current version.

    Note: This is a simple heuristic check. For reliability, ensure_chromium_installed()
    will always verify the installation is correct for the current Playwright version.

    Returns:
        True if chromium directories exist in playwright cache (may still need update).
    """
    cache_dir = get_playwright_cache_dir()
    if not cache_dir.exists():
        return False

    # Quick check for any chromium installation
    # Note: This doesn't verify version compatibility - ensure_chromium_installed handles that
    chromium_dirs = list(cache_dir.glob("chromium-*"))
    headless_shell_dirs = list(cache_dir.glob("chromium_headless_shell-*"))
    return len(chromium_dirs) > 0 and len(headless_shell_dirs) > 0


def ensure_chromium_installed() -> bool:
    """Ensure Chromium is installed for the current Playwright version.

    This always runs `playwright install chromium` to handle version mismatches
    between different Playwright installations. The command is idempotent and
    exits quickly if the correct browser version is already installed.

    Returns:
        True if chromium is available (was installed or already present)

    Raises:
        RuntimeError: If installation fails
    """
    # Quick heuristic check - if nothing installed, show user-friendly message
    first_install = not is_chromium_installed()

    if first_install:
        console.print(
            "[yellow]Chromium browser not found. Installing automatically...[/yellow]"
        )
        console.print("[dim]This is a one-time setup that may take a minute.[/dim]")

    try:
        # Always run install to handle version mismatches between Playwright versions
        # The command is idempotent - exits quickly if correct version already installed
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout for slow connections
        )

        if result.returncode != 0:
            console.print(f"[red]Failed to install Chromium: {result.stderr}[/red]")
            raise RuntimeError(
                f"Playwright chromium installation failed: {result.stderr}"
            )

        if first_install:
            console.print("[green]Chromium installed successfully![/green]")
        return True

    except subprocess.TimeoutExpired as err:
        console.print(
            "[red]Chromium installation timed out. Please run manually:[/red]"
        )
        console.print("[yellow]  playwright install chromium[/yellow]")
        raise RuntimeError("Playwright chromium installation timed out") from err
    except FileNotFoundError as err:
        console.print("[red]Playwright CLI not found. Package may be corrupted.[/red]")
        raise RuntimeError("Playwright module not found") from err
