#!/usr/bin/env python3
"""Test email processing with sample data for development and debugging."""

import json
import sys
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from models.email_types import EmailMessage, EmailType
    from processors.factory import EmailProcessorFactory
    from utils.config import get_settings
    from utils.logging import configure_logging
except ImportError as e:
    print(f"❌ Failed to import project modules: {e}")
    print("   Make sure you're running this from the project root.")
    sys.exit(1)


# Sample email data for testing
SAMPLE_EMAILS = {
    "ana_flight": {
        "id": "test_ana_001",
        "subject": "ANA ご予約確認 [確認番号: 887525617]",
        "body": """山田太郎 様

この度は、ANAをご利用いただき、誠にありがとうございます。
以下の内容でご予約を承りました。

■ 確認番号: 887525617
■ 予約番号: 0709

■ 往路
便名: NH006
出発: 2024年1月15日 08:30 羽田空港(HND)
到着: 2024年1月15日 11:45 伊丹空港(ITM)
座席: 12A

■ 復路
便名: NH017
出発: 2024年1月20日 18:20 伊丹空港(ITM)
到着: 2024年1月20日 19:35 羽田空港(HND)
座席: 15C

■ 搭乗者
山田太郎

ANA""",
        "domain": "ana.co.jp",
        "expected_type": EmailType.FLIGHT,
    },
    "times_car": {
        "id": "test_times_001",
        "subject": "【タイムズカー】ご利用開始のお知らせ [予約番号: TC123456]",
        "body": """山田太郎 様

タイムズカーのご予約が完了いたしました。

■ 予約番号: TC123456
■ 利用者: 山田太郎
■ ステーション: 新宿駅南口ステーション
■ 住所: 東京都新宿区新宿3-1-1

■ 利用時間
開始: 2024年1月10日 14:00
終了: 2024年1月10日 16:00

タイムズカー""",
        "domain": "share.timescar.jp",
        "expected_type": EmailType.CAR_SHARE,
    },
    "promotional": {
        "id": "test_promo_001",
        "subject": "ANAマイルキャンペーン開始！",
        "body": """マイル獲得の絶好のチャンス！

期間限定でマイル2倍キャンペーンを実施中です。

ANA""",
        "domain": "ana.co.jp",
        "expected_type": None,  # Should be filtered out
    },
}


def create_test_email(email_data: dict[str, Any]) -> EmailMessage:
    """Create EmailMessage from test data."""
    from datetime import datetime

    return EmailMessage(
        id=email_data["id"],
        subject=email_data["subject"],
        body=email_data["body"],
        domain=email_data["domain"],
        datetime=datetime.now(),
    )


def test_email_processing(email_key: str) -> None:
    """Test processing of a specific email type."""
    if email_key not in SAMPLE_EMAILS:
        print(f"❌ Unknown email type: {email_key}")
        print(f"   Available types: {', '.join(SAMPLE_EMAILS.keys())}")
        return

    email_data = SAMPLE_EMAILS[email_key]
    email = create_test_email(email_data)

    print(f"\n🧪 Testing {email_key} email processing...")
    print(f"📧 Subject: {email.subject}")
    print(f"🌐 Domain: {email.domain}")
    print(f"📝 Expected Type: {email_data['expected_type']}")

    # Initialize processor factory
    try:
        settings = get_settings()
        factory = EmailProcessorFactory(settings)
    except Exception as e:
        print(f"❌ Failed to initialize processor factory: {e}")
        return

    # Get appropriate processor
    processor = factory.get_processor(email)

    if not processor:
        if email_data["expected_type"] is None:
            print("✅ No processor found (expected for promotional emails)")
        else:
            print("❌ No processor found for this email type")
        return

    print(f"🔧 Processor: {type(processor).__name__}")

    # Check if it should be processed with AI
    should_process = processor.should_process_with_ai(email)
    print(f"🤖 Should process with AI: {should_process}")

    if not should_process and email_data["expected_type"] is None:
        print("✅ Correctly filtered out promotional email")
        return

    # Process the email (dry run - don't actually create calendar events)
    print("⚙️  Processing email...")

    try:
        # Note: This will actually call OpenAI API if not filtered out
        # For true dry-run, you'd need to mock the OpenAI client
        result = processor.process(email)

        print("📊 Processing Result:")
        print(f"  Success: {result.success}")
        print(f"  Email Type: {result.email_type}")

        if result.success and result.extracted_data:
            print("  Extracted Data:")
            print(json.dumps(result.extracted_data, indent=2, ensure_ascii=False))
        elif result.error_message:
            print(f"  Error: {result.error_message}")

    except Exception as e:
        print(f"❌ Processing failed: {e}")


def test_all_emails() -> None:
    """Test processing of all sample emails."""
    print("🧪 Testing all sample email types...")

    for email_key in SAMPLE_EMAILS:
        test_email_processing(email_key)
        print("-" * 50)


def main():
    """Main function."""
    print("📧 Gmail Calendar Sync - Email Processing Tester")
    print("=" * 50)

    # Setup logging
    configure_logging("DEBUG", json_format=False)

    if len(sys.argv) < 2:
        print("Usage:")
        print(f"  {sys.argv[0]} <email_type>     # Test specific email type")
        print(f"  {sys.argv[0]} all              # Test all email types")
        print(f"\nAvailable email types: {', '.join(SAMPLE_EMAILS.keys())}")
        return

    email_type = sys.argv[1]

    if email_type == "all":
        test_all_emails()
    else:
        test_email_processing(email_type)

    print("\n✅ Email processing test completed!")
    print("\n📝 Notes:")
    print("  - This test uses real OpenAI API calls (if not filtered)")
    print("  - No calendar events are actually created")
    print("  - Check logs for detailed processing information")


if __name__ == "__main__":
    main()
