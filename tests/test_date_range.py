"""Tests for date range and time period functionality."""

import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from src.services.gmail_client import GmailClient
from src.utils.config import Settings


class TestDateRangeAndTimeFeature:
    """Test date range and time period functionality."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.flight_domains = ["ana.co.jp", "booking.jal.com"]
        settings.gmail_label = "PROCESSED_BY_GMAIL_SYNC"
        settings.gmail_client_id = "test_id"
        settings.gmail_client_secret = "test_secret"
        settings.gmail_refresh_token = "test_token"
        return settings
    
    @pytest.fixture
    def gmail_client(self, mock_settings):
        """Create Gmail client with mocked service."""
        client = GmailClient(mock_settings)
        client._service = Mock()
        return client
    
    def test_date_range_config_from_env(self):
        """Test date range configuration from environment variables."""
        # Set environment variables
        os.environ["GMAIL_CLIENT_ID"] = "test_id"
        os.environ["GMAIL_CLIENT_SECRET"] = "test_secret"
        os.environ["GMAIL_REFRESH_TOKEN"] = "test_token"
        os.environ["CALENDAR_CLIENT_ID"] = "test_cal_id"
        os.environ["CALENDAR_CLIENT_SECRET"] = "test_cal_secret"
        os.environ["CALENDAR_REFRESH_TOKEN"] = "test_cal_token"
        os.environ["OPENAI_API_KEY"] = "test_openai_key"
        os.environ["SYNC_START_DATE"] = "2024-01-01"
        os.environ["SYNC_END_DATE"] = "2024-01-31"
        os.environ["SYNC_PERIOD_HOURS"] = "12"
        
        try:
            settings = Settings()
            
            assert settings.sync_start_date == "2024-01-01"
            assert settings.sync_end_date == "2024-01-31"
            assert settings.sync_period_hours == 12
            assert settings.sync_period_days == 30  # Default value
            
        finally:
            # Clean up environment variables
            for key in ["GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN",
                       "CALENDAR_CLIENT_ID", "CALENDAR_CLIENT_SECRET", "CALENDAR_REFRESH_TOKEN",
                       "OPENAI_API_KEY", "SYNC_START_DATE", "SYNC_END_DATE", "SYNC_PERIOD_HOURS"]:
                os.environ.pop(key, None)
    
    def test_search_emails_with_date_range(self, gmail_client):
        """Test email search with start and end dates."""
        # Mock the Gmail API response
        gmail_client._service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}, {"id": "msg2"}]
        }
        
        # Test with date range
        result = gmail_client.search_emails(
            query="from:ana.co.jp",
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        
        assert result == ["msg1", "msg2"]
        
        # Verify the query includes date filters
        call_args = gmail_client._service.users().messages().list.call_args
        query_param = call_args[1]["q"]
        assert "after:2024/01/01" in query_param
        assert "before:2024/01/31" in query_param
    
    def test_search_emails_with_start_date_only(self, gmail_client):
        """Test email search with start date only."""
        gmail_client._service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        
        result = gmail_client.search_emails(
            query="from:ana.co.jp",
            start_date="2024-01-01"
        )
        
        assert result == ["msg1"]
        
        call_args = gmail_client._service.users().messages().list.call_args
        query_param = call_args[1]["q"]
        assert "after:2024/01/01" in query_param
        assert "before:" not in query_param
    
    def test_search_emails_with_end_date_only(self, gmail_client):
        """Test email search with end date only."""
        gmail_client._service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        
        result = gmail_client.search_emails(
            query="from:ana.co.jp",
            end_date="2024-01-31"
        )
        
        assert result == ["msg1"]
        
        call_args = gmail_client._service.users().messages().list.call_args
        query_param = call_args[1]["q"]
        assert "before:2024/01/31" in query_param
        assert "after:" not in query_param
    
    def test_search_emails_date_range_overrides_since_days(self, gmail_client):
        """Test that date range takes precedence over since_days."""
        gmail_client._service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        
        result = gmail_client.search_emails(
            query="from:ana.co.jp",
            since_days=30,
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        
        call_args = gmail_client._service.users().messages().list.call_args
        query_param = call_args[1]["q"]
        
        # Should use date range, not since_days
        assert "after:2024/01/01" in query_param
        assert "before:2024/01/31" in query_param
        
        # Should not contain since_days calculation
        today = datetime.now()
        since_date = (today - timedelta(days=30)).strftime("%Y/%m/%d")
        assert f"after:{since_date}" not in query_param
    
    def test_search_emails_with_hours(self, gmail_client):
        """Test email search with hours-based filtering."""
        gmail_client._service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        
        result = gmail_client.search_emails(
            query="from:ana.co.jp",
            since_hours=8
        )
        
        assert result == ["msg1"]
        
        call_args = gmail_client._service.users().messages().list.call_args
        query_param = call_args[1]["q"]
        
        # Should use hours-based calculation (8 hours ago)
        expected_datetime = datetime.now() - timedelta(hours=8)
        expected_date = expected_datetime.strftime("%Y/%m/%d")
        assert f"after:{expected_date}" in query_param
    
    def test_search_emails_hours_priority_over_days(self, gmail_client):
        """Test that hours takes precedence over days."""
        gmail_client._service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        
        result = gmail_client.search_emails(
            query="from:ana.co.jp",
            since_days=30,
            since_hours=8  # Should take precedence
        )
        
        call_args = gmail_client._service.users().messages().list.call_args
        query_param = call_args[1]["q"]
        
        # Should use hours, not days
        expected_datetime = datetime.now() - timedelta(hours=8)
        expected_date = expected_datetime.strftime("%Y/%m/%d")
        assert f"after:{expected_date}" in query_param
        
        # Should not contain days calculation
        days_datetime = datetime.now() - timedelta(days=30)
        days_date = days_datetime.strftime("%Y/%m/%d")
        assert f"after:{days_date}" not in query_param
    
    def test_invalid_date_format_raises_error(self, gmail_client):
        """Test that invalid date format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid start_date format"):
            gmail_client.search_emails(
                query="from:ana.co.jp",
                start_date="01/01/2024"  # Wrong format
            )
        
        with pytest.raises(ValueError, match="Invalid end_date format"):
            gmail_client.search_emails(
                query="from:ana.co.jp",
                end_date="2024-13-01"  # Invalid date
            )
    
    @patch("src.services.gmail_client.GmailClient.get_email")
    def test_get_flight_emails_with_date_range(self, mock_get_email, gmail_client):
        """Test get_flight_emails with date range parameters."""
        # Mock email response
        mock_email = Mock()
        mock_get_email.return_value = mock_email
        
        gmail_client._service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        
        result = gmail_client.get_flight_emails(
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        
        assert len(result) == len(gmail_client.settings.flight_domains)  # One email per domain
        
        # Verify search was called with correct parameters
        call_args = gmail_client._service.users().messages().list.call_args
        query_param = call_args[1]["q"]
        assert "after:2024/01/01" in query_param
        assert "before:2024/01/31" in query_param
    
    @patch("src.services.gmail_client.GmailClient.get_email")
    def test_get_flight_emails_with_hours(self, mock_get_email, gmail_client):
        """Test get_flight_emails with hours parameter."""
        # Mock email response
        mock_email = Mock()
        mock_get_email.return_value = mock_email
        
        gmail_client._service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        
        result = gmail_client.get_flight_emails(since_hours=8)
        
        assert len(result) == len(gmail_client.settings.flight_domains)  # One email per domain
        
        # Verify search was called with correct parameters
        call_args = gmail_client._service.users().messages().list.call_args
        query_param = call_args[1]["q"]
        
        # Should use hours-based calculation
        expected_datetime = datetime.now() - timedelta(hours=8)
        expected_date = expected_datetime.strftime("%Y/%m/%d")
        assert f"after:{expected_date}" in query_param