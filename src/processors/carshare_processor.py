"""Car sharing email processor."""

from datetime import datetime, timedelta
from typing import Any

import structlog

from ..models.calendar import CalendarEvent, create_carshare_events
from ..models.carshare import BookingStatus, CarShareBooking, get_provider_from_domain
from ..models.email_types import EmailMessage, EmailType, ProcessingResult
from ..services.calendar_client import CalendarClient
from ..services.openai_client import OpenAIClient
from ..utils.config import Settings
from ..utils.email_filter import is_likely_booking_email, is_promotional_email
from .base import BaseEmailProcessor

logger = structlog.get_logger()


class CarShareEmailProcessor(BaseEmailProcessor):
    """Processor for car sharing booking emails."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.openai_client = OpenAIClient(settings)
        self.calendar_client = CalendarClient(settings)

    def can_process(self, email: EmailMessage) -> bool:
        """Check if this email is from a car sharing domain or a forwarded car sharing email."""
        # Check if email is from a car sharing domain directly
        provider = get_provider_from_domain(email.domain)
        if provider is not None:
            return True

        # Check if email is from a forwarded email address
        sender_email = email.sender.lower()
        for forwarded_email in self.settings.forwarded_from_email_list:
            if forwarded_email.lower() in sender_email:
                # For forwarded emails, check if body/subject contains car sharing-related keywords
                content = (email.subject + " " + email.body).lower()

                # Check for car sharing-related keywords in content
                carshare_keywords = [
                    "カーシェア", "タイムズカー", "timescar", "carshare",
                    "レンタカー", "rental car", "予約完了", "利用明細"
                ]

                if any(keyword in content for keyword in carshare_keywords):
                    return True

        return False

    def process(self, email: EmailMessage) -> ProcessingResult:
        """Process car sharing booking email."""
        logger.info(
            "Processing car sharing email",
            email_id=email.id,
            subject=email.subject[:100],
            domain=email.domain,
        )

        try:
            # Quick check if email is likely a booking email based on subject
            if not is_likely_booking_email(email):
                logger.info(
                    "Skipping non-booking email based on subject",
                    email_id=email.id,
                    subject=email.subject[:100],
                )
                return ProcessingResult(
                    email_id=email.id,
                    email_type=EmailType.CAR_SHARE,
                    success=False,
                    error_message="No car sharing information found in email",
                )

            # Check if email is promotional before sending to OpenAI
            if is_promotional_email(email):
                logger.info(
                    "Skipping promotional email",
                    email_id=email.id,
                    subject=email.subject[:100],
                )
                return ProcessingResult(
                    email_id=email.id,
                    email_type=EmailType.CAR_SHARE,
                    success=False,
                    error_message="Skipped promotional email",
                )

            # Extract car sharing data using OpenAI
            extracted_data = self.extract_data(email)

            if not extracted_data:
                return ProcessingResult(
                    email_id=email.id,
                    email_type=EmailType.CAR_SHARE,
                    success=False,
                    error_message="No car sharing information found in email",
                )

            # Create calendar events
            calendar_events = self.create_calendar_events(extracted_data, email)

            # Check if this was a successful cancellation (no events created is expected)
            carshare_booking = CarShareBooking(**extracted_data)
            if carshare_booking.status == BookingStatus.CANCELLED:
                return ProcessingResult(
                    email_id=email.id,
                    email_type=EmailType.CAR_SHARE,
                    success=True,
                    extracted_data=extracted_data,
                )

            if not calendar_events:
                return ProcessingResult(
                    email_id=email.id,
                    email_type=EmailType.CAR_SHARE,
                    success=False,
                    extracted_data=extracted_data,
                    error_message="Failed to create calendar events",
                )

            return ProcessingResult(
                email_id=email.id,
                email_type=EmailType.CAR_SHARE,
                success=True,
                extracted_data=extracted_data,
            )

        except Exception as e:
            logger.error(
                "Failed to process car sharing email", email_id=email.id, error=str(e)
            )

            return ProcessingResult(
                email_id=email.id,
                email_type=EmailType.CAR_SHARE,
                success=False,
                error_message=f"Processing error: {str(e)}",
            )

    def extract_data(self, email: EmailMessage) -> dict | None:
        """Extract car sharing booking data from email."""
        try:
            # Get provider from domain
            provider = get_provider_from_domain(email.domain)
            if not provider:
                logger.warning("Unknown car sharing provider", domain=email.domain)
                return None

            carshare_booking = self.openai_client.extract_carshare_info(
                email.body, email.subject, provider.value
            )

            if carshare_booking:
                # Add email metadata
                carshare_data = carshare_booking.model_dump()
                carshare_data["email_received_at"] = email.received_at.isoformat()
                return carshare_data

            return None

        except Exception as e:
            logger.error(
                "Failed to extract car sharing data", email_id=email.id, error=str(e)
            )
            return None

    def create_calendar_events(
        self, extracted_data: dict, email: EmailMessage
    ) -> list[CalendarEvent]:
        """Create or update calendar events from car sharing booking data."""
        try:
            # Convert dict back to CarShareBooking model
            carshare_booking = CarShareBooking(**extracted_data)

            # Check for overlapping bookings (time-based conflict detection)
            overlapping_events = self.find_overlapping_events(carshare_booking)

            # Special handling for cancelled bookings - just remove existing events
            if carshare_booking.status == BookingStatus.CANCELLED:
                if overlapping_events:
                    logger.info(
                        "Deleting cancelled car sharing events",
                        email_id=email.id,
                        booking_reference=carshare_booking.booking_reference,
                        overlapping_count=len(overlapping_events),
                    )

                    # Delete all overlapping events for cancelled booking
                    deleted_count = 0
                    for old_event in overlapping_events:
                        if self.calendar_client.delete_event(old_event["id"]):
                            deleted_count += 1
                            logger.info(
                                "Deleted cancelled car sharing event",
                                event_id=old_event["id"],
                                old_summary=old_event.get("summary", "Unknown"),
                            )

                    logger.info(
                        "Cancelled car sharing booking processed",
                        email_id=email.id,
                        booking_reference=carshare_booking.booking_reference,
                        deleted_count=deleted_count,
                    )
                else:
                    logger.info(
                        "No existing events found for cancelled booking",
                        email_id=email.id,
                        booking_reference=carshare_booking.booking_reference,
                    )

                # For cancelled bookings, return success but with empty events
                return []

            # Create new calendar events for non-cancelled bookings
            new_calendar_events = create_carshare_events(carshare_booking, email.id)

            if overlapping_events:
                logger.info(
                    "Found overlapping car sharing events",
                    email_id=email.id,
                    booking_reference=carshare_booking.booking_reference,
                    overlapping_count=len(overlapping_events),
                    new_count=len(new_calendar_events),
                )

                # Handle overlapping events (replace with newer booking)
                self.handle_overlapping_events(
                    overlapping_events, new_calendar_events, carshare_booking, email
                )
            else:
                # No overlapping events, create new ones
                event_ids = self.calendar_client.create_events(new_calendar_events)
                successful_count = sum(
                    1 for event_id in event_ids if event_id is not None
                )

                logger.info(
                    "Created new car sharing calendar events",
                    email_id=email.id,
                    booking_reference=carshare_booking.booking_reference,
                    event_count=len(new_calendar_events),
                    successful_count=successful_count,
                )

            return new_calendar_events

        except Exception as e:
            logger.error(
                "Failed to create/update car sharing calendar events",
                email_id=email.id,
                error=str(e),
            )
            return []

    def find_overlapping_events(self, booking: CarShareBooking) -> list[dict[str, Any]]:
        """Find existing events that overlap with the new booking time."""
        try:
            # Search for events around the booking time (±2 hours window)
            start_window = booking.start_time - timedelta(hours=2)
            end_window = booking.end_time + timedelta(hours=2)

            service = self.calendar_client._get_service()
            events_result = (
                service.events()
                .list(
                    calendarId=self.calendar_client.calendar_id,
                    timeMin=start_window.isoformat(),
                    timeMax=end_window.isoformat(),
                    privateExtendedProperty="source=gmail-calendar-sync",
                )
                .execute()
            )

            all_events = events_result.get("items", [])

            # Filter for car sharing events that truly overlap
            overlapping_events = []
            for event in all_events:
                # Check if it's a car sharing event
                extended_props = event.get("extendedProperties", {}).get("private", {})
                if not extended_props.get("source") == "gmail-calendar-sync":
                    continue

                # Check for time overlap
                event_start = datetime.fromisoformat(
                    event["start"]["dateTime"].replace("Z", "+00:00")
                )
                event_end = datetime.fromisoformat(
                    event["end"]["dateTime"].replace("Z", "+00:00")
                )

                # Check if times overlap (not just touch)
                if booking.start_time < event_end and booking.end_time > event_start:
                    # Additional check: same station or same provider (car sharing specific)
                    event_location = event.get("location", "")
                    if booking.station.station_name in event_location or any(
                        provider in event.get("summary", "")
                        for provider in ["Times Car", "三井のカーシェアーズ"]
                    ):
                        overlapping_events.append(event)

            return overlapping_events

        except Exception as e:
            logger.error("Failed to find overlapping events", error=str(e))
            return []

    def handle_overlapping_events(
        self,
        overlapping_events: list[dict],
        new_events: list[CalendarEvent],
        booking: CarShareBooking,
        email: EmailMessage,
    ) -> None:
        """Handle overlapping events by updating or replacing them."""

        # For car sharing, newer booking usually replaces older one
        # Delete old overlapping events
        deleted_count = 0
        for old_event in overlapping_events:
            if self.calendar_client.delete_event(old_event["id"]):
                deleted_count += 1
                logger.info(
                    "Deleted overlapping car sharing event",
                    event_id=old_event["id"],
                    old_summary=old_event.get("summary", "Unknown"),
                )

        # Create new events
        event_ids = self.calendar_client.create_events(new_events)
        successful_count = sum(1 for event_id in event_ids if event_id is not None)

        logger.info(
            "Replaced overlapping car sharing events",
            email_id=email.id,
            booking_reference=booking.booking_reference,
            deleted_count=deleted_count,
            created_count=successful_count,
        )
