"""Tests for domain models."""

import pytest
from datetime import datetime
from src.beacon_dl.models import Collection, Episode, VideoMetadata, DownloadJob


class TestCollection:
    """Tests for Collection model."""

    def test_collection_basic_fields(self):
        """Test basic collection field parsing."""
        collection = Collection(
            id="123",
            name="Campaign 4",
            slug="campaign-4",
        )

        assert collection.id == "123"
        assert collection.name == "Campaign 4"
        assert collection.slug == "campaign-4"
        assert collection.is_series is True  # default
        assert collection.item_count is None  # default

    def test_collection_with_all_fields(self):
        """Test collection with all fields."""
        collection = Collection(
            id="456",
            name="Candela Obscura",
            slug="candela-obscura",
            isSeries=True,
            itemCount=23,
        )

        assert collection.is_series is True
        assert collection.item_count == 23

    def test_collection_non_series(self):
        """Test non-series collection."""
        collection = Collection(
            id="789",
            name="One Shot",
            slug="one-shot",
            isSeries=False,
        )

        assert collection.is_series is False


class TestEpisode:
    """Tests for Episode model."""

    def test_episode_basic_fields(self):
        """Test basic episode field parsing."""
        episode = Episode(
            id="ep-123",
            title="C4 E007 | On the Scent",
            slug="c4-e007-on-the-scent",
        )

        assert episode.id == "ep-123"
        assert episode.title == "C4 E007 | On the Scent"
        assert episode.slug == "c4-e007-on-the-scent"
        assert episode.season_number is None
        assert episode.episode_number is None

    def test_episode_with_season_episode(self):
        """Test episodic content."""
        episode = Episode(
            id="ep-456",
            title="C4 E007 | On the Scent",
            slug="c4-e007-on-the-scent",
            seasonNumber=4,
            episodeNumber=7,
        )

        assert episode.season_number == 4
        assert episode.episode_number == 7
        assert episode.is_episodic is True

    def test_episode_not_episodic(self):
        """Test non-episodic content."""
        episode = Episode(
            id="ep-789",
            title="One Shot Special",
            slug="one-shot-special",
        )

        assert episode.is_episodic is False

    def test_episode_partial_episodic(self):
        """Test episode with only season number."""
        episode = Episode(
            id="ep-101",
            title="Test",
            slug="test",
            seasonNumber=1,
        )

        assert episode.is_episodic is False  # Both required

    def test_episode_duration_seconds(self):
        """Test duration_seconds property."""
        episode = Episode(
            id="ep-102",
            title="Test",
            slug="test",
            duration=13949000,  # milliseconds
        )

        assert episode.duration_seconds == 13949

    def test_episode_duration_seconds_none(self):
        """Test duration_seconds when no duration."""
        episode = Episode(
            id="ep-103",
            title="Test",
            slug="test",
        )

        assert episode.duration_seconds is None

    def test_episode_duration_formatted(self):
        """Test duration_formatted property."""
        # 4 hours 12 minutes = 15120 seconds = 15120000 ms
        episode = Episode(
            id="ep-104",
            title="Test",
            slug="test",
            duration=15120000,
        )

        assert episode.duration_formatted == "4h 12m"

    def test_episode_duration_formatted_minutes_only(self):
        """Test duration_formatted with minutes only."""
        # 45 minutes = 2700 seconds = 2700000 ms
        episode = Episode(
            id="ep-105",
            title="Test",
            slug="test",
            duration=2700000,
        )

        assert episode.duration_formatted == "45m"

    def test_episode_duration_formatted_unknown(self):
        """Test duration_formatted with no duration."""
        episode = Episode(
            id="ep-106",
            title="Test",
            slug="test",
        )

        assert episode.duration_formatted == "Unknown"

    def test_episode_season_episode_str(self):
        """Test season_episode_str property."""
        episode = Episode(
            id="ep-107",
            title="Test",
            slug="test",
            seasonNumber=4,
            episodeNumber=7,
        )

        assert episode.season_episode_str == "S04E07"

    def test_episode_season_episode_str_high_numbers(self):
        """Test season_episode_str with high numbers."""
        episode = Episode(
            id="ep-108",
            title="Test",
            slug="test",
            seasonNumber=12,
            episodeNumber=142,
        )

        assert episode.season_episode_str == "S12E142"

    def test_episode_season_episode_str_empty(self):
        """Test season_episode_str when not episodic."""
        episode = Episode(
            id="ep-109",
            title="Test",
            slug="test",
        )

        assert episode.season_episode_str == ""

    def test_episode_to_url(self):
        """Test to_url method."""
        episode = Episode(
            id="ep-110",
            title="Test",
            slug="c4-e007-on-the-scent",
        )

        assert episode.to_url() == "https://beacon.tv/content/c4-e007-on-the-scent"

    def test_episode_with_collection(self):
        """Test episode with primary collection."""
        collection = Collection(
            id="col-123",
            name="Campaign 4",
            slug="campaign-4",
        )
        episode = Episode(
            id="ep-111",
            title="Test",
            slug="test",
            primaryCollection=collection,
        )

        assert episode.primary_collection is not None
        assert episode.primary_collection.name == "Campaign 4"


class TestVideoMetadata:
    """Tests for VideoMetadata model."""

    def test_video_metadata_basic(self):
        """Test basic video metadata."""
        metadata = VideoMetadata(
            resolution="1080p",
            video_codec="H.264",
            audio_codec="AAC",
            audio_channels="2.0",
        )

        assert metadata.resolution == "1080p"
        assert metadata.video_codec == "H.264"
        assert metadata.audio_codec == "AAC"
        assert metadata.audio_channels == "2.0"
        assert metadata.source_type == "WEB-DL"  # default
        assert metadata.container_format == "mkv"  # default

    def test_video_metadata_with_all_fields(self):
        """Test video metadata with all fields."""
        metadata = VideoMetadata(
            resolution="720p",
            video_codec="H.265",
            audio_codec="Opus",
            audio_channels="5.1",
            source_type="WEB-RIP",
            container_format="mp4",
        )

        assert metadata.resolution == "720p"
        assert metadata.source_type == "WEB-RIP"
        assert metadata.container_format == "mp4"


class TestDownloadJob:
    """Tests for DownloadJob model."""

    def test_download_job_basic(self):
        """Test basic download job."""
        episode = Episode(
            id="ep-200",
            title="Test Episode",
            slug="test-episode",
        )
        metadata = VideoMetadata(
            resolution="1080p",
            video_codec="H.264",
            audio_codec="AAC",
            audio_channels="2.0",
        )
        job = DownloadJob(
            episode=episode,
            metadata=metadata,
            output_path="/tmp/output.mkv",
        )

        assert job.episode.id == "ep-200"
        assert job.metadata.resolution == "1080p"
        assert job.output_path == "/tmp/output.mkv"
        assert job.status == "pending"  # default

    def test_download_job_status_change(self):
        """Test download job status."""
        episode = Episode(id="ep-201", title="Test", slug="test")
        metadata = VideoMetadata(
            resolution="1080p",
            video_codec="H.264",
            audio_codec="AAC",
            audio_channels="2.0",
        )
        job = DownloadJob(
            episode=episode,
            metadata=metadata,
            output_path="/tmp/output.mkv",
            status="downloading",
        )

        assert job.status == "downloading"
