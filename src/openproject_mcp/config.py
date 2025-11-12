from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AnyHttpUrl


class Settings(BaseSettings):
    """OpenProject MCP Server configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Will read from OPENPROJECT_URL or OPENPROJECT_BASE_URL
    url: AnyHttpUrl = Field(
        ...,
        description="OpenProject instance URL (e.g. https://openproject.example.com)",
        validation_alias="OPENPROJECT_URL",
    )

    # Will read from OPENPROJECT_API_KEY or OPENPROJECT_API_TOKEN
    api_key: str = Field(
        ...,
        description="API key with API v3 access",
        validation_alias="OPENPROJECT_API_KEY",
    )

    connect_timeout: float = Field(
        default=10.0, description="Connection timeout in seconds"
    )
    read_timeout: float = Field(default=10.0, description="Read timeout in seconds")
    max_retries: int = Field(
        default=3, description="Maximum number of retries for failed requests"
    )
    page_size_default: int = Field(
        default=25, description="Default page size for paginated requests"
    )
    page_size_max: int = Field(
        default=200, description="Maximum page size for paginated requests"
    )
