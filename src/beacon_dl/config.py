from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import re

class Settings(BaseSettings):
    """Configuration settings for Beacon TV downloader.

    All user-controllable settings are validated to prevent injection attacks.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True  # Allow both field names and aliases
    )

    release_group: str = Field(default="Pawsty", validation_alias="RELEASE_GROUP")
    preferred_resolution: str = Field(default="1080p", validation_alias="PREFERRED_RESOLUTION")
    source_type: str = Field(default="WEB-DL", validation_alias="SOURCE_TYPE")
    container_format: str = Field(default="mkv", validation_alias="CONTAINER_FORMAT")

    @field_validator('release_group', 'source_type', 'default_audio_codec', 'default_video_codec')
    @classmethod
    def validate_alphanum_with_symbols(cls, v: str) -> str:
        """Validate alphanumeric fields with common symbols.

        Security: Prevents shell metacharacter injection.
        Allows: alphanumeric, dots, hyphens, underscores.
        """
        if not v:
            raise ValueError('Value cannot be empty')
        if not re.match(r'^[a-zA-Z0-9._-]+$', v):
            raise ValueError(
                f'Invalid value: "{v}". '
                'Only alphanumeric characters, dots, hyphens, and underscores allowed.'
            )
        if len(v) > 100:
            raise ValueError(f'Value too long (max 100 characters)')
        return v

    @field_validator('container_format')
    @classmethod
    def validate_container_format(cls, v: str) -> str:
        """Validate container format against whitelist."""
        allowed = ['mkv', 'mp4', 'avi', 'mov', 'webm', 'flv', 'm4v']
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(
                f'Unsupported format: "{v}". Allowed: {", ".join(allowed)}'
            )
        return v_lower

    @field_validator('preferred_resolution')
    @classmethod
    def validate_resolution(cls, v: str) -> str:
        """Validate video resolution format (e.g., 1080p, 720p)."""
        if not re.match(r'^\d{3,4}p$', v):
            raise ValueError(
                f'Invalid resolution: "{v}". Expected format: XXXp (e.g., 1080p)'
            )
        return v

    @field_validator('default_audio_channels')
    @classmethod
    def validate_audio_channels(cls, v: str) -> str:
        """Validate audio channel configuration."""
        if not re.match(r'^\d+\.\d+$', v):
            raise ValueError(
                f'Invalid audio channels: "{v}". Expected format: X.Y (e.g., 2.0, 5.1)'
            )
        return v

    # Audio defaults
    default_audio_codec: str = Field(default="AAC", validation_alias="DEFAULT_AUDIO_CODEC")
    default_audio_channels: str = Field(default="2.0", validation_alias="DEFAULT_AUDIO_CHANNELS")
    default_video_codec: str = Field(default="H.264", validation_alias="DEFAULT_VIDEO_CODEC")

    # Browser
    user_agent: str = Field(
        default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        validation_alias="USER_AGENT"
    )

    # Auth
    beacon_username: Optional[str] = Field(default=None, validation_alias="BEACON_USERNAME")
    beacon_password: Optional[str] = Field(default=None, validation_alias="BEACON_PASSWORD")
    browser_profile: Optional[str] = Field(default=None, validation_alias="BROWSER_PROFILE")

    # Debug
    debug: bool = Field(default=False, validation_alias="DEBUG")

settings = Settings()
