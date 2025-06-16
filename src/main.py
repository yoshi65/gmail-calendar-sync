"""Main entrypoint for Gmail Calendar Sync."""

import sys

import structlog

from .models.email_types import ProcessingResult
from .processors.factory import EmailProcessorFactory
from .services.calendar_client import CalendarClient
from .services.gmail_client import GmailClient
from .utils.config import get_settings
from .utils.exceptions import GmailCalendarSyncError
from .utils.logging import configure_logging


def setup_logging():
    """Setup logging configuration."""
    settings = get_settings()
    # Use JSON format in production (GitHub Actions)
    json_format = True
    configure_logging(settings.log_level, json_format=json_format)


def process_emails(
    gmail_client: GmailClient,
    calendar_client: CalendarClient,
    processor_factory: EmailProcessorFactory,
    settings
) -> list[ProcessingResult]:
    """Process flight emails and create calendar events."""
    logger = structlog.get_logger()

    # Get flight emails based on date range or period (priority: absolute > hours > days)
    if settings.sync_start_date or settings.sync_end_date:
        logger.info("Fetching flight emails with date range", 
                   start_date=settings.sync_start_date,
                   end_date=settings.sync_end_date)
        emails = gmail_client.get_flight_emails(
            start_date=settings.sync_start_date,
            end_date=settings.sync_end_date
        )
    elif settings.sync_period_hours:
        logger.info("Fetching flight emails", sync_period_hours=settings.sync_period_hours)
        emails = gmail_client.get_flight_emails(since_hours=settings.sync_period_hours)
    else:
        logger.info("Fetching flight emails", sync_period_days=settings.sync_period_days)
        emails = gmail_client.get_flight_emails(since_days=settings.sync_period_days)

    if not emails:
        logger.info("No flight emails found")
        return []

    logger.info("Processing emails", count=len(emails))

    results = []

    for email in emails:
        logger.info("Processing email",
                   email_id=email.id,
                   subject=email.subject[:100],
                   domain=email.domain)

        try:
            # Get appropriate processor
            processor = processor_factory.get_processor(email)

            if not processor:
                logger.warning("No processor found for email",
                              email_id=email.id,
                              domain=email.domain)
                continue

            # Process the email
            result = processor.process(email)
            results.append(result)

            if result.success and result.extracted_data:
                # Processor handles calendar event creation/updating
                # Just mark email as processed
                gmail_client.add_label(email.id, settings.gmail_label)
                
                logger.info("Created calendar events",
                           email_id=email.id,
                           event_count=len(result.extracted_data.get("outbound_segments", [])))
                
                # Note: calendar event creation is now handled within the processor

            elif not result.success:
                logger.warning("Email processing failed",
                              email_id=email.id,
                              error=result.error_message)

        except Exception as e:
            logger.error("Unexpected error processing email",
                        email_id=email.id,
                        error=str(e))

            result = ProcessingResult(
                email_id=email.id,
                email_type=None,
                success=False,
                error_message=f"Unexpected error: {str(e)}"
            )
            results.append(result)

    return results


def send_slack_notification(results: list[ProcessingResult], settings):
    """Send Slack notification with processing summary."""
    if not settings.slack_webhook_url:
        return

    logger = structlog.get_logger()

    try:
        import httpx

        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful

        message = "📧 Gmail Calendar Sync Summary\n"
        message += f"✅ Processed: {successful}\n"
        message += f"❌ Failed: {failed}\n"
        message += f"📊 Total emails: {len(results)}"

        if failed > 0:
            message += "\n\nErrors:\n"
            for result in results:
                if not result.success:
                    message += f"• {result.email_id}: {result.error_message}\n"

        payload = {"text": message}

        response = httpx.post(settings.slack_webhook_url, json=payload, timeout=10)
        response.raise_for_status()

        logger.info("Sent Slack notification", successful=successful, failed=failed)

    except Exception as e:
        logger.error("Failed to send Slack notification", error=str(e))


def main():
    """Main function."""
    setup_logging()
    logger = structlog.get_logger()

    try:
        logger.info("Starting Gmail Calendar Sync")

        # Load settings
        settings = get_settings()

        # Initialize clients
        gmail_client = GmailClient(settings)
        calendar_client = CalendarClient(settings)
        processor_factory = EmailProcessorFactory(settings)

        # Process emails
        results = process_emails(
            gmail_client,
            calendar_client,
            processor_factory,
            settings
        )

        # Send notification
        send_slack_notification(results, settings)

        # Summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful

        logger.info("Gmail Calendar Sync completed",
                   total=len(results),
                   successful=successful,
                   failed=failed)

        if failed > 0:
            logger.warning("Some emails failed to process", failed_count=failed)
            sys.exit(1)

    except GmailCalendarSyncError as e:
        logger.error("Gmail Calendar Sync error", error=str(e))
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
