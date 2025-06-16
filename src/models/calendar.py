"""Google Calendar event models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CalendarEvent(BaseModel):
    """Google Calendar event data."""
    summary: str = Field(..., description="Event title")
    description: str | None = Field(None, description="Event description")
    start_time: datetime = Field(..., description="Event start time")
    end_time: datetime = Field(..., description="Event end time")
    location: str | None = Field(None, description="Event location")

    # Additional metadata
    source_email_id: str = Field(..., description="Source email ID")
    confirmation_code: str | None = Field(None, description="Booking confirmation code")
    booking_reference: str | None = Field(None, description="Booking reference number")
    seat_number: str | None = Field(None, description="Seat number")

    def to_google_calendar_format(self) -> dict[str, Any]:
        """Convert to Google Calendar API format."""
        event_data = {
            'summary': self.summary,
            'start': {
                'dateTime': self.start_time.isoformat(),
                'timeZone': str(self.start_time.tzinfo) if self.start_time.tzinfo else 'UTC',
            },
            'end': {
                'dateTime': self.end_time.isoformat(),
                'timeZone': str(self.end_time.tzinfo) if self.end_time.tzinfo else 'UTC',
            },
        }

        if self.description:
            event_data['description'] = self.description

        if self.location:
            event_data['location'] = self.location

        # Add source metadata
        event_data['extendedProperties'] = {
            'private': {
                'source': 'gmail-calendar-sync',
                'source_email_id': self.source_email_id,
            }
        }

        if self.confirmation_code:
            event_data['extendedProperties']['private']['confirmation_code'] = self.confirmation_code
        
        if self.booking_reference:
            event_data['extendedProperties']['private']['booking_reference'] = self.booking_reference
        
        if self.seat_number:
            event_data['extendedProperties']['private']['seat_number'] = self.seat_number

        return event_data


def create_flight_events(flight_booking, source_email_id: str) -> list[CalendarEvent]:
    """Create calendar events from flight booking."""
    from .flight import FlightBooking

    if not isinstance(flight_booking, FlightBooking):
        raise ValueError("Expected FlightBooking instance")

    events = []

    # Create outbound flight events
    for i, segment in enumerate(flight_booking.outbound_segments):
        # Use city name if available, otherwise airport name, fallback to code
        departure_name = (segment.departure_airport.city or 
                         segment.departure_airport.name or 
                         segment.departure_airport.code)
        arrival_name = (segment.arrival_airport.city or 
                       segment.arrival_airport.name or 
                       segment.arrival_airport.code)
        
        # Remove "Airport" suffix if present for cleaner display
        departure_name = departure_name.replace(" Airport", "").replace("空港", "")
        arrival_name = arrival_name.replace(" Airport", "").replace("空港", "")
        
        summary = f"✈️ {departure_name} → {arrival_name} ({segment.airline} {segment.flight_number})"

        description_parts = [
            f"Flight: {segment.airline} {segment.flight_number}",
            f"Route: {segment.departure_airport.code} → {segment.arrival_airport.code}",
            f"Passenger: {flight_booking.passenger_name}",
            f"Confirmation: {flight_booking.confirmation_code}",
        ]

        if flight_booking.booking_reference:
            description_parts.append(f"Booking Reference: {flight_booking.booking_reference}")

        if segment.seat_number:
            description_parts.append(f"Seat: {segment.seat_number}")

        if flight_booking.checkin_url:
            description_parts.append(f"Check-in: {flight_booking.checkin_url}")

        location = f"{segment.departure_airport.name or segment.departure_airport.code}"
        if segment.departure_airport.city:
            location += f", {segment.departure_airport.city}"

        event = CalendarEvent(
            summary=summary,
            description="\n".join(description_parts),
            start_time=segment.departure_time,
            end_time=segment.arrival_time,
            location=location,
            source_email_id=source_email_id,
            confirmation_code=flight_booking.confirmation_code,
            booking_reference=flight_booking.booking_reference,
            seat_number=segment.seat_number,
        )
        events.append(event)

    # Create return flight events
    for i, segment in enumerate(flight_booking.return_segments):
        # Use city name if available, otherwise airport name, fallback to code
        departure_name = (segment.departure_airport.city or 
                         segment.departure_airport.name or 
                         segment.departure_airport.code)
        arrival_name = (segment.arrival_airport.city or 
                       segment.arrival_airport.name or 
                       segment.arrival_airport.code)
        
        # Remove "Airport" suffix if present for cleaner display
        departure_name = departure_name.replace(" Airport", "").replace("空港", "")
        arrival_name = arrival_name.replace(" Airport", "").replace("空港", "")
        
        summary = f"✈️ {departure_name} → {arrival_name} ({segment.airline} {segment.flight_number})"

        description_parts = [
            f"Flight: {segment.airline} {segment.flight_number}",
            f"Route: {segment.departure_airport.code} → {segment.arrival_airport.code}",
            f"Passenger: {flight_booking.passenger_name}",
            f"Confirmation: {flight_booking.confirmation_code}",
        ]

        if flight_booking.booking_reference:
            description_parts.append(f"Booking Reference: {flight_booking.booking_reference}")

        if segment.seat_number:
            description_parts.append(f"Seat: {segment.seat_number}")

        if flight_booking.checkin_url:
            description_parts.append(f"Check-in: {flight_booking.checkin_url}")

        location = f"{segment.departure_airport.name or segment.departure_airport.code}"
        if segment.departure_airport.city:
            location += f", {segment.departure_airport.city}"

        event = CalendarEvent(
            summary=summary,
            description="\n".join(description_parts),
            start_time=segment.departure_time,
            end_time=segment.arrival_time,
            location=location,
            source_email_id=source_email_id,
            confirmation_code=flight_booking.confirmation_code,
            booking_reference=flight_booking.booking_reference,
            seat_number=segment.seat_number,
        )
        events.append(event)

    return events
