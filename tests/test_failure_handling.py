"""Regression checks for failures previously reported as successful skips."""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import Mock, patch

import pytest

from src.main import main, process_emails
from src.models.carshare import (
    BookingStatus,
    CarShareBooking,
    CarShareProvider,
    StationInfo,
)
from src.models.email_types import EmailMessage
from src.processors.carshare_processor import CarShareEmailProcessor
from src.processors.flight_processor import FlightEmailProcessor
from src.services.openai_client import OpenAIClient
from src.utils.config import Settings
from src.utils.logging import add_severity


@pytest.mark.parametrize("kind", ["flight", "carshare"])
@pytest.mark.parametrize(
    "response",
    [
        RuntimeError("private response"),
        "",
        "broken",
        "{}",
        '{"no_booking_found": "true"}',
    ],
)
def test_extraction_failure_reaches_summary(kind, response):
    settings = Settings(_env_file=None, openai_api_key="test-key")
    with patch("src.services.openai_client.OpenAI"):
        client = OpenAIClient(settings)
    if isinstance(response, Exception):
        client.client.chat.completions.create.side_effect = response
    else:
        result = Mock()
        result.usage = None
        result.choices = [Mock(message=Mock(content=response))]
        client.client.chat.completions.create.return_value = result
    processor_type = (
        FlightEmailProcessor if kind == "flight" else CarShareEmailProcessor
    )
    with patch("src.services.openai_client.OpenAI"):
        processor = processor_type(settings)
    processor.openai_client = client
    processor.calendar_client = Mock()
    processor.calendar_client.scope_events.side_effect = lambda events, _: events
    email = EmailMessage(
        id="test-id",
        thread_id="test-thread",
        subject="予約確認 Flight Confirmation",
        sender="notice@ana.co.jp" if kind == "flight" else "notice@share.timescar.jp",
        body="予約の詳細",
        received_at=datetime.now(UTC),
    )
    gmail = Mock()
    gmail.get_all_supported_emails.return_value = [email]
    factory = Mock()
    factory.get_processor.return_value = processor
    results = process_emails(gmail, Mock(), factory, settings)
    assert len(results) == 1
    assert not results[0].success
    assert results[0].error_message is not None
    assert results[0].error_message.startswith("Processing error:")
    assert "private response" not in results[0].error_message
    gmail.add_label.assert_not_called()
    processor.calendar_client.create_events.assert_not_called()
    with (
        patch("src.main.get_settings", return_value=settings),
        patch("src.main.setup_logging"),
        patch("src.main.process_emails", return_value=results),
        patch("src.main.GmailClient"),
        patch("src.main.CalendarClient"),
        patch("src.main.EmailProcessorFactory"),
        patch("src.main.send_slack_notification") as notify,
    ):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        notify.assert_called_once_with(results, settings)


@pytest.mark.parametrize("cancelled", [False, True])
def test_carshare_write_failure_is_not_success(cancelled):
    settings = Settings(_env_file=None, openai_api_key="test-key")
    with patch("src.services.openai_client.OpenAI"):
        processor: Any = CarShareEmailProcessor(settings)
    start = datetime(2030, 1, 1, 10, tzinfo=UTC)
    booking = CarShareBooking(
        provider=CarShareProvider.TIMES_CAR,
        status=BookingStatus.CANCELLED if cancelled else BookingStatus.RESERVED,
        user_name="Test",
        booking_reference="TEST123",
        start_time=start,
        end_time=start + timedelta(hours=1),
        station=StationInfo(station_name="Test Station"),
    )
    processor.extract_data = Mock(return_value=booking.model_dump())
    processor.find_overlapping_events = Mock(
        return_value=[{"id": "old"}] if cancelled else []
    )
    processor.calendar_client = Mock()
    processor.calendar_client.scope_events.side_effect = lambda events, _: events
    processor.calendar_client.find_events_by_reservation_id.return_value = []
    processor.calendar_client.find_events_by_source_email.return_value = []
    processor.calendar_client.delete_event.return_value = False
    processor.calendar_client.create_events.return_value = [None]
    email = EmailMessage(
        id="test-id",
        thread_id="thread",
        subject="予約確認",
        sender="notice@share.timescar.jp",
        body="details",
        received_at=start,
    )
    result = processor.process(email)
    assert not result.success
    assert result.error_message is not None
    assert result.error_message.startswith("Processing error:")


@pytest.mark.parametrize(
    "level, expected", [("error", "ERROR"), ("warning", "WARNING"), ("info", "INFO")]
)
def test_cloud_logging_severity(level, expected):
    assert add_severity(None, level, {"event": "test"})["severity"] == expected
