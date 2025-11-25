"""Domain models for beacon-tv-downloader.

Provides type-safe data models for episodes, series, and collections.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    item_count: int | None = Field(alias="itemCount", default=None)


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
    season_number: int | None = Field(alias="seasonNumber", default=None)
    episode_number: int | None = Field(alias="episodeNumber", default=None)
    release_date: datetime | None = Field(alias="releaseDate", default=None)
    duration: int | None = None  # milliseconds
    description: str | None = None
    primary_collection: Collection | None = Field(
        alias="primaryCollection", default=None
    )

    @property
    def is_episodic(self) -> bool:
        """Check if this is episodic content."""
        return self.season_number is not None and self.episode_number is not None

    @property
    def duration_seconds(self) -> int | None:
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
