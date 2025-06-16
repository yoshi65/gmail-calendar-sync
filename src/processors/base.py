"""Base email processor."""

from abc import ABC, abstractmethod

from ..models.calendar import CalendarEvent
from ..models.email_types import EmailMessage, ProcessingResult


class BaseEmailProcessor(ABC):
    """Base class for email processors."""

    @abstractmethod
    def can_process(self, email: EmailMessage) -> bool:
        """Check if this processor can handle the given email."""
        pass

    @abstractmethod
    def process(self, email: EmailMessage) -> ProcessingResult:
        """Process the email and return result."""
        pass

    @abstractmethod
    def extract_data(self, email: EmailMessage) -> dict | None:
        """Extract structured data from email."""
        pass

    @abstractmethod
    def create_calendar_events(
        self, extracted_data: dict, email: EmailMessage
    ) -> list[CalendarEvent]:
        """Create calendar events from extracted data."""
        pass
