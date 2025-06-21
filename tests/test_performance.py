"""Performance tests for email filtering functionality."""

from datetime import datetime

import pytest

from src.models.email_types import EmailMessage
from src.utils.email_filter import (
    EmailFilter,
    is_likely_booking_email,
    is_promotional_email,
)


@pytest.fixture
def sample_emails():
    """Create sample emails for performance testing."""
    base_time = datetime.now()
    return [
        EmailMessage(
            id="1",
            subject="ANA予約確認",
            body="予約内容...",
            sender="noreply@ana.co.jp",
            received_at=base_time,
            thread_id="thread1",
        ),
        EmailMessage(
            id="2",
            subject="キャンペーンのお知らせ",
            body="キャンペーン内容...",
            sender="info@ana.co.jp",
            received_at=base_time,
            thread_id="thread2",
        ),
        EmailMessage(
            id="3",
            subject="JAL eチケット",
            body="チケット内容...",
            sender="noreply@booking.jal.com",
            received_at=base_time,
            thread_id="thread3",
        ),
        EmailMessage(
            id="4",
            subject="タイムズカー利用開始",
            body="利用内容...",
            sender="noreply@share.timescar.jp",
            received_at=base_time,
            thread_id="thread4",
        ),
        EmailMessage(
            id="5",
            subject="プレゼントキャンペーン",
            body="プレゼント内容...",
            sender="campaign@carshares.jp",
            received_at=base_time,
            thread_id="thread5",
        ),
    ] * 20  # 100 emails total


def test_email_filter_performance(benchmark, sample_emails):
    """Test email filtering performance."""
    email_filter = EmailFilter()

    def filter_emails():
        results = []
        for email in sample_emails:
            is_promo = email_filter.is_promotional_email(email)
            is_booking = email_filter.is_likely_booking_email(email)
            results.append((is_promo, is_booking))
        return results

    result = benchmark(filter_emails)
    assert len(result) == len(sample_emails)


def test_promotional_filter_performance(benchmark, sample_emails):
    """Test promotional filtering performance."""

    def filter_promotional():
        return [is_promotional_email(email) for email in sample_emails]

    result = benchmark(filter_promotional)
    assert len(result) == len(sample_emails)


def test_booking_detection_performance(benchmark, sample_emails):
    """Test booking detection performance."""

    def detect_bookings():
        return [is_likely_booking_email(email) for email in sample_emails]

    result = benchmark(detect_bookings)
    assert len(result) == len(sample_emails)
