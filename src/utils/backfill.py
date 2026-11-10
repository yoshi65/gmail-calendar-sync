"""Read-only checks before replaying historical booking emails."""

from datetime import datetime
from zoneinfo import ZoneInfo

from ..models.email_types import EmailMessage
from ..processors.factory import EmailProcessorFactory
from ..services.gmail_client import GmailClient
from .config import booking_domain
from .email_filter import is_likely_booking_email, is_promotional_email
from .exceptions import DataExtractionError


def booking_keys(
    email: EmailMessage, data: dict, domains: list[str]
) -> set[tuple[str, str]]:
    """Match reservation identifiers within the original provider's domain."""
    domain = booking_domain(email.original_domain, domains)
    keys = {
        (domain, str(data[field]).strip().upper())
        for field in ("confirmation_code", "booking_reference")
        if data.get(field) and str(data[field]).strip()
    }
    if not keys:
        raise DataExtractionError("Backfill requires a reservation identifier")
    return keys


def prepare_backfill(
    emails: list[EmailMessage], gmail: GmailClient, factory: EmailProcessorFactory
) -> tuple[dict[str, dict | None], set[str]]:
    """Pre-extract bookings and prevent replay over a later processed change/cancel."""
    prepared: dict[str, dict | None] = {}
    pending_keys = {}
    for email in emails:
        processor = factory.get_processor(email)
        if (
            not processor
            or not is_likely_booking_email(email)
            or is_promotional_email(email)
        ):
            continue
        data = processor.extract_data(email)
        prepared[email.id] = data
        if data is not None:
            pending_keys[email.id] = booking_keys(
                email, data, gmail.settings.all_supported_domains
            )
    if not pending_keys:
        return prepared, set()

    oldest = min(email.received_at for email in emails)
    # No end date: a processed cancellation outside the replay interval matters too.
    processed = gmail.get_all_supported_emails(
        start_date=oldest.astimezone(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d"),
        processed_only=True,
    )
    latest: dict[tuple[str, str], datetime] = {}
    for email in processed:
        if email.received_at < oldest:
            continue
        processor = factory.get_processor(email)
        if not processor:
            raise DataExtractionError("Cannot verify a processed booking")
        data = processor.extract_data(email)
        if data is None:
            raise DataExtractionError("Cannot verify a processed booking")
        for key in booking_keys(email, data, gmail.settings.all_supported_domains):
            latest[key] = max(latest.get(key, email.received_at), email.received_at)

    superseded = {
        email.id
        for email in emails
        if email.id in pending_keys
        and any(
            key in latest and latest[key] >= email.received_at
            for key in pending_keys[email.id]
        )
    }
    return prepared, superseded
