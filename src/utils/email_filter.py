"""Email filtering utilities to identify promotional emails."""

import re
from re import Pattern

import structlog

from ..models.email_types import EmailMessage

logger = structlog.get_logger()


class EmailFilter:
    """Filter to identify promotional emails that should not be sent to OpenAI."""

    def __init__(self):
        # Promotional subject line patterns (Japanese)
        self.promotional_subject_patterns: list[Pattern[str]] = [
            # Campaign and promotional keywords
            re.compile(r"キャンペーン", re.IGNORECASE),
            re.compile(r"プレゼント", re.IGNORECASE),
            re.compile(r"抽選", re.IGNORECASE),
            re.compile(r"割引", re.IGNORECASE),
            re.compile(r"セール", re.IGNORECASE),
            re.compile(r"特典", re.IGNORECASE),
            re.compile(r"お得", re.IGNORECASE),
            re.compile(r"限定", re.IGNORECASE),
            re.compile(r"応募", re.IGNORECASE),
            re.compile(r"マイル.*キャンペーン", re.IGNORECASE),
            re.compile(r"ポイント.*キャンペーン", re.IGNORECASE),
            # Newsletter indicators
            re.compile(r"メルマガ", re.IGNORECASE),
            re.compile(r"ニュースレター", re.IGNORECASE),
            re.compile(r"お知らせ", re.IGNORECASE),
            re.compile(r"新着", re.IGNORECASE),
            re.compile(r"情報配信", re.IGNORECASE),
            # ANA specific promotional patterns
            re.compile(r"ANA.*キャンペーン", re.IGNORECASE),
            re.compile(r"ANA.*プレゼント", re.IGNORECASE),
            re.compile(r"ANA.*マイル", re.IGNORECASE),
            re.compile(r"ANAからのお知らせ", re.IGNORECASE),
            # JAL specific promotional patterns
            re.compile(r"JAL.*キャンペーン", re.IGNORECASE),
            re.compile(r"JAL.*プレゼント", re.IGNORECASE),
            re.compile(r"JAL.*マイル", re.IGNORECASE),
            re.compile(r"JALからのお知らせ", re.IGNORECASE),
            # Car sharing promotional patterns
            re.compile(r"タイムズカー.*キャンペーン", re.IGNORECASE),
            re.compile(r"カレコ.*キャンペーン", re.IGNORECASE),
            re.compile(r"三井のカーシェアーズ.*キャンペーン", re.IGNORECASE),
            re.compile(r"カーシェア.*お得", re.IGNORECASE),
            # Generic promotional terms
            re.compile(r"今すぐ", re.IGNORECASE),
            re.compile(r"急いで", re.IGNORECASE),
            re.compile(r"見逃し", re.IGNORECASE),
            re.compile(r"最後のチャンス", re.IGNORECASE),
            re.compile(r"期間限定", re.IGNORECASE),
            re.compile(r"無料", re.IGNORECASE),
            re.compile(r"プレミアム", re.IGNORECASE),
        ]

        # Promotional body content patterns
        self.promotional_body_patterns: list[Pattern[str]] = [
            # URLs and promotional content indicators
            re.compile(r"クリックして.*キャンペーン", re.IGNORECASE),
            re.compile(r"詳しくはこちら.*キャンペーン", re.IGNORECASE),
            re.compile(r"応募.*こちら", re.IGNORECASE),
            re.compile(r"配信停止", re.IGNORECASE),
            re.compile(r"メール配信.*停止", re.IGNORECASE),
            re.compile(r"購読解除", re.IGNORECASE),
            # General promotional body patterns
            re.compile(r"キャンペーン.*情報", re.IGNORECASE),
            re.compile(r"詳しくはこちら", re.IGNORECASE),
            re.compile(r"今すぐ.*クリック", re.IGNORECASE),
            # Multiple promotional keywords in body
            re.compile(
                r"(キャンペーン|プレゼント|抽選).*?(キャンペーン|プレゼント|抽選)",
                re.IGNORECASE,
            ),
        ]

        # Booking confirmation patterns (to avoid false positives)
        self.booking_confirmation_patterns: list[Pattern[str]] = [
            # Flight booking confirmations
            re.compile(r"予約.*受付.*ました", re.IGNORECASE),
            re.compile(r"ご予約.*確認", re.IGNORECASE),
            re.compile(r"搭乗券", re.IGNORECASE),
            re.compile(r"フライト.*確認", re.IGNORECASE),
            re.compile(r"航空券", re.IGNORECASE),
            re.compile(r"確認番号", re.IGNORECASE),
            re.compile(r"予約番号", re.IGNORECASE),
            re.compile(r"チェックイン", re.IGNORECASE),
            # Car sharing booking confirmations
            re.compile(r"利用.*開始", re.IGNORECASE),
            re.compile(r"利用.*終了", re.IGNORECASE),
            re.compile(r"予約.*開始", re.IGNORECASE),
            re.compile(r"返却.*完了", re.IGNORECASE),
            re.compile(r"キャンセル.*受付", re.IGNORECASE),
            re.compile(r"変更.*受付", re.IGNORECASE),
        ]

    def is_promotional_email(self, email: EmailMessage) -> bool:
        """
        Determine if an email is promotional and should be filtered out.

        Returns True if the email is promotional, False if it's likely a booking email.
        """
        subject = email.subject
        body = email.body

        # First check if it's clearly a booking confirmation (avoid false positives)
        if self._is_booking_confirmation(subject, body):
            logger.debug(
                "Email identified as booking confirmation",
                email_id=email.id,
                subject=subject[:100],
            )
            return False

        # Check for promotional patterns in subject
        promotional_subject_matches = sum(
            1
            for pattern in self.promotional_subject_patterns
            if pattern.search(subject)
        )

        # Check for promotional patterns in body
        promotional_body_matches = sum(
            1 for pattern in self.promotional_body_patterns if pattern.search(body)
        )

        # Decision logic - more conservative to avoid false positives
        is_promotional = False

        # Very strong indicators in subject line (multiple promotional keywords)
        if promotional_subject_matches >= 2:
            is_promotional = True
            logger.info(
                "Email identified as promotional (multiple subject patterns)",
                email_id=email.id,
                subject=subject[:100],
                subject_matches=promotional_subject_matches,
            )

        # Strong promotional pattern in subject + body evidence
        elif promotional_subject_matches >= 1 and promotional_body_matches >= 2:
            is_promotional = True
            logger.info(
                "Email identified as promotional (subject + multiple body patterns)",
                email_id=email.id,
                subject=subject[:100],
                subject_matches=promotional_subject_matches,
                body_matches=promotional_body_matches,
            )

        # Very high volume of promotional content in body only
        elif promotional_body_matches >= 3:
            is_promotional = True
            logger.info(
                "Email identified as promotional (many body patterns)",
                email_id=email.id,
                subject=subject[:100],
                body_matches=promotional_body_matches,
            )

        if not is_promotional:
            logger.debug(
                "Email passed promotional filter",
                email_id=email.id,
                subject=subject[:100],
                subject_matches=promotional_subject_matches,
                body_matches=promotional_body_matches,
            )

        return is_promotional

    def _is_booking_confirmation(self, subject: str, body: str) -> bool:
        """Check if email contains booking confirmation patterns."""
        # Check subject for booking confirmation patterns
        for pattern in self.booking_confirmation_patterns:
            if pattern.search(subject):
                return True

        # Check body for booking confirmation patterns (with higher threshold)
        confirmation_matches = sum(
            1 for pattern in self.booking_confirmation_patterns if pattern.search(body)
        )

        return (
            confirmation_matches >= 2
        )  # Require multiple confirmation indicators in body


def is_promotional_email(email: EmailMessage) -> bool:
    """
    Convenience function to check if an email is promotional.

    Returns True if the email should be filtered out (is promotional).
    """
    email_filter = EmailFilter()
    return email_filter.is_promotional_email(email)
