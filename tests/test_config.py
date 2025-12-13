"""Tests for config.py - Settings validation.

This module tests the Pydantic Settings model including:
- Default values
- Validation of various fields
- Environment variable loading
- Security validators for injection prevention
"""

import pytest
from pydantic import ValidationError

from src.beacon_dl.config import Settings

pytestmark = pytest.mark.unit  # All tests in this module are unit tests

# =============================================================================
# Default Values Tests
# =============================================================================


class TestDefaultSettings:
    """Tests for default settings values."""

    def test_default_resolution(self):
        """Test default preferred resolution is 1080p."""
        settings = Settings()
        assert settings.preferred_resolution == "1080p"

    def test_default_source_type(self):
        """Test default source type is WEB-DL."""
        settings = Settings()
        assert settings.source_type == "WEB-DL"

    def test_default_container_format(self):
        """Test default container format is mkv."""
        settings = Settings()
        assert settings.container_format == "mkv"

    def test_default_audio_codec(self):
        """Test default audio codec is AAC."""
        settings = Settings()
        assert settings.default_audio_codec == "AAC"

    def test_default_audio_channels(self):
        """Test default audio channels is 2.0."""
        settings = Settings()
        assert settings.default_audio_channels == "2.0"

    def test_default_video_codec(self):
        """Test default video codec is H.264."""
        settings = Settings()
        assert settings.default_video_codec == "H.264"

    def test_default_debug_false(self):
        """Test debug is disabled by default."""
        settings = Settings()
        assert settings.debug is False

    def test_default_credentials_none(self, monkeypatch):
        """Test credentials are None by default when not in env."""
        # Clear any existing credentials from environment
        monkeypatch.delenv("BEACON_USERNAME", raising=False)
        monkeypatch.delenv("BEACON_PASSWORD", raising=False)
        # Create settings without loading .env file
        settings = Settings(_env_file=None)
        assert settings.beacon_username is None
        assert settings.beacon_password is None

    def test_default_cookie_buffer_hours(self):
        """Test default cookie expiry buffer is 6 hours."""
        settings = Settings()
        assert settings.cookie_expiry_buffer_hours == 6

    def test_default_release_group(self):
        """Test default release group is Pawsty."""
        settings = Settings()
        assert settings.release_group == "Pawsty"

    def test_default_user_agent(self):
        """Test default user agent is a Chrome user agent."""
        settings = Settings()
        assert "Chrome" in settings.user_agent
        assert "Mozilla" in settings.user_agent


# =============================================================================
# Resolution Validation Tests
# =============================================================================


class TestResolutionValidation:
    """Tests for preferred_resolution field validation."""

    @pytest.mark.parametrize(
        "resolution",
        [
            "1080p",
            "720p",
            "480p",
            "360p",
            "2160p",  # 4K
        ],
        ids=["1080p", "720p", "480p", "360p", "4k"],
    )
    def test_valid_resolutions(self, resolution):
        """Test valid resolution formats are accepted."""
        settings = Settings(preferred_resolution=resolution)
        assert settings.preferred_resolution == resolution

    @pytest.mark.parametrize(
        "resolution",
        [
            "1080",  # Missing p
            "1080P",  # Uppercase P
            "1080px",  # Extra suffix
            "fullhd",  # Word instead of number
            "hd",
            "4k",  # Should be 2160p
            "",  # Empty
            "1080p; rm -rf /",  # Injection attempt
        ],
        ids=[
            "missing_p",
            "uppercase_p",
            "extra_suffix",
            "word_fullhd",
            "word_hd",
            "4k_word",
            "empty",
            "injection",
        ],
    )
    def test_invalid_resolutions_rejected(self, resolution):
        """Test invalid resolution formats are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(preferred_resolution=resolution)
        assert "preferred_resolution" in str(exc_info.value)


# =============================================================================
# Container Format Validation Tests
# =============================================================================


class TestContainerFormatValidation:
    """Tests for container_format field validation."""

    @pytest.mark.parametrize(
        "format_value,expected",
        [
            ("mkv", "mkv"),
            ("MKV", "mkv"),  # Lowercased
            ("mp4", "mp4"),
            ("MP4", "mp4"),
            ("avi", "avi"),
            ("mov", "mov"),
            ("webm", "webm"),
            ("flv", "flv"),
            ("m4v", "m4v"),
        ],
        ids=["mkv", "mkv_upper", "mp4", "mp4_upper", "avi", "mov", "webm", "flv", "m4v"],
    )
    def test_valid_container_formats(self, format_value, expected):
        """Test valid container formats are accepted and lowercased."""
        settings = Settings(container_format=format_value)
        assert settings.container_format == expected

    @pytest.mark.parametrize(
        "format_value",
        [
            "wmv",  # Not in whitelist
            "ogg",
            "ts",
            "",
            "mkv; rm -rf /",  # Injection
            "../etc/passwd",  # Path traversal
        ],
        ids=["wmv", "ogg", "ts", "empty", "injection", "path_traversal"],
    )
    def test_invalid_container_formats_rejected(self, format_value):
        """Test invalid container formats are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(container_format=format_value)
        assert "container_format" in str(exc_info.value)


# =============================================================================
# Source Type Validation Tests
# =============================================================================


class TestSourceTypeValidation:
    """Tests for source_type field validation."""

    @pytest.mark.parametrize(
        "source_type",
        [
            "WEB-DL",
            "WEBRip",
            "HDTV",
            "BluRay",
            "DVDRip",
            "Custom_Source.v2",
        ],
        ids=["web_dl", "webrip", "hdtv", "bluray", "dvdrip", "custom_with_dot"],
    )
    def test_valid_source_types(self, source_type):
        """Test valid source types are accepted."""
        settings = Settings(source_type=source_type)
        assert settings.source_type == source_type

    @pytest.mark.parametrize(
        "source_type",
        [
            "",  # Empty
            "WEB-DL; rm -rf /",  # Injection
            "Source$(whoami)",  # Command substitution
            "Source`id`",  # Backticks
            "A" * 101,  # Too long
        ],
        ids=["empty", "injection", "command_sub", "backticks", "too_long"],
    )
    def test_invalid_source_types_rejected(self, source_type):
        """Test invalid source types are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(source_type=source_type)
        assert "source_type" in str(exc_info.value)


# =============================================================================
# Audio Channels Validation Tests
# =============================================================================


class TestAudioChannelsValidation:
    """Tests for default_audio_channels field validation."""

    @pytest.mark.parametrize(
        "channels",
        [
            "2.0",
            "5.1",
            "7.1",
            "1.0",
        ],
        ids=["stereo", "surround", "7.1", "mono"],
    )
    def test_valid_audio_channels(self, channels):
        """Test valid audio channel formats are accepted."""
        settings = Settings(default_audio_channels=channels)
        assert settings.default_audio_channels == channels

    @pytest.mark.parametrize(
        "channels",
        [
            "2",  # Missing decimal
            "stereo",  # Word
            "2.0.1",  # Too many parts
            "",  # Empty
            "2.0; id",  # Injection
        ],
        ids=["no_decimal", "word", "too_many_parts", "empty", "injection"],
    )
    def test_invalid_audio_channels_rejected(self, channels):
        """Test invalid audio channel formats are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(default_audio_channels=channels)
        assert "default_audio_channels" in str(exc_info.value)


# =============================================================================
# Release Group Validation Tests
# =============================================================================


class TestReleaseGroupValidation:
    """Tests for release_group field validation."""

    @pytest.mark.parametrize(
        "release_group",
        [
            "Pawsty",
            "Kitsune",
            "My-Group",
            "Group_123",
            "ABC123",
        ],
        ids=["pawsty", "kitsune", "with_hyphen", "with_underscore", "alphanumeric"],
    )
    def test_valid_release_groups(self, release_group):
        """Test valid release group values are accepted."""
        settings = Settings(release_group=release_group)
        assert settings.release_group == release_group

    @pytest.mark.parametrize(
        "release_group",
        [
            "",  # Empty
            "Invalid!Group",  # Special char
            "Group With Spaces",  # Spaces
            "Group;rm -rf",  # Injection
            "A" * 51,  # Too long
        ],
        ids=["empty", "special_char", "spaces", "injection", "too_long"],
    )
    def test_invalid_release_groups_rejected(self, release_group):
        """Test invalid release group values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(release_group=release_group)
        assert "release_group" in str(exc_info.value)


# =============================================================================
# Cookie Buffer Hours Validation Tests
# =============================================================================


class TestCookieBufferHoursValidation:
    """Tests for cookie_expiry_buffer_hours field validation."""

    @pytest.mark.parametrize(
        "hours",
        [0, 1, 6, 12, 24],
        ids=["zero", "one", "six", "twelve", "twentyfour"],
    )
    def test_valid_buffer_hours(self, hours):
        """Test valid buffer hours are accepted."""
        settings = Settings(cookie_expiry_buffer_hours=hours)
        assert settings.cookie_expiry_buffer_hours == hours

    @pytest.mark.parametrize(
        "hours",
        [-1, 25, 100],
        ids=["negative", "over_24", "way_over"],
    )
    def test_invalid_buffer_hours_rejected(self, hours):
        """Test invalid buffer hours are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(cookie_expiry_buffer_hours=hours)
        assert "cookie_expiry_buffer_hours" in str(exc_info.value)


# =============================================================================
# Environment Variable Loading Tests
# =============================================================================


class TestEnvironmentVariables:
    """Tests for environment variable loading."""

    def test_load_resolution_from_env(self, monkeypatch):
        """Test loading preferred resolution from environment."""
        monkeypatch.setenv("PREFERRED_RESOLUTION", "720p")
        settings = Settings()
        assert settings.preferred_resolution == "720p"

    def test_load_container_format_from_env(self, monkeypatch):
        """Test loading container format from environment."""
        monkeypatch.setenv("CONTAINER_FORMAT", "mp4")
        settings = Settings()
        assert settings.container_format == "mp4"

    def test_load_source_type_from_env(self, monkeypatch):
        """Test loading source type from environment."""
        monkeypatch.setenv("SOURCE_TYPE", "WEBRip")
        settings = Settings()
        assert settings.source_type == "WEBRip"

    def test_load_debug_from_env(self, monkeypatch):
        """Test loading debug flag from environment."""
        monkeypatch.setenv("DEBUG", "true")
        settings = Settings()
        assert settings.debug is True

    def test_load_credentials_from_env(self, monkeypatch):
        """Test loading credentials from environment."""
        monkeypatch.setenv("BEACON_USERNAME", "user@example.com")
        monkeypatch.setenv("BEACON_PASSWORD", "secret123")
        settings = Settings()
        assert settings.beacon_username == "user@example.com"
        assert settings.beacon_password == "secret123"

    def test_load_cookie_buffer_from_env(self, monkeypatch):
        """Test loading cookie buffer hours from environment."""
        monkeypatch.setenv("COOKIE_EXPIRY_BUFFER_HOURS", "12")
        settings = Settings()
        assert settings.cookie_expiry_buffer_hours == 12


# =============================================================================
# Security Validation Tests
# =============================================================================


class TestSecurityValidation:
    """Tests for security-related validation."""

    @pytest.mark.parametrize(
        "field_name,value",
        [
            ("source_type", "WEB-DL; rm -rf /"),
            ("source_type", "$(whoami)"),
            ("source_type", "`id`"),
            ("source_type", "test|cat /etc/passwd"),
            ("default_audio_codec", "AAC; id"),
            ("default_video_codec", "H.264 && ls"),
        ],
        ids=[
            "semicolon_injection",
            "command_substitution",
            "backtick_injection",
            "pipe_injection",
            "audio_codec_injection",
            "video_codec_injection",
        ],
    )
    def test_injection_prevention(self, field_name, value):
        """Test shell injection attempts are rejected."""
        with pytest.raises(ValidationError):
            Settings(**{field_name: value})

    def test_path_traversal_prevention(self):
        """Test path traversal attempts are rejected."""
        with pytest.raises(ValidationError):
            Settings(container_format="../../../etc/passwd")

    def test_max_length_enforcement(self):
        """Test maximum length enforcement."""
        long_value = "A" * 101
        with pytest.raises(ValidationError):
            Settings(source_type=long_value)


# =============================================================================
# Full Settings Creation Tests
# =============================================================================


class TestFullSettingsCreation:
    """Tests for creating Settings with multiple custom values."""

    def test_create_with_all_custom_values(self, monkeypatch):
        """Test creating Settings with all custom values."""
        monkeypatch.setenv("PREFERRED_RESOLUTION", "720p")
        monkeypatch.setenv("CONTAINER_FORMAT", "mp4")
        monkeypatch.setenv("SOURCE_TYPE", "WEBRip")
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEFAULT_AUDIO_CODEC", "Opus")
        monkeypatch.setenv("DEFAULT_AUDIO_CHANNELS", "5.1")
        monkeypatch.setenv("DEFAULT_VIDEO_CODEC", "H.265")
        monkeypatch.setenv("COOKIE_EXPIRY_BUFFER_HOURS", "12")

        settings = Settings()

        assert settings.preferred_resolution == "720p"
        assert settings.container_format == "mp4"
        assert settings.source_type == "WEBRip"
        assert settings.debug is True
        assert settings.default_audio_codec == "Opus"
        assert settings.default_audio_channels == "5.1"
        assert settings.default_video_codec == "H.265"
        assert settings.cookie_expiry_buffer_hours == 12

    def test_settings_extra_ignored(self, monkeypatch):
        """Test that unknown environment variables are ignored."""
        monkeypatch.setenv("UNKNOWN_SETTING", "some_value")
        # Should not raise
        settings = Settings()
        assert not hasattr(settings, "unknown_setting")
