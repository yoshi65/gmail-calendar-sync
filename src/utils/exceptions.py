"""Custom exceptions for Gmail Calendar Sync."""


class GmailCalendarSyncError(Exception):
    """Base exception for Gmail Calendar Sync errors."""
    pass


class ConfigurationError(GmailCalendarSyncError):
    """Raised when there's a configuration issue."""
    pass


class GmailAPIError(GmailCalendarSyncError):
    """Raised when Gmail API operations fail."""
    pass


class CalendarAPIError(GmailCalendarSyncError):
    """Raised when Calendar API operations fail."""
    pass


class OpenAIAPIError(GmailCalendarSyncError):
    """Raised when OpenAI API operations fail."""
    pass


class EmailProcessingError(GmailCalendarSyncError):
    """Raised when email processing fails."""
    pass


class DataExtractionError(EmailProcessingError):
    """Raised when data extraction from email fails."""
    pass


class CalendarEventCreationError(EmailProcessingError):
    """Raised when calendar event creation fails."""
    pass
