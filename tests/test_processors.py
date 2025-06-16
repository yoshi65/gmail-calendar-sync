"""Tests for email processors."""

from datetime import datetime, timezone
import pytest
from unittest.mock import Mock, MagicMock

from src.processors.flight_processor import FlightEmailProcessor
from src.processors.factory import EmailProcessorFactory
from src.models.email_types import EmailMessage, EmailType
from src.models.flight import FlightBooking, FlightSegment, Airport
from src.utils.config import Settings


class TestFlightEmailProcessor:
    """Test FlightEmailProcessor."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.flight_domains = ["ana.co.jp", "booking.jal.com"]
        settings.openai_api_key = "test_key"
        return settings
    
    @pytest.fixture
    def processor(self, mock_settings):
        """Create flight email processor with mocked dependencies."""
        processor = FlightEmailProcessor(mock_settings)
        # Mock the OpenAI client
        processor.openai_client = Mock()
        # Mock the Calendar client
        processor.calendar_client = Mock()
        processor.calendar_client.find_events_by_reservation_id.return_value = []
        processor.calendar_client.create_events.return_value = ["event_id_1"]
        return processor
    
    @pytest.fixture
    def sample_email(self):
        """Create sample email message."""
        return EmailMessage(
            id="msg123",
            subject="Flight Confirmation - ANA",
            sender="noreply@ana.co.jp",
            body="Your flight NH006 is confirmed...",
            received_at=datetime.now(),
            thread_id="thread123"
        )
    
    @pytest.fixture
    def sample_flight_booking(self):
        """Create sample flight booking."""
        dep_airport = Airport(code="NRT", name="Narita", city="Tokyo")
        arr_airport = Airport(code="LAX", name="Los Angeles", city="Los Angeles")
        
        segment = FlightSegment(
            airline="ANA",
            flight_number="NH006",
            departure_airport=dep_airport,
            arrival_airport=arr_airport,
            departure_time=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc),
            arrival_time=datetime(2024, 1, 15, 18, 45, tzinfo=timezone.utc),
        )
        
        return FlightBooking(
            confirmation_code="ABC123",
            passenger_name="Taro Yamada",
            outbound_segments=[segment]
        )
    
    def test_can_process_flight_domain(self, processor, sample_email):
        """Test can_process for flight domain emails."""
        assert processor.can_process(sample_email) is True
    
    def test_can_process_non_flight_domain(self, processor):
        """Test can_process for non-flight domain emails."""
        email = EmailMessage(
            id="msg123",
            subject="Order Confirmation",
            sender="orders@amazon.com",
            body="Your order is confirmed",
            received_at=datetime.now(),
            thread_id="thread123"
        )
        
        assert processor.can_process(email) is False
    
    def test_extract_data_success(self, processor, sample_email, sample_flight_booking):
        """Test successful data extraction."""
        # Mock OpenAI client to return flight booking
        processor.openai_client.extract_flight_info.return_value = sample_flight_booking
        
        result = processor.extract_data(sample_email)
        
        assert result is not None
        assert result["confirmation_code"] == "ABC123"
        assert result["passenger_name"] == "Taro Yamada"
        processor.openai_client.extract_flight_info.assert_called_once()
    
    def test_extract_data_no_flight_info(self, processor, sample_email):
        """Test data extraction when no flight info found."""
        # Mock OpenAI client to return None
        processor.openai_client.extract_flight_info.return_value = None
        
        result = processor.extract_data(sample_email)
        
        assert result is None
    
    def test_create_calendar_events(self, processor, sample_email, sample_flight_booking):
        """Test calendar event creation."""
        extracted_data = sample_flight_booking.dict()
        
        events = processor.create_calendar_events(extracted_data, sample_email)
        
        assert len(events) == 1
        assert events[0].summary == "✈️ Tokyo → Los Angeles (ANA NH006)"
        assert events[0].source_email_id == "msg123"
        assert events[0].confirmation_code == "ABC123"
    
    def test_process_success(self, processor, sample_email, sample_flight_booking):
        """Test successful email processing."""
        # Mock extract_data and create_calendar_events
        processor.extract_data = Mock(return_value=sample_flight_booking.dict())
        processor.create_calendar_events = Mock(return_value=[Mock()])
        
        result = processor.process(sample_email)
        
        assert result.success is True
        assert result.email_id == "msg123"
        assert result.email_type == EmailType.FLIGHT
        assert result.extracted_data is not None
    
    def test_process_no_flight_info(self, processor, sample_email):
        """Test processing when no flight info found."""
        # Mock extract_data to return None
        processor.extract_data = Mock(return_value=None)
        
        result = processor.process(sample_email)
        
        assert result.success is False
        assert result.error_message == "No flight information found in email"


class TestEmailProcessorFactory:
    """Test EmailProcessorFactory."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.flight_domains = ["ana.co.jp", "booking.jal.com"]
        settings.openai_api_key = "test_key"
        return settings
    
    @pytest.fixture
    def factory(self, mock_settings):
        """Create email processor factory."""
        return EmailProcessorFactory(mock_settings)
    
    def test_get_processor_for_flight_email(self, factory):
        """Test getting processor for flight email."""
        email = EmailMessage(
            id="msg123",
            subject="Flight Confirmation",
            sender="noreply@ana.co.jp",
            body="Flight confirmed",
            received_at=datetime.now(),
            thread_id="thread123"
        )
        
        processor = factory.get_processor(email)
        
        assert processor is not None
        assert isinstance(processor, FlightEmailProcessor)
    
    def test_get_processor_for_unknown_email(self, factory):
        """Test getting processor for unknown email type."""
        email = EmailMessage(
            id="msg123",
            subject="Newsletter",
            sender="newsletter@example.com",
            body="Newsletter content",
            received_at=datetime.now(),
            thread_id="thread123"
        )
        
        processor = factory.get_processor(email)
        
        assert processor is None
    
    def test_get_all_processors(self, factory):
        """Test getting all available processors."""
        processors = factory.get_all_processors()
        
        assert len(processors) >= 1
        assert any(isinstance(p, FlightEmailProcessor) for p in processors)