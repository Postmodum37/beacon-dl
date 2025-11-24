"""CLI entry point for beacon-dl.

This module provides the command-line interface for the BeaconTV downloader.
"""

import typer
from rich.console import Console
from rich.table import Table
from typing import Optional
from pathlib import Path

from .downloader import BeaconDownloader
from .config import settings
from .graphql import BeaconGraphQL
from .auth import get_cookie_file
from .history import DownloadHistory, VerifyResult

app = typer.Typer(
    help="Beacon TV Downloader - Simplified direct download",
    invoke_without_command=True,
    no_args_is_help=False,
)
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Default to download command when no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        # No subcommand provided - run download with defaults
        download(
            url=None,
            username=None,
            password=None,
            browser=None,
            series=None,
            debug=False,
        )


def get_authenticated_cookie_file(
    username: Optional[str] = None,
    password: Optional[str] = None,
    browser: Optional[str] = None,
) -> Path:
    """Get authenticated cookie file, prompting for login if needed.

    Args:
        username: Optional username override
        password: Optional password override
        browser: Optional browser profile override

    Returns:
        Path to cookie file

    Raises:
        typer.Exit: If authentication fails
    """
    # Update settings if provided
    if username:
        settings.beacon_username = username
    if password:
        settings.beacon_password = password
    if browser:
        settings.browser_profile = browser

    cookie_file = get_cookie_file()

    if not cookie_file or not cookie_file.exists():
        console.print("[red]❌ No cookies found. Please login first.[/red]")
        console.print("[yellow]Use --username and --password to authenticate.[/yellow]")
        raise typer.Exit(code=1)

    return cookie_file


@app.command()
def download(
    url: Optional[str] = typer.Argument(None, help="Beacon TV URL to download (default: latest episode from Campaign 4)"),
    username: Optional[str] = typer.Option(None, help="Beacon TV Username"),
    password: Optional[str] = typer.Option(None, help="Beacon TV Password"),
    browser: Optional[str] = typer.Option(None, help="Browser profile to use (e.g. firefox:default)"),
    series: Optional[str] = typer.Option(None, help="Series slug to fetch latest episode from (default: campaign-4)"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode with verbose output"),
):
    """
    Download video from Beacon TV.

    If no URL is provided, automatically downloads the latest episode from Campaign 4
    (or the series specified with --series).

    Examples:
        beacon-dl                                     # Latest from Campaign 4
        beacon-dl --series exu-calamity              # Latest from EXU Calamity
        beacon-dl https://beacon.tv/content/c4-e007  # Specific episode
    """
    try:
        if debug:
            settings.debug = debug
            console.print("[yellow]Debug mode enabled[/yellow]")
            console.print(f"[dim]Settings: release_group={settings.release_group}, resolution={settings.preferred_resolution}[/dim]")

        console.print("[bold blue]Beacon TV Downloader[/bold blue]")

        # Get authenticated cookie file
        cookie_file = get_authenticated_cookie_file(username, password, browser)

        # If no URL provided, fetch latest episode
        if not url:
            series_slug = series or "campaign-4"
            console.print(f"[yellow]No URL provided. Fetching latest episode from {series_slug}...[/yellow]")

            client = BeaconGraphQL(cookie_file)
            latest = client.get_latest_episode(series_slug)

            if not latest:
                console.print(f"[red]❌ Failed to get latest episode from {series_slug}[/red]")
                raise typer.Exit(code=1)

            url = f"https://beacon.tv/content/{latest['slug']}"
            console.print(f"[green]✓ Latest: {latest['title']}[/green]")

        console.print(f"URL: {url}")

        # Download
        downloader = BeaconDownloader(cookie_file)
        downloader.download_url(url)

    except KeyboardInterrupt:
        console.print("\n[yellow]Download interrupted by user[/yellow]")
        raise typer.Exit(code=130)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        if settings.debug:
            console.print_exception()
        raise typer.Exit(code=1)


@app.command("list-series")
def list_series(
    username: Optional[str] = typer.Option(None, help="Beacon TV Username"),
    password: Optional[str] = typer.Option(None, help="Beacon TV Password"),
    browser: Optional[str] = typer.Option(None, help="Browser profile to use"),
):
    """
    List all available series on Beacon TV.
    """
    try:
        console.print("[bold blue]Available Series on Beacon TV[/bold blue]\n")

        cookie_file = get_authenticated_cookie_file(username, password, browser)

        client = BeaconGraphQL(cookie_file)
        collections = client.list_collections(series_only=True)

        if not collections:
            console.print("[yellow]No series found[/yellow]")
            return

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Series Name", style="green")
        table.add_column("Slug", style="dim")
        table.add_column("Episodes", justify="right", style="yellow")

        for collection in collections:
            table.add_row(
                collection["name"],
                collection["slug"],
                str(collection.get("itemCount", "?"))
            )

        console.print(table)
        console.print(f"\n[dim]Total: {len(collections)} series[/dim]")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("list-episodes")
def list_episodes(
    series: str = typer.Argument(..., help="Series slug (e.g., campaign-4)"),
    username: Optional[str] = typer.Option(None, help="Beacon TV Username"),
    password: Optional[str] = typer.Option(None, help="Beacon TV Password"),
    browser: Optional[str] = typer.Option(None, help="Browser profile to use"),
):
    """
    List all episodes in a series.

    Example: beacon-dl list-episodes campaign-4
    """
    try:
        cookie_file = get_authenticated_cookie_file(username, password, browser)

        client = BeaconGraphQL(cookie_file)

        # Get series info
        info = client.get_collection_info(series)
        if info:
            console.print(f"[bold blue]{info['name']}[/bold blue]")
            console.print(f"[dim]Total episodes: {info.get('itemCount', '?')}[/dim]\n")

        episodes = client.get_series_episodes(series)

        if not episodes:
            console.print(f"[yellow]No episodes found for series: {series}[/yellow]")
            return

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Episode", style="yellow", width=10)
        table.add_column("Title", style="green")
        table.add_column("Release Date", style="dim", width=12)
        table.add_column("Duration", style="cyan", width=10)

        for episode in episodes:
            season = episode.get("seasonNumber", "?")
            ep_num = episode.get("episodeNumber", "?")
            episode_str = f"S{season:02d}E{ep_num:02d}" if isinstance(season, int) and isinstance(ep_num, int) else f"S{season}E{ep_num}"

            release_date = episode.get("releaseDate", "")
            date_str = release_date[:10] if release_date else "?"

            duration_ms = episode.get("duration", 0)
            if duration_ms:
                duration_sec = duration_ms // 1000
                hours = duration_sec // 3600
                minutes = (duration_sec % 3600) // 60
                duration_str = f"{hours}h {minutes}m"
            else:
                duration_str = "?"

            table.add_row(episode_str, episode["title"], date_str, duration_str)

        console.print(table)
        console.print(f"\n[dim]Total: {len(episodes)} episodes[/dim]")
        console.print(f"[dim]URL format: https://beacon.tv/content/{{slug}}[/dim]")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("check-new")
def check_new(
    series: str = typer.Option("campaign-4", help="Series slug to check (default: campaign-4)"),
    username: Optional[str] = typer.Option(None, help="Beacon TV Username"),
    password: Optional[str] = typer.Option(None, help="Beacon TV Password"),
    browser: Optional[str] = typer.Option(None, help="Browser profile to use"),
):
    """
    Check for new episodes in a series.

    Example: beacon-dl check-new --series campaign-4
    """
    try:
        console.print(f"[blue]Checking for new episodes in {series}...[/blue]")

        cookie_file = get_authenticated_cookie_file(username, password, browser)

        client = BeaconGraphQL(cookie_file)
        latest = client.get_latest_episode(series)

        if not latest:
            console.print(f"[yellow]No episodes found for series: {series}[/yellow]")
            return

        season = latest.get("seasonNumber", "?")
        ep_num = latest.get("episodeNumber", "?")
        episode_str = f"S{season:02d}E{ep_num:02d}" if isinstance(season, int) and isinstance(ep_num, int) else f"S{season}E{ep_num}"

        release_date = latest.get("releaseDate", "")
        date_str = release_date[:10] if release_date else "Unknown"

        console.print(f"\n[green]✓ Latest episode found:[/green]")
        console.print(f"  [yellow]{episode_str}[/yellow] - [bold]{latest['title']}[/bold]")
        console.print(f"  Released: {date_str}")
        console.print(f"  URL: https://beacon.tv/content/{latest['slug']}")

        console.print(f"\n[dim]To download:[/dim]")
        console.print(f"  beacon-dl https://beacon.tv/content/{latest['slug']}")
        console.print(f"  [dim]or just:[/dim]")
        console.print(f"  beacon-dl  [dim](downloads latest automatically)[/dim]")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("batch-download")
def batch_download(
    series: str = typer.Argument(..., help="Series slug (e.g., campaign-4)"),
    start: int = typer.Option(1, "--start", "-s", help="Start episode number (default: 1)"),
    end: Optional[int] = typer.Option(None, "--end", "-e", help="End episode number (default: all)"),
    username: Optional[str] = typer.Option(None, help="Beacon TV Username"),
    password: Optional[str] = typer.Option(None, help="Beacon TV Password"),
    browser: Optional[str] = typer.Option(None, help="Browser profile to use"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode"),
):
    """
    Batch download multiple episodes from a series.

    Example:
        beacon-dl batch-download campaign-4              # Download all episodes
        beacon-dl batch-download campaign-4 --start 1 --end 5  # Download episodes 1-5
    """
    try:
        if debug:
            settings.debug = debug

        console.print(f"[bold blue]Batch Download: {series}[/bold blue]\n")

        cookie_file = get_authenticated_cookie_file(username, password, browser)

        client = BeaconGraphQL(cookie_file)
        episodes = client.get_series_episodes(series)

        if not episodes:
            console.print(f"[yellow]No episodes found for series: {series}[/yellow]")
            return

        # Filter episodes by range
        filtered_episodes = []
        for episode in episodes:
            ep_num = episode.get("episodeNumber")
            if ep_num is None:
                continue
            if ep_num < start:
                continue
            if end is not None and ep_num > end:
                continue
            filtered_episodes.append(episode)

        if not filtered_episodes:
            console.print(f"[yellow]No episodes found in range {start}-{end or 'end'}[/yellow]")
            return

        console.print(f"[green]Found {len(filtered_episodes)} episodes to download[/green]\n")

        downloader = BeaconDownloader(cookie_file)
        success_count = 0
        failed_count = 0

        for i, episode in enumerate(filtered_episodes, 1):
            url = f"https://beacon.tv/content/{episode['slug']}"
            console.print(f"\n[bold cyan]Downloading {i}/{len(filtered_episodes)}:[/bold cyan] {episode['title']}")

            try:
                downloader.download_url(url)
                success_count += 1
            except Exception as e:
                console.print(f"[red]❌ Failed to download: {e}[/red]")
                failed_count += 1

                if settings.debug:
                    console.print_exception()

                if i < len(filtered_episodes):
                    continue_download = typer.confirm("\nContinue with next episode?", default=True)
                    if not continue_download:
                        break

        console.print(f"\n[bold]Download Summary:[/bold]")
        console.print(f"  [green]✓ Success: {success_count}[/green]")
        if failed_count > 0:
            console.print(f"  [red]✗ Failed: {failed_count}[/red]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Batch download interrupted by user[/yellow]")
        raise typer.Exit(code=130)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        if settings.debug:
            console.print_exception()
        raise typer.Exit(code=1)


@app.command("history")
def show_history(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of records to show"),
):
    """
    Show download history.

    Lists recent downloads with their status and metadata.
    """
    try:
        history = DownloadHistory()
        downloads = history.list_downloads(limit=limit)

        if not downloads:
            console.print("[yellow]No downloads in history yet[/yellow]")
            console.print("[dim]Downloads will be tracked after your first download[/dim]")
            return

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Date", style="dim", width=12)
        table.add_column("Episode", style="yellow", width=10)
        table.add_column("Title", style="green")
        table.add_column("Size", justify="right", style="cyan", width=10)
        table.add_column("Status", width=8)

        for dl in downloads:
            # Parse date
            date_str = dl.downloaded_at[:10] if dl.downloaded_at else "?"

            # Parse episode from title
            episode_str = "?"
            import re
            match = re.match(r"C(\d+)\s+E(\d+)", dl.title)
            if match:
                episode_str = f"S{int(match.group(1)):02d}E{int(match.group(2)):02d}"
            else:
                match = re.match(r"S(\d+)E(\d+)", dl.title)
                if match:
                    episode_str = f"S{int(match.group(1)):02d}E{int(match.group(2)):02d}"

            # Format file size
            if dl.file_size:
                if dl.file_size >= 1_000_000_000:
                    size_str = f"{dl.file_size / 1_000_000_000:.1f} GB"
                elif dl.file_size >= 1_000_000:
                    size_str = f"{dl.file_size / 1_000_000:.1f} MB"
                else:
                    size_str = f"{dl.file_size / 1_000:.1f} KB"
            else:
                size_str = "?"

            # Status indicator
            status_str = "[green]OK[/green]" if dl.status == "completed" else f"[red]{dl.status}[/red]"

            # Title (truncate if too long)
            title = dl.title
            if len(title) > 40:
                title = title[:37] + "..."

            table.add_row(date_str, episode_str, title, size_str, status_str)

        console.print(table)
        console.print(f"\n[dim]Total: {history.count_downloads()} downloads[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("verify")
def verify_files(
    filename: Optional[str] = typer.Argument(None, help="Specific filename to verify (optional)"),
    full: bool = typer.Option(False, "--full", "-f", help="Full verification with SHA256 hash check"),
):
    """
    Verify integrity of downloaded files.

    Checks that downloaded files match their recorded size and optionally
    verifies SHA256 checksums. Without --full, only checks file size (fast).
    """
    try:
        history = DownloadHistory()
        downloads = history.list_downloads(limit=1000)

        if not downloads:
            console.print("[yellow]No downloads in history to verify[/yellow]")
            return

        if filename:
            # Verify specific file
            record = history.get_download_by_filename(filename)
            if not record:
                console.print(f"[red]File not found in history: {filename}[/red]")
                raise typer.Exit(code=1)
            downloads = [record]

        console.print(f"[blue]Verifying {len(downloads)} file(s)...[/blue]\n")

        valid_count = 0
        invalid_count = 0

        for dl in downloads:
            file_path = Path(dl.filename)

            if not file_path.exists():
                console.print(f"[red]MISSING[/red] {dl.filename}")
                invalid_count += 1
                continue

            # Check file size
            actual_size = file_path.stat().st_size
            if dl.file_size and actual_size != dl.file_size:
                console.print(f"[red]SIZE MISMATCH[/red] {dl.filename}")
                console.print(f"  [dim]Expected: {dl.file_size}, Actual: {actual_size}[/dim]")
                invalid_count += 1
                continue

            # Full verification with SHA256
            if full and dl.sha256:
                console.print(f"[dim]Checking SHA256 for {file_path.name}...[/dim]")
                actual_hash = DownloadHistory.calculate_sha256(file_path)
                if actual_hash != dl.sha256:
                    console.print(f"[red]HASH MISMATCH[/red] {dl.filename}")
                    console.print(f"  [dim]Expected: {dl.sha256[:16]}...[/dim]")
                    console.print(f"  [dim]Actual:   {actual_hash[:16]}...[/dim]")
                    invalid_count += 1
                    continue

            console.print(f"[green]OK[/green] {file_path.name}")
            valid_count += 1

        console.print(f"\n[bold]Verification Summary:[/bold]")
        console.print(f"  [green]Valid: {valid_count}[/green]")
        if invalid_count > 0:
            console.print(f"  [red]Invalid: {invalid_count}[/red]")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("clear-history")
def clear_history(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
):
    """
    Clear all download history.

    This removes all records from the history database but does not
    delete any downloaded files.
    """
    try:
        history = DownloadHistory()
        count = history.count_downloads()

        if count == 0:
            console.print("[yellow]History is already empty[/yellow]")
            return

        if not force:
            confirm = typer.confirm(f"Are you sure you want to clear {count} download record(s)?")
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]")
                return

        deleted = history.clear_history()
        console.print(f"[green]Cleared {deleted} download record(s)[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


def main():
    app()


if __name__ == "__main__":
    main()
