"""CLI entry point for beacon-dl.

This module provides the command-line interface for the BeaconTV downloader.
"""

import csv
import json
import re
import sys
import time
from enum import Enum
from pathlib import Path

import typer
from rich.table import Table

from .auth import get_cookie_file
from .config import settings
from .content import get_video_content
from .downloader import BeaconDownloader
from .graphql import BeaconGraphQL
from .history import DownloadHistory
from .utils import (
    console,
    extract_slug,
    format_bitrate,
    format_duration,
    format_episode_code,
    format_file_size,
    print_error,
    print_warning,
    retry_with_backoff,
)


class OutputFormat(str, Enum):
    """Output format options for export commands."""

    table = "table"
    json = "json"
    csv = "csv"


app = typer.Typer(
    help="Beacon TV Downloader - Simplified direct download",
    invoke_without_command=True,
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def default_callback(
    ctx: typer.Context,
    cookie_path: Path | None = typer.Option(
        None,
        "--cookie-path",
        "-c",
        help="Path to cookie file (default: from config)",
    ),
) -> None:
    """Default to download command when no subcommand is provided."""
    # Apply global cookie path override if provided
    if cookie_path is not None:
        settings.cookie_path = cookie_path

    if ctx.invoked_subcommand is None:
        # No subcommand provided - run download with defaults
        download(
            url=None,
            username=None,
            password=None,
            series=None,
            retry=0,
            output_dir=None,
            debug=False,
        )


def get_authenticated_cookie_file(
    username: str | None = None,
    password: str | None = None,
) -> Path:
    """Get authenticated cookie file, prompting for login if needed.

    Args:
        username: Optional username override
        password: Optional password override

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

    cookie_file = get_cookie_file()

    if not cookie_file or not cookie_file.exists():
        console.print("[red]❌ No cookies found. Please login first.[/red]")
        console.print("[yellow]Use --username and --password to authenticate.[/yellow]")
        raise typer.Exit(code=1)

    return cookie_file


@app.command()
def download(
    url: str | None = typer.Argument(
        None, help="Beacon TV URL to download (default: latest episode from Campaign 4)"
    ),
    username: str | None = typer.Option(None, help="Beacon TV Username"),
    password: str | None = typer.Option(None, help="Beacon TV Password"),
    series: str | None = typer.Option(
        None, help="Series slug to fetch latest episode from (default: campaign-4)"
    ),
    retry: int = typer.Option(
        0, "--retry", "-r", help="Number of retry attempts on failure (with exponential backoff)"
    ),
    output_dir: Path | None = typer.Option(
        None, "--output-dir", "-o", help="Output directory for downloaded files (default: from config)"
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug mode with verbose output"
    ),
) -> None:
    """
    Download video from Beacon TV.

    If no URL is provided, automatically downloads the latest episode from Campaign 4
    (or the series specified with --series).

    Examples:
        beacon-dl                                     # Latest from Campaign 4
        beacon-dl --series exu-calamity              # Latest from EXU Calamity
        beacon-dl https://beacon.tv/content/c4-e007  # Specific episode
        beacon-dl --retry 3                          # Retry up to 3 times on failure
    """
    try:
        if debug:
            settings.debug = debug
            console.print("[yellow]Debug mode enabled[/yellow]")
            console.print(
                f"[dim]Settings: resolution={settings.preferred_resolution}[/dim]"
            )

        console.print("[bold blue]Beacon TV Downloader[/bold blue]")

        # Get authenticated cookie file
        cookie_file = get_authenticated_cookie_file(username, password)

        # If no URL provided, fetch latest episode
        if not url:
            series_slug = series or "campaign-4"
            console.print(
                f"[dim]Downloading latest episode from [bold]{series_slug}[/bold] (default series)[/dim]"
            )

            client = BeaconGraphQL(cookie_file)
            latest = client.get_latest_episode(series_slug)

            if not latest:
                print_error(f"Failed to get latest episode from {series_slug}")
                raise typer.Exit(code=1)

            url = f"https://beacon.tv/content/{latest['slug']}"
            console.print(f"[green]✓ Latest: {latest['title']}[/green]")

        console.print(f"URL: {url}")

        # Determine output directory
        download_path = output_dir if output_dir else settings.download_path

        # Download with retry logic
        downloader = BeaconDownloader(cookie_file, output_dir=download_path)

        def on_retry(attempt: int, error: Exception, wait_time: float) -> None:
            print_warning(f"Attempt {attempt + 1} failed: {error}")
            console.print(f"[dim]Retrying in {wait_time:.0f}s...[/dim]")

        retry_with_backoff(
            lambda: downloader.download_url(url),
            retries=retry,
            on_retry=on_retry,
        )

    except KeyboardInterrupt:
        console.print("\n[yellow]Download interrupted by user[/yellow]")
        raise typer.Exit(code=130)
    except typer.Exit:
        raise
    except Exception as e:
        print_error(str(e))
        if settings.debug:
            console.print_exception()
        raise typer.Exit(code=1)


@app.command("list-series")
def list_series(
    username: str | None = typer.Option(None, help="Beacon TV Username"),
    password: str | None = typer.Option(None, help="Beacon TV Password"),
) -> None:
    """
    List all available series on Beacon TV.
    """
    try:
        console.print("[bold blue]Available Series on Beacon TV[/bold blue]\n")

        cookie_file = get_authenticated_cookie_file(username, password)

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
                str(collection.get("itemCount", "?")),
            )

        console.print(table)
        console.print(f"\n[dim]Total: {len(collections)} series[/dim]")

    except typer.Exit:
        raise
    except Exception as e:
        print_error(str(e))
        raise typer.Exit(code=1)


@app.command("list-episodes")
def list_episodes(
    series: str = typer.Argument(..., help="Series slug (e.g., campaign-4)"),
    username: str | None = typer.Option(None, help="Beacon TV Username"),
    password: str | None = typer.Option(None, help="Beacon TV Password"),
) -> None:
    """
    List all episodes in a series.

    Example: beacon-dl list-episodes campaign-4
    """
    try:
        cookie_file = get_authenticated_cookie_file(username, password)

        client = BeaconGraphQL(cookie_file)

        # Get series info
        info = client.get_collection_info(series)
        if info:
            console.print(f"[bold blue]{info['name']}[/bold blue]")
            console.print(f"[dim]Total episodes: {info.get('itemCount', '?')}[/dim]\n")

        episodes = client.get_series_episodes(series)

        if not episodes:
            print_warning(f"No episodes found for series: {series}")
            return

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Episode", style="yellow", width=10)
        table.add_column("Title", style="green")
        table.add_column("Release Date", style="dim", width=12)
        table.add_column("Duration", style="cyan", width=10)

        for episode in episodes:
            season = episode.get("seasonNumber")
            ep_num = episode.get("episodeNumber")
            episode_str = format_episode_code(season, ep_num)

            release_date = episode.get("releaseDate", "")
            date_str = release_date[:10] if release_date else "?"

            duration_ms = episode.get("duration", 0)
            duration_str = format_duration(duration_ms // 1000) if duration_ms else "?"

            table.add_row(episode_str, episode["title"], date_str, duration_str)

        console.print(table)
        console.print(f"\n[dim]Total: {len(episodes)} episodes[/dim]")
        console.print("[dim]URL format: https://beacon.tv/content/{slug}[/dim]")

    except typer.Exit:
        raise
    except Exception as e:
        print_error(str(e))
        raise typer.Exit(code=1)


@app.command("search")
def search_content(
    query: str = typer.Argument(..., help="Search text (title, description)"),
    series: str | None = typer.Option(
        None, "--series", "-s", help="Filter by series slug (e.g., campaign-4)"
    ),
    limit: int = typer.Option(10, "--limit", "-n", help="Maximum results to show"),
    username: str | None = typer.Option(None, help="Beacon TV Username"),
    password: str | None = typer.Option(None, help="Beacon TV Password"),
) -> None:
    """
    Search for episodes by title or description.

    Examples:
        beacon-dl search "on the scent"
        beacon-dl search "dragon" --series campaign-4
        beacon-dl search "bells" --limit 20
    """
    try:
        cookie_file = get_authenticated_cookie_file(username, password)

        client = BeaconGraphQL(cookie_file)
        result = client.search(
            collection_slug=series,
            search_text=query,
            limit=limit,
        )

        docs = result.get("docs", [])
        total = result.get("totalDocs", 0)

        if not docs:
            print_warning(f"No results found for: {query}")
            return

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Episode", style="yellow", width=10)
        table.add_column("Title", style="green")
        table.add_column("Series", style="dim", width=20)
        table.add_column("Release Date", style="dim", width=12)

        for doc in docs:
            season = doc.get("seasonNumber")
            ep_num = doc.get("episodeNumber")
            episode_str = format_episode_code(season, ep_num)

            release_date = doc.get("releaseDate", "")
            date_str = release_date[:10] if release_date else "?"

            collection = doc.get("primaryCollection") or {}
            series_name = collection.get("name", "?")
            if len(series_name) > 18:
                series_name = series_name[:17] + "…"

            table.add_row(episode_str, doc["title"], series_name, date_str)

        console.print(table)
        console.print(f"\n[dim]Showing {len(docs)} of {total} results[/dim]")
        console.print("[dim]URL format: https://beacon.tv/content/{slug}[/dim]")

    except typer.Exit:
        raise
    except Exception as e:
        print_error(str(e))
        raise typer.Exit(code=1)


@app.command("check-new")
def check_new(
    series: str = typer.Option(
        "campaign-4", help="Series slug to check (default: campaign-4)"
    ),
    username: str | None = typer.Option(None, help="Beacon TV Username"),
    password: str | None = typer.Option(None, help="Beacon TV Password"),
) -> None:
    """
    Check for new episodes in a series.

    Example: beacon-dl check-new --series campaign-4
    """
    try:
        console.print(f"[blue]Checking for new episodes in {series}...[/blue]")

        cookie_file = get_authenticated_cookie_file(username, password)

        client = BeaconGraphQL(cookie_file)
        latest = client.get_latest_episode(series)

        if not latest:
            print_warning(f"No episodes found for series: {series}")
            return

        season = latest.get("seasonNumber")
        ep_num = latest.get("episodeNumber")
        episode_str = format_episode_code(season, ep_num)

        release_date = latest.get("releaseDate", "")
        date_str = release_date[:10] if release_date else "Unknown"

        console.print("\n[green]✓ Latest episode found:[/green]")
        console.print(
            f"  [yellow]{episode_str}[/yellow] - [bold]{latest['title']}[/bold]"
        )
        console.print(f"  Released: {date_str}")
        console.print(f"  URL: https://beacon.tv/content/{latest['slug']}")

        # Check if already downloaded
        history = DownloadHistory()
        existing = history.get_download_by_slug(latest['slug'])

        if existing:
            console.print(
                f"\n[green]✓ Already downloaded:[/green] {existing.filename}"
            )
        else:
            console.print("\n[dim]To download:[/dim]")
            console.print(f"  beacon-dl https://beacon.tv/content/{latest['slug']}")
            console.print("  [dim]or just:[/dim]")
            console.print("  beacon-dl  [dim](downloads latest automatically)[/dim]")

    except typer.Exit:
        raise
    except Exception as e:
        print_error(str(e))
        raise typer.Exit(code=1)


@app.command("batch-download")
def batch_download(
    series: str = typer.Argument(..., help="Series slug (e.g., campaign-4)"),
    start: int = typer.Option(
        1, "--start", "-s", help="Start episode number (default: 1)"
    ),
    end: int | None = typer.Option(
        None, "--end", "-e", help="End episode number (default: all)"
    ),
    retry: int = typer.Option(
        0, "--retry", "-r", help="Number of retry attempts per episode (with exponential backoff)"
    ),
    output_dir: Path | None = typer.Option(
        None, "--output-dir", "-o", help="Output directory for downloaded files (default: from config)"
    ),
    username: str | None = typer.Option(None, help="Beacon TV Username"),
    password: str | None = typer.Option(None, help="Beacon TV Password"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode"),
) -> None:
    """
    Batch download multiple episodes from a series.

    Examples:
        beacon-dl batch-download campaign-4              # Download all episodes
        beacon-dl batch-download campaign-4 --start 1 --end 5  # Download episodes 1-5
        beacon-dl batch-download campaign-4 --retry 2    # Retry failed downloads twice
    """
    try:
        if debug:
            settings.debug = debug

        console.print(f"[bold blue]Batch Download: {series}[/bold blue]\n")

        cookie_file = get_authenticated_cookie_file(username, password)

        client = BeaconGraphQL(cookie_file)
        episodes = client.get_series_episodes(series)

        if not episodes:
            print_warning(f"No episodes found for series: {series}")
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
            console.print(
                f"[yellow]No episodes found in range {start}-{end or 'end'}[/yellow]"
            )
            return

        console.print(
            f"[green]Found {len(filtered_episodes)} episodes to download[/green]\n"
        )

        # Determine output directory
        download_path = output_dir if output_dir else settings.download_path

        downloader = BeaconDownloader(cookie_file, output_dir=download_path)
        success_count = 0
        skipped_count = 0
        failed_count = 0
        failed_episodes: list[str] = []

        for i, episode in enumerate(filtered_episodes, 1):
            url = f"https://beacon.tv/content/{episode['slug']}"
            console.print(
                f"\n[bold cyan][{i}/{len(filtered_episodes)}][/bold cyan] {episode['title']}"
            )

            # Attempt download with retry logic
            last_error = None
            for attempt in range(retry + 1):
                try:
                    downloader.download_url(url)
                    success_count += 1
                    last_error = None
                    break
                except Exception as e:
                    # Check if it was skipped (already downloaded)
                    if "Already downloaded" in str(e) or "already exists" in str(e).lower():
                        skipped_count += 1
                        last_error = None
                        break

                    last_error = e
                    if attempt < retry:
                        wait_time = 2 ** attempt
                        print_warning(f"Attempt {attempt + 1} failed: {e}")
                        console.print(f"[dim]Retrying in {wait_time}s...[/dim]")
                        time.sleep(wait_time)

            if last_error:
                print_error(f"Failed to download: {last_error}")
                failed_count += 1
                failed_episodes.append(episode['title'])

                if settings.debug:
                    console.print_exception()

                if i < len(filtered_episodes):
                    continue_download = typer.confirm(
                        "\nContinue with next episode?", default=True
                    )
                    if not continue_download:
                        break

        # Summary
        console.print("\n[bold]Download Summary:[/bold]")
        console.print(f"  [green]✓ Downloaded: {success_count}[/green]")
        if skipped_count > 0:
            console.print(f"  [dim]⊘ Skipped (already downloaded): {skipped_count}[/dim]")
        if failed_count > 0:
            console.print(f"  [red]✗ Failed: {failed_count}[/red]")
            for title in failed_episodes:
                console.print(f"    [dim]- {title}[/dim]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Batch download interrupted by user[/yellow]")
        raise typer.Exit(code=130)
    except typer.Exit:
        raise
    except Exception as e:
        print_error(str(e))
        if settings.debug:
            console.print_exception()
        raise typer.Exit(code=1)


@app.command("history")
def show_history(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of records to show"),
    output_format: OutputFormat = typer.Option(
        OutputFormat.table, "--format", "-f", help="Output format: table, json, csv"
    ),
) -> None:
    """
    Show download history.

    Lists recent downloads with their status and metadata.

    Examples:
        beacon-dl history
        beacon-dl history --format json > downloads.json
        beacon-dl history --format csv > downloads.csv
    """
    try:
        history = DownloadHistory()
        downloads = history.list_downloads(limit=limit)

        if not downloads:
            if output_format == OutputFormat.table:
                console.print("[yellow]No downloads in history yet[/yellow]")
                console.print(
                    "[dim]Downloads will be tracked after your first download[/dim]"
                )
            elif output_format == OutputFormat.json:
                print("[]")
            # csv: just output empty (header only will be below)
            return

        # JSON output
        if output_format == OutputFormat.json:
            data = [
                {
                    "content_id": dl.content_id,
                    "slug": dl.slug,
                    "title": dl.title,
                    "filename": dl.filename,
                    "file_size": dl.file_size,
                    "sha256": dl.sha256,
                    "downloaded_at": dl.downloaded_at,
                    "status": dl.status,
                }
                for dl in downloads
            ]
            print(json.dumps(data, indent=2))
            return

        # CSV output
        if output_format == OutputFormat.csv:
            writer = csv.writer(sys.stdout)
            writer.writerow(
                ["content_id", "slug", "title", "filename", "file_size", "sha256", "downloaded_at", "status"]
            )
            for dl in downloads:
                writer.writerow(
                    [dl.content_id, dl.slug, dl.title, dl.filename, dl.file_size, dl.sha256, dl.downloaded_at, dl.status]
                )
            return

        # Table output (default)
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
            episode_str = "-"
            match = re.match(r"C(\d+)\s+E(\d+)", dl.title)
            if match:
                episode_str = format_episode_code(int(match.group(1)), int(match.group(2)))
            else:
                match = re.match(r"S(\d+)E(\d+)", dl.title)
                if match:
                    episode_str = format_episode_code(int(match.group(1)), int(match.group(2)))

            # Format file size
            size_str = format_file_size(dl.file_size) if dl.file_size else "?"

            # Status indicator
            status_str = (
                "[green]OK[/green]"
                if dl.status == "completed"
                else f"[red]{dl.status}[/red]"
            )

            # Title (truncate if too long)
            title = dl.title
            if len(title) > 40:
                title = title[:37] + "..."

            table.add_row(date_str, episode_str, title, size_str, status_str)

        console.print(table)
        console.print(f"\n[dim]Total: {history.count_downloads()} downloads[/dim]")

    except Exception as e:
        print_error(str(e))
        raise typer.Exit(code=1)


@app.command("config")
def show_config() -> None:
    """
    Show current configuration settings.

    Displays all configuration values from environment variables and .env file.
    Sensitive values (passwords) are masked.

    Example: beacon-dl config
    """
    console.print("[bold blue]Current Configuration[/bold blue]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Setting", style="yellow")
    table.add_column("Value", style="green")
    table.add_column("Source", style="dim")

    # Display settings with their values
    config_items = [
        ("preferred_resolution", settings.preferred_resolution, "PREFERRED_RESOLUTION"),
        ("source_type", settings.source_type, "SOURCE_TYPE"),
        ("container_format", settings.container_format, "CONTAINER_FORMAT"),
        ("default_audio_codec", settings.default_audio_codec, "DEFAULT_AUDIO_CODEC"),
        ("default_audio_channels", settings.default_audio_channels, "DEFAULT_AUDIO_CHANNELS"),
        ("default_video_codec", settings.default_video_codec, "DEFAULT_VIDEO_CODEC"),
        ("debug", str(settings.debug), "DEBUG"),
        ("cookie_expiry_buffer_hours", str(settings.cookie_expiry_buffer_hours), "COOKIE_EXPIRY_BUFFER_HOURS"),
    ]

    for name, value, env_var in config_items:
        table.add_row(name, value, env_var)

    # Auth (masked)
    username_display = "********" if settings.beacon_username else "[dim]not set[/dim]"
    password_display = "********" if settings.beacon_password else "[dim]not set[/dim]"
    table.add_row("beacon_username", username_display, "BEACON_USERNAME")
    table.add_row("beacon_password", password_display, "BEACON_PASSWORD")

    console.print(table)
    console.print("\n[dim]Set values via environment variables or .env file[/dim]")


@app.command("verify")
def verify_files(
    filename: str | None = typer.Argument(
        None, help="Specific filename to verify (optional)"
    ),
    full: bool = typer.Option(
        False, "--full", "-f", help="Full verification with SHA256 hash check"
    ),
    slug_filter: str | None = typer.Option(
        None, "--filter", help="Filter by slug pattern (e.g., 'c4' for Campaign 4)"
    ),
    status_filter: str | None = typer.Option(
        None, "--status", "-s", help="Filter by status (completed, failed)"
    ),
) -> None:
    """
    Verify integrity of downloaded files.

    Checks that downloaded files match their recorded size and optionally
    verifies SHA256 checksums. Without --full, only checks file size (fast).

    Examples:
        beacon-dl verify                    # Verify all
        beacon-dl verify --full             # Full SHA256 verification
        beacon-dl verify --filter c4        # Only Campaign 4 episodes
        beacon-dl verify --status completed # Only completed downloads
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
                print_error(f"File not found in history: {filename}")
                raise typer.Exit(code=1)
            downloads = [record]

        # Apply filters
        if slug_filter:
            downloads = [dl for dl in downloads if slug_filter.lower() in dl.slug.lower()]
            if not downloads:
                print_warning(f"No downloads matching filter: {slug_filter}")
                return

        if status_filter:
            downloads = [dl for dl in downloads if dl.status == status_filter]
            if not downloads:
                print_warning(f"No downloads with status: {status_filter}")
                return

        console.print(f"[blue]Verifying {len(downloads)} file(s)...[/blue]\n")

        valid_count = 0
        invalid_count = 0

        for dl in downloads:
            file_path = Path(dl.filename)

            if not file_path.exists():
                print_error(f"MISSING: {dl.filename}")
                invalid_count += 1
                continue

            # Check file size
            actual_size = file_path.stat().st_size
            if dl.file_size and actual_size != dl.file_size:
                print_error(f"SIZE MISMATCH: {dl.filename}")
                console.print(
                    f"  [dim]Expected: {dl.file_size}, Actual: {actual_size}[/dim]"
                )
                invalid_count += 1
                continue

            # Full verification with SHA256
            if full and dl.sha256:
                console.print(f"[dim]Checking SHA256 for {file_path.name}...[/dim]")
                actual_hash = DownloadHistory.calculate_sha256(file_path)
                if actual_hash != dl.sha256:
                    print_error(f"HASH MISMATCH: {dl.filename}")
                    console.print(f"  [dim]Expected: {dl.sha256[:16]}...[/dim]")
                    console.print(f"  [dim]Actual:   {actual_hash[:16]}...[/dim]")
                    invalid_count += 1
                    continue

            console.print(f"[green]OK[/green] {file_path.name}")
            valid_count += 1

        console.print("\n[bold]Verification Summary:[/bold]")
        console.print(f"  [green]Valid: {valid_count}[/green]")
        if invalid_count > 0:
            console.print(f"  [red]Invalid: {invalid_count}[/red]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Verification interrupted by user[/yellow]")
        raise typer.Exit(code=130)
    except typer.Exit:
        raise
    except Exception as e:
        print_error(str(e))
        raise typer.Exit(code=1)


@app.command("clear-history")
def clear_history(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
) -> None:
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
            confirm = typer.confirm(
                f"Are you sure you want to clear {count} download record(s)?"
            )
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]")
                return

        deleted = history.clear_history()
        console.print(f"[green]Cleared {deleted} download record(s)[/green]")

    except Exception as e:
        print_error(str(e))
        raise typer.Exit(code=1)


@app.command("rename")
def rename_files(
    directory: Path = typer.Argument(
        Path("."),
        help="Directory containing files to rename",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--execute",
        help="Show what would be renamed without making changes",
    ),
    pattern: str = typer.Option(
        "*.mkv",
        "--pattern",
        help="Glob pattern for files to consider",
    ),
) -> None:
    """
    Rename existing files to current scene-style naming schema.

    Converts old naming format to new scene-style format with:
    - Collection name -> Display name (Campaign.4 -> Critical.Role)
    - BCTV service tag added
    - Release group appended

    Old: Campaign.4.S04E07.On.the.Scent.1080p.WEB-DL.AAC2.0.H.264.mkv
    New: Critical.Role.S04E07.On.the.Scent.1080p.BCTV.WEB-DL.AAC2.0.H.264-Pawsty.mkv

    Use --execute to actually perform renames (default is --dry-run).

    Examples:
        beacon-dl rename                    # Dry-run in current directory
        beacon-dl rename ./downloads        # Dry-run in downloads folder
        beacon-dl rename --execute          # Actually rename files
        beacon-dl rename --pattern "*.mp4"  # Only rename mp4 files
    """
    from .constants import COLLECTION_DISPLAY_NAMES, SERVICE_TAG

    try:
        console.print("[bold blue]File Renaming Tool[/bold blue]\n")

        if dry_run:
            console.print("[yellow]DRY RUN - no files will be renamed[/yellow]")
            console.print("[dim]Use --execute to actually rename files[/dim]\n")

        # Pattern to match old format:
        # Campaign.4.S04E07.Title.1080p.WEB-DL.AAC2.0.H.264.mkv
        # or with existing release group:
        # Campaign.4.S04E07.Title.1080p.WEB-DL.AAC2.0.H.264-Group.mkv
        old_format_pattern = re.compile(
            r"^(Campaign\.\d+|Candela\.Obscura|4-Sided\.Dive|Exandria\.Unlimited|Midst)"
            r"\.(S\d{2}E\d{2})"
            r"\.(.+?)"
            r"\.(\d{3,4}p)"
            r"\.([A-Za-z0-9.-]+)"  # source type (WEB-DL, etc)
            r"\.([A-Z]+\d+\.\d+)"  # audio (AAC2.0, etc)
            r"\.([A-Za-z0-9.]+?)"  # video codec (H.264, etc)
            r"(?:-([A-Za-z0-9]+))?"  # optional existing release group
            r"\.(\w+)$"  # extension
        )

        # Build reverse mapping from dotted names to original names
        dotted_to_original: dict[str, str] = {}
        for original, _display in COLLECTION_DISPLAY_NAMES.items():
            dotted = original.replace(" ", ".")
            dotted_to_original[dotted] = original

        # Find files matching glob pattern
        files = list(directory.glob(pattern))
        if not files:
            print_warning(f"No files found matching '{pattern}' in {directory}")
            return

        history = DownloadHistory()
        renamed_count = 0
        skipped_count = 0
        no_match_count = 0

        release_group = settings.release_group

        for file_path in sorted(files):
            filename = file_path.name
            match = old_format_pattern.match(filename)

            if not match:
                # Check if already in new format (has BCTV tag)
                if ".BCTV." in filename:
                    continue  # Already converted
                no_match_count += 1
                if settings.debug:
                    console.print(f"[dim]NO MATCH: {filename}[/dim]")
                continue

            old_collection = match.group(1)  # e.g., "Campaign.4"
            season_ep = match.group(2)  # e.g., "S04E07"
            title = match.group(3)  # e.g., "On.the.Scent"
            resolution = match.group(4)  # e.g., "1080p"
            source = match.group(5)  # e.g., "WEB-DL"
            audio = match.group(6)  # e.g., "AAC2.0"
            video = match.group(7)  # e.g., "H.264"
            # group(8) is existing release group (ignored)
            extension = match.group(9)  # e.g., "mkv"

            # Convert collection name to display name
            original_name = dotted_to_original.get(old_collection)
            if original_name and original_name in COLLECTION_DISPLAY_NAMES:
                display_name = COLLECTION_DISPLAY_NAMES[original_name]
            else:
                display_name = old_collection  # Keep as-is if not in mapping

            # Build new filename with BCTV service tag and release group
            new_filename = (
                f"{display_name}.{season_ep}.{title}.{resolution}."
                f"{SERVICE_TAG}.{source}.{audio}.{video}-{release_group}.{extension}"
            )
            new_path = file_path.parent / new_filename

            # Skip if already has correct name
            if filename == new_filename:
                continue

            # Check if target already exists
            if new_path.exists() and new_path != file_path:
                print_warning(f"SKIP: {filename}")
                console.print(f"  [dim]Target already exists: {new_filename}[/dim]")
                skipped_count += 1
                continue

            if dry_run:
                console.print(f"[cyan]WOULD RENAME[/cyan] {filename}")
                console.print(f"  [dim]→ {new_filename}[/dim]")
            else:
                # Actually rename the file
                file_path.rename(new_path)
                console.print(f"[green]RENAMED[/green] {filename}")
                console.print(f"  [dim]→ {new_filename}[/dim]")

                # Update history database if this file is tracked
                record = history.get_download_by_filename(filename)
                if record:
                    history.update_filename(record.content_id, new_filename)
                    console.print("  [dim]Updated history record[/dim]")

            renamed_count += 1

        console.print("\n[bold]Summary:[/bold]")
        if dry_run:
            console.print(f"  [cyan]Would rename: {renamed_count}[/cyan]")
        else:
            console.print(f"  [green]Renamed: {renamed_count}[/green]")
        if skipped_count > 0:
            console.print(f"  [yellow]Skipped: {skipped_count}[/yellow]")
        if no_match_count > 0 and settings.debug:
            console.print(f"  [dim]No match: {no_match_count}[/dim]")

        if dry_run and renamed_count > 0:
            console.print("\n[dim]Run with --execute to apply changes[/dim]")

    except Exception as e:
        print_error(str(e))
        if settings.debug:
            console.print_exception()
        raise typer.Exit(code=1)


@app.command("info")
def show_info(
    url_or_slug: str | None = typer.Argument(None, help="Episode URL or slug"),
    series: str | None = typer.Option(
        None, "--series", "-s", help="Series slug (use with --episode)"
    ),
    episode: int | None = typer.Option(
        None, "--episode", "-e", help="Episode number (use with --series)"
    ),
    username: str | None = typer.Option(None, help="Beacon TV Username"),
    password: str | None = typer.Option(None, help="Beacon TV Password"),
) -> None:
    """
    Show detailed information about an episode.

    Displays available resolutions, subtitles, metadata, and download status.

    Examples:
        beacon-dl info c4-e007-on-the-scent
        beacon-dl info https://beacon.tv/content/c4-e007-on-the-scent
        beacon-dl info --series campaign-4 --episode 7
    """
    try:
        # Get authenticated cookie file (once, up front)
        cookie_file = get_authenticated_cookie_file(username, password)

        # Determine the slug
        if url_or_slug:
            slug = extract_slug(url_or_slug)
        elif series and episode:
            # Lookup episode by series and episode number
            client = BeaconGraphQL(cookie_file)
            episodes = client.get_series_episodes(series)

            # Find matching episode
            matching = [
                ep for ep in episodes
                if ep.get("episodeNumber") == episode
            ]
            if not matching:
                print_error(f"Episode {episode} not found in series: {series}")
                raise typer.Exit(code=1)

            slug = matching[0]["slug"]
            console.print(f"[dim]Found: {slug}[/dim]\n")
        else:
            print_error("Provide either a URL/slug or --series and --episode")
            raise typer.Exit(code=1)

        console.print("[bold blue]Episode Information[/bold blue]\n")

        # Fetch video content
        content = get_video_content(slug, cookie_file)
        if not content:
            print_error(f"Failed to fetch content for: {slug}")
            raise typer.Exit(code=1)

        meta = content.metadata

        # Episode info section
        console.print(f"[bold]Title:[/bold]       {meta.title}")
        if meta.collection_name:
            console.print(f"[bold]Series:[/bold]      {meta.collection_name}")
        if meta.season_number or meta.episode_number:
            console.print(
                f"[bold]Episode:[/bold]     {format_episode_code(meta.season_number, meta.episode_number)}"
            )
        if meta.duration:
            # Duration from API is in milliseconds, convert to seconds
            duration_seconds = meta.duration // 1000
            console.print(
                f"[bold]Duration:[/bold]    {format_duration(duration_seconds)}"
            )
        console.print(f"[bold]URL:[/bold]         https://beacon.tv/content/{slug}")

        # Description
        if meta.description:
            console.print("\n[bold]Description:[/bold]")
            # Truncate long descriptions
            desc = meta.description
            if len(desc) > 300:
                desc = desc[:297] + "..."
            console.print(f"  [dim]{desc}[/dim]")

        # Available resolutions table
        if content.sources:
            console.print("\n[bold cyan]Available Resolutions[/bold cyan]")
            res_table = Table(show_header=True, header_style="bold")
            res_table.add_column("Quality", style="yellow")
            res_table.add_column("Resolution", style="green")
            res_table.add_column("Bitrate", style="cyan", justify="right")
            res_table.add_column("Format", style="dim")

            for source in content.sources:
                res_table.add_row(
                    source.label or f"{source.height}p",
                    f"{source.width}x{source.height}",
                    format_bitrate(source.bitrate) if source.bitrate else "?",
                    source.file_type or "video/mp4",
                )

            console.print(res_table)

        # Subtitles table
        if content.subtitles:
            console.print("\n[bold cyan]Subtitles[/bold cyan]")
            sub_table = Table(show_header=True, header_style="bold")
            sub_table.add_column("Language", style="green")
            sub_table.add_column("Code", style="dim")

            for sub in content.subtitles:
                sub_table.add_row(sub.label, sub.language)

            console.print(sub_table)
        else:
            console.print("\n[dim]No subtitles available[/dim]")

        # Download history status
        history = DownloadHistory()
        record = history.get_download_by_slug(slug)

        console.print()
        if record:
            console.print("[bold green]Download Status: ✓ Downloaded[/bold green]")
            console.print(f"  [dim]Filename:[/dim] {record.filename}")
            if record.file_size:
                console.print(
                    f"  [dim]Size:[/dim]     {format_file_size(record.file_size)}"
                )
            if record.downloaded_at:
                date_str = record.downloaded_at[:10]
                console.print(f"  [dim]Date:[/dim]     {date_str}")
        else:
            console.print("[yellow]Download Status: Not downloaded[/yellow]")
            console.print(f"  [dim]Run: beacon-dl {slug}[/dim]")

    except typer.Exit:
        raise
    except Exception as e:
        print_error(str(e))
        if settings.debug:
            console.print_exception()
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
