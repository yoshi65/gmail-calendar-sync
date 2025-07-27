"""Tests for exceptions module."""

import pytest

from src.utils.exceptions import (
    CalendarAPIError,
    CalendarEventCreationError,
    ConfigurationError,
    DataExtractionError,
    EmailProcessingError,
    GmailAPIError,
    GmailCalendarSyncError,
    OpenAIAPIError,
)


class TestGmailCalendarSyncError:
    """Test base exception class."""

    def test_basic_exception(self):
        """Test basic exception creation."""
        error = GmailCalendarSyncError("Test error")
        assert str(error) == "Test error"
        assert error.args == ("Test error",)

    def test_exception_with_cause(self):
        """Test exception with underlying cause."""
        original_error = ValueError("Original error")
        try:
            raise GmailCalendarSyncError("Wrapper error") from original_error
        except GmailCalendarSyncError as error:
            assert str(error) == "Wrapper error"
            assert error.__cause__ == original_error

    def test_exception_inheritance(self):
        """Test that custom exception inherits from Exception."""
        error = GmailCalendarSyncError("Test")
        assert isinstance(error, Exception)


class TestConfigurationError:
    """Test configuration error."""

    def test_configuration_error(self):
        """Test configuration error creation."""
        error = ConfigurationError("Missing API key")
        assert str(error) == "Missing API key"
        assert isinstance(error, GmailCalendarSyncError)

    def test_configuration_error_with_details(self):
        """Test configuration error with detailed message."""
        error = ConfigurationError("Invalid configuration")
        assert "Invalid configuration" in str(error)
        assert isinstance(error, GmailCalendarSyncError)


class TestGmailAPIError:
    """Test Gmail API error."""

    def test_gmail_api_error(self):
        """Test Gmail API error creation."""
        error = GmailAPIError("Token expired")
        assert str(error) == "Token expired"
        assert isinstance(error, GmailCalendarSyncError)

    def test_gmail_api_error_details(self):
        """Test Gmail API error with details."""
        error = GmailAPIError("OAuth refresh failed")
        assert "OAuth refresh failed" in str(error)


class TestEmailProcessingError:
    """Test email processing error."""

    def test_email_processing_error(self):
        """Test email processing error creation."""
        error = EmailProcessingError("Failed to parse email content")
        assert str(error) == "Failed to parse email content"
        assert isinstance(error, GmailCalendarSyncError)

    def test_email_processing_error_with_email_id(self):
        """Test email processing error with email ID."""
        error = EmailProcessingError("Parsing failed")
        assert "Parsing failed" in str(error)
        assert isinstance(error, GmailCalendarSyncError)


class TestCalendarAPIError:
    """Test calendar API error."""

    def test_calendar_api_error(self):
        """Test calendar API error creation."""
        error = CalendarAPIError("Failed to create event")
        assert str(error) == "Failed to create event"
        assert isinstance(error, GmailCalendarSyncError)

    def test_calendar_api_error_with_details(self):
        """Test calendar API error with details."""
        error = CalendarAPIError("Event creation failed")
        assert "Event creation failed" in str(error)


class TestOpenAIAPIError:
    """Test OpenAI API error."""

    def test_openai_api_error(self):
        """Test OpenAI API error creation."""
        error = OpenAIAPIError("API rate limit exceeded")
        assert str(error) == "API rate limit exceeded"
        assert isinstance(error, GmailCalendarSyncError)

    def test_openai_api_error_details(self):
        """Test OpenAI API error with details."""
        error = OpenAIAPIError("Request failed")
        assert "Request failed" in str(error)


class TestExceptionHierarchy:
    """Test exception hierarchy and relationships."""

    def test_all_exceptions_inherit_from_base(self):
        """Test that all custom exceptions inherit from GmailCalendarSyncError."""
        exceptions = [
            ConfigurationError("test"),
            GmailAPIError("test"),
            EmailProcessingError("test"),
            CalendarAPIError("test"),
            OpenAIAPIError("test"),
            DataExtractionError("test"),
            CalendarEventCreationError("test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, GmailCalendarSyncError)
            assert isinstance(exc, Exception)

    def test_exception_types_are_distinct(self):
        """Test that different exception types can be distinguished."""
        config_error = ConfigurationError("config")
        gmail_error = GmailAPIError("gmail")

        assert type(config_error) is not type(gmail_error)
        assert not isinstance(config_error, GmailAPIError)
        assert not isinstance(gmail_error, ConfigurationError)

    def test_exception_catching(self):
        """Test that exceptions can be caught properly."""
        # Test catching specific exception
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Config error")

        # Test catching base exception
        with pytest.raises(GmailCalendarSyncError):
            raise GmailAPIError("Gmail error")

        # Test catching general exception
        with pytest.raises(CalendarAPIError):
            raise CalendarAPIError("Calendar error")
