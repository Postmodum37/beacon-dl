"""Video downloader for beacon.tv.

This module handles downloading videos and subtitles from beacon.tv using
direct HTTP downloads. This replaces the yt-dlp-based approach with a simpler
direct download method.
"""

import re
import shutil
import subprocess
from pathlib import Path

import httpx
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from .config import settings
from .content import VideoContent, VideoSource, get_video_content
from .exceptions import ContentNotFoundError, DownloadError, MergeError, ValidationError
from .history import DownloadHistory
from .utils import sanitize_filename

console = Console()

# HTTP client with retry support and connection pooling
DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
DEFAULT_TRANSPORT = httpx.HTTPTransport(retries=3)


class BeaconDownloader:
    """Downloads videos from beacon.tv using direct HTTP requests.

    This class supports the context manager protocol for proper resource cleanup.

    Example:
        >>> with BeaconDownloader(cookie_file) as downloader:
        ...     downloader.download_slug("c4-e007-on-the-scent")
    """

    def __init__(self, cookie_file: Path):
        """Initialize downloader.

        Args:
            cookie_file: Path to Netscape format cookie file for authentication
        """
        self.cookie_file = cookie_file
        self.client = httpx.Client(
            timeout=DEFAULT_TIMEOUT,
            transport=DEFAULT_TRANSPORT,
            headers={"User-Agent": settings.user_agent},
            follow_redirects=True,
        )

    def __enter__(self) -> "BeaconDownloader":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager, closing HTTP client."""
        self.close()

    def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self.client:
            self.client.close()

    def download_url(self, url: str) -> None:
        """Download video from a beacon.tv URL.

        Args:
            url: Full beacon.tv content URL (e.g., https://beacon.tv/content/c4-e007-on-the-scent)

        Raises:
            ValidationError: If URL format is invalid
        """
        # Extract slug from URL
        slug = self._extract_slug(url)
        if not slug:
            raise ValidationError(
                f"Invalid URL: {url}. Expected format: https://beacon.tv/content/<slug>"
            )

        self.download_slug(slug)

    def download_slug(self, slug: str) -> None:
        """Download video by content slug.

        Args:
            slug: Content slug (e.g., "c4-e007-on-the-scent")

        Raises:
            ContentNotFoundError: If content cannot be fetched
            DownloadError: If download fails
            MergeError: If ffmpeg merge fails
        """
        console.print(f"[blue]==> Fetching video metadata for {slug}...[/blue]")

        # Get video content
        content = get_video_content(slug, self.cookie_file)
        if not content:
            raise ContentNotFoundError(f"Failed to get video content for slug: {slug}")

        # Initialize download history
        history = DownloadHistory()
        content_id = content.metadata.id

        # Display info
        console.print(f"[green]Title:[/green] {content.metadata.title}")
        if content.metadata.collection_name:
            console.print(f"[green]Series:[/green] {content.metadata.collection_name}")
        console.print(
            f"[green]Sources:[/green] {len(content.sources)} resolutions available"
        )
        console.print(
            f"[green]Subtitles:[/green] {len(content.subtitles)} languages available"
        )

        # Select best source for preferred resolution
        source = self._select_source(content.sources)
        if not source:
            raise ContentNotFoundError(
                f"No suitable video source found for slug: {slug}. "
                f"Available sources: {len(content.sources)}"
            )

        console.print(
            f"[green]Selected:[/green] {source.label} ({source.width}x{source.height})"
        )

        # Generate output filename
        output_name = self._generate_filename(content, source)
        output_file = Path(f"{output_name}.{settings.container_format}")

        console.print(f"[green]Output:[/green] {output_file}")

        # Check download history first (fast, no file I/O needed)
        if content_id and history.is_downloaded(content_id):
            record = history.get_download(content_id)
            if record and output_file.exists():
                # Validate file size
                actual_size = output_file.stat().st_size
                if record.file_size and actual_size == record.file_size:
                    console.print(
                        f"[green]✓ Already downloaded (verified by content ID): {output_file}[/green]"
                    )
                    return
                else:
                    console.print(
                        f"[yellow]⚠️  File size mismatch (expected {record.file_size}, got {actual_size}), re-downloading...[/yellow]"
                    )
            elif record:
                console.print(
                    "[yellow]⚠️  File missing from disk, re-downloading...[/yellow]"
                )
        # Fallback to filename check (for files downloaded before history was added)
        elif output_file.exists():
            console.print(f"[green]✓ Video already exists: {output_file}[/green]")
            console.print(
                "[dim]Tip: Run 'beacon-dl verify' to add existing files to history[/dim]"
            )
            return

        # Create temp directory
        temp_dir = Path("temp_dl")
        temp_dir.mkdir(exist_ok=True)

        try:
            # Download video
            temp_video = temp_dir / "video.mp4"
            console.print(f"\n[blue]==> Downloading video ({source.label})...[/blue]")
            self._download_file(source.url, temp_video)

            # Download subtitles
            console.print(
                f"\n[blue]==> Downloading {len(content.subtitles)} subtitle tracks...[/blue]"
            )
            subtitle_files = []
            for sub in content.subtitles:
                sub_file = temp_dir / f"subs.{sub.language}.{sub.label}.vtt"
                console.print(f"  [dim]Downloading {sub.label}...[/dim]")
                self._download_file(sub.url, sub_file, show_progress=False)
                subtitle_files.append((sub_file, sub.language, sub.label))

            # Merge with ffmpeg
            console.print(f"\n[blue]==> Merging into {output_file}...[/blue]")
            self._merge_files(temp_video, subtitle_files, output_file)

            # Calculate SHA256 and record download
            if content_id:
                console.print("[dim]Calculating file checksum...[/dim]")
                file_size = output_file.stat().st_size
                sha256 = DownloadHistory.calculate_sha256(output_file)
                history.record_download(
                    content_id=content_id,
                    slug=slug,
                    title=content.metadata.title,
                    filename=str(output_file),
                    file_size=file_size,
                    sha256=sha256,
                )
                console.print(f"[dim]SHA256: {sha256[:16]}...[/dim]")

            console.print(f"[green]✓ Download complete: {output_file}[/green]")

        finally:
            # Cleanup
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def _extract_slug(self, url: str) -> str | None:
        """Extract content slug from URL."""
        # Match beacon.tv/content/<slug>
        match = re.search(r"beacon\.tv/content/([a-zA-Z0-9_-]+)", url)
        return match.group(1) if match else None

    def _select_source(self, sources: list[VideoSource]) -> VideoSource | None:
        """Select the best video source for preferred resolution."""
        if not sources:
            return None

        # Parse preferred resolution (e.g., "1080p" -> 1080)
        preferred = int(settings.preferred_resolution.rstrip("p"))

        # Find exact match or closest lower resolution
        best = None
        for source in sources:
            if source.height == preferred:
                return source
            if source.height < preferred and (
                best is None or source.height > best.height
            ):
                best = source

        # If no lower resolution found, return highest available
        return best or sources[0]

    def _generate_filename(self, content: VideoContent, source: VideoSource) -> str:
        """Generate output filename matching release naming conventions."""
        meta = content.metadata

        # Get show name
        show_name = meta.collection_name or "Critical Role"
        show_name = sanitize_filename(show_name)

        # Resolution from actual source
        resolution = f"{source.height}p"

        # Detect video codec from URL or default
        video_codec = settings.default_video_codec
        if "avc" in source.url.lower() or "h264" in source.url.lower():
            video_codec = "H.264"
        elif "hevc" in source.url.lower() or "h265" in source.url.lower():
            video_codec = "H.265"

        # Audio codec (beacon.tv uses AAC)
        audio_codec = settings.default_audio_codec
        audio_channels = settings.default_audio_channels

        # Check if episodic
        if meta.season_number is not None and meta.episode_number is not None:
            # Episodic format
            season = f"{meta.season_number:02d}"
            episode = f"{meta.episode_number:02d}"

            # Extract episode title from full title
            episode_title = self._extract_episode_title(meta.title)
            episode_title = sanitize_filename(episode_title)

            return (
                f"{show_name}.S{season}E{episode}.{episode_title}."
                f"{resolution}.{settings.source_type}.{audio_codec}{audio_channels}."
                f"{video_codec}"
            )
        else:
            # Non-episodic format
            title = sanitize_filename(meta.title)

            # Check if title already starts with show name
            escaped_show = re.escape(show_name)
            if re.match(rf"^{escaped_show}\.", title):
                return (
                    f"{title}.{resolution}.{settings.source_type}."
                    f"{audio_codec}{audio_channels}.{video_codec}"
                )
            else:
                return (
                    f"{show_name}.{title}.{resolution}.{settings.source_type}."
                    f"{audio_codec}{audio_channels}.{video_codec}"
                )

    def _extract_episode_title(self, full_title: str) -> str:
        """Extract episode title from full title string.

        Handles formats like:
        - "C4 E007 | On the Scent"
        - "S04E07 - Title"
        - "S04E07: Title"
        """
        # "C4 E007 | Title"
        match = re.match(r"C\d+\s+E\d+\s*\|\s*(.+)", full_title)
        if match:
            return match.group(1)

        # "S04E07 - Title" or "S04E07: Title"
        match = re.match(r"S\d+E\d+\s*[-:]\s*(.+)", full_title)
        if match:
            return match.group(1)

        # "S04E07 Title"
        match = re.match(r"S\d+E\d+\s+(.+)", full_title)
        if match:
            return match.group(1)

        # "4x07 - Title"
        match = re.match(r"\d+x\d+\s*[-:]\s*(.+)", full_title)
        if match:
            return match.group(1)

        # Fallback: return as-is
        return full_title

    def _download_file(self, url: str, dest: Path, show_progress: bool = True) -> None:
        """Download a file from URL.

        Args:
            url: URL to download
            dest: Destination path
            show_progress: Whether to show progress bar
        """
        try:
            with self.client.stream("GET", url) as response:
                response.raise_for_status()
                total_size = int(response.headers.get("content-length", 0))

                if show_progress and total_size > 0:
                    with Progress(
                        TextColumn(
                            "[bold blue]{task.fields[filename]}", justify="right"
                        ),
                        BarColumn(bar_width=None),
                        "[progress.percentage]{task.percentage:>3.1f}%",
                        "•",
                        DownloadColumn(),
                        "•",
                        TransferSpeedColumn(),
                        "•",
                        TimeRemainingColumn(),
                        console=console,
                        transient=True,
                    ) as progress:
                        filename = (
                            dest.name[:30] + "..." if len(dest.name) > 30 else dest.name
                        )
                        task = progress.add_task(
                            "download", filename=filename, total=total_size
                        )

                        with open(dest, "wb") as f:
                            for chunk in response.iter_bytes(chunk_size=65536):
                                f.write(chunk)
                                progress.update(
                                    task, completed=response.num_bytes_downloaded
                                )
                else:
                    with open(dest, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=65536):
                            f.write(chunk)

        except httpx.HTTPStatusError as e:
            raise DownloadError(
                f"Download failed (HTTP {e.response.status_code}): {url}"
            ) from e
        except httpx.RequestError as e:
            raise DownloadError(f"Download failed: {e}") from e

    def _merge_files(
        self,
        video_path: Path,
        subtitle_files: list[tuple[Path, str, str]],
        output_path: Path,
    ) -> None:
        """Merge video and subtitles using ffmpeg.

        Args:
            video_path: Path to video file
            subtitle_files: List of (path, language_code, label) tuples
            output_path: Output file path
        """
        cmd = ["ffmpeg", "-i", str(video_path)]

        # Add subtitle inputs
        for sub_path, _, _ in subtitle_files:
            cmd.extend(["-i", str(sub_path)])

        # Map video and audio from first input
        cmd.extend(["-map", "0:v", "-map", "0:a"])

        # Map each subtitle
        for i, _ in enumerate(subtitle_files):
            cmd.extend(["-map", str(i + 1)])

        # Copy video and audio, convert subtitles to SRT
        cmd.extend(["-c:v", "copy", "-c:a", "copy", "-c:s", "srt"])

        # Add language metadata for subtitles
        for i, (_, lang_code, _) in enumerate(subtitle_files):
            cmd.extend([f"-metadata:s:s:{i}", f"language={lang_code}"])

        # Output options
        cmd.extend([str(output_path), "-y", "-hide_banner", "-loglevel", "warning"])

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            raise MergeError(f"FFmpeg merge failed: {e}") from e
        except FileNotFoundError as e:
            raise MergeError(
                "FFmpeg not found. Please install ffmpeg: brew install ffmpeg (macOS) "
                "or apt install ffmpeg (Linux)"
            ) from e
