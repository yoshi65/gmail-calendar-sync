"""Tests for email processors."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from src.models.carshare import (
    BookingStatus,
    CarShareBooking,
    CarShareProvider,
    StationInfo,
)
from src.models.email_types import EmailMessage, EmailType
from src.models.flight import Airport, FlightBooking, FlightSegment
from src.processors.carshare_processor import CarShareEmailProcessor
from src.processors.factory import EmailProcessorFactory
from src.processors.flight_processor import FlightEmailProcessor
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
            thread_id="thread123",
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
            departure_time=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
            arrival_time=datetime(2024, 1, 15, 18, 45, tzinfo=UTC),
        )

        return FlightBooking(
            confirmation_code="ABC123",
            passenger_name="Taro Yamada",
            outbound_segments=[segment],
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
            thread_id="thread123",
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

    def test_create_calendar_events(
        self, processor, sample_email, sample_flight_booking
    ):
        """Test calendar event creation."""
        extracted_data = sample_flight_booking.model_dump()

        # Mock calendar client methods to return appropriate values
        processor.calendar_client.find_events_by_confirmation_code.return_value = []
        processor.calendar_client.create_events.return_value = ["event_id_1"]

        events = processor.create_calendar_events(extracted_data, sample_email)

        assert len(events) == 1
        assert events[0].summary == "✈️ Tokyo → Los Angeles (ANA NH006)"
        assert events[0].source_email_id == "msg123"
        assert events[0].confirmation_code == "ABC123"

    def test_process_success(self, processor, sample_email, sample_flight_booking):
        """Test successful email processing."""
        # Mock extract_data and create_calendar_events
        processor.extract_data = Mock(return_value=sample_flight_booking.model_dump())
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
            thread_id="thread123",
        )

        processor = factory.get_processor(email)

        assert processor is not None
        assert isinstance(processor, FlightEmailProcessor)

    def test_get_processor_for_carshare_email(self, factory):
        """Test getting processor for carshare email."""
        email = EmailMessage(
            id="msg123",
            subject="予約開始のお知らせ",
            sender="noreply@share.timescar.jp",
            body="タイムズカーの予約が開始されました",
            received_at=datetime.now(),
            thread_id="thread123",
        )

        processor = factory.get_processor(email)

        assert processor is not None
        assert isinstance(processor, CarShareEmailProcessor)

    def test_get_processor_for_unknown_email(self, factory):
        """Test getting processor for unknown email type."""
        email = EmailMessage(
            id="msg123",
            subject="Newsletter",
            sender="newsletter@example.com",
            body="Newsletter content",
            received_at=datetime.now(),
            thread_id="thread123",
        )

        processor = factory.get_processor(email)

        assert processor is None

    def test_get_all_processors(self, factory):
        """Test getting all available processors."""
        processors = factory.get_all_processors()

        assert len(processors) >= 2
        assert any(isinstance(p, FlightEmailProcessor) for p in processors)
        assert any(isinstance(p, CarShareEmailProcessor) for p in processors)


class TestCarShareEmailProcessor:
    """Test CarShareEmailProcessor."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.carshare_domains = ["carshares.jp", "share.timescar.jp"]
        settings.openai_api_key = "test_key"
        return settings

    @pytest.fixture
    def processor(self, mock_settings):
        """Create car share email processor with mocked dependencies."""
        processor = CarShareEmailProcessor(mock_settings)
        # Mock the OpenAI client
        processor.openai_client = Mock()
        # Mock the Calendar client
        processor.calendar_client = Mock()
        processor.calendar_client.find_events_by_reservation_id.return_value = []
        processor.calendar_client.create_events.return_value = ["event_id_1"]
        return processor

    @pytest.fixture
    def sample_email(self):
        """Create sample carshare email message."""
        return EmailMessage(
            id="msg123",
            subject="予約開始のお知らせ",
            sender="noreply@share.timescar.jp",
            body="タイムズカーの予約が開始されました...",
            received_at=datetime.now(),
            thread_id="thread123",
        )

    @pytest.fixture
    def sample_carshare_booking(self):
        """Create sample carshare booking."""
        station = StationInfo(
            station_name="新宿ステーション",
            station_address="東京都新宿区1-1-1",
            station_code="ST001",
        )

        return CarShareBooking(
            booking_reference="CS123456",
            provider=CarShareProvider.TIMES_CAR,
            status=BookingStatus.RESERVED,
            user_name="山田太郎",
            start_time=datetime(2024, 1, 15, 10, 0, tzinfo=UTC),
            end_time=datetime(2024, 1, 15, 12, 0, tzinfo=UTC),
            station=station,
        )

    def test_can_process_carshare_domain(self, processor, sample_email):
        """Test can_process for carshare domain emails."""
        assert processor.can_process(sample_email) is True

    def test_can_process_non_carshare_domain(self, processor):
        """Test can_process for non-carshare domain emails."""
        email = EmailMessage(
            id="msg123",
            subject="Order Confirmation",
            sender="orders@amazon.com",
            body="Your order is confirmed",
            received_at=datetime.now(),
            thread_id="thread123",
        )

        assert processor.can_process(email) is False

    def test_can_process_mitsui_carshares(self, processor):
        """Test can_process for Mitsui CarShares domain."""
        email = EmailMessage(
            id="msg123",
            subject="予約確認",
            sender="info@carshares.jp",
            body="カーシェアの予約が確認されました",
            received_at=datetime.now(),
            thread_id="thread123",
        )

        assert processor.can_process(email) is True

    def test_extract_data_success(
        self, processor, sample_email, sample_carshare_booking
    ):
        """Test successful data extraction."""
        # Mock OpenAI client to return carshare booking
        processor.openai_client.extract_carshare_info.return_value = (
            sample_carshare_booking
        )

        result = processor.extract_data(sample_email)

        assert result is not None
        assert result["booking_reference"] == "CS123456"
        assert result["user_name"] == "山田太郎"
        assert result["provider"] == CarShareProvider.TIMES_CAR
        processor.openai_client.extract_carshare_info.assert_called_once()

    def test_extract_data_no_carshare_info(self, processor, sample_email):
        """Test data extraction when no carshare info found."""
        # Mock OpenAI client to return None
        processor.openai_client.extract_carshare_info.return_value = None

        result = processor.extract_data(sample_email)

        assert result is None

    def test_process_success(self, processor, sample_email, sample_carshare_booking):
        """Test successful email processing."""
        # Mock extract_data and create_calendar_events
        processor.extract_data = Mock(return_value=sample_carshare_booking.model_dump())
        processor.create_calendar_events = Mock(return_value=[Mock()])

        result = processor.process(sample_email)

        assert result.success is True
        assert result.email_id == "msg123"
        assert result.email_type == EmailType.CAR_SHARE
        assert result.extracted_data is not None

    def test_process_no_carshare_info(self, processor, sample_email):
        """Test processing when no carshare info found."""
        # Mock extract_data to return None
        processor.extract_data = Mock(return_value=None)

        result = processor.process(sample_email)

        assert result.success is False
        assert result.error_message == "No car sharing information found in email"

    def test_process_cancelled_booking(
        self, processor, sample_email, sample_carshare_booking
    ):
        """Test processing cancelled booking."""
        # Create cancelled booking
        cancelled_booking = sample_carshare_booking.model_copy()
        cancelled_booking.status = BookingStatus.CANCELLED

        # Mock extract_data and create_calendar_events
        processor.extract_data = Mock(return_value=cancelled_booking.model_dump())
        processor.create_calendar_events = Mock(
            return_value=[]
        )  # Empty list for cancelled

        result = processor.process(sample_email)

        assert result.success is True
        assert result.email_id == "msg123"
        assert result.email_type == EmailType.CAR_SHARE

    def test_process_promotional_email_skipped(self, processor):
        """Test that promotional emails are skipped."""
        promotional_email = EmailMessage(
            id="msg123",
            subject="キャンペーン情報！お得なプラン",
            sender="campaign@share.timescar.jp",
            body="期間限定キャンペーン実施中！詳しくはこちら",
            received_at=datetime.now(),
            thread_id="thread123",
        )

        result = processor.process(promotional_email)

        assert result.success is False
        assert result.error_message == "Skipped promotional email"

    def test_create_calendar_events_reserved_booking(
        self, processor, sample_email, sample_carshare_booking
    ):
        """Test calendar event creation for reserved booking."""
        extracted_data = sample_carshare_booking.model_dump()

        # Mock calendar client methods
        processor.find_overlapping_events = Mock(return_value=[])
        processor.calendar_client.create_events.return_value = ["event_id_1"]

        events = processor.create_calendar_events(extracted_data, sample_email)

        assert len(events) == 1
        assert events[0].summary == "🚗 新宿ステーション"
        assert events[0].source_email_id == "msg123"

    def test_create_calendar_events_cancelled_booking(
        self, processor, sample_email, sample_carshare_booking
    ):
        """Test calendar event handling for cancelled booking."""
        # Create cancelled booking
        cancelled_booking = sample_carshare_booking.model_copy()
        cancelled_booking.status = BookingStatus.CANCELLED
        extracted_data = cancelled_booking.model_dump()

        # Mock overlapping events found
        mock_event = {"id": "existing_event_id", "summary": "Existing booking"}
        processor.find_overlapping_events = Mock(return_value=[mock_event])
        processor.calendar_client.delete_event.return_value = True

        events = processor.create_calendar_events(extracted_data, sample_email)

        # Should return empty list for cancelled booking
        assert len(events) == 0
        # Should have called delete_event
        processor.calendar_client.delete_event.assert_called_once_with(
            "existing_event_id"
        )

    def test_find_overlapping_events(self, processor, sample_carshare_booking):
        """Test finding overlapping events."""
        # Mock calendar service
        mock_service = Mock()
        processor.calendar_client._get_service = Mock(return_value=mock_service)
        processor.calendar_client.calendar_id = "test_calendar"

        # Mock overlapping event
        mock_event = {
            "id": "existing_event",
            "summary": "Times Car booking",
            "location": "新宿ステーション",
            "start": {"dateTime": "2024-01-15T09:30:00Z"},
            "end": {"dateTime": "2024-01-15T11:30:00Z"},
            "extendedProperties": {"private": {"source": "gmail-calendar-sync"}},
        }

        mock_service.events().list().execute.return_value = {"items": [mock_event]}

        overlapping = processor.find_overlapping_events(sample_carshare_booking)

        assert len(overlapping) == 1
        assert overlapping[0]["id"] == "existing_event"

    def test_handle_overlapping_events(
        self, processor, sample_email, sample_carshare_booking
    ):
        """Test handling overlapping events."""
        # Mock overlapping events
        overlapping_events = [
            {"id": "old_event_1", "summary": "Old booking 1"},
            {"id": "old_event_2", "summary": "Old booking 2"},
        ]

        # Mock new events
        new_events = [Mock()]

        # Mock calendar client methods
        processor.calendar_client.delete_event.return_value = True
        processor.calendar_client.create_events.return_value = ["new_event_id"]

        processor.handle_overlapping_events(
            overlapping_events, new_events, sample_carshare_booking, sample_email
        )

        # Should delete old events
        assert processor.calendar_client.delete_event.call_count == 2
        # Should create new events
        processor.calendar_client.create_events.assert_called_once_with(new_events)
