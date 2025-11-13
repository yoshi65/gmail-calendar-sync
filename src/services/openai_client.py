"""OpenAI API client for email content analysis."""

import json
import time
from datetime import datetime
from typing import Any

import structlog
from openai import OpenAI

from ..models.carshare import (
    BookingStatus,
    CarInfo,
    CarShareBooking,
    CarShareProvider,
    StationInfo,
)
from ..models.flight import Airport, FlightBooking, FlightSegment
from ..models.openai_metrics import OpenAIMetrics
from ..utils.config import Settings
from ..utils.openai_metrics_collector import get_metrics_collector

logger = structlog.get_logger()


class OpenAIClient:
    """OpenAI API client for analyzing email content."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = OpenAI(api_key=settings.openai_api_key)

    def extract_flight_info(
        self, email_content: str, email_subject: str = ""
    ) -> FlightBooking | None:
        """Extract flight booking information from email content."""
        system_prompt = """You are an expert at extracting flight booking information from emails in multiple languages (Japanese, English, etc.).

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
- **Emails may be in Japanese, English, or other languages** - extract information regardless of language
- **Ignore forwarded email headers** - Skip lines starting with ">" or sections like "---------- Forwarded message ---------"
- Always include timezone information in datetime fields (e.g., "2024-01-15T10:30:00+09:00" or "2025-11-25T23:55:00+09:00")
- Use 3-letter IATA airport codes (NRT, HND, LAX, KUL, BKK, etc.) - these are universal across languages
- Extract passenger name exactly as it appears
- If multiple passengers, use the first passenger's name
- Return null if no valid flight information is found
- Be precise with dates and times, including time zones if available
- **For confirmation_code/booking_reference**:
  - Japanese: Look for "確認番号" or "予約番号" (typically 6-9 digits)
  - English: Look for "Booking No", "Confirmation Number", "PNR" (may be 6-character alphanumeric like "I6U6TY")
  - Accept both numeric-only and alphanumeric formats
  - DO NOT use short numbers like "0709" which are likely dates
- For international flights, pay special attention to timezone differences between departure and arrival
"""

        user_prompt = f"""Email Subject: {email_subject}

Email Content:
{email_content}

Extract the flight booking information from this email and return it as JSON."""

        try:
            logger.info(
                "Extracting flight info from email", subject=email_subject[:100]
            )

            # Start timing
            start_time = time.time()

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=2000,
            )

            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000

            # Create and collect metrics
            metrics = OpenAIMetrics.create_from_response(
                model="gpt-3.5-turbo",
                email_type="flight",
                processing_time_ms=processing_time_ms,
                response=response,
                success=True,
            )

            # Add to metrics collector
            get_metrics_collector().add_metrics(metrics)

            logger.info(
                "OpenAI API call completed",
                message="OpenAI API call completed",
                model=metrics.model,
                email_type=metrics.email_type,
                processing_time_ms=metrics.processing_time_ms,
                prompt_tokens=metrics.usage.prompt_tokens,
                completion_tokens=metrics.usage.completion_tokens,
                total_tokens=metrics.usage.total_tokens,
                cost_usd=metrics.cost_usd,
                success=metrics.success,
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
                    content = (
                        content.replace("```json\n", "").replace("```", "").strip()
                    )
                elif content.startswith("```"):
                    content = content.replace("```\n", "").replace("```", "").strip()

                flight_data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(
                    "Failed to parse OpenAI JSON response",
                    error=str(e),
                    content=content,
                )
                return None

            # Convert to FlightBooking model
            flight_booking = self._convert_to_flight_booking(flight_data)

            if flight_booking:
                logger.info(
                    "Successfully extracted flight booking",
                    confirmation_code=flight_booking.confirmation_code,
                    passenger=flight_booking.passenger_name,
                    outbound_segments=len(flight_booking.outbound_segments),
                    return_segments=len(flight_booking.return_segments),
                )

            return flight_booking

        except Exception as e:
            # Calculate processing time even for failed calls
            processing_time_ms = (
                (time.time() - start_time) * 1000 if "start_time" in locals() else 0
            )

            # Create and collect error metrics
            error_metrics = OpenAIMetrics.create_from_response(
                model="gpt-3.5-turbo",
                email_type="flight",
                processing_time_ms=processing_time_ms,
                response=None,
                success=False,
                error_message=str(e),
            )

            # Add to metrics collector
            get_metrics_collector().add_metrics(error_metrics)

            logger.error(
                "OpenAI API call failed",
                message="OpenAI API call failed",
                model=error_metrics.model,
                email_type=error_metrics.email_type,
                processing_time_ms=error_metrics.processing_time_ms,
                cost_usd=error_metrics.cost_usd,
                success=error_metrics.success,
                error=str(e),
            )
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
                    logger.warning(
                        "Invalid booking date format", date=data["booking_date"]
                    )

            checkin_opens = None
            if data.get("checkin_opens"):
                try:
                    checkin_opens = datetime.fromisoformat(data["checkin_opens"])
                except ValueError:
                    logger.warning(
                        "Invalid checkin opens date format", date=data["checkin_opens"]
                    )

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

    def _create_flight_segment(
        self, segment_data: dict[str, Any]
    ) -> FlightSegment | None:
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
            logger.error(
                "Failed to create flight segment",
                error=str(e),
                segment_data=segment_data,
            )
            return None

    def extract_carshare_info(
        self, email_content: str, email_subject: str = "", provider: str = ""
    ) -> CarShareBooking | None:
        """Extract car sharing booking information from email content."""
        system_prompt = """You are an expert at extracting car sharing booking information from emails.

Extract car sharing booking details from the provided email and return them in the following JSON format:

{
  "booking_reference": "string (optional)",
  "confirmation_code": "string (optional)",
  "status": "reserved|changed|cancelled|completed",
  "user_name": "string",
  "start_time": "ISO 8601 datetime with timezone",
  "end_time": "ISO 8601 datetime with timezone",
  "station": {
    "station_name": "string",
    "station_address": "string (optional)",
    "station_code": "string (optional)"
  },
  "car": {
    "car_type": "string (optional)",
    "car_number": "string (optional)",
    "car_name": "string (optional)"
  },
  "booking_date": "ISO 8601 datetime (optional)",
  "total_price": "string with currency (optional)"
}

Important guidelines:
- Always include timezone information in datetime fields (e.g., "2024-01-15T10:30:00+09:00")
- Extract user name exactly as it appears in the email
- For status field, analyze the email SUBJECT LINE FIRST, then email content to determine the booking status:
  * "reserved": Subject contains "予約を受付けました" or "予約開始" or similar reservation confirmation
  * "changed": Subject contains "変更を受付けました" or "変更" or similar modification text
  * "cancelled": Subject contains "キャンセル" or "予約を取り消し" or "取消" or similar cancellation text
  * "completed": Subject contains "利用終了" or "返却" or "利用完了" or similar completion text
  * IMPORTANT: The subject line is the most reliable indicator - prioritize it over email body content
- Return null if no valid car sharing information is found
- Be precise with dates and times, including time zones if available
- Extract station name and address carefully
- Look for car type, model, or license plate information
- For Times Car emails, look for "タイムズカー" related information
- For 三井のカーシェアーズ emails, look for "カレコ" or "三井のカーシェアーズ" related information
"""

        user_prompt = f"""Email Subject: {email_subject}
Provider: {provider}

Email Content:
{email_content}

Extract the car sharing booking information from this email and return it as JSON."""

        try:
            logger.info(
                "Extracting car sharing info from email",
                subject=email_subject[:100],
                provider=provider,
            )

            # Start timing
            start_time = time.time()

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=2000,
            )

            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000

            # Create and collect metrics
            metrics = OpenAIMetrics.create_from_response(
                model="gpt-3.5-turbo",
                email_type="carshare",
                processing_time_ms=processing_time_ms,
                response=response,
                success=True,
            )

            # Add to metrics collector
            get_metrics_collector().add_metrics(metrics)

            logger.info(
                "OpenAI API call completed",
                message="OpenAI API call completed",
                model=metrics.model,
                email_type=metrics.email_type,
                processing_time_ms=metrics.processing_time_ms,
                prompt_tokens=metrics.usage.prompt_tokens,
                completion_tokens=metrics.usage.completion_tokens,
                total_tokens=metrics.usage.total_tokens,
                cost_usd=metrics.cost_usd,
                success=metrics.success,
            )

            content = response.choices[0].message.content
            logger.debug("OpenAI response", content=content)

            if not content or content.strip().lower() == "null":
                logger.info("No car sharing information found in email")
                return None

            # Parse JSON response
            try:
                # Remove markdown code blocks if present
                if content.startswith("```json"):
                    content = (
                        content.replace("```json\n", "").replace("```", "").strip()
                    )
                elif content.startswith("```"):
                    content = content.replace("```\n", "").replace("```", "").strip()

                carshare_data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(
                    "Failed to parse OpenAI JSON response",
                    error=str(e),
                    content=content,
                )
                return None

            # Convert to CarShareBooking model
            carshare_booking = self._convert_to_carshare_booking(
                carshare_data, provider
            )

            if carshare_booking:
                logger.info(
                    "Successfully extracted car sharing booking",
                    booking_reference=carshare_booking.booking_reference,
                    user_name=carshare_booking.user_name,
                    provider=carshare_booking.provider,
                    status=carshare_booking.status,
                    station=carshare_booking.station.station_name,
                )

            return carshare_booking

        except Exception as e:
            # Calculate processing time even for failed calls
            processing_time_ms = (
                (time.time() - start_time) * 1000 if "start_time" in locals() else 0
            )

            # Create and collect error metrics
            error_metrics = OpenAIMetrics.create_from_response(
                model="gpt-3.5-turbo",
                email_type="carshare",
                processing_time_ms=processing_time_ms,
                response=None,
                success=False,
                error_message=str(e),
            )

            # Add to metrics collector
            get_metrics_collector().add_metrics(error_metrics)

            logger.error(
                "OpenAI API call failed",
                message="OpenAI API call failed",
                model=error_metrics.model,
                email_type=error_metrics.email_type,
                processing_time_ms=error_metrics.processing_time_ms,
                cost_usd=error_metrics.cost_usd,
                success=error_metrics.success,
                error=str(e),
            )
            return None

    def _convert_to_carshare_booking(
        self, data: dict[str, Any], provider: str
    ) -> CarShareBooking | None:
        """Convert extracted data to CarShareBooking model."""
        try:
            # Map provider string to enum
            provider_mapping = {
                "mitsui_carshares": CarShareProvider.MITSUI_CARSHARES,
                "times_car": CarShareProvider.TIMES_CAR,
            }

            provider_enum = provider_mapping.get(provider)
            if not provider_enum:
                logger.warning("Unknown car sharing provider", provider=provider)
                return None

            # Parse status
            status_mapping = {
                "reserved": BookingStatus.RESERVED,
                "changed": BookingStatus.CHANGED,
                "cancelled": BookingStatus.CANCELLED,
                "completed": BookingStatus.COMPLETED,
            }

            status = status_mapping.get(
                data.get("status", "reserved"), BookingStatus.RESERVED
            )

            # Parse station info
            station_data = data.get("station", {})
            if not station_data.get("station_name"):
                logger.warning("No station name found in car sharing data")
                return None

            station = StationInfo(
                station_name=station_data["station_name"],
                station_address=station_data.get("station_address"),
                station_code=station_data.get("station_code"),
            )

            # Parse car info (optional)
            car = None
            car_data = data.get("car")
            if car_data and any(car_data.values()):
                car = CarInfo(
                    car_type=car_data.get("car_type"),
                    car_number=car_data.get("car_number"),
                    car_name=car_data.get("car_name"),
                )

            # Parse optional dates
            booking_date = None
            if data.get("booking_date"):
                try:
                    booking_date = datetime.fromisoformat(data["booking_date"])
                except ValueError:
                    logger.warning(
                        "Invalid booking date format", date=data["booking_date"]
                    )

            # Parse required times
            try:
                start_time = datetime.fromisoformat(data["start_time"])
                end_time = datetime.fromisoformat(data["end_time"])
            except (KeyError, ValueError) as e:
                logger.error("Invalid or missing start/end time", error=str(e))
                return None

            carshare_booking = CarShareBooking(
                booking_reference=data.get("booking_reference"),
                confirmation_code=data.get("confirmation_code"),
                provider=provider_enum,
                status=status,
                user_name=data["user_name"],
                start_time=start_time,
                end_time=end_time,
                station=station,
                car=car,
                booking_date=booking_date,
                total_price=data.get("total_price"),
                email_received_at=None,  # Set later by processor
            )

            return carshare_booking

        except Exception as e:
            logger.error("Failed to convert car sharing data", error=str(e), data=data)
            return None
