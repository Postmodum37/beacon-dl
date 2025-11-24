"""Domain models for beacon-tv-downloader.

Provides type-safe data models for episodes, series, and collections.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class Collection(BaseModel):
    """Represents a BeaconTV collection/series.

    Attributes:
        id: Unique collection identifier
        name: Display name of the collection
        slug: URL-safe slug
        is_series: Whether this is a series (vs one-off content)
        item_count: Number of items in the collection
    """
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    slug: str
    is_series: bool = Field(alias="isSeries", default=True)
    item_count: Optional[int] = Field(alias="itemCount", default=None)


class Episode(BaseModel):
    """Represents a BeaconTV episode.

    Attributes:
        id: Unique episode identifier
        title: Episode title
        slug: URL-safe slug for the episode
        season_number: Season number (if episodic content)
        episode_number: Episode number (if episodic content)
        release_date: Episode release date
        duration: Episode duration in milliseconds
        description: Episode description/summary
        primary_collection: The series/collection this episode belongs to
    """
    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    slug: str
    season_number: Optional[int] = Field(alias="seasonNumber", default=None)
    episode_number: Optional[int] = Field(alias="episodeNumber", default=None)
    release_date: Optional[datetime] = Field(alias="releaseDate", default=None)
    duration: Optional[int] = None  # milliseconds
    description: Optional[str] = None
    primary_collection: Optional[Collection] = Field(
        alias="primaryCollection", default=None
    )

    @property
    def is_episodic(self) -> bool:
        """Check if this is episodic content."""
        return self.season_number is not None and self.episode_number is not None

    @property
    def duration_seconds(self) -> Optional[int]:
        """Get duration in seconds."""
        return self.duration // 1000 if self.duration else None

    @property
    def duration_formatted(self) -> str:
        """Get formatted duration string (e.g., '4h 12m')."""
        if not self.duration:
            return "Unknown"

        seconds = self.duration_seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    @property
    def season_episode_str(self) -> str:
        """Get formatted season/episode string (e.g., 'S04E07')."""
        if not self.is_episodic:
            return ""

        return f"S{self.season_number:02d}E{self.episode_number:02d}"

    def to_url(self) -> str:
        """Get the full BeaconTV URL for this episode."""
        return f"https://beacon.tv/content/{self.slug}"


class VideoMetadata(BaseModel):
    """Video technical metadata.

    Attributes:
        resolution: Video resolution (e.g., '1080p')
        video_codec: Video codec (e.g., 'H.264')
        audio_codec: Audio codec (e.g., 'AAC')
        audio_channels: Audio channels (e.g., '2.0')
        source_type: Source type (e.g., 'WEB-DL')
        container_format: Container format (e.g., 'mkv')
    """

    resolution: str
    video_codec: str
    audio_codec: str
    audio_channels: str
    source_type: str = "WEB-DL"
    container_format: str = "mkv"


class DownloadJob(BaseModel):
    """Represents a download job.

    Attributes:
        episode: Episode to download
        metadata: Video metadata
        output_path: Output file path
        status: Job status
    """

    episode: Episode
    metadata: VideoMetadata
    output_path: str
    status: str = "pending"  # pending, downloading, completed, failed

    @property
    def filename(self) -> str:
        """Generate filename from episode and metadata."""
        from .utils import sanitize_filename

        show_name = sanitize_filename(
            episode.primary_collection.name if episode.primary_collection else "Unknown"
        )

        if episode.is_episodic:
            # Episodic format: Show.S01E01.Title.1080p.WEB-DL.AAC2.0.H.264-Group.mkv
            title = sanitize_filename(episode.title.split("|")[-1].strip())
            return (
                f"{show_name}.{episode.season_episode_str}.{title}."
                f"{self.metadata.resolution}.{self.metadata.source_type}."
                f"{self.metadata.audio_codec}{self.metadata.audio_channels}."
                f"{self.metadata.video_codec}.{self.metadata.container_format}"
            )
        else:
            # Non-episodic format: Show.Title.1080p.WEB-DL.AAC2.0.H.264-Group.mkv
            title = sanitize_filename(episode.title)
            return (
                f"{show_name}.{title}."
                f"{self.metadata.resolution}.{self.metadata.source_type}."
                f"{self.metadata.audio_codec}{self.metadata.audio_channels}."
                f"{self.metadata.video_codec}.{self.metadata.container_format}"
            )
