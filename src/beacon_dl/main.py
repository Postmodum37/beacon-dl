import typer
from rich.console import Console
from typing import Optional
from .downloader import BeaconDownloader
from .config import settings
from .utils import get_latest_episode_url

app = typer.Typer(help="Beacon TV Downloader")
console = Console()

@app.command()
def download(
    url: Optional[str] = typer.Argument(None, help="Beacon TV URL to download (default: latest episode from Campaign 4)"),
    username: Optional[str] = typer.Option(None, help="Beacon TV Username"),
    password: Optional[str] = typer.Option(None, help="Beacon TV Password"),
    browser: Optional[str] = typer.Option(None, help="Browser profile to use (e.g. firefox:default)"),
    series: Optional[str] = typer.Option(None, help="Series URL to fetch latest episode from (default: https://beacon.tv/series/campaign-4)"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode with verbose output"),
):
    """
    Download video from Beacon TV.

    If no URL is provided, automatically downloads the latest episode from Campaign 4
    (or the series specified with --series).
    """
    try:
        # Update settings if provided via CLI
        if username:
            settings.beacon_username = username
        if password:
            settings.beacon_password = password
        if browser:
            settings.browser_profile = browser
        if debug:
            settings.debug = debug

        console.print("[bold blue]Beacon TV Downloader[/bold blue]")

        if settings.debug:
            console.print("[yellow]Debug mode enabled[/yellow]")
            console.print(f"[dim]Settings: release_group={settings.release_group}, resolution={settings.preferred_resolution}[/dim]")

        # If no URL provided, fetch latest episode
        if not url:
            series_url = series or "https://beacon.tv/series/campaign-4"
            console.print(f"[yellow]No URL provided. Fetching latest episode from {series_url}...[/yellow]")
            url = get_latest_episode_url(series_url)

        console.print(f"URL: {url}")

        downloader = BeaconDownloader()
        downloader.process_url(url)

    except KeyboardInterrupt:
        console.print("\n[yellow]Download interrupted by user[/yellow]")
        raise typer.Exit(code=130)
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        if settings.debug:
            console.print_exception()
        raise typer.Exit(code=1)

def main():
    app()

if __name__ == "__main__":
    main()
