from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True  # Allow both field names and aliases
    )

    release_group: str = Field(default="Pawsty", validation_alias="RELEASE_GROUP")
    preferred_resolution: str = Field(default="1080p", validation_alias="PREFERRED_RESOLUTION")
    source_type: str = Field(default="WEB-DL", validation_alias="SOURCE_TYPE")
    container_format: str = Field(default="mkv", validation_alias="CONTAINER_FORMAT")

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
