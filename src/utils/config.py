"""Configuration management for Gmail Calendar Sync."""


from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Google APIs OAuth2 (shared for Gmail and Calendar)
    google_client_id: str = Field(..., env="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(..., env="GOOGLE_CLIENT_SECRET")
    google_refresh_token: str = Field(..., env="GOOGLE_REFRESH_TOKEN")

    # Legacy: Individual API settings (fallback compatibility)
    gmail_client_id: str | None = Field(None, env="GMAIL_CLIENT_ID")
    gmail_client_secret: str | None = Field(None, env="GMAIL_CLIENT_SECRET")
    gmail_refresh_token: str | None = Field(None, env="GMAIL_REFRESH_TOKEN")
    calendar_client_id: str | None = Field(None, env="CALENDAR_CLIENT_ID")
    calendar_client_secret: str | None = Field(None, env="CALENDAR_CLIENT_SECRET")
    calendar_refresh_token: str | None = Field(None, env="CALENDAR_REFRESH_TOKEN")

    # OpenAI API
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")

    # Optional settings
    slack_webhook_url: str | None = Field(None, env="SLACK_WEBHOOK_URL")
    sync_period_hours: int = Field(8, env="SYNC_PERIOD_HOURS")  # Default 8 hours
    sync_period_days: int = Field(30, env="SYNC_PERIOD_DAYS")   # Fallback for backward compatibility
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    # Date range settings (optional, overrides period settings)
    sync_start_date: str | None = Field(None, env="SYNC_START_DATE")
    sync_end_date: str | None = Field(None, env="SYNC_END_DATE")

    # Gmail settings
    gmail_label: str = "PROCESSED_BY_GMAIL_SYNC"

    # Supported email domains
    flight_domains: list[str] = ["ana.co.jp", "booking.jal.com"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def get_gmail_credentials(self) -> tuple[str, str, str]:
        """Get Gmail OAuth2 credentials (client_id, client_secret, refresh_token)."""
        # Use shared Google credentials if available, otherwise fall back to Gmail-specific
        client_id = self.google_client_id if hasattr(self, 'google_client_id') else self.gmail_client_id
        client_secret = self.google_client_secret if hasattr(self, 'google_client_secret') else self.gmail_client_secret
        refresh_token = self.google_refresh_token if hasattr(self, 'google_refresh_token') else self.gmail_refresh_token
        
        if not all([client_id, client_secret, refresh_token]):
            raise ValueError("Gmail OAuth2 credentials not properly configured")
        
        return client_id, client_secret, refresh_token
    
    def get_calendar_credentials(self) -> tuple[str, str, str]:
        """Get Calendar OAuth2 credentials (client_id, client_secret, refresh_token)."""
        # Use shared Google credentials if available, otherwise fall back to Calendar-specific
        client_id = self.google_client_id if hasattr(self, 'google_client_id') else self.calendar_client_id
        client_secret = self.google_client_secret if hasattr(self, 'google_client_secret') else self.calendar_client_secret
        refresh_token = self.google_refresh_token if hasattr(self, 'google_refresh_token') else self.calendar_refresh_token
        
        if not all([client_id, client_secret, refresh_token]):
            raise ValueError("Calendar OAuth2 credentials not properly configured")
        
        return client_id, client_secret, refresh_token


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
