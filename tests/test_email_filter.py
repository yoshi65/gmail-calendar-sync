"""Tests for email filtering functionality."""

from datetime import datetime

from src.models.email_types import EmailMessage
from src.utils.email_filter import EmailFilter, is_promotional_email


class TestEmailFilter:
    """Test email filtering functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.email_filter = EmailFilter()

    def test_promotional_email_campaign_subject(self):
        """Test detection of promotional emails with campaign keywords in subject."""
        email = EmailMessage(
            id="test_promo_1",
            subject="ANAキャンペーン開始！マイルプレゼント",
            sender="ana@ana.co.jp",
            body="キャンペーンの詳細についてはこちらをクリック",
            received_at=datetime.now(),
            thread_id="thread_1",
            labels=[],
        )

        assert self.email_filter.is_promotional_email(email) is True

    def test_promotional_email_multiple_patterns(self):
        """Test detection of promotional emails with multiple patterns."""
        email = EmailMessage(
            id="test_promo_2",
            subject="お得な情報をお知らせ",
            sender="carshares@carshares.jp",
            body="期間限定キャンペーン実施中！今すぐクリックして詳しくはこちら",
            received_at=datetime.now(),
            thread_id="thread_2",
            labels=[],
        )

        assert self.email_filter.is_promotional_email(email) is True

    def test_flight_booking_confirmation(self):
        """Test that flight booking confirmations are not filtered."""
        email = EmailMessage(
            id="test_booking_1",
            subject="ご予約を受付けました - 確認番号: 123456789",
            sender="booking@ana.co.jp",
            body="航空券のご予約が完了いたしました。確認番号: 123456789 搭乗券はこちら",
            received_at=datetime.now(),
            thread_id="thread_3",
            labels=[],
        )

        assert self.email_filter.is_promotional_email(email) is False

    def test_carshare_booking_confirmation(self):
        """Test that car sharing booking confirmations are not filtered."""
        email = EmailMessage(
            id="test_booking_2",
            subject="予約開始のお知らせ - 利用開始しました",
            sender="noreply@carshares.jp",
            body="タイムズカーの利用を開始しました。返却時間にご注意ください。",
            received_at=datetime.now(),
            thread_id="thread_4",
            labels=[],
        )

        assert self.email_filter.is_promotional_email(email) is False

    def test_carshare_cancellation(self):
        """Test that car sharing cancellations are not filtered."""
        email = EmailMessage(
            id="test_cancel_1",
            subject="予約キャンセルを受付けました",
            sender="noreply@share.timescar.jp",
            body="予約のキャンセルが完了しました。",
            received_at=datetime.now(),
            thread_id="thread_5",
            labels=[],
        )

        assert self.email_filter.is_promotional_email(email) is False

    def test_newsletter_email(self):
        """Test detection of newsletter emails."""
        email = EmailMessage(
            id="test_newsletter_1",
            subject="JALからのお知らせメルマガ",
            sender="newsletter@jal.com",
            body="今月の新着情報をお届けします。配信停止はこちら",
            received_at=datetime.now(),
            thread_id="thread_6",
            labels=[],
        )

        assert self.email_filter.is_promotional_email(email) is True

    def test_false_positive_prevention(self):
        """Test that emails with both promotional and booking keywords are classified correctly."""
        # Email with campaign keywords but clearly a booking confirmation
        email = EmailMessage(
            id="test_mixed_1",
            subject="予約確認 - ご予約を受付けました",
            sender="booking@ana.co.jp",
            body="航空券のご予約が完了しました。確認番号: 987654321 キャンペーン対象便です。",
            received_at=datetime.now(),
            thread_id="thread_7",
            labels=[],
        )

        # Should not be filtered because it's clearly a booking confirmation
        assert self.email_filter.is_promotional_email(email) is False

    def test_booking_with_campaign_mention(self):
        """Test that booking emails mentioning campaigns are not filtered."""
        email = EmailMessage(
            id="test_booking_campaign",
            subject="【ANA】ご予約を受付けました",
            sender="booking@ana.co.jp",
            body="搭乗券の予約が完了しました。確認番号: 123456789 今回のフライトはマイルキャンペーン対象です。チェックインはこちら",
            received_at=datetime.now(),
            thread_id="thread_booking_campaign",
            labels=[],
        )

        # Should not be filtered - booking confirmation with campaign mention
        assert self.email_filter.is_promotional_email(email) is False

    def test_pure_campaign_email(self):
        """Test that pure campaign emails are filtered."""
        email = EmailMessage(
            id="test_pure_campaign",
            subject="【ANA】期間限定キャンペーン！プレゼント抽選",
            sender="campaign@ana.co.jp",
            body="今だけの特別キャンペーン！応募はこちらから。詳しくはこちらをクリック。配信停止はこちら",
            received_at=datetime.now(),
            thread_id="thread_pure_campaign",
            labels=[],
        )

        # Should be filtered - multiple promotional patterns
        assert self.email_filter.is_promotional_email(email) is True

    def test_convenience_function(self):
        """Test the convenience function."""
        email = EmailMessage(
            id="test_conv_1",
            subject="限定プレゼントキャンペーン",
            sender="promo@ana.co.jp",
            body="期間限定のキャンペーンです",
            received_at=datetime.now(),
            thread_id="thread_8",
            labels=[],
        )

        assert is_promotional_email(email) is True

    def test_edge_case_empty_subject(self):
        """Test handling of emails with empty subject but clear promotional body."""
        email = EmailMessage(
            id="test_empty_1",
            subject="",
            sender="test@ana.co.jp",
            body="キャンペーン情報です。詳しくはこちらをクリック。応募はこちらから。配信停止はこちら",
            received_at=datetime.now(),
            thread_id="thread_9",
            labels=[],
        )

        # Should be detected based on multiple body patterns (3+ matches)
        assert self.email_filter.is_promotional_email(email) is True

    def test_normal_email_not_filtered(self):
        """Test that normal emails without promotional patterns are not filtered."""
        email = EmailMessage(
            id="test_normal_1",
            subject="利用状況のお知らせ",
            sender="info@carshares.jp",
            body="先月のご利用状況をお知らせいたします。",
            received_at=datetime.now(),
            thread_id="thread_10",
            labels=[],
        )

        assert self.email_filter.is_promotional_email(email) is False
