from pathlib import Path
from typing import Optional, Any
from datetime import datetime
from playwright.sync_api import sync_playwright
from rich.console import Console
from .config import settings
from .utils import detect_browser_profile

console = Console()


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
        with open(cookie_file, "r") as f:
            lines = f.readlines()

        # Filter out comments and empty lines
        cookie_lines = [line for line in lines if line.strip() and not line.startswith("#")]

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

                if "beacon.tv" in domain and not "members.beacon.tv" in domain:
                    beacon_tv_cookies.append((name, value))
                elif "members.beacon.tv" in domain:
                    members_beacon_tv_cookies.append((name, value))

        # Validation checks
        console.print(f"[blue]Cookie validation:[/blue]")
        console.print(f"[blue]  ✓ Total cookies: {len(cookie_lines)}[/blue]")
        console.print(f"[blue]  ✓ beacon.tv cookies: {len(beacon_tv_cookies)}[/blue]")
        console.print(f"[blue]  ✓ members.beacon.tv cookies: {len(members_beacon_tv_cookies)}[/blue]")

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

def login_and_get_cookies(username: str, password: str, target_url: Optional[str] = None) -> Path:
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

    # Clear persistent browser context to ensure fresh login
    user_data_dir = Path("playwright_profile")
    if user_data_dir.exists():
        import shutil
        if settings.debug:
            console.print("[dim]Clearing old browser profile for fresh login[/dim]")
        shutil.rmtree(user_data_dir)
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
            user_agent=settings.user_agent
        )
        page = context.new_page()
        
        try:
            # Navigate to login page
            console.print("[yellow]Navigating to login page...[/yellow]")
            page.goto("https://members.beacon.tv/auth/sign_in", wait_until="domcontentloaded", timeout=30000)

            if settings.debug:
                console.print(f"[dim]Current URL: {page.url}[/dim]")
                page.screenshot(path="debug_01_login_page.png")
                console.print("[dim]Screenshot: debug_01_login_page.png[/dim]")

            # Step 1: Enter Email
            console.print("Entering email...")
            page.wait_for_selector("#session_email", timeout=10000)
            page.fill("#session_email", username)

            if settings.debug:
                console.print("[dim]Email filled[/dim]")
                page.screenshot(path="debug_02_email_filled.png")

            # Step 2: Click Continue button
            console.print("Clicking continue button...")
            page.click(".btn-branding")
            page.wait_for_timeout(2000)  # Wait for transition

            if settings.debug:
                console.print("[dim]Continue button clicked[/dim]")

            # Step 3: Wait for password field and enter password
            console.print("Waiting for password field...")
            page.wait_for_selector("#session_password", timeout=10000)

            console.print("Entering password...")
            page.fill("#session_password", password)

            if settings.debug:
                console.print("[dim]Password filled[/dim]")
                page.screenshot(path="debug_03_password_filled.png")

            # Step 4: Click Sign In button
            console.print("Clicking sign in button...")
            page.click(".btn-branding")

            if settings.debug:
                console.print("[dim]Sign in button clicked[/dim]")

            # Step 5: Wait for redirect chain to complete
            # After login, members.beacon.tv redirects through a callback URL
            # that sets the beacon-session cookie on beacon.tv
            console.print("Waiting for login redirect chain to complete...")

            # Wait for any navigation away from sign_in
            page.wait_for_url(lambda url: "sign_in" not in url, timeout=30000)

            # Give time for any redirect callbacks
            page.wait_for_timeout(3000)

            if settings.debug:
                console.print(f"[dim]Current URL after login: {page.url}[/dim]")
                page.screenshot(path="debug_04_after_login.png")

            console.print("[green]Login successful on members.beacon.tv[/green]")

            # Handle cookie consent banner that appears AFTER login
            try:
                console.print("Checking for post-login cookie banner...")
                page.wait_for_timeout(2000)  # Wait for banner to appear
                accept_button = page.locator("button:has-text('Accept'), button:has-text('I Agree'), button:has-text('I Accept'), button:has-text('Accept All')")
                if accept_button.count() > 0:
                    console.print("Accepting cookies...")
                    accept_button.first.click()
                    page.wait_for_timeout(1000)
            except:
                pass  # Cookie banner might not appear

            # CRITICAL: Navigate to beacon.tv and trigger SSO to get beacon-session cookie
            # BeaconTV uses members.beacon.tv for login but beacon.tv for content
            # We need to click "Login" on beacon.tv to establish the session via SSO
            console.print("[yellow]Establishing session on beacon.tv via SSO...[/yellow]")

            # Step 1: Navigate to homepage
            page.goto("https://beacon.tv", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            console.print("[green]✓ Loaded beacon.tv homepage[/green]")

            # Step 2: Click the Login button to trigger SSO
            # Since we're already logged into members.beacon.tv, this will create the beacon-session cookie
            try:
                console.print("[yellow]Clicking Login button to trigger SSO...[/yellow]")
                login_button = page.locator("a:has-text('Login'), button:has-text('Login')").first
                login_button.click(timeout=5000)
                page.wait_for_timeout(5000)  # Wait for SSO to complete
                console.print("[green]✓ SSO completed - beacon-session cookie established[/green]")

                if settings.debug:
                    console.print(f"[dim]Current URL after SSO: {page.url}[/dim]")
                    page.screenshot(path="debug_05_after_sso.png")

            except Exception as e:
                console.print(f"[yellow]⚠️  Could not click Login button (may already be logged in): {e}[/yellow]")

            # Step 3: Navigate to content page to ensure all content cookies are set
            page.goto("https://beacon.tv/content", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            console.print("[green]✓ Loaded beacon.tv/content page[/green]")

            # Step 4: If target URL provided, navigate to it
            if target_url:
                console.print(f"[yellow]Navigating to target URL: {target_url}[/yellow]")
                page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3000)
                console.print("[green]✓ Loaded target content page[/green]")

            # Extract ALL cookies from the persistent context
            console.print("Extracting cookies from all beacon.tv domains...")
            cookies = context.cookies()

            # Debug: Show which domains we got cookies from
            domains = set(cookie["domain"] for cookie in cookies)
            console.print(f"[blue]Found cookies from domains: {', '.join(sorted(domains))}[/blue]")

            # Write cookies to Netscape format
            _write_netscape_cookies(cookies, cookie_file)

            console.print(f"[green]✓ Login successful! Cookies saved to {cookie_file}[/green]")
            console.print(f"[blue]Extracted {len(cookies)} total cookies from authenticated session[/blue]")

            # Validate the cookies to ensure authentication will work
            if not validate_cookies(cookie_file):
                console.print("[red]⚠️  Warning: Cookie validation failed![/red]")
                console.print("[red]Authentication may not work properly.[/red]")
                console.print("[yellow]This could mean:[/yellow]")
                console.print("[yellow]  1. Login succeeded but cookies weren't set for beacon.tv domain[/yellow]")
                console.print("[yellow]  2. Try running again - sometimes cookies take time to propagate[/yellow]")
                console.print("[yellow]  3. Consider using browser cookies instead (fallback method)[/yellow]")

        except Exception as e:
            console.print(f"[red]Login failed: {e}[/red]")
            # Maybe take screenshot?
            page.screenshot(path="login_error.png")
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
    main_count = sum(1 for c in beacon_cookies if c["domain"] in ["beacon.tv", ".beacon.tv"])

    console.print(f"[blue]Writing {len(beacon_cookies)} beacon.tv cookies to file:[/blue]")
    console.print(f"[blue]  - {members_count} from members.beacon.tv[/blue]")
    console.print(f"[blue]  - {main_count} from beacon.tv[/blue]")

    with open(path, "w") as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# This file is generated by beacon-tv-downloader\n")
        f.write("# Contains cookies from all beacon.tv domains\n\n")

        for cookie in beacon_cookies:
            domain = cookie["domain"]
            flag = "TRUE" if domain.startswith(".") else "FALSE"
            path_str = cookie["path"]
            secure = "TRUE" if cookie["secure"] else "FALSE"
            expires = str(int(cookie["expires"])) if "expires" in cookie and cookie["expires"] != -1 else "0"
            name = cookie["name"]
            value = cookie["value"]

            # Write cookie in Netscape format
            f.write(f"{domain}\t{flag}\t{path_str}\t{secure}\t{expires}\t{name}\t{value}\n")

def get_auth_args(target_url: Optional[str] = None) -> list[str]:
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
        console.print("[blue]🔐 Authenticating with Playwright (username/password)[/blue]")
        console.print("[blue]This is the recommended method for Docker and automated environments.[/blue]")
        cookie_file = login_and_get_cookies(
            settings.beacon_username,
            settings.beacon_password,
            target_url
        )
        return ["--cookies", str(cookie_file)]

    # SECOND PRIORITY: Explicitly configured browser profile
    if settings.browser_profile:
        console.print(f"[yellow]⚠️  Falling back to browser cookies: {settings.browser_profile}[/yellow]")
        console.print("[yellow]Consider using --username and --password for better reliability.[/yellow]")
        return ["--cookies-from-browser", settings.browser_profile]

    # THIRD PRIORITY: Auto-detect browser profile
    detected = detect_browser_profile()
    if detected:
        console.print(f"[yellow]⚠️  Falling back to auto-detected browser: {detected}[/yellow]")
        console.print("[yellow]Consider using --username and --password for better reliability.[/yellow]")
        return ["--cookies-from-browser", detected]

    # NO AUTHENTICATION AVAILABLE
    console.print("[red]❌ Error: No authentication method configured![/red]")
    console.print("[yellow]Please choose one of the following:[/yellow]")
    console.print("[yellow]  1. Provide credentials: --username user@example.com --password yourpassword (recommended)[/yellow]")
    console.print("[yellow]  2. Log into BeaconTV in your browser (Firefox/Chrome/Zen)[/yellow]")
    console.print("[yellow]  3. Set environment variables: BEACON_USERNAME and BEACON_PASSWORD[/yellow]")
    return []
