"""Configuration management for Gmail Calendar Sync."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Google APIs OAuth2 (shared for Gmail and Calendar)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""

    # Legacy: Individual API settings (fallback compatibility)
    gmail_client_id: str | None = None
    gmail_client_secret: str | None = None
    gmail_refresh_token: str | None = None
    calendar_client_id: str | None = None
    calendar_client_secret: str | None = None
    calendar_refresh_token: str | None = None

    # OpenAI API
    openai_api_key: str = ""

    # Optional settings
    slack_webhook_url: str | None = None
    sync_period_hours: int = 3  # Default 3 hours (optimized for 1-hour cron interval)
    sync_period_days: int = 30  # Fallback for backward compatibility
    log_level: str = "INFO"

    # Date range settings (optional, overrides period settings)
    sync_start_date: str | None = None
    sync_end_date: str | None = None

    # Gmail settings
    gmail_label: str = "PROCESSED_BY_GMAIL_SYNC"

    # Supported email domains
    flight_domains: list[str] = ["ana.co.jp", "booking.jal.com"]
    carshare_domains: list[str] = ["carshares.jp", "share.timescar.jp"]

    @property
    def all_supported_domains(self) -> list[str]:
        """Get all supported email domains."""
        return self.flight_domains + self.carshare_domains

    def get_gmail_credentials(self) -> tuple[str, str, str]:
        """Get Gmail OAuth2 credentials (client_id, client_secret, refresh_token)."""
        # Use shared Google credentials if available, otherwise fall back to Gmail-specific
        client_id = self.google_client_id or self.gmail_client_id
        client_secret = self.google_client_secret or self.gmail_client_secret
        refresh_token = self.google_refresh_token or self.gmail_refresh_token

        if not all([client_id, client_secret, refresh_token]):
            raise ValueError("Gmail OAuth2 credentials not properly configured")

        # Type checker now knows these are not None due to the check above
        assert client_id is not None
        assert client_secret is not None
        assert refresh_token is not None

        return client_id, client_secret, refresh_token

    def get_calendar_credentials(self) -> tuple[str, str, str]:
        """Get Calendar OAuth2 credentials (client_id, client_secret, refresh_token)."""
        # Use shared Google credentials if available, otherwise fall back to Calendar-specific
        client_id = self.google_client_id or self.calendar_client_id
        client_secret = self.google_client_secret or self.calendar_client_secret
        refresh_token = self.google_refresh_token or self.calendar_refresh_token

        if not all([client_id, client_secret, refresh_token]):
            raise ValueError("Calendar OAuth2 credentials not properly configured")

        # Type checker now knows these are not None due to the check above
        assert client_id is not None
        assert client_secret is not None
        assert refresh_token is not None

        return client_id, client_secret, refresh_token


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
