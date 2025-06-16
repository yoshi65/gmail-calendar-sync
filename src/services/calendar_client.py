"""Google Calendar API client."""

from typing import Any

import structlog
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..models.calendar import CalendarEvent
from ..utils.config import Settings

logger = structlog.get_logger()


class CalendarClient:
    """Google Calendar API client for managing calendar events."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._service = None
        self.calendar_id = "primary"  # Use primary calendar

    def _get_service(self) -> Any:
        """Get Google Calendar API service."""
        if self._service is None:
            client_id, client_secret, refresh_token = (
                self.settings.get_calendar_credentials()
            )

            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
            )

            # Refresh the token
            credentials.refresh(Request())

            self._service = build("calendar", "v3", credentials=credentials)

        return self._service

    def create_event(self, event: CalendarEvent) -> str | None:
        """Create a calendar event and return event ID."""
        try:
            service = self._get_service()

            # Convert to Google Calendar format
            event_data = event.to_google_calendar_format()

            logger.info(
                "Creating calendar event", summary=event.summary, start=event.start_time
            )

            created_event = (
                service.events()
                .insert(calendarId=self.calendar_id, body=event_data)
                .execute()
            )

            event_id = created_event.get("id")
            logger.info(
                "Created calendar event", event_id=event_id, summary=event.summary
            )

            return event_id

        except HttpError as error:
            logger.error(
                "Failed to create calendar event",
                error=str(error),
                summary=event.summary,
            )
            return None

    def create_events(self, events: list[CalendarEvent]) -> list[str | None]:
        """Create multiple calendar events and return list of event IDs."""
        event_ids = []

        for event in events:
            event_id = self.create_event(event)
            event_ids.append(event_id)

        successful_count = sum(1 for event_id in event_ids if event_id is not None)
        logger.info(
            "Created calendar events",
            total=len(events),
            successful=successful_count,
            failed=len(events) - successful_count,
        )

        return event_ids

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        """Get calendar event by ID."""
        try:
            service = self._get_service()

            event = (
                service.events()
                .get(calendarId=self.calendar_id, eventId=event_id)
                .execute()
            )

            return event

        except HttpError as error:
            if error.resp.status == 404:
                logger.warning("Calendar event not found", event_id=event_id)
                return None
            logger.error(
                "Failed to get calendar event", event_id=event_id, error=str(error)
            )
            return None

    def update_event(self, event_id: str, event: CalendarEvent) -> bool:
        """Update an existing calendar event."""
        try:
            service = self._get_service()

            # Convert to Google Calendar format
            event_data = event.to_google_calendar_format()

            logger.info(
                "Updating calendar event", event_id=event_id, summary=event.summary
            )

            service.events().update(
                calendarId=self.calendar_id, eventId=event_id, body=event_data
            ).execute()

            logger.info("Updated calendar event", event_id=event_id)
            return True

        except HttpError as error:
            logger.error(
                "Failed to update calendar event", event_id=event_id, error=str(error)
            )
            return False

    def delete_event(self, event_id: str) -> bool:
        """Delete a calendar event."""
        try:
            service = self._get_service()

            logger.info("Deleting calendar event", event_id=event_id)

            service.events().delete(
                calendarId=self.calendar_id, eventId=event_id
            ).execute()

            logger.info("Deleted calendar event", event_id=event_id)
            return True

        except HttpError as error:
            if error.resp.status == 404:
                logger.warning(
                    "Calendar event not found for deletion", event_id=event_id
                )
                return True  # Already deleted
            logger.error(
                "Failed to delete calendar event", event_id=event_id, error=str(error)
            )
            return False

    def find_events_by_source_email(self, source_email_id: str) -> list[dict[str, Any]]:
        """Find calendar events created from a specific email."""
        try:
            service = self._get_service()

            # Search for events with matching source email ID in extended properties
            events_result = (
                service.events()
                .list(
                    calendarId=self.calendar_id,
                    privateExtendedProperty=f"source_email_id={source_email_id}",
                )
                .execute()
            )

            events = events_result.get("items", [])
            logger.info(
                "Found events by source email",
                source_email_id=source_email_id,
                count=len(events),
            )

            return events

        except HttpError as error:
            logger.error(
                "Failed to find events by source email",
                source_email_id=source_email_id,
                error=str(error),
            )
            return []

    def check_event_exists(
        self, source_email_id: str, confirmation_code: str | None = None
    ) -> bool:
        """Check if an event already exists for the given email/confirmation."""
        events = self.find_events_by_source_email(source_email_id)

        if not events:
            return False

        # If confirmation code is provided, check for exact match
        if confirmation_code:
            for event in events:
                extended_props = event.get("extendedProperties", {}).get("private", {})
                if extended_props.get("confirmation_code") == confirmation_code:
                    logger.info(
                        "Event already exists",
                        source_email_id=source_email_id,
                        confirmation_code=confirmation_code,
                    )
                    return True
            return False

        # If no confirmation code, just check if any event exists
        logger.info("Event already exists", source_email_id=source_email_id)
        return True

    def find_events_by_confirmation_code(
        self, confirmation_code: str
    ) -> list[dict[str, Any]]:
        """Find calendar events by confirmation code."""
        try:
            service = self._get_service()

            # Search for events with matching confirmation code in extended properties
            events_result = (
                service.events()
                .list(
                    calendarId=self.calendar_id,
                    privateExtendedProperty=f"confirmation_code={confirmation_code}",
                )
                .execute()
            )

            events = events_result.get("items", [])
            logger.info(
                "Found events by confirmation code",
                confirmation_code=confirmation_code,
                count=len(events),
            )

            return events

        except HttpError as error:
            logger.error(
                "Failed to find events by confirmation code",
                confirmation_code=confirmation_code,
                error=str(error),
            )
            return []

    def find_events_by_booking_reference(
        self, booking_reference: str
    ) -> list[dict[str, Any]]:
        """Find calendar events by booking reference."""
        try:
            service = self._get_service()

            # Search for events with matching booking reference in extended properties
            events_result = (
                service.events()
                .list(
                    calendarId=self.calendar_id,
                    privateExtendedProperty=f"booking_reference={booking_reference}",
                )
                .execute()
            )

            events = events_result.get("items", [])
            logger.info(
                "Found events by booking reference",
                booking_reference=booking_reference,
                count=len(events),
            )

            return events

        except HttpError as error:
            logger.error(
                "Failed to find events by booking reference",
                booking_reference=booking_reference,
                error=str(error),
            )
            return []

    def check_event_exists_by_confirmation(self, confirmation_code: str) -> bool:
        """Check if events already exist for the given confirmation code."""
        events = self.find_events_by_confirmation_code(confirmation_code)
        exists = len(events) > 0

        if exists:
            logger.info(
                "Events already exist for confirmation code",
                confirmation_code=confirmation_code,
                count=len(events),
            )

        return exists

    def find_events_by_reservation_id(
        self, booking_reference: str | None, confirmation_code: str | None
    ) -> list[dict[str, Any]]:
        """Find calendar events by booking reference (preferred) or confirmation code (fallback)."""
        events = []

        # First try to find by booking reference (preferred)
        if booking_reference:
            events = self.find_events_by_booking_reference(booking_reference)
            if events:
                logger.info(
                    "Found events by booking reference",
                    booking_reference=booking_reference,
                    count=len(events),
                )
                return events

        # Fallback to confirmation code
        if confirmation_code:
            events = self.find_events_by_confirmation_code(confirmation_code)
            if events:
                logger.info(
                    "Found events by confirmation code (fallback)",
                    confirmation_code=confirmation_code,
                    count=len(events),
                )
                return events

        logger.info(
            "No events found",
            booking_reference=booking_reference,
            confirmation_code=confirmation_code,
        )
        return []

    def needs_update(
        self, existing_event: dict[str, Any], new_event: CalendarEvent
    ) -> bool:
        """Check if an existing event needs to be updated with new information."""
        try:
            # Get extended properties from existing event
            existing_props = existing_event.get("extendedProperties", {}).get(
                "private", {}
            )

            # Convert new event to Google Calendar format to get comparable properties
            new_event_data = new_event.to_google_calendar_format()
            new_props = new_event_data.get("extendedProperties", {}).get("private", {})

            # Check seat number updates (e.g., from "未指定" to specific seat)
            existing_seat = existing_props.get("seat_number", "")
            new_seat = new_props.get("seat_number", "")
            if existing_seat != new_seat and new_seat and new_seat != "未指定":
                logger.info(
                    "Seat number update detected", existing=existing_seat, new=new_seat
                )
                return True

            # Check time changes
            existing_start = existing_event.get("start", {}).get("dateTime", "")
            new_start = new_event.start_time.isoformat() if new_event.start_time else ""
            if existing_start != new_start:
                logger.info(
                    "Start time update detected", existing=existing_start, new=new_start
                )
                return True

            existing_end = existing_event.get("end", {}).get("dateTime", "")
            new_end = new_event.end_time.isoformat() if new_event.end_time else ""
            if existing_end != new_end:
                logger.info(
                    "End time update detected", existing=existing_end, new=new_end
                )
                return True

            # Check description changes (might contain updated info)
            existing_desc = existing_event.get("description", "")
            new_desc = new_event.description or ""
            if len(new_desc) > len(existing_desc):
                logger.info("Description update detected (more detailed info)")
                return True

            return False

        except Exception as error:
            logger.error("Error checking if update needed", error=str(error))
            return False
