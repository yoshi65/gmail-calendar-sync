"""Tests for configuration management."""

import os
import pytest

from src.utils.config import Settings, get_settings


class TestSettings:
    """Test Settings model."""
    
    def test_default_values(self):
        """Test default configuration values."""
        # Mock required environment variables
        env_vars = {
            "GMAIL_CLIENT_ID": "test_gmail_client_id",
            "GMAIL_CLIENT_SECRET": "test_gmail_secret",
            "GMAIL_REFRESH_TOKEN": "test_gmail_token",
            "CALENDAR_CLIENT_ID": "test_calendar_client_id",
            "CALENDAR_CLIENT_SECRET": "test_calendar_secret",
            "CALENDAR_REFRESH_TOKEN": "test_calendar_token",
            "OPENAI_API_KEY": "test_openai_key",
        }
        
        for key, value in env_vars.items():
            os.environ[key] = value
        
        try:
            settings = Settings()
            
            # Test required fields
            assert settings.gmail_client_id == "test_gmail_client_id"
            assert settings.openai_api_key == "test_openai_key"
            
            # Test default values
            assert settings.sync_period_days == 30
            assert settings.log_level == "INFO"
            assert settings.gmail_label == "PROCESSED_BY_GMAIL_SYNC"
            assert settings.flight_domains == ["ana.co.jp", "booking.jal.com"]
            assert settings.slack_webhook_url is None
            
        finally:
            # Clean up environment variables
            for key in env_vars:
                os.environ.pop(key, None)
    
    def test_environment_override(self):
        """Test environment variable override."""
        env_vars = {
            "GMAIL_CLIENT_ID": "test_gmail_client_id",
            "GMAIL_CLIENT_SECRET": "test_gmail_secret",
            "GMAIL_REFRESH_TOKEN": "test_gmail_token",
            "CALENDAR_CLIENT_ID": "test_calendar_client_id",
            "CALENDAR_CLIENT_SECRET": "test_calendar_secret",
            "CALENDAR_REFRESH_TOKEN": "test_calendar_token",
            "OPENAI_API_KEY": "test_openai_key",
            "SYNC_PERIOD_DAYS": "7",
            "LOG_LEVEL": "DEBUG",
            "SLACK_WEBHOOK_URL": "https://hooks.slack.com/test",
        }
        
        for key, value in env_vars.items():
            os.environ[key] = value
        
        try:
            settings = Settings()
            
            assert settings.sync_period_days == 7
            assert settings.log_level == "DEBUG"
            assert settings.slack_webhook_url == "https://hooks.slack.com/test"
            
        finally:
            # Clean up environment variables
            for key in env_vars:
                os.environ.pop(key, None)


def test_get_settings():
    """Test get_settings function."""
    env_vars = {
        "GMAIL_CLIENT_ID": "test_gmail_client_id",
        "GMAIL_CLIENT_SECRET": "test_gmail_secret",
        "GMAIL_REFRESH_TOKEN": "test_gmail_token",
        "CALENDAR_CLIENT_ID": "test_calendar_client_id",
        "CALENDAR_CLIENT_SECRET": "test_calendar_secret",
        "CALENDAR_REFRESH_TOKEN": "test_calendar_token",
        "OPENAI_API_KEY": "test_openai_key",
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    try:
        settings = get_settings()
        assert isinstance(settings, Settings)
        assert settings.gmail_client_id == "test_gmail_client_id"
        
    finally:
        # Clean up environment variables
        for key in env_vars:
            os.environ.pop(key, None)