"""Flight booking data models."""

from datetime import datetime

from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    TypeAdapter,
    ValidationError,
    field_validator,
)

# Reused adapter so an injected/malformed check-in URL is validated in isolation.
_CHECKIN_URL_ADAPTER = TypeAdapter(HttpUrl)


class Airport(BaseModel):
    """Airport information."""

    code: str = Field(..., description="Airport code (e.g., NRT, HND)")
    name: str | None = Field(None, description="Airport name")
    city: str | None = Field(None, description="City name")


class FlightSegment(BaseModel):
    """Individual flight segment."""

    airline: str = Field(..., description="Airline name")
    flight_number: str = Field(..., description="Flight number")
    departure_airport: Airport
    arrival_airport: Airport
    departure_time: datetime
    arrival_time: datetime
    aircraft_type: str | None = Field(None, description="Aircraft type")
    seat_number: str | None = Field(None, description="Seat number")

    @field_validator("departure_time", "arrival_time")
    @classmethod
    def validate_times(cls, v: datetime) -> datetime:
        """Ensure times are timezone-aware."""
        if v.tzinfo is None:
            raise ValueError("Flight times must be timezone-aware")
        return v


class FlightBooking(BaseModel):
    """Complete flight booking information."""

    confirmation_code: str | None = Field(None, description="Booking confirmation code")
    passenger_name: str = Field(..., description="Passenger name")
    booking_reference: str | None = Field(
        None, description="Additional booking reference"
    )

    # Flight segments (outbound and return)
    outbound_segments: list[FlightSegment] = Field(..., min_length=1)
    return_segments: list[FlightSegment] = Field(default_factory=list)

    # Booking details
    booking_date: datetime | None = Field(
        None, description="Date when booking was made"
    )
    total_price: str | None = Field(None, description="Total price with currency")

    # Check-in information
    checkin_url: HttpUrl | None = Field(None, description="Online check-in URL")
    checkin_opens: datetime | None = Field(None, description="When check-in opens")

    @field_validator("checkin_url", mode="before")
    @classmethod
    def sanitize_checkin_url(cls, v: object) -> object:
        """Coerce a malformed or non-http(s) check-in URL to None.

        The value originates from an LLM parsing untrusted email text, so a
        crafted email could try to plant a phishing link. Returning None for an
        invalid URL neutralizes the link without discarding the valid booking.
        """
        if not v:
            return None
        try:
            return _CHECKIN_URL_ADAPTER.validate_python(v)
        except ValidationError:
            return None

    @property
    def departure_date(self) -> datetime:
        """Get departure date of the first segment."""
        return self.outbound_segments[0].departure_time

    @property
    def return_date(self) -> datetime | None:
        """Get departure date of return flight if exists."""
        if self.return_segments:
            return self.return_segments[0].departure_time
        return None

    @property
    def is_round_trip(self) -> bool:
        """Check if this is a round trip booking."""
        return len(self.return_segments) > 0
