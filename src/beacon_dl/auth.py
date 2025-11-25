from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright
from rich.console import Console

from .config import settings
from .constants import (
    PLAYWRIGHT_BANNER_TIMEOUT,
    PLAYWRIGHT_CLICK_TIMEOUT,
    PLAYWRIGHT_NAVIGATION_TIMEOUT,
    PLAYWRIGHT_NETWORKIDLE_TIMEOUT,
    PLAYWRIGHT_PAGE_TIMEOUT,
    PLAYWRIGHT_SELECTOR_TIMEOUT,
    PLAYWRIGHT_SSO_TIMEOUT,
)
from .utils import detect_browser_profile

console = Console()


def are_cookies_valid_with_buffer(cookie_file: Path, buffer_hours: int = 6) -> bool:
    """
    Check if cookies are valid and not expiring soon.

    This is used for cookie caching - if cookies are still valid with some buffer
    time remaining, we can skip re-authentication entirely.

    Args:
        cookie_file: Path to Netscape format cookie file
        buffer_hours: Hours before expiration to consider cookies invalid.
                     Default 6 hours provides safety margin.

    Returns:
        True if cookies exist, contain beacon-session, and won't expire within buffer_hours
    """
    if not cookie_file.exists():
        return False

    try:
        with open(cookie_file) as f:
            lines = f.readlines()

        current_time = int(datetime.now().timestamp())
        buffer_seconds = buffer_hours * 3600
        threshold = current_time + buffer_seconds

        beacon_session_found = False
        beacon_tv_cookie_valid = False

        for line in lines:
            if line.startswith("#") or not line.strip():
                continue

            parts = line.strip().split("\t")
            if len(parts) >= 7:
                domain, _, _, _, expires, name, value = parts[:7]

                # Check for beacon-session cookie (the critical auth cookie)
                if name == "beacon-session" and "beacon.tv" in domain:
                    beacon_session_found = True

                    # Session cookies (expires=0) are considered valid
                    if expires != "0":
                        exp_time = int(expires)
                        if exp_time < threshold:
                            if settings.debug:
                                console.print(
                                    f"[yellow]beacon-session cookie expiring within {buffer_hours}h[/yellow]"
                                )
                            return False

                # Track if we have any valid beacon.tv cookies
                if (
                    "beacon.tv" in domain
                    and "members.beacon.tv" not in domain
                    and (expires == "0" or int(expires) > current_time)
                ):
                    beacon_tv_cookie_valid = True

        if not beacon_session_found:
            if settings.debug:
                console.print(
                    "[yellow]No beacon-session cookie found in cache[/yellow]"
                )
            return False

        if not beacon_tv_cookie_valid:
            if settings.debug:
                console.print(
                    "[yellow]No valid beacon.tv cookies found in cache[/yellow]"
                )
            return False

        return True

    except Exception as e:
        if settings.debug:
            console.print(f"[yellow]Cookie cache check error: {e}[/yellow]")
        return False


def validate_cookies(cookie_file: Path) -> bool:
    """
    Validate that the cookie file contains required authentication cookies for BeaconTV.

    This function checks that:
    1. The cookie file exists and is readable
    2. The file contains at least one valid (non-expired) cookie
    3. Cookies are present for the beacon.tv domain (required for content access)

    BeaconTV uses two domains:
    - members.beacon.tv: Authentication and login
    - beacon.tv: Content access (videos)

    Both sets of cookies may be present, but beacon.tv cookies are required for
    downloading content.

    Args:
        cookie_file: Path to the Netscape format cookie file

    Returns:
        True if cookies appear valid and contain beacon.tv domain cookies, False otherwise

    Example:
        >>> cookie_file = Path("beacon_cookies.txt")
        >>> if validate_cookies(cookie_file):
        ...     print("Cookies are valid")
        ... else:
        ...     print("Cookie validation failed")
    """
    if not cookie_file.exists():
        console.print(f"[red]❌ Cookie file not found: {cookie_file}[/red]")
        return False

    try:
        with open(cookie_file) as f:
            lines = f.readlines()

        # Filter out comments and empty lines
        cookie_lines = [
            line for line in lines if line.strip() and not line.startswith("#")
        ]

        if not cookie_lines:
            console.print("[red]❌ Cookie file is empty (no valid cookies found)[/red]")
            return False

        # Parse cookies to check domains and expiration
        beacon_tv_cookies = []
        members_beacon_tv_cookies = []
        expired_count = 0
        current_time = int(datetime.now().timestamp())

        for line in cookie_lines:
            parts = line.strip().split("\t")
            if len(parts) >= 7:
                domain, _, _, _, expires, name, value = parts[:7]

                # Check if cookie is expired
                if expires != "0" and int(expires) < current_time:
                    expired_count += 1
                    continue

                if "beacon.tv" in domain and "members.beacon.tv" not in domain:
                    beacon_tv_cookies.append((name, value))
                elif "members.beacon.tv" in domain:
                    members_beacon_tv_cookies.append((name, value))

        # Validation checks
        console.print("[blue]Cookie validation:[/blue]")
        console.print(f"[blue]  ✓ Total cookies: {len(cookie_lines)}[/blue]")
        console.print(f"[blue]  ✓ beacon.tv cookies: {len(beacon_tv_cookies)}[/blue]")
        console.print(
            f"[blue]  ✓ members.beacon.tv cookies: {len(members_beacon_tv_cookies)}[/blue]"
        )

        if expired_count > 0:
            console.print(f"[yellow]  ⚠️  Expired cookies: {expired_count}[/yellow]")

        # We need cookies from the main beacon.tv domain for content access
        if len(beacon_tv_cookies) == 0:
            console.print("[red]❌ No cookies found for beacon.tv domain![/red]")
            console.print("[red]Authentication may fail when accessing content.[/red]")
            return False

        console.print("[green]✓ Cookie validation passed[/green]")
        return True

    except Exception as e:
        console.print(f"[red]❌ Error validating cookies: {e}[/red]")
        return False


def get_cookie_file() -> Path | None:
    """
    Get the cookie file path, using cached cookies if valid.

    This function implements cookie caching to avoid re-authentication on every run:
    1. If username/password provided AND valid cached cookies exist -> use cache
    2. If username/password provided AND no valid cache -> perform login
    3. If no credentials -> return existing cookie file if it exists

    The cookie cache is considered valid if:
    - beacon_cookies.txt exists
    - Contains beacon-session cookie
    - Cookie won't expire within cookie_expiry_buffer_hours (default 6h)

    Returns:
        Path to cookie file if available, None otherwise

    Example:
        >>> cookie_file = get_cookie_file()
        >>> if cookie_file and cookie_file.exists():
        ...     print(f"Using cookies from {cookie_file}")
    """
    cookie_file = Path("beacon_cookies.txt")

    # If username and password provided, check cache before logging in
    if settings.beacon_username and settings.beacon_password:
        # Check if valid cached cookies exist first
        if cookie_file.exists():
            buffer = getattr(settings, "cookie_expiry_buffer_hours", 6)
            if are_cookies_valid_with_buffer(cookie_file, buffer_hours=buffer):
                console.print("[green]✓ Using cached cookies (still valid)[/green]")
                return cookie_file
            else:
                console.print(
                    "[yellow]Cached cookies invalid or expiring soon[/yellow]"
                )

        # Cookies missing, invalid, or expiring - perform login
        console.print("[blue]Logging in with Playwright to get fresh cookies...[/blue]")
        cookie_file = login_and_get_cookies(
            username=settings.beacon_username, password=settings.beacon_password
        )
        return cookie_file

    # Otherwise, return existing cookie file if it exists
    if cookie_file.exists():
        return cookie_file

    return None


def _dismiss_cookie_banner(page) -> None:
    """Attempt to dismiss cookie consent banner if present.

    This is a non-blocking operation - if the banner isn't found
    or clicking fails, we silently continue.

    Args:
        page: Playwright page object
    """
    try:
        accept_button = page.locator(
            "button:has-text('Accept'), "
            "button:has-text('I Agree'), "
            "button:has-text('I Accept'), "
            "button:has-text('Accept All')"
        )
        if accept_button.count() > 0:
            accept_button.first.click(timeout=PLAYWRIGHT_BANNER_TIMEOUT)
    except Exception:
        pass  # Cookie banner might not appear or click timed out


def _perform_members_login(page, username: str, password: str) -> None:
    """Perform login flow on members.beacon.tv.

    Args:
        page: Playwright page object (should be on login page)
        username: User's email address
        password: User's password

    Raises:
        Exception: If any step of the login process fails
    """
    # Step 1: Enter Email
    console.print("Entering email...")
    page.wait_for_selector("#session_email", timeout=PLAYWRIGHT_SELECTOR_TIMEOUT)
    page.fill("#session_email", username)

    if settings.debug:
        console.print("[dim]Email filled[/dim]")

    # Step 2: Click Continue button and wait for password field
    console.print("Clicking continue button...")
    page.click(".btn-branding")
    page.wait_for_selector("#session_password", timeout=PLAYWRIGHT_SELECTOR_TIMEOUT)

    if settings.debug:
        console.print("[dim]Continue clicked, password field ready[/dim]")

    # Step 3: Enter password
    console.print("Entering password...")
    page.fill("#session_password", password)

    if settings.debug:
        console.print("[dim]Password filled[/dim]")

    # Step 4: Click Sign In button
    console.print("Clicking sign in button...")
    page.click(".btn-branding")

    if settings.debug:
        console.print("[dim]Sign in button clicked[/dim]")

    # Step 5: Wait for redirect to complete
    console.print("Waiting for login redirect...")
    page.wait_for_url(
        lambda url: "sign_in" not in url, timeout=PLAYWRIGHT_NAVIGATION_TIMEOUT
    )
    page.wait_for_load_state("networkidle", timeout=PLAYWRIGHT_NETWORKIDLE_TIMEOUT)

    if settings.debug:
        console.print(f"[dim]Current URL after login: {page.url}[/dim]")
        page.screenshot(path="debug_04_after_login.png")

    console.print("[green]Login successful on members.beacon.tv[/green]")


def _establish_beacon_session(page) -> None:
    """Navigate to beacon.tv and establish SSO session.

    Args:
        page: Playwright page object (should be logged into members.beacon.tv)
    """
    console.print("[yellow]Establishing session on beacon.tv...[/yellow]")

    # Navigate to homepage
    page.goto(
        "https://beacon.tv",
        wait_until="domcontentloaded",
        timeout=PLAYWRIGHT_PAGE_TIMEOUT,
    )
    page.wait_for_load_state("networkidle", timeout=PLAYWRIGHT_NETWORKIDLE_TIMEOUT)

    # Check if already logged in
    already_logged_in = (
        page.locator(
            "[data-testid='user-menu'], .user-avatar, .profile-link, .account-menu"
        ).count()
        > 0
    )

    if not already_logged_in:
        # Click Login button to trigger SSO
        try:
            login_button = page.locator(
                "a:has-text('Login'), button:has-text('Login')"
            ).first
            login_button.click(timeout=PLAYWRIGHT_CLICK_TIMEOUT)
            page.wait_for_load_state("networkidle", timeout=PLAYWRIGHT_SSO_TIMEOUT)
            console.print("[green]✓ SSO completed[/green]")
        except Exception as e:
            if settings.debug:
                console.print(f"[dim]Login button not found: {e}[/dim]")
    else:
        console.print("[green]✓ Already authenticated via SSO[/green]")


def login_and_get_cookies(
    username: str, password: str, target_url: str | None = None
) -> Path:
    """
    Log in to BeaconTV using Playwright and save authentication cookies to a Netscape format file.

    This function performs a complete authentication flow:
    1. Launches Chromium browser (headless by default, visible in debug mode)
    2. Navigates to members.beacon.tv login page
    3. Enters username and password
    4. Waits for successful login to members.beacon.tv
    5. Navigates to beacon.tv homepage to trigger cross-domain cookies
    6. Navigates to beacon.tv/content to ensure content-specific cookies are set
    7. Optionally navigates to a target URL if provided
    8. Extracts all cookies from both domains (members.beacon.tv and beacon.tv)
    9. Writes cookies to Netscape format file for yt-dlp compatibility
    10. Validates the cookies contain required authentication tokens

    The function handles cross-domain authentication, which is critical because BeaconTV
    uses members.beacon.tv for login but beacon.tv for content access.

    Args:
        username: BeaconTV account username or email address
        password: BeaconTV account password
        target_url: Optional specific content URL to navigate to after login.
                   Useful for ensuring all content-specific cookies are captured.
                   If None, only navigates to homepage and /content.

    Returns:
        Path to the Netscape format cookie file (beacon_cookies.txt)

    Raises:
        Exception: If login fails (invalid credentials, network error, timeout, etc.)
                  A screenshot (login_error.png) is saved on failure.

    Example:
        >>> cookie_file = login_and_get_cookies(
        ...     username="user@example.com",
        ...     password="mypassword",
        ...     target_url="https://beacon.tv/content/c4-e007"
        ... )
        >>> print(f"Cookies saved to: {cookie_file}")

    Note:
        - Runs headless by default (headless=True) unless DEBUG=true is set
        - Creates a persistent browser profile in ./playwright_profile directory
        - Overwrites existing cookie file on each run to ensure fresh session
        - Uses browser automation detection bypass flags
    """
    cookie_file = Path("beacon_cookies.txt")

    console.print("[yellow]Logging in to Beacon TV via Playwright...[/yellow]")

    # Keep browser profile between runs for faster subsequent logins
    user_data_dir = Path("playwright_profile")
    user_data_dir.mkdir(exist_ok=True)

    with sync_playwright() as p:
        # Launch browser with persistent context to save cookies
        # Run headless by default unless debug mode is enabled
        headless_mode = not settings.debug

        if settings.debug:
            console.print(f"[dim]Launching Chromium (headless={headless_mode})[/dim]")

        context = p.chromium.launch_persistent_context(
            str(user_data_dir),
            headless=headless_mode,  # Headless by default, visible in debug mode
            args=["--disable-blink-features=AutomationControlled"],
            user_agent=settings.user_agent,
        )
        page = context.new_page()

        try:
            # Navigate to login page
            console.print("[yellow]Navigating to login page...[/yellow]")
            page.goto(
                "https://members.beacon.tv/auth/sign_in",
                wait_until="domcontentloaded",
                timeout=PLAYWRIGHT_PAGE_TIMEOUT,
            )

            if settings.debug:
                console.print(f"[dim]Current URL: {page.url}[/dim]")
                screenshot_path = "debug_01_login_page.png"
                page.screenshot(path=screenshot_path)
                import os

                os.chmod(screenshot_path, 0o600)
                console.print("[dim]Screenshot: debug_01_login_page.png[/dim]")

            # Perform login on members.beacon.tv
            _perform_members_login(page, username, password)

            # Handle cookie consent banner if present
            _dismiss_cookie_banner(page)

            # Navigate to beacon.tv and establish SSO session
            _establish_beacon_session(page)

            # Navigate to target URL if provided
            if target_url:
                console.print(f"[yellow]Navigating to: {target_url}[/yellow]")
                page.goto(
                    target_url,
                    wait_until="domcontentloaded",
                    timeout=PLAYWRIGHT_PAGE_TIMEOUT,
                )
                page.wait_for_load_state(
                    "networkidle", timeout=PLAYWRIGHT_NETWORKIDLE_TIMEOUT
                )

            # Extract ALL cookies from the persistent context
            console.print("Extracting cookies from all beacon.tv domains...")
            cookies = context.cookies()

            # Debug: Show which domains we got cookies from
            domains = set(cookie["domain"] for cookie in cookies)
            console.print(
                f"[blue]Found cookies from domains: {', '.join(sorted(domains))}[/blue]"
            )

            # Write cookies to Netscape format
            _write_netscape_cookies(cookies, cookie_file)

            console.print(
                f"[green]✓ Login successful! Cookies saved to {cookie_file}[/green]"
            )
            console.print(
                f"[blue]Extracted {len(cookies)} total cookies from authenticated session[/blue]"
            )

            # Validate the cookies to ensure authentication will work
            if not validate_cookies(cookie_file):
                console.print("[red]⚠️  Warning: Cookie validation failed![/red]")
                console.print("[red]Authentication may not work properly.[/red]")
                console.print("[yellow]This could mean:[/yellow]")
                console.print(
                    "[yellow]  1. Login succeeded but cookies weren't set for beacon.tv domain[/yellow]"
                )
                console.print(
                    "[yellow]  2. Try running again - sometimes cookies take time to propagate[/yellow]"
                )
                console.print(
                    "[yellow]  3. Consider using browser cookies instead (fallback method)[/yellow]"
                )

        except Exception as e:
            console.print(f"[red]Login failed: {e}[/red]")
            page.screenshot(path="login_error.png")
            # Clear browser profile on failure to force fresh session next time
            import shutil

            shutil.rmtree(user_data_dir, ignore_errors=True)
            console.print(
                "[yellow]Browser profile cleared - will retry with fresh session[/yellow]"
            )
            raise e
        finally:
            context.close()

    return cookie_file


def _write_netscape_cookies(cookies: list[dict[str, Any]], path: Path) -> None:
    """
    Write Playwright cookies to Netscape HTTP Cookie File format.

    This function converts Playwright's cookie format to the Netscape cookie format
    that yt-dlp expects. Only beacon.tv related cookies are written to the file.

    Netscape cookie format (tab-separated):
    domain  flag  path  secure  expiration  name  value

    Where:
    - domain: The domain for which the cookie is valid
    - flag: TRUE if domain starts with '.', FALSE otherwise
    - path: The path for which the cookie is valid
    - secure: TRUE if cookie requires HTTPS, FALSE otherwise
    - expiration: Unix timestamp when cookie expires (0 for session cookies)
    - name: Cookie name
    - value: Cookie value

    Args:
        cookies: List of cookie dictionaries from Playwright context.cookies()
                Each cookie dict contains: domain, path, secure, expires, name, value
        path: Path where the Netscape format cookie file will be written

    Returns:
        None

    Example:
        >>> cookies = context.cookies()  # From Playwright
        >>> _write_netscape_cookies(cookies, Path("cookies.txt"))

    Note:
        - Only cookies containing "beacon.tv" in domain are written
        - Filters out cookies from other domains
        - Prints summary of cookies written to console
    """
    # Filter for beacon.tv related cookies only
    beacon_cookies = [c for c in cookies if "beacon.tv" in c["domain"]]

    # Count cookies by domain for debugging
    members_count = sum(1 for c in beacon_cookies if "members.beacon.tv" in c["domain"])
    main_count = sum(
        1 for c in beacon_cookies if c["domain"] in ["beacon.tv", ".beacon.tv"]
    )

    console.print(
        f"[blue]Writing {len(beacon_cookies)} beacon.tv cookies to file:[/blue]"
    )
    console.print(f"[blue]  - {members_count} from members.beacon.tv[/blue]")
    console.print(f"[blue]  - {main_count} from beacon.tv[/blue]")

    # Create file with secure permissions to prevent race condition
    import os

    old_umask = os.umask(0o077)  # Temporarily set restrictive umask

    try:
        with open(path, "w") as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write("# This file is generated by beacon-tv-downloader\n")
            f.write("# Contains cookies from all beacon.tv domains\n\n")

            for cookie in beacon_cookies:
                domain = cookie["domain"]
                flag = "TRUE" if domain.startswith(".") else "FALSE"
                path_str = cookie["path"]
                secure = "TRUE" if cookie["secure"] else "FALSE"
                expires = (
                    str(int(cookie["expires"]))
                    if "expires" in cookie and cookie["expires"] != -1
                    else "0"
                )
                name = cookie["name"]
                value = cookie["value"]

                # Write cookie in Netscape format
                f.write(
                    f"{domain}\t{flag}\t{path_str}\t{secure}\t{expires}\t{name}\t{value}\n"
                )
    finally:
        os.umask(old_umask)  # Restore original umask

    # Ensure file has secure permissions (owner read/write only)
    os.chmod(path, 0o600)


def get_auth_args(target_url: str | None = None) -> list[str]:
    """
    Get yt-dlp command-line arguments for BeaconTV authentication.

    This function determines the best authentication method based on available
    configuration and returns the appropriate yt-dlp arguments.

    Authentication Priority (in order):

    1. **Playwright Login** (RECOMMENDED, PRIMARY METHOD):
       - Used when: BEACON_USERNAME and BEACON_PASSWORD are set
       - Method: Launches Chromium, logs in, captures cookies from both domains
       - Returns: ["--cookies", "beacon_cookies.txt"]
       - Advantages: Docker-compatible, automated, no manual browser login needed
       - Disadvantages: Slower (30-60 seconds for login process)

    2. **Configured Browser Profile** (FALLBACK):
       - Used when: BROWSER_PROFILE environment variable is set
       - Method: Extracts cookies directly from specified browser
       - Returns: ["--cookies-from-browser", "firefox:default"] (example)
       - Advantages: Fast, uses existing browser session
       - Disadvantages: Requires manual browser login, not Docker-compatible

    3. **Auto-detected Browser Profile** (LAST RESORT):
       - Used when: No credentials or browser profile configured
       - Method: Auto-detects browser (Zen → Firefox → Chrome) and extracts cookies
       - Returns: ["--cookies-from-browser", "chrome:Default"] (example)
       - Advantages: Zero configuration for local development
       - Disadvantages: Requires manual browser login, may fail if no browser found

    4. **No Authentication**:
       - Used when: None of the above methods available
       - Returns: [] (empty list)
       - Result: Download will fail for members-only content

    Args:
        target_url: Optional specific BeaconTV content URL to navigate to during
                   Playwright login. If provided, ensures content-specific cookies
                   are captured. Only used with Playwright authentication.

    Returns:
        List of yt-dlp command-line arguments for authentication.
        Examples:
        - ["--cookies", "beacon_cookies.txt"] for Playwright
        - ["--cookies-from-browser", "firefox:default"] for browser cookies
        - [] if no authentication available

    Example:
        >>> auth_args = get_auth_args(target_url="https://beacon.tv/content/c4-e007")
        >>> ydl_opts = {
        ...     "format": "best",
        ...     "outtmpl": "video.mp4",
        ... }
        >>> # Add auth args to yt-dlp command
        >>> # Example: yt-dlp --cookies beacon_cookies.txt <url>

    Note:
        - Prints colored status messages to console indicating which method is used
        - For Playwright: Shows "🔐 Authenticating with Playwright"
        - For fallback: Shows "⚠️  Falling back to browser cookies"
        - For no auth: Shows "❌ Error: No authentication method configured!"
    """
    # FIRST PRIORITY: Playwright login with username/password (Docker-compatible)
    if settings.beacon_username and settings.beacon_password:
        console.print(
            "[blue]🔐 Authenticating with Playwright (username/password)[/blue]"
        )
        console.print(
            "[blue]This is the recommended method for Docker and automated environments.[/blue]"
        )
        cookie_file = login_and_get_cookies(
            settings.beacon_username, settings.beacon_password, target_url
        )
        return ["--cookies", str(cookie_file)]

    # SECOND PRIORITY: Explicitly configured browser profile
    if settings.browser_profile:
        console.print(
            f"[yellow]⚠️  Falling back to browser cookies: {settings.browser_profile}[/yellow]"
        )
        console.print(
            "[yellow]Consider using --username and --password for better reliability.[/yellow]"
        )
        return ["--cookies-from-browser", settings.browser_profile]

    # THIRD PRIORITY: Auto-detect browser profile
    detected = detect_browser_profile()
    if detected:
        console.print(
            f"[yellow]⚠️  Falling back to auto-detected browser: {detected}[/yellow]"
        )
        console.print(
            "[yellow]Consider using --username and --password for better reliability.[/yellow]"
        )
        return ["--cookies-from-browser", detected]

    # NO AUTHENTICATION AVAILABLE
    console.print("[red]❌ Error: No authentication method configured![/red]")
    console.print("[yellow]Please choose one of the following:[/yellow]")
    console.print(
        "[yellow]  1. Provide credentials: --username user@example.com --password yourpassword (recommended)[/yellow]"
    )
    console.print(
        "[yellow]  2. Log into BeaconTV in your browser (Firefox/Chrome/Zen)[/yellow]"
    )
    console.print(
        "[yellow]  3. Set environment variables: BEACON_USERNAME and BEACON_PASSWORD[/yellow]"
    )
    return []
