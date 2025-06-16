"""OpenAI API client for email content analysis."""

import json
from datetime import datetime
from typing import Any

import structlog
from openai import OpenAI

from ..models.flight import Airport, FlightBooking, FlightSegment
from ..utils.config import Settings

logger = structlog.get_logger()


class OpenAIClient:
    """OpenAI API client for analyzing email content."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = OpenAI(api_key=settings.openai_api_key)

    def extract_flight_info(self, email_content: str, email_subject: str = "") -> FlightBooking | None:
        """Extract flight booking information from email content."""
        system_prompt = """You are an expert at extracting flight booking information from emails.

Extract flight booking details from the provided email and return them in the following JSON format:

{
  "confirmation_code": "string",
  "passenger_name": "string",
  "booking_reference": "string (optional)",
  "outbound_segments": [
    {
      "airline": "string",
      "flight_number": "string",
      "departure_airport": {
        "code": "string (3-letter airport code)",
        "name": "string (optional)",
        "city": "string (optional)"
      },
      "arrival_airport": {
        "code": "string (3-letter airport code)",
        "name": "string (optional)",
        "city": "string (optional)"
      },
      "departure_time": "ISO 8601 datetime with timezone",
      "arrival_time": "ISO 8601 datetime with timezone",
      "aircraft_type": "string (optional)",
      "seat_number": "string (optional)"
    }
  ],
  "return_segments": [
    // Same format as outbound_segments, empty array if one-way
  ],
  "booking_date": "ISO 8601 datetime (optional)",
  "total_price": "string with currency (optional)",
  "checkin_url": "string (optional)",
  "checkin_opens": "ISO 8601 datetime (optional)"
}

Important guidelines:
- Always include timezone information in datetime fields (e.g., "2024-01-15T10:30:00+09:00")
- Use 3-letter IATA airport codes (NRT, HND, LAX, etc.)
- Extract passenger name exactly as it appears
- If multiple passengers, use the first passenger's name
- Return null if no valid flight information is found
- Be precise with dates and times, including time zones if available
- For confirmation_code: ONLY use values that appear after "確認番号" or "Confirmation Number" labels in the email. These are typically longer numeric codes (6+ digits). DO NOT use short numbers like "0709" or "0520" which are reservation numbers, not confirmation codes
- For booking_reference: Extract the first reservation number (予約番号) found in the email
- If you cannot find a line with "確認番号" label, return null for confirmation_code
"""

        user_prompt = f"""Email Subject: {email_subject}

Email Content:
{email_content}

Extract the flight booking information from this email and return it as JSON."""

        try:
            logger.info("Extracting flight info from email", subject=email_subject[:100])

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )

            content = response.choices[0].message.content
            logger.debug("OpenAI response", content=content)

            if not content or content.strip().lower() == "null":
                logger.info("No flight information found in email")
                return None

            # Parse JSON response
            try:
                # Remove markdown code blocks if present
                if content.startswith("```json"):
                    content = content.replace("```json\n", "").replace("```", "").strip()
                elif content.startswith("```"):
                    content = content.replace("```\n", "").replace("```", "").strip()
                
                flight_data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error("Failed to parse OpenAI JSON response", error=str(e), content=content)
                return None

            # Convert to FlightBooking model
            flight_booking = self._convert_to_flight_booking(flight_data)

            if flight_booking:
                logger.info("Successfully extracted flight booking",
                           confirmation_code=flight_booking.confirmation_code,
                           passenger=flight_booking.passenger_name,
                           outbound_segments=len(flight_booking.outbound_segments),
                           return_segments=len(flight_booking.return_segments))

            return flight_booking

        except Exception as e:
            logger.error("Failed to extract flight info", error=str(e))
            return None

    def _convert_to_flight_booking(self, data: dict[str, Any]) -> FlightBooking | None:
        """Convert extracted data to FlightBooking model."""
        try:
            # Parse outbound segments
            outbound_segments = []
            for segment_data in data.get("outbound_segments", []):
                segment = self._create_flight_segment(segment_data)
                if segment:
                    outbound_segments.append(segment)

            if not outbound_segments:
                logger.warning("No valid outbound segments found")
                return None

            # Parse return segments
            return_segments = []
            for segment_data in data.get("return_segments", []):
                segment = self._create_flight_segment(segment_data)
                if segment:
                    return_segments.append(segment)

            # Parse optional dates
            booking_date = None
            if data.get("booking_date"):
                try:
                    booking_date = datetime.fromisoformat(data["booking_date"])
                except ValueError:
                    logger.warning("Invalid booking date format", date=data["booking_date"])

            checkin_opens = None
            if data.get("checkin_opens"):
                try:
                    checkin_opens = datetime.fromisoformat(data["checkin_opens"])
                except ValueError:
                    logger.warning("Invalid checkin opens date format", date=data["checkin_opens"])

            flight_booking = FlightBooking(
                confirmation_code=data["confirmation_code"],
                passenger_name=data["passenger_name"],
                booking_reference=data.get("booking_reference"),
                outbound_segments=outbound_segments,
                return_segments=return_segments,
                booking_date=booking_date,
                total_price=data.get("total_price"),
                checkin_url=data.get("checkin_url"),
                checkin_opens=checkin_opens,
            )

            return flight_booking

        except Exception as e:
            logger.error("Failed to convert flight data", error=str(e), data=data)
            return None

    def _create_flight_segment(self, segment_data: dict[str, Any]) -> FlightSegment | None:
        """Create FlightSegment from extracted data."""
        try:
            # Parse airports
            dep_airport_data = segment_data["departure_airport"]
            arr_airport_data = segment_data["arrival_airport"]

            departure_airport = Airport(
                code=dep_airport_data["code"],
                name=dep_airport_data.get("name"),
                city=dep_airport_data.get("city"),
            )

            arrival_airport = Airport(
                code=arr_airport_data["code"],
                name=arr_airport_data.get("name"),
                city=arr_airport_data.get("city"),
            )

            # Parse times
            departure_time = datetime.fromisoformat(segment_data["departure_time"])
            arrival_time = datetime.fromisoformat(segment_data["arrival_time"])

            segment = FlightSegment(
                airline=segment_data["airline"],
                flight_number=segment_data["flight_number"],
                departure_airport=departure_airport,
                arrival_airport=arrival_airport,
                departure_time=departure_time,
                arrival_time=arrival_time,
                aircraft_type=segment_data.get("aircraft_type"),
                seat_number=segment_data.get("seat_number"),
            )

            return segment

        except Exception as e:
            logger.error("Failed to create flight segment", error=str(e), segment_data=segment_data)
            return None
