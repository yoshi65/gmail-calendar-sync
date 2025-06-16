"""Email type definitions."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EmailType(str, Enum):
    """Supported email types."""

    FLIGHT = "flight"
    CAR_SHARE = "car_share"
    RESTAURANT = "restaurant"


class EmailMessage(BaseModel):
    """Email message data."""

    id: str
    subject: str
    sender: str
    body: str
    received_at: datetime
    thread_id: str
    labels: list[str] = Field(default_factory=list)

    @property
    def domain(self) -> str:
        """Extract domain from sender email."""
        if "@" in self.sender:
            domain_part = self.sender.split("@")[-1].lower()
            # Remove any trailing > or other characters
            if ">" in domain_part:
                domain_part = domain_part.split(">")[0]
            return domain_part.strip()
        return ""


class ProcessingResult(BaseModel):
    """Result of email processing."""

    email_id: str
    email_type: EmailType
    success: bool
    extracted_data: dict[str, Any] | None = None
    error_message: str | None = None
    calendar_event_id: str | None = None
