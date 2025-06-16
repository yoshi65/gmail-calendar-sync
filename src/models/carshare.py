"""Car sharing booking models."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class CarShareProvider(str, Enum):
    """Supported car sharing providers."""

    MITSUI_CARSHARES = "mitsui_carshares"
    TIMES_CAR = "times_car"


class BookingStatus(str, Enum):
    """Car sharing booking status."""

    RESERVED = "reserved"
    CHANGED = "changed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class CarInfo(BaseModel):
    """Car information."""

    car_type: str | None = Field(None, description="Car type/model")
    car_number: str | None = Field(None, description="Car license plate number")
    car_name: str | None = Field(None, description="Car name/identifier")


class StationInfo(BaseModel):
    """Car sharing station information."""

    station_name: str = Field(..., description="Station name")
    station_address: str | None = Field(None, description="Station address")
    station_code: str | None = Field(None, description="Station code/ID")


class CarShareBooking(BaseModel):
    """Car sharing booking information."""

    # Booking identification
    booking_reference: str | None = Field(None, description="Booking reference number")
    confirmation_code: str | None = Field(None, description="Booking confirmation code")

    # Provider and status
    provider: CarShareProvider = Field(..., description="Car sharing provider")
    status: BookingStatus = Field(BookingStatus.RESERVED, description="Booking status")

    # User information
    user_name: str = Field(..., description="User name")

    # Booking times
    start_time: datetime = Field(..., description="Rental start time")
    end_time: datetime = Field(..., description="Rental end time")

    # Location and car details
    station: StationInfo = Field(..., description="Pickup/return station")
    car: CarInfo | None = Field(None, description="Car information")

    # Booking details
    booking_date: datetime | None = Field(None, description="When booking was made")
    total_price: str | None = Field(None, description="Total price with currency")

    # Email metadata
    email_received_at: datetime | None = Field(
        None, description="When email was received"
    )

    @property
    def duration_hours(self) -> float:
        """Calculate rental duration in hours."""
        delta = self.end_time - self.start_time
        return delta.total_seconds() / 3600

    @property
    def is_active(self) -> bool:
        """Check if booking is active (not cancelled)."""
        return self.status != BookingStatus.CANCELLED

    @property
    def unique_key(self) -> str:
        """Generate unique key for overlap detection."""
        # Use start time and station for overlap detection
        start_str = self.start_time.strftime("%Y%m%d%H%M")
        station_key = self.station.station_code or self.station.station_name
        return f"{self.provider}_{station_key}_{start_str}"


def get_provider_from_domain(domain: str) -> CarShareProvider | None:
    """Get car share provider from email domain."""
    domain_mapping = {
        "carshares.jp": CarShareProvider.MITSUI_CARSHARES,
        "share.timescar.jp": CarShareProvider.TIMES_CAR,
    }

    for provider_domain, provider in domain_mapping.items():
        if domain == provider_domain or domain.endswith("." + provider_domain):
            return provider

    return None
