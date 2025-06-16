"""Tests for data models."""

from datetime import UTC, datetime

import pytest

from src.models.calendar import CalendarEvent
from src.models.carshare import (
    BookingStatus,
    CarInfo,
    CarShareBooking,
    CarShareProvider,
    StationInfo,
    get_provider_from_domain,
)
from src.models.email_types import EmailMessage
from src.models.flight import Airport, FlightBooking, FlightSegment


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

        departure_time = datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
        arrival_time = datetime(2024, 1, 15, 18, 45, tzinfo=UTC)

        segment = FlightSegment(
            airline="ANA",
            flight_number="NH006",
            departure_airport=dep_airport,
            arrival_airport=arr_airport,
            departure_time=departure_time,
            arrival_time=arrival_time,
            seat_number="14A",
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
                arrival_time=datetime(2024, 1, 15, 18, 45, tzinfo=UTC),
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
            departure_time=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
            arrival_time=datetime(2024, 1, 15, 18, 45, tzinfo=UTC),
        )

    def test_one_way_booking(self, sample_segment):
        """Test one-way flight booking."""
        booking = FlightBooking(
            confirmation_code="ABC123",
            passenger_name="Taro Yamada",
            outbound_segments=[sample_segment],
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
            departure_time=datetime(2024, 1, 20, 12, 0, tzinfo=UTC),
            arrival_time=datetime(2024, 1, 20, 20, 15, tzinfo=UTC),
        )

        booking = FlightBooking(
            confirmation_code="ABC123",
            passenger_name="Taro Yamada",
            outbound_segments=[sample_segment],
            return_segments=[return_segment],
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
            thread_id="thread123",
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
            thread_id="thread123",
        )

        assert email.domain == "booking.jal.com"


class TestCalendarEvent:
    """Test CalendarEvent model."""

    def test_calendar_event_creation(self):
        """Test calendar event creation."""
        start_time = datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
        end_time = datetime(2024, 1, 15, 18, 45, tzinfo=UTC)

        event = CalendarEvent(
            summary="Flight ANA NH006",
            start_time=start_time,
            end_time=end_time,
            source_email_id="msg123",
            confirmation_code="ABC123",
        )

        assert event.summary == "Flight ANA NH006"
        assert event.source_email_id == "msg123"
        assert event.confirmation_code == "ABC123"

    def test_google_calendar_format(self):
        """Test conversion to Google Calendar format."""
        start_time = datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
        end_time = datetime(2024, 1, 15, 18, 45, tzinfo=UTC)

        event = CalendarEvent(
            summary="Flight ANA NH006",
            description="Flight details",
            start_time=start_time,
            end_time=end_time,
            location="Narita Airport",
            source_email_id="msg123",
            confirmation_code="ABC123",
        )

        google_format = event.to_google_calendar_format()

        assert google_format["summary"] == "Flight ANA NH006"
        assert google_format["description"] == "Flight details"
        assert google_format["location"] == "Narita Airport"
        assert "extendedProperties" in google_format
        assert (
            google_format["extendedProperties"]["private"]["source_email_id"]
            == "msg123"
        )


class TestCarInfo:
    """Test CarInfo model."""

    def test_car_info_creation(self):
        """Test car info creation."""
        car = CarInfo(
            car_type="デミオ", car_number="品川 500 あ 1234", car_name="Car001"
        )

        assert car.car_type == "デミオ"
        assert car.car_number == "品川 500 あ 1234"
        assert car.car_name == "Car001"

    def test_car_info_minimal(self):
        """Test car info with minimal data."""
        car = CarInfo()

        assert car.car_type is None
        assert car.car_number is None
        assert car.car_name is None


class TestStationInfo:
    """Test StationInfo model."""

    def test_station_info_creation(self):
        """Test station info creation."""
        station = StationInfo(
            station_name="新宿ステーション",
            station_address="東京都新宿区1-1-1",
            station_code="ST001",
        )

        assert station.station_name == "新宿ステーション"
        assert station.station_address == "東京都新宿区1-1-1"
        assert station.station_code == "ST001"

    def test_station_info_minimal(self):
        """Test station info with minimal data."""
        station = StationInfo(station_name="渋谷ステーション")

        assert station.station_name == "渋谷ステーション"
        assert station.station_address is None
        assert station.station_code is None


class TestCarShareBooking:
    """Test CarShareBooking model."""

    @pytest.fixture
    def sample_station(self):
        """Create sample station."""
        return StationInfo(
            station_name="新宿ステーション",
            station_address="東京都新宿区1-1-1",
            station_code="ST001",
        )

    @pytest.fixture
    def sample_car(self):
        """Create sample car."""
        return CarInfo(
            car_type="デミオ", car_number="品川 500 あ 1234", car_name="Car001"
        )

    def test_carshare_booking_creation(self, sample_station, sample_car):
        """Test car share booking creation."""
        start_time = datetime(2024, 1, 15, 10, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 15, 12, 0, tzinfo=UTC)
        booking_date = datetime(2024, 1, 10, 15, 30, tzinfo=UTC)

        booking = CarShareBooking(
            booking_reference="CS123456",
            confirmation_code="ABC123",
            provider=CarShareProvider.TIMES_CAR,
            status=BookingStatus.RESERVED,
            user_name="山田太郎",
            start_time=start_time,
            end_time=end_time,
            station=sample_station,
            car=sample_car,
            booking_date=booking_date,
            total_price="¥1,200",
        )

        assert booking.booking_reference == "CS123456"
        assert booking.confirmation_code == "ABC123"
        assert booking.provider == CarShareProvider.TIMES_CAR
        assert booking.status == BookingStatus.RESERVED
        assert booking.user_name == "山田太郎"
        assert booking.start_time == start_time
        assert booking.end_time == end_time
        assert booking.station.station_name == "新宿ステーション"
        assert booking.car.car_type == "デミオ"
        assert booking.total_price == "¥1,200"

    def test_duration_calculation(self, sample_station):
        """Test duration calculation."""
        start_time = datetime(2024, 1, 15, 10, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 15, 12, 30, tzinfo=UTC)  # 2.5 hours

        booking = CarShareBooking(
            provider=CarShareProvider.TIMES_CAR,
            user_name="山田太郎",
            start_time=start_time,
            end_time=end_time,
            station=sample_station,
        )

        assert booking.duration_hours == 2.5

    def test_is_active_property(self, sample_station):
        """Test is_active property."""
        start_time = datetime(2024, 1, 15, 10, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 15, 12, 0, tzinfo=UTC)

        # Active booking
        active_booking = CarShareBooking(
            provider=CarShareProvider.TIMES_CAR,
            status=BookingStatus.RESERVED,
            user_name="山田太郎",
            start_time=start_time,
            end_time=end_time,
            station=sample_station,
        )
        assert active_booking.is_active is True

        # Cancelled booking
        cancelled_booking = CarShareBooking(
            provider=CarShareProvider.TIMES_CAR,
            status=BookingStatus.CANCELLED,
            user_name="山田太郎",
            start_time=start_time,
            end_time=end_time,
            station=sample_station,
        )
        assert cancelled_booking.is_active is False

    def test_unique_key_generation(self, sample_station):
        """Test unique key generation."""
        start_time = datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
        end_time = datetime(2024, 1, 15, 12, 0, tzinfo=UTC)

        booking = CarShareBooking(
            provider=CarShareProvider.TIMES_CAR,
            user_name="山田太郎",
            start_time=start_time,
            end_time=end_time,
            station=sample_station,
        )

        expected_key = "CarShareProvider.TIMES_CAR_ST001_202401151030"
        assert booking.unique_key == expected_key

    def test_unique_key_with_station_name_fallback(self):
        """Test unique key generation when station_code is not available."""
        station = StationInfo(station_name="新宿ステーション")
        start_time = datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
        end_time = datetime(2024, 1, 15, 12, 0, tzinfo=UTC)

        booking = CarShareBooking(
            provider=CarShareProvider.MITSUI_CARSHARES,
            user_name="山田太郎",
            start_time=start_time,
            end_time=end_time,
            station=station,
        )

        expected_key = "CarShareProvider.MITSUI_CARSHARES_新宿ステーション_202401151030"
        assert booking.unique_key == expected_key

    def test_minimal_booking(self, sample_station):
        """Test booking with minimal required fields."""
        start_time = datetime(2024, 1, 15, 10, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 15, 12, 0, tzinfo=UTC)

        booking = CarShareBooking(
            provider=CarShareProvider.TIMES_CAR,
            user_name="山田太郎",
            start_time=start_time,
            end_time=end_time,
            station=sample_station,
        )

        assert booking.provider == CarShareProvider.TIMES_CAR
        assert booking.status == BookingStatus.RESERVED  # Default value
        assert booking.user_name == "山田太郎"
        assert booking.booking_reference is None
        assert booking.car is None


class TestCarShareProvider:
    """Test CarShareProvider enum and related functions."""

    def test_provider_values(self):
        """Test provider enum values."""
        assert CarShareProvider.TIMES_CAR == "times_car"
        assert CarShareProvider.MITSUI_CARSHARES == "mitsui_carshares"

    def test_get_provider_from_domain_times_car(self):
        """Test getting Times Car provider from domain."""
        assert (
            get_provider_from_domain("share.timescar.jp") == CarShareProvider.TIMES_CAR
        )

    def test_get_provider_from_domain_mitsui(self):
        """Test getting Mitsui CarShares provider from domain."""
        assert (
            get_provider_from_domain("carshares.jp")
            == CarShareProvider.MITSUI_CARSHARES
        )

    def test_get_provider_from_unknown_domain(self):
        """Test getting provider from unknown domain."""
        assert get_provider_from_domain("unknown.com") is None
        assert get_provider_from_domain("gmail.com") is None

    def test_get_provider_with_subdomain(self):
        """Test getting provider with subdomain."""
        assert (
            get_provider_from_domain("mail.carshares.jp")
            == CarShareProvider.MITSUI_CARSHARES
        )
        assert (
            get_provider_from_domain("subdomain.share.timescar.jp")
            == CarShareProvider.TIMES_CAR
        )


class TestBookingStatus:
    """Test BookingStatus enum."""

    def test_status_values(self):
        """Test booking status enum values."""
        assert BookingStatus.RESERVED == "reserved"
        assert BookingStatus.CHANGED == "changed"
        assert BookingStatus.CANCELLED == "cancelled"
        assert BookingStatus.COMPLETED == "completed"
