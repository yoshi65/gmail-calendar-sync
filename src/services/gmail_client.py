"""Gmail API client."""

import base64
from datetime import datetime, timedelta
from typing import Any

import structlog
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..models.email_types import EmailMessage
from ..utils.config import Settings

logger = structlog.get_logger()


class GmailClient:
    """Gmail API client for reading and managing emails."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._service = None

    def _get_service(self) -> Any:
        """Get Gmail API service."""
        if self._service is None:
            (
                client_id,
                client_secret,
                refresh_token,
            ) = self.settings.get_gmail_credentials()

            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
            )

            # Refresh the token
            credentials.refresh(Request())

            self._service = build("gmail", "v1", credentials=credentials)

        return self._service

    def search_emails(
        self,
        query: str,
        max_results: int = 100,
        since_days: int | None = None,
        since_hours: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[str]:
        """Search for emails and return message IDs."""
        try:
            service = self._get_service()

            # Add date filter with priority: absolute dates > hours > days
            if start_date or end_date:
                if start_date:
                    # Validate and format start date (YYYY-MM-DD -> YYYY/MM/DD)
                    try:
                        parsed_start = datetime.strptime(start_date, "%Y-%m-%d")
                        formatted_start = parsed_start.strftime("%Y/%m/%d")
                        query = f"{query} after:{formatted_start}"
                    except ValueError as e:
                        logger.error("Invalid start_date format", start_date=start_date)
                        raise ValueError(
                            f"Invalid start_date format: {start_date}. Use YYYY-MM-DD"
                        ) from e

                if end_date:
                    # Validate and format end date (YYYY-MM-DD -> YYYY/MM/DD)
                    try:
                        parsed_end = datetime.strptime(end_date, "%Y-%m-%d")
                        formatted_end = parsed_end.strftime("%Y/%m/%d")
                        query = f"{query} before:{formatted_end}"
                    except ValueError as e:
                        logger.error("Invalid end_date format", end_date=end_date)
                        raise ValueError(
                            f"Invalid end_date format: {end_date}. Use YYYY-MM-DD"
                        ) from e

            elif since_hours:
                # Convert hours to datetime and use for filtering
                since_datetime = datetime.now() - timedelta(hours=since_hours)
                date_filter = since_datetime.strftime("%Y/%m/%d")
                query = f"{query} after:{date_filter}"
                logger.debug(
                    "Using hours-based filter",
                    since_hours=since_hours,
                    date_filter=date_filter,
                )

            elif since_days:
                # Fallback to relative days if no other time filters specified
                since_date = datetime.now() - timedelta(days=since_days)
                date_filter = since_date.strftime("%Y/%m/%d")
                query = f"{query} after:{date_filter}"
                logger.debug(
                    "Using days-based filter",
                    since_days=since_days,
                    date_filter=date_filter,
                )

            logger.info("Searching emails", query=query, max_results=max_results)

            result = (
                service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )

            messages = result.get("messages", [])
            message_ids = [msg["id"] for msg in messages]

            logger.info("Found emails", count=len(message_ids))
            return message_ids

        except HttpError as error:
            logger.error("Failed to search emails", error=str(error))
            raise

    def get_email(self, message_id: str) -> EmailMessage:
        """Get email details by message ID."""
        try:
            service = self._get_service()

            message = (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )

            # Extract email data
            headers = {
                h["name"].lower(): h["value"] for h in message["payload"]["headers"]
            }

            subject = headers.get("subject", "")
            sender = headers.get("from", "")
            date_str = headers.get("date", "")

            # Parse date
            received_at = datetime.now()  # fallback
            if date_str:
                try:
                    # Parse RFC 2822 date format
                    import email.utils

                    timestamp = email.utils.parsedate_tz(date_str)
                    if timestamp:
                        received_at = datetime.fromtimestamp(
                            email.utils.mktime_tz(timestamp)
                        )
                except Exception as e:
                    logger.warning(
                        "Failed to parse email date", date_str=date_str, error=str(e)
                    )

            # Extract body
            body = self._extract_body(message["payload"])

            # Detect forwarded email and extract original sender
            is_forwarded, original_sender = self._detect_forwarded_email(body, subject)

            # Get labels
            labels = message.get("labelIds", [])

            return EmailMessage(
                id=message_id,
                subject=subject,
                sender=sender,
                body=body,
                received_at=received_at,
                thread_id=message["threadId"],
                labels=labels,
                is_forwarded=is_forwarded,
                original_sender=original_sender,
            )

        except HttpError as error:
            logger.error("Failed to get email", message_id=message_id, error=str(error))
            raise

    def _extract_body(self, payload: Any) -> str:
        """Extract email body from payload, handling nested multipart structures."""

        def extract_from_part(part: Any) -> str:
            """Recursively extract text from a MIME part."""
            mime_type = part.get("mimeType", "")

            # Handle nested multipart structures (e.g., multipart/mixed, multipart/alternative)
            if "parts" in part:
                extracted = ""
                for nested_part in part["parts"]:
                    text = extract_from_part(nested_part)
                    if text:
                        extracted += text
                return extracted

            # Extract text/plain content
            if mime_type == "text/plain":
                if "data" in part.get("body", {}):
                    try:
                        return base64.urlsafe_b64decode(part["body"]["data"]).decode(
                            "utf-8"
                        )
                    except Exception as e:
                        logger.warning("Failed to decode text/plain part", error=str(e))
                        return ""

            # Extract text/html as fallback
            elif mime_type == "text/html":
                if "data" in part.get("body", {}):
                    try:
                        html_body = base64.urlsafe_b64decode(
                            part["body"]["data"]
                        ).decode("utf-8")
                        # Simple HTML to text conversion
                        import re

                        return re.sub(r"<[^>]+>", "", html_body)
                    except Exception as e:
                        logger.warning("Failed to decode text/html part", error=str(e))
                        return ""

            return ""

        # Start extraction from root payload
        body = extract_from_part(payload)
        return body.strip()

    def _detect_forwarded_email(
        self, body: str, subject: str
    ) -> tuple[bool, str | None]:
        """Detect if email is forwarded and extract original sender.

        Args:
            body: Email body text
            subject: Email subject

        Returns:
            Tuple of (is_forwarded, original_sender)
        """
        import re

        # Check for forwarded subject
        if not (
            subject.lower().startswith("fwd:")
            or subject.lower().startswith("fw:")
            or "転送:" in subject
        ):
            return False, None

        # Debug: Log body snippet to check content
        logger.debug(
            "Checking forwarded email",
            subject=subject,
            body_preview=body[:500] if body else "EMPTY",
            has_forwarded_marker="---------- Forwarded message" in body,
        )

        # Gmail forwarded message pattern
        if "---------- Forwarded message" not in body:
            return False, None

        # Extract original sender from forwarded message header
        # Pattern: From: <email@domain.com> or From: Name <email@domain.com>
        pattern = r"From:\s*<?([^<>\s]+@[^<>\s]+)>?"
        match = re.search(pattern, body)

        if match:
            original_sender = match.group(1).strip()
            logger.debug(
                "Detected forwarded email",
                original_sender=original_sender,
                subject=subject,
            )
            return True, original_sender

        logger.warning(
            "Forwarded email detected but could not extract original sender",
            subject=subject,
        )
        return True, None

    def add_label(self, message_id: str, label_name: str) -> bool:
        """Add label to an email."""
        try:
            service = self._get_service()

            # First, try to get or create the label
            label_id = self._get_or_create_label(label_name)

            # Add label to message
            service.users().messages().modify(
                userId="me", id=message_id, body={"addLabelIds": [label_id]}
            ).execute()

            logger.info("Added label to email", message_id=message_id, label=label_name)
            return True

        except HttpError as error:
            logger.error(
                "Failed to add label",
                message_id=message_id,
                label=label_name,
                error=str(error),
            )
            return False

    def _get_or_create_label(self, label_name: str) -> str:
        """Get existing label ID or create new label."""
        try:
            service = self._get_service()

            # List existing labels
            labels_result = service.users().labels().list(userId="me").execute()
            labels = labels_result.get("labels", [])

            # Check if label exists
            for label in labels:
                if label["name"] == label_name:
                    return label["id"]

            # Create new label
            label_object = {
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }

            created_label = (
                service.users()
                .labels()
                .create(userId="me", body=label_object)
                .execute()
            )

            logger.info(
                "Created new label", label=label_name, label_id=created_label["id"]
            )
            return created_label["id"]

        except HttpError as error:
            logger.error(
                "Failed to get or create label", label=label_name, error=str(error)
            )
            raise

    def get_flight_emails(
        self,
        since_days: int | None = None,
        since_hours: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[EmailMessage]:
        """Get flight-related emails from supported domains."""
        all_emails = []

        for domain in self.settings.flight_domains:
            # Search for emails from this domain, excluding already processed ones
            query = f"from:{domain} -label:{self.settings.gmail_label}"
            message_ids = self.search_emails(
                query,
                since_days=since_days,
                since_hours=since_hours,
                start_date=start_date,
                end_date=end_date,
            )

            for message_id in message_ids:
                try:
                    email_msg = self.get_email(message_id)
                    all_emails.append(email_msg)
                except Exception as e:
                    logger.error(
                        "Failed to get email", message_id=message_id, error=str(e)
                    )

        # Sort emails by received date (oldest first) for proper chronological processing
        all_emails.sort(key=lambda email: email.received_at)

        logger.info("Retrieved flight emails", count=len(all_emails))
        return all_emails

    def get_all_supported_emails(
        self,
        since_days: int | None = None,
        since_hours: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[EmailMessage]:
        """Get all supported emails (flight and car sharing) from supported domains and forwarded emails."""
        all_emails = []

        # Get emails from supported domains
        for domain in self.settings.all_supported_domains:
            # Search for emails from this domain, excluding already processed ones
            query = f"from:{domain} -label:{self.settings.gmail_label}"
            message_ids = self.search_emails(
                query,
                since_days=since_days,
                since_hours=since_hours,
                start_date=start_date,
                end_date=end_date,
            )

            for message_id in message_ids:
                try:
                    email_msg = self.get_email(message_id)
                    all_emails.append(email_msg)
                except Exception as e:
                    logger.error(
                        "Failed to get email", message_id=message_id, error=str(e)
                    )

        # Get forwarded emails if configured
        for forwarded_email in self.settings.forwarded_from_email_list:
            # Search for forwarded emails from this address, excluding already processed ones
            query = f"from:{forwarded_email} (subject:Fwd OR subject:Fw OR subject:転送) -label:{self.settings.gmail_label}"
            message_ids = self.search_emails(
                query,
                since_days=since_days,
                since_hours=since_hours,
                start_date=start_date,
                end_date=end_date,
            )

            for message_id in message_ids:
                try:
                    email_msg = self.get_email(message_id)
                    all_emails.append(email_msg)
                except Exception as e:
                    logger.error(
                        "Failed to get email", message_id=message_id, error=str(e)
                    )

        # Sort emails by received date (oldest first) for proper chronological processing
        all_emails.sort(key=lambda email: email.received_at)

        logger.info("Retrieved all supported emails", count=len(all_emails))
        return all_emails

    def remove_label(self, message_id: str, label_name: str) -> bool:
        """Remove a label from an email message."""
        try:
            service = self._get_service()

            # Get label ID
            label_id = self._get_or_create_label(label_name)

            # Remove label from message
            service.users().messages().modify(
                userId="me", id=message_id, body={"removeLabelIds": [label_id]}
            ).execute()

            logger.info(
                "Removed label from message", message_id=message_id, label=label_name
            )
            return True

        except HttpError as error:
            logger.error(
                "Failed to remove label from message",
                message_id=message_id,
                label=label_name,
                error=str(error),
            )
            return False
