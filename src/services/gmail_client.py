"""Gmail API client."""

import base64
from datetime import datetime, timedelta

import structlog
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
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

    def _get_service(self):
        """Get Gmail API service."""
        if self._service is None:
            client_id, client_secret, refresh_token = self.settings.get_gmail_credentials()
            
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
        end_date: str | None = None
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
                    except ValueError:
                        logger.error("Invalid start_date format", start_date=start_date)
                        raise ValueError(f"Invalid start_date format: {start_date}. Use YYYY-MM-DD")
                
                if end_date:
                    # Validate and format end date (YYYY-MM-DD -> YYYY/MM/DD)
                    try:
                        parsed_end = datetime.strptime(end_date, "%Y-%m-%d")
                        formatted_end = parsed_end.strftime("%Y/%m/%d")
                        query = f"{query} before:{formatted_end}"
                    except ValueError:
                        logger.error("Invalid end_date format", end_date=end_date)
                        raise ValueError(f"Invalid end_date format: {end_date}. Use YYYY-MM-DD")
            
            elif since_hours:
                # Convert hours to datetime and use for filtering
                since_datetime = datetime.now() - timedelta(hours=since_hours)
                date_filter = since_datetime.strftime("%Y/%m/%d")
                query = f"{query} after:{date_filter}"
                logger.debug("Using hours-based filter", since_hours=since_hours, date_filter=date_filter)
            
            elif since_days:
                # Fallback to relative days if no other time filters specified
                since_date = datetime.now() - timedelta(days=since_days)
                date_filter = since_date.strftime("%Y/%m/%d")
                query = f"{query} after:{date_filter}"
                logger.debug("Using days-based filter", since_days=since_days, date_filter=date_filter)

            logger.info("Searching emails", query=query, max_results=max_results)

            result = service.users().messages().list(
                userId="me",
                q=query,
                maxResults=max_results
            ).execute()

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

            message = service.users().messages().get(
                userId="me",
                id=message_id,
                format="full"
            ).execute()

            # Extract email data
            headers = {h["name"].lower(): h["value"] for h in message["payload"]["headers"]}

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
                        received_at = datetime.fromtimestamp(email.utils.mktime_tz(timestamp))
                except Exception as e:
                    logger.warning("Failed to parse email date", date_str=date_str, error=str(e))

            # Extract body
            body = self._extract_body(message["payload"])

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
            )

        except HttpError as error:
            logger.error("Failed to get email", message_id=message_id, error=str(error))
            raise

    def _extract_body(self, payload) -> str:
        """Extract email body from payload."""
        body = ""

        if "parts" in payload:
            # Multipart message
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    if "data" in part["body"]:
                        body += base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                elif part["mimeType"] == "text/html" and not body:
                    # Use HTML if no plain text found
                    if "data" in part["body"]:
                        html_body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                        # Simple HTML to text conversion
                        import re
                        body = re.sub(r'<[^>]+>', '', html_body)
        else:
            # Single part message
            if payload["mimeType"] in ["text/plain", "text/html"]:
                if "data" in payload["body"]:
                    body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
                    if payload["mimeType"] == "text/html":
                        import re
                        body = re.sub(r'<[^>]+>', '', body)

        return body.strip()

    def add_label(self, message_id: str, label_name: str) -> bool:
        """Add label to an email."""
        try:
            service = self._get_service()

            # First, try to get or create the label
            label_id = self._get_or_create_label(label_name)

            # Add label to message
            service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"addLabelIds": [label_id]}
            ).execute()

            logger.info("Added label to email", message_id=message_id, label=label_name)
            return True

        except HttpError as error:
            logger.error("Failed to add label", message_id=message_id, label=label_name, error=str(error))
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
                "messageListVisibility": "show"
            }

            created_label = service.users().labels().create(
                userId="me",
                body=label_object
            ).execute()

            logger.info("Created new label", label=label_name, label_id=created_label["id"])
            return created_label["id"]

        except HttpError as error:
            logger.error("Failed to get or create label", label=label_name, error=str(error))
            raise

    def get_flight_emails(
        self, 
        since_days: int | None = None,
        since_hours: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None
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
                end_date=end_date
            )

            for message_id in message_ids:
                try:
                    email_msg = self.get_email(message_id)
                    all_emails.append(email_msg)
                except Exception as e:
                    logger.error("Failed to get email", message_id=message_id, error=str(e))

        logger.info("Retrieved flight emails", count=len(all_emails))
        return all_emails
    
    def remove_label(self, message_id: str, label_name: str) -> bool:
        """Remove a label from an email message."""
        try:
            service = self._get_service()
            
            # Get label ID
            label_id = self._get_or_create_label(label_name)
            
            # Remove label from message
            service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": [label_id]}
            ).execute()
            
            logger.info("Removed label from message", 
                       message_id=message_id, 
                       label=label_name)
            return True
            
        except HttpError as error:
            logger.error("Failed to remove label from message", 
                        message_id=message_id,
                        label=label_name, 
                        error=str(error))
            return False
