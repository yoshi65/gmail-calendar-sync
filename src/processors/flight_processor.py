"""Flight email processor."""

import structlog

from ..models.calendar import CalendarEvent, create_flight_events
from ..models.email_types import EmailMessage, EmailType, ProcessingResult
from ..models.flight import FlightBooking
from ..services.calendar_client import CalendarClient
from ..services.openai_client import OpenAIClient
from ..utils.config import Settings
from ..utils.email_filter import is_likely_booking_email, is_promotional_email
from .base import BaseEmailProcessor

logger = structlog.get_logger()


class FlightEmailProcessor(BaseEmailProcessor):
    """Processor for flight booking emails."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.openai_client = OpenAIClient(settings)
        self.calendar_client = CalendarClient(settings)

    def can_process(self, email: EmailMessage) -> bool:
        """Check if this email is from a flight booking domain."""
        domain = email.domain
        # Check for exact match or subdomain match
        for flight_domain in self.settings.flight_domains:
            if domain == flight_domain or domain.endswith("." + flight_domain):
                return True
        return False

    def process(self, email: EmailMessage) -> ProcessingResult:
        """Process flight booking email."""
        logger.info(
            "Processing flight email",
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
                    email_type=EmailType.FLIGHT,
                    success=False,
                    error_message="No flight information found in email",
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
                    email_type=EmailType.FLIGHT,
                    success=False,
                    error_message="Skipped promotional email",
                )

            # Extract flight data using OpenAI
            extracted_data = self.extract_data(email)

            if not extracted_data:
                return ProcessingResult(
                    email_id=email.id,
                    email_type=EmailType.FLIGHT,
                    success=False,
                    error_message="No flight information found in email",
                )

            # Create calendar events
            calendar_events = self.create_calendar_events(extracted_data, email)

            if not calendar_events:
                return ProcessingResult(
                    email_id=email.id,
                    email_type=EmailType.FLIGHT,
                    success=False,
                    extracted_data=extracted_data,
                    error_message="Failed to create calendar events",
                )

            return ProcessingResult(
                email_id=email.id,
                email_type=EmailType.FLIGHT,
                success=True,
                extracted_data=extracted_data,
            )

        except Exception as e:
            logger.error(
                "Failed to process flight email", email_id=email.id, error=str(e)
            )

            return ProcessingResult(
                email_id=email.id,
                email_type=EmailType.FLIGHT,
                success=False,
                error_message=f"Processing error: {str(e)}",
            )

    def extract_data(self, email: EmailMessage) -> dict | None:
        """Extract flight booking data from email."""
        try:
            flight_booking = self.openai_client.extract_flight_info(
                email.body, email.subject
            )

            if flight_booking:
                # Convert to dict for storage
                return flight_booking.model_dump()

            return None

        except Exception as e:
            logger.error(
                "Failed to extract flight data", email_id=email.id, error=str(e)
            )
            return None

    def create_calendar_events(
        self, extracted_data: dict, email: EmailMessage
    ) -> list[CalendarEvent]:
        """Create or update calendar events from flight booking data."""
        try:
            # Convert dict back to FlightBooking model
            flight_booking = FlightBooking(**extracted_data)
            confirmation_code = flight_booking.confirmation_code
            booking_reference = flight_booking.booking_reference

            # Check if events already exist for this confirmation code or booking reference
            if confirmation_code:
                existing_events = self.calendar_client.find_events_by_confirmation_code(
                    confirmation_code
                )
                logger.info(
                    "Using confirmation code for duplicate detection",
                    confirmation_code=confirmation_code,
                    email_id=email.id,
                )
            elif booking_reference:
                # Fallback to booking reference if no confirmation code
                existing_events = self.calendar_client.find_events_by_booking_reference(
                    booking_reference
                )
                logger.info(
                    "Using booking reference as fallback identifier",
                    booking_reference=booking_reference,
                    email_id=email.id,
                )
            else:
                existing_events = []
                logger.warning(
                    "No confirmation code or booking reference found", email_id=email.id
                )

            # Create new calendar events from flight data
            new_calendar_events = create_flight_events(flight_booking, email.id)

            if existing_events:
                logger.info(
                    "Found existing events, checking for updates",
                    email_id=email.id,
                    confirmation_code=confirmation_code,
                    booking_reference=booking_reference,
                    existing_count=len(existing_events),
                    new_count=len(new_calendar_events),
                )

                # Update existing events if needed
                updated_count = 0
                for i, new_event in enumerate(new_calendar_events):
                    if i < len(existing_events):
                        existing_event = existing_events[i]
                        if self.calendar_client.needs_update(existing_event, new_event):
                            event_id = existing_event["id"]
                            success = self.calendar_client.update_event(
                                event_id, new_event
                            )
                            if success:
                                updated_count += 1
                                logger.info(
                                    "Updated existing calendar event",
                                    event_id=event_id,
                                    confirmation_code=confirmation_code,
                                )
                            else:
                                logger.error(
                                    "Failed to update calendar event",
                                    event_id=event_id,
                                    confirmation_code=confirmation_code,
                                )
                        else:
                            logger.info(
                                "No update needed for existing event",
                                event_id=existing_event["id"],
                                confirmation_code=confirmation_code,
                            )

                # If there are more new events than existing ones, create the additional ones
                if len(new_calendar_events) > len(existing_events):
                    for new_event in new_calendar_events[len(existing_events) :]:
                        event_id = self.calendar_client.create_event(new_event)
                        if event_id:
                            logger.info(
                                "Created additional calendar event",
                                event_id=event_id,
                                confirmation_code=confirmation_code,
                            )

                logger.info(
                    "Processed existing events",
                    email_id=email.id,
                    confirmation_code=confirmation_code,
                    updated_count=updated_count,
                )

                return new_calendar_events  # Return the new events for consistency

            else:
                # No existing events, create new ones
                event_ids = self.calendar_client.create_events(new_calendar_events)
                successful_count = sum(
                    1 for event_id in event_ids if event_id is not None
                )

                logger.info(
                    "Created new calendar events",
                    email_id=email.id,
                    confirmation_code=confirmation_code,
                    event_count=len(new_calendar_events),
                    successful_count=successful_count,
                )

                return new_calendar_events

        except Exception as e:
            logger.error(
                "Failed to create/update calendar events",
                email_id=email.id,
                error=str(e),
            )
            return []
