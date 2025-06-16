"""Tests for data models."""

from datetime import datetime, timezone
import pytest

from src.models.flight import Airport, FlightSegment, FlightBooking
from src.models.calendar import CalendarEvent, create_flight_events
from src.models.email_types import EmailMessage, EmailType, ProcessingResult


class TestAirport:
    """Test Airport model."""
    
    def test_airport_creation(self):
        """Test basic airport creation."""
        airport = Airport(code="NRT", name="Narita International Airport", city="Tokyo")
        
        assert airport.code == "NRT"
        assert airport.name == "Narita International Airport"
        assert airport.city == "Tokyo"
    
    def test_airport_minimal(self):
        """Test airport with minimal data."""
        airport = Airport(code="HND")
        
        assert airport.code == "HND"
        assert airport.name is None
        assert airport.city is None


class TestFlightSegment:
    """Test FlightSegment model."""
    
    def test_flight_segment_creation(self):
        """Test flight segment creation."""
        dep_airport = Airport(code="NRT", name="Narita", city="Tokyo")
        arr_airport = Airport(code="LAX", name="Los Angeles", city="Los Angeles")
        
        departure_time = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        arrival_time = datetime(2024, 1, 15, 18, 45, tzinfo=timezone.utc)
        
        segment = FlightSegment(
            airline="ANA",
            flight_number="NH006",
            departure_airport=dep_airport,
            arrival_airport=arr_airport,
            departure_time=departure_time,
            arrival_time=arrival_time,
            seat_number="14A"
        )
        
        assert segment.airline == "ANA"
        assert segment.flight_number == "NH006"
        assert segment.departure_airport.code == "NRT"
        assert segment.arrival_airport.code == "LAX"
        assert segment.seat_number == "14A"
    
    def test_timezone_validation(self):
        """Test timezone validation for flight times."""
        dep_airport = Airport(code="NRT")
        arr_airport = Airport(code="LAX")
        
        # Should raise error for naive datetime
        with pytest.raises(ValueError, match="timezone-aware"):
            FlightSegment(
                airline="ANA",
                flight_number="NH006",
                departure_airport=dep_airport,
                arrival_airport=arr_airport,
                departure_time=datetime(2024, 1, 15, 10, 30),  # No timezone
                arrival_time=datetime(2024, 1, 15, 18, 45, tzinfo=timezone.utc),
            )


class TestFlightBooking:
    """Test FlightBooking model."""
    
    @pytest.fixture
    def sample_segment(self):
        """Create sample flight segment."""
        dep_airport = Airport(code="NRT", name="Narita", city="Tokyo")
        arr_airport = Airport(code="LAX", name="Los Angeles", city="Los Angeles")
        
        return FlightSegment(
            airline="ANA",
            flight_number="NH006",
            departure_airport=dep_airport,
            arrival_airport=arr_airport,
            departure_time=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc),
            arrival_time=datetime(2024, 1, 15, 18, 45, tzinfo=timezone.utc),
        )
    
    def test_one_way_booking(self, sample_segment):
        """Test one-way flight booking."""
        booking = FlightBooking(
            confirmation_code="ABC123",
            passenger_name="Taro Yamada",
            outbound_segments=[sample_segment]
        )
        
        assert booking.confirmation_code == "ABC123"
        assert booking.passenger_name == "Taro Yamada"
        assert len(booking.outbound_segments) == 1
        assert len(booking.return_segments) == 0
        assert not booking.is_round_trip
        assert booking.return_date is None
    
    def test_round_trip_booking(self, sample_segment):
        """Test round-trip flight booking."""
        return_segment = FlightSegment(
            airline="ANA",
            flight_number="NH005",
            departure_airport=sample_segment.arrival_airport,
            arrival_airport=sample_segment.departure_airport,
            departure_time=datetime(2024, 1, 20, 12, 0, tzinfo=timezone.utc),
            arrival_time=datetime(2024, 1, 20, 20, 15, tzinfo=timezone.utc),
        )
        
        booking = FlightBooking(
            confirmation_code="ABC123",
            passenger_name="Taro Yamada",
            outbound_segments=[sample_segment],
            return_segments=[return_segment]
        )
        
        assert booking.is_round_trip
        assert booking.return_date is not None
        assert len(booking.return_segments) == 1


class TestEmailMessage:
    """Test EmailMessage model."""
    
    def test_email_message_creation(self):
        """Test email message creation."""
        email = EmailMessage(
            id="msg123",
            subject="Flight Confirmation",
            sender="noreply@ana.co.jp",
            body="Your flight is confirmed",
            received_at=datetime.now(),
            thread_id="thread123"
        )
        
        assert email.id == "msg123"
        assert email.domain == "ana.co.jp"
    
    def test_domain_extraction(self):
        """Test domain extraction from sender."""
        email = EmailMessage(
            id="msg123",
            subject="Test",
            sender="John Doe <john@booking.jal.com>",
            body="Test body",
            received_at=datetime.now(),
            thread_id="thread123"
        )
        
        assert email.domain == "booking.jal.com"


class TestCalendarEvent:
    """Test CalendarEvent model."""
    
    def test_calendar_event_creation(self):
        """Test calendar event creation."""
        start_time = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 15, 18, 45, tzinfo=timezone.utc)
        
        event = CalendarEvent(
            summary="Flight ANA NH006",
            start_time=start_time,
            end_time=end_time,
            source_email_id="msg123",
            confirmation_code="ABC123"
        )
        
        assert event.summary == "Flight ANA NH006"
        assert event.source_email_id == "msg123"
        assert event.confirmation_code == "ABC123"
    
    def test_google_calendar_format(self):
        """Test conversion to Google Calendar format."""
        start_time = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 15, 18, 45, tzinfo=timezone.utc)
        
        event = CalendarEvent(
            summary="Flight ANA NH006",
            description="Flight details",
            start_time=start_time,
            end_time=end_time,
            location="Narita Airport",
            source_email_id="msg123",
            confirmation_code="ABC123"
        )
        
        google_format = event.to_google_calendar_format()
        
        assert google_format["summary"] == "Flight ANA NH006"
        assert google_format["description"] == "Flight details"
        assert google_format["location"] == "Narita Airport"
        assert "extendedProperties" in google_format
        assert google_format["extendedProperties"]["private"]["source_email_id"] == "msg123"