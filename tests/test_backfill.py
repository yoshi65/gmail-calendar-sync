"""Pagination, calendar-date boundaries, and safe historical replay."""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import Mock, patch

import pytest

from src.main import process_emails
from src.models.carshare import (
    BookingStatus,
    CarShareBooking,
    CarShareProvider,
    StationInfo,
)
from src.models.email_types import EmailMessage
from src.processors.carshare_processor import CarShareEmailProcessor
from src.services.calendar_client import CalendarClient
from src.services.gmail_client import GmailClient
from src.utils.backfill import prepare_backfill
from src.utils.config import Settings, date_range_bounds
from src.utils.exceptions import CalendarAPIError, DataExtractionError


def email(message_id, received=None):
    return EmailMessage(
        id=message_id,
        thread_id="thread",
        subject="予約確認",
        sender="notice@share.timescar.jp",
        body=message_id,
        received_at=received or datetime(2030, 1, 1, tzinfo=UTC),
    )


def test_gmail_pagination_and_deduplication():
    client = GmailClient(Settings(_env_file=None))
    client._service = Mock()
    request = client._service.users().messages().list()
    request.execute.side_effect = [
        {"messages": [{"id": str(i)} for i in range(100)], "nextPageToken": "next"},
        {"messages": [{"id": "99"}, {"id": "100"}]},
    ]
    assert client.search_emails("test-query") == [str(i) for i in range(101)]
    assert (
        client._service.users().messages().list.call_args.kwargs["pageToken"] == "next"
    )


def test_second_page_failure_is_not_partial_success():
    client = GmailClient(Settings(_env_file=None))
    client._service = Mock()
    client._service.users().messages().list().execute.side_effect = [
        {"messages": [{"id": "one"}], "nextPageToken": "next"},
        RuntimeError("test failure"),
    ]
    with pytest.raises(RuntimeError):
        client.search_emails("test-query")


def test_jst_boundaries_source_dedup_and_order():
    settings = Settings(
        _env_file=None,
        flight_domains=["ana.co.jp"],
        carshare_domains=["share.timescar.jp"],
    )
    client = GmailClient(settings)
    start, end = date_range_bounds("2030-01-01", "2030-01-01")
    assert start is not None and end is not None
    assert start.astimezone(UTC) == datetime(2029, 12, 31, 15, tzinfo=UTC)
    messages = {
        name: email(name, at)
        for name, at in [
            ("before", start - timedelta(milliseconds=1)),
            ("start", start),
            ("last", end - timedelta(milliseconds=1)),
            ("end", end),
        ]
    }
    with (
        patch.object(
            client, "search_emails", return_value=["last", "start", "end", "before"]
        ),
        patch.object(client, "get_email", side_effect=messages.__getitem__) as get,
    ):
        found = client.get_all_supported_emails(
            start_date="2030-01-01", end_date="2030-01-01"
        )
    assert [message.id for message in found] == ["start", "last"]
    assert get.call_count == 4


@pytest.mark.parametrize(
    "start,end", [("2030-01-02", "2030-01-01"), ("2030-1-1", None), (None, "bad")]
)
def test_invalid_range_rejected_before_processing(start, end):
    with pytest.raises(ValueError):
        Settings(_env_file=None, sync_start_date=start, sync_end_date=end)


def test_internal_date_controls_order_not_sender_date():
    client = GmailClient(Settings(_env_file=None))
    client._service = Mock()
    client._service.users().messages().get().execute.return_value = {
        "internalDate": "1893456000123",
        "threadId": "thread",
        "payload": {
            "headers": [{"name": "Date", "value": "Wed, 01 Jan 2020 00:00:00 +0000"}],
            "body": {},
        },
    }
    assert client.get_email("id").received_at == datetime(
        2030, 1, 1, 0, 0, 0, 123000, tzinfo=UTC
    )


def test_calendar_lookup_reads_all_pages():
    client = CalendarClient(Settings(_env_file=None))
    client._service = Mock()
    client._service.events().list().execute.side_effect = [
        {"items": [{"id": "one"}], "nextPageToken": "next"},
        {"items": [{"id": "two"}]},
    ]
    assert [
        event["id"] for event in client.find_events_by_booking_reference("TEST")
    ] == ["one", "two"]


def test_superseding_processed_cancellation_outside_interval_never_recreates_event():
    settings = Settings(
        _env_file=None,
        openai_api_key="test-key",
        sync_start_date="2030-01-01",
        sync_end_date="2030-01-01",
    )
    older, newer = email("older"), email("newer", datetime(2030, 1, 3, tzinfo=UTC))
    gmail = Mock(settings=settings)
    gmail.get_all_supported_emails.side_effect = [[older], [newer]]
    processor = Mock()
    processor.extract_data.return_value = {
        "provider": "times_car",
        "booking_reference": "TEST123",
    }
    factory = Mock()
    factory.get_processor.return_value = processor
    result = process_emails(gmail, Mock(), factory, settings)
    assert result[0].success
    processor.process.assert_not_called()
    gmail.add_label.assert_called_once_with(older.id, settings.gmail_label)
    assert gmail.get_all_supported_emails.call_args.kwargs == {
        "start_date": "2030-01-01",
        "processed_only": True,
    }


def test_unverifiable_processed_booking_stops_replay():
    gmail = Mock(settings=Settings(_env_file=None))
    gmail.get_all_supported_emails.return_value = [
        email("processed", datetime(2030, 1, 2, tzinfo=UTC))
    ]
    processor = Mock()
    processor.extract_data.side_effect = [{"booking_reference": "TEST123"}, None]
    factory = Mock()
    factory.get_processor.return_value = processor
    with pytest.raises(DataExtractionError):
        prepare_backfill([email("pending")], gmail, factory)
    processor.process.assert_not_called()


def test_booking_change_cancel_and_retry_preserve_latest_state():
    settings = Settings(
        _env_file=None,
        openai_api_key="test-key",
        sync_start_date="2030-01-01",
        sync_end_date="2030-01-03",
    )
    messages = [email(str(i), datetime(2030, 1, i + 1, tzinfo=UTC)) for i in range(3)]
    with patch("src.services.openai_client.OpenAI"):
        processor: Any = CarShareEmailProcessor(settings)
    start = datetime(2030, 2, 1, 10, tzinfo=UTC)
    bookings = {
        str(i): CarShareBooking(
            provider=CarShareProvider.TIMES_CAR,
            user_name="Test",
            station=StationInfo(station_name="Test"),
            booking_reference="TEST123",
            status=status,
            start_time=start + timedelta(days=i),
            end_time=start + timedelta(days=i, hours=1),
        ).model_dump()
        for i, status in enumerate(
            [BookingStatus.RESERVED, BookingStatus.CHANGED, BookingStatus.CANCELLED]
        )
    }
    processor.extract_data = Mock(side_effect=lambda item: bookings[item.id])
    events: dict[str, dict] = {}
    calendar = Mock()
    calendar.scope_events.side_effect = lambda events, _: events
    calendar.find_events_by_reservation_id.side_effect = lambda *_: list(
        events.values()
    )
    calendar.find_events_by_source_email.return_value = []
    calendar.list_events.return_value = []

    def create(items):
        events["event"] = {"id": "event", "data": items[0]}
        return ["event"]

    def update(event_id, event):
        events[event_id] = {"id": event_id, "data": event}
        return True

    def delete(event_id):
        events.pop(event_id, None)
        return True

    calendar.create_events.side_effect = create
    calendar.update_event.side_effect = update
    calendar.delete_event.side_effect = delete
    processor.calendar_client = calendar
    factory = Mock()
    factory.get_processor.return_value = processor
    labeled = set()
    gmail = Mock(settings=settings)
    gmail.get_all_supported_emails.side_effect = lambda **kw: [
        item
        for item in messages
        if (item.id in labeled) == kw.get("processed_only", False)
    ]

    def label(message_id, _):
        labeled.add(message_id)
        return True

    gmail.add_label.side_effect = label
    result = process_emails(gmail, calendar, factory, settings)
    assert all(item.success for item in result)
    assert not events and len(labeled) == 3
    assert calendar.create_events.call_count == 1
    assert calendar.update_event.call_count == 1
    assert calendar.delete_event.call_count == 1
    assert process_emails(gmail, calendar, factory, settings) == []


def test_failed_carshare_update_preserves_old_event():
    settings = Settings(_env_file=None, openai_api_key="test-key")
    with patch("src.services.openai_client.OpenAI"):
        processor: Any = CarShareEmailProcessor(settings)
    processor.calendar_client = Mock()
    processor.calendar_client.update_event.return_value = False
    with pytest.raises(CalendarAPIError):
        processor.handle_overlapping_events(
            [{"id": "old"}], [Mock()], Mock(), email("test")
        )
    processor.calendar_client.delete_event.assert_not_called()


def test_no_booking_preflight_result_is_not_extracted_again():
    settings = Settings(_env_file=None, sync_start_date="2030-01-01")
    gmail = Mock(settings=settings)
    gmail.get_all_supported_emails.return_value = [email("no-booking")]
    processor = Mock()
    processor.extract_data.side_effect = [None, {"booking_reference": "UNSAFE"}]
    factory = Mock()
    factory.get_processor.return_value = processor
    result = process_emails(gmail, Mock(), factory, settings)
    assert not result[0].success
    assert result[0].error_message == "No car sharing information found in email"
    processor.extract_data.assert_called_once()
    processor.process.assert_not_called()
    gmail.add_label.assert_not_called()


def test_sender_aliases_share_reservation_history():
    settings = Settings(_env_file=None)
    older = email("older").model_copy(update={"sender": "notice@booking.airasia.com"})
    newer = email("newer", datetime(2030, 1, 2, tzinfo=UTC)).model_copy(
        update={"sender": "notice@airasia.com"}
    )
    gmail = Mock(settings=settings)
    gmail.get_all_supported_emails.return_value = [newer]
    processor = Mock()
    processor.extract_data.return_value = {"confirmation_code": "TEST123"}
    factory = Mock()
    factory.get_processor.return_value = processor
    with pytest.raises(DataExtractionError, match="manual reconciliation"):
        prepare_backfill([older], gmail, factory)


def test_missing_identifier_stops_backfill_before_writes():
    gmail = Mock(settings=Settings(_env_file=None))
    processor = Mock()
    processor.extract_data.return_value = {"station": {"station_name": "Test"}}
    factory = Mock()
    factory.get_processor.return_value = processor
    with pytest.raises(DataExtractionError, match="reservation identifier"):
        prepare_backfill([email("pending")], gmail, factory)
    processor.process.assert_not_called()


def test_same_reservation_code_from_another_provider_is_not_mutated():
    settings = Settings(_env_file=None)
    calendar = CalendarClient(settings)
    events = [
        {
            "id": domain,
            "extendedProperties": {
                "private": {
                    "source": "gmail-calendar-sync",
                    "booking_reference": "TEST123",
                    "source_domain": domain,
                }
            },
        }
        for domain in ("ana.co.jp", "carshares.jp", "share.timescar.jp")
    ]
    assert [item["id"] for item in calendar.scope_events(events, email("test"))] == [
        "share.timescar.jp"
    ]


def test_legacy_event_source_is_verified_from_original_email():
    calendar = CalendarClient(Settings(_env_file=None))
    event: dict = {
        "id": "legacy",
        "extendedProperties": {
            "private": {"source": "gmail-calendar-sync", "source_email_id": "original"}
        },
    }
    with patch("src.services.calendar_client.GmailClient") as gmail:
        gmail.return_value.get_email.return_value = email("original")
        assert calendar.scope_events([event], email("pending")) == [event]
        gmail.return_value.get_email.assert_called_once_with("original")
    event["extendedProperties"]["private"].pop("source_email_id")
    with pytest.raises(CalendarAPIError, match="legacy"):
        calendar.scope_events([event], email("pending"))


@pytest.mark.parametrize("fallback", ["confirmation", "source"])
def test_lookup_scopes_each_identifier_before_trying_next(fallback):
    calendar = CalendarClient(Settings(_env_file=None))
    other = {
        "id": "other",
        "extendedProperties": {
            "private": {"source": "gmail-calendar-sync", "source_domain": "ana.co.jp"}
        },
    }
    correct = {
        "id": "correct",
        "extendedProperties": {
            "private": {
                "source": "gmail-calendar-sync",
                "source_domain": "share.timescar.jp",
            }
        },
    }
    with (
        patch.object(
            calendar, "find_events_by_booking_reference", return_value=[other]
        ),
        patch.object(
            calendar,
            "find_events_by_confirmation_code",
            return_value=[correct] if fallback == "confirmation" else [],
        ),
        patch.object(calendar, "find_events_by_source_email", return_value=[correct]),
    ):
        assert calendar.find_events_by_reservation_id(
            "TEST-BOOKING", "TEST-CONFIRM", email("pending")
        ) == [correct]


def test_equal_values_in_different_identifier_fields_are_not_superseded():
    gmail = Mock(settings=Settings(_env_file=None))
    gmail.get_all_supported_emails.return_value = [
        email("processed", datetime(2030, 1, 2, tzinfo=UTC))
    ]
    processor = Mock()
    processor.extract_data.side_effect = [
        {"confirmation_code": "123456", "booking_reference": "BOOK-A"},
        {"confirmation_code": "987654", "booking_reference": "123456"},
    ]
    factory = Mock()
    factory.get_processor.return_value = processor
    _, superseded = prepare_backfill([email("pending")], gmail, factory)
    assert not superseded


def test_later_processed_partial_flight_does_not_discard_unregistered_leg():
    settings = Settings(
        _env_file=None, sync_start_date="2030-01-01", sync_end_date="2030-01-01"
    )
    older = email("pending").model_copy(update={"sender": "notice@ana.co.jp"})
    newer = email("processed", datetime(2030, 1, 3, tzinfo=UTC)).model_copy(
        update={"sender": "notice@ana.co.jp"}
    )
    outbound = {"flight_number": "NH101"}
    returning = {"flight_number": "NH102"}
    processor = Mock()
    processor.extract_data.side_effect = [
        {
            "confirmation_code": "TEST123",
            "outbound_segments": [outbound],
            "return_segments": [returning],
        },
        {
            "confirmation_code": "TEST123",
            "outbound_segments": [returning],
            "return_segments": [],
        },
    ]
    factory = Mock()
    factory.get_processor.return_value = processor
    gmail = Mock(settings=settings)
    gmail.get_all_supported_emails.side_effect = [[older], [newer]]
    with pytest.raises(DataExtractionError, match="manual reconciliation"):
        process_emails(gmail, Mock(), factory, settings)
    processor.process.assert_not_called()
    gmail.add_label.assert_not_called()
