"""Tests for main module."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.main import main, process_emails, setup_logging
from src.models.email_types import EmailType, ProcessingResult
from src.utils.exceptions import GmailCalendarSyncError


class TestSetupLogging:
    """Test logging setup."""

    @patch("src.main.get_settings")
    @patch("src.main.configure_logging")
    def test_setup_logging(self, mock_configure, mock_get_settings):
        """Test that logging is configured with correct parameters."""
        mock_settings = Mock()
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings

        setup_logging()

        mock_get_settings.assert_called_once()
        mock_configure.assert_called_once_with("INFO", json_format=True)


class TestProcessEmails:
    """Test email processing function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.gmail_client = Mock()
        self.calendar_client = Mock()
        self.processor_factory = Mock()
        self.settings = Mock()
        self.settings.sync_start_date = None
        self.settings.sync_end_date = None
        self.settings.sync_period_hours = None
        self.settings.sync_period_days = 7

    def test_process_emails_with_date_range(self):
        """Test processing emails with absolute date range."""
        # Setup
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        self.settings.sync_start_date = start_date
        self.settings.sync_end_date = end_date

        mock_email = Mock()
        mock_email.id = "email123"
        mock_email.subject = "Flight confirmation - AA123"
        mock_email.sender = "noreply@airline.com"
        mock_email.body = "Your flight booking details..."
        mock_email.domain = "airline.com"
        mock_email.type = EmailType.FLIGHT
        self.gmail_client.get_all_supported_emails.return_value = [mock_email]

        mock_processor = Mock()
        mock_processor.process.return_value = ProcessingResult(
            email_id="email123",
            email_type=EmailType.FLIGHT,
            success=True,
            extracted_data={"flight": "data"},
            calendar_event_id="event123",
        )
        self.processor_factory.get_processor.return_value = mock_processor

        # Execute
        results = process_emails(
            self.gmail_client,
            self.calendar_client,
            self.processor_factory,
            self.settings,
        )

        # Assert
        self.gmail_client.get_all_supported_emails.assert_called_once_with(
            start_date=start_date, end_date=end_date
        )
        self.processor_factory.get_processor.assert_called_once_with(mock_email)
        mock_processor.process.assert_called_once_with(mock_email)
        assert len(results) == 1
        assert results[0].success

    def test_process_emails_with_hours_period(self):
        """Test processing emails with hours period."""
        # Setup
        self.settings.sync_period_hours = 24

        mock_email = Mock()
        mock_email.id = "email456"
        mock_email.subject = "Car reservation confirmed"
        mock_email.sender = "noreply@carshare.com"
        mock_email.body = "Your car share booking..."
        mock_email.domain = "carshare.com"
        mock_email.type = EmailType.CAR_SHARE
        self.gmail_client.get_all_supported_emails.return_value = [mock_email]

        mock_processor = Mock()
        mock_processor.process.return_value = ProcessingResult(
            email_id="email456",
            email_type=EmailType.CAR_SHARE,
            success=True,
            extracted_data={"carshare": "data"},
            calendar_event_id="event456",
        )
        self.processor_factory.get_processor.return_value = mock_processor

        # Execute
        results = process_emails(
            self.gmail_client,
            self.calendar_client,
            self.processor_factory,
            self.settings,
        )

        # Assert
        self.gmail_client.get_all_supported_emails.assert_called_once_with(
            since_hours=24
        )
        assert len(results) == 1
        assert results[0].success

    def test_process_emails_with_days_period(self):
        """Test processing emails with days period (fallback)."""
        # Setup - no start/end dates, no hours period
        self.settings.sync_period_days = 14

        mock_email = Mock()
        mock_email.id = "email789"
        mock_email.subject = "Flight booking details"
        mock_email.sender = "booking@airline.com"
        mock_email.body = "Flight booking information..."
        mock_email.domain = "airline.com"
        mock_email.type = EmailType.FLIGHT
        self.gmail_client.get_all_supported_emails.return_value = [mock_email]

        mock_processor = Mock()
        mock_processor.process.return_value = ProcessingResult(
            email_id="email789",
            email_type=EmailType.FLIGHT,
            success=False,
            error_message="Already processed",
        )
        self.processor_factory.get_processor.return_value = mock_processor

        # Execute
        results = process_emails(
            self.gmail_client,
            self.calendar_client,
            self.processor_factory,
            self.settings,
        )

        # Assert
        self.gmail_client.get_all_supported_emails.assert_called_once_with(
            since_days=14
        )
        assert len(results) == 1
        assert not results[0].success

    def test_process_emails_multiple_types(self):
        """Test processing multiple email types."""
        # Setup
        flight_email = Mock()
        flight_email.id = "flight123"
        flight_email.subject = "Flight confirmation"
        flight_email.sender = "confirm@airline.com"
        flight_email.body = "Flight confirmed..."
        flight_email.domain = "airline.com"
        flight_email.type = EmailType.FLIGHT

        carshare_email = Mock()
        carshare_email.id = "carshare456"
        carshare_email.subject = "Car share booking"
        carshare_email.sender = "booking@carshare.com"
        carshare_email.body = "Car booking confirmed..."
        carshare_email.domain = "carshare.com"
        carshare_email.type = EmailType.CAR_SHARE

        self.gmail_client.get_all_supported_emails.return_value = [
            flight_email,
            carshare_email,
        ]

        # Mock processors
        flight_processor = Mock()
        flight_processor.process.return_value = ProcessingResult(
            email_id="flight123",
            email_type=EmailType.FLIGHT,
            success=True,
            extracted_data={"flight": "data"},
            calendar_event_id="flight_event",
        )

        carshare_processor = Mock()
        carshare_processor.process.return_value = ProcessingResult(
            email_id="carshare456",
            email_type=EmailType.CAR_SHARE,
            success=True,
            extracted_data={"carshare": "data"},
            calendar_event_id="carshare_event",
        )

        def mock_get_processor(email):
            if email.type == EmailType.FLIGHT:
                return flight_processor
            elif email.type == EmailType.CAR_SHARE:
                return carshare_processor
            return None

        self.processor_factory.get_processor.side_effect = mock_get_processor

        # Execute
        results = process_emails(
            self.gmail_client,
            self.calendar_client,
            self.processor_factory,
            self.settings,
        )

        # Assert
        assert len(results) == 2
        assert self.processor_factory.get_processor.call_count == 2
        assert all(r.success for r in results)

    def test_process_emails_handles_processing_error(self):
        """Test handling of processing errors."""
        # Setup
        mock_email = Mock()
        mock_email.id = "error_email"
        mock_email.subject = "Flight booking error test"
        mock_email.sender = "test@airline.com"
        mock_email.body = "Error test email..."
        mock_email.domain = "airline.com"
        mock_email.type = EmailType.FLIGHT
        self.gmail_client.get_all_supported_emails.return_value = [mock_email]

        mock_processor = Mock()
        mock_processor.process.return_value = ProcessingResult(
            email_id="error_email",
            email_type=EmailType.FLIGHT,
            success=False,
            error_message="Processing failed: OpenAI API error",
        )
        self.processor_factory.get_processor.return_value = mock_processor

        # Execute
        results = process_emails(
            self.gmail_client,
            self.calendar_client,
            self.processor_factory,
            self.settings,
        )

        # Assert
        assert len(results) == 1
        assert not results[0].success
        error_message = results[0].error_message
        assert error_message is not None and "Processing failed" in error_message

    def test_process_emails_no_emails_found(self):
        """Test processing when no emails are found."""
        # Setup
        self.gmail_client.get_all_supported_emails.return_value = []

        # Execute
        results = process_emails(
            self.gmail_client,
            self.calendar_client,
            self.processor_factory,
            self.settings,
        )

        # Assert
        assert len(results) == 0
        self.processor_factory.get_processor.assert_not_called()


class TestMain:
    """Test main function."""

    @patch("src.main.get_metrics_collector")
    @patch("src.main.setup_logging")
    @patch("src.main.process_emails")
    @patch("src.main.EmailProcessorFactory")
    @patch("src.main.CalendarClient")
    @patch("src.main.GmailClient")
    @patch("src.main.get_settings")
    def test_main_success(
        self,
        mock_get_settings,
        mock_gmail_client_class,
        mock_calendar_client_class,
        mock_processor_factory_class,
        mock_process_emails,
        mock_setup_logging,
        mock_get_metrics,
    ):
        """Test successful main execution."""
        # Setup
        mock_settings = Mock()
        mock_get_settings.return_value = mock_settings

        mock_gmail_client = Mock()
        mock_gmail_client_class.return_value = mock_gmail_client

        mock_calendar_client = Mock()
        mock_calendar_client_class.return_value = mock_calendar_client

        mock_processor_factory = Mock()
        mock_processor_factory_class.return_value = mock_processor_factory

        mock_metrics_collector = Mock()
        mock_get_metrics.return_value = mock_metrics_collector

        # Mock successful results
        mock_results = [
            ProcessingResult(
                email_id="test123",
                email_type=EmailType.FLIGHT,
                success=True,
                extracted_data={"test": "data"},
                calendar_event_id="event123",
            ),
            ProcessingResult(
                email_id="test456",
                email_type=EmailType.CAR_SHARE,
                success=False,
                error_message="Skipped",
            ),
        ]
        mock_process_emails.return_value = mock_results

        # Execute
        with patch("sys.exit") as mock_exit:
            main()

        # Assert
        mock_setup_logging.assert_called_once()
        mock_get_settings.assert_called_once()
        mock_gmail_client_class.assert_called_once_with(mock_settings)
        mock_calendar_client_class.assert_called_once_with(mock_settings)
        mock_processor_factory_class.assert_called_once()
        mock_process_emails.assert_called_once()
        mock_exit.assert_called_once_with(0)

    @patch("src.main.setup_logging")
    @patch("src.main.get_settings")
    def test_main_settings_error(self, mock_get_settings, mock_setup_logging):
        """Test main with settings configuration error."""
        # Setup
        mock_setup_logging.side_effect = Exception("Config error")

        # Execute
        with patch("sys.exit") as mock_exit:
            main()

        # Assert
        mock_exit.assert_called_once_with(1)

    @patch("src.main.get_metrics_collector")
    @patch("src.main.setup_logging")
    @patch("src.main.GmailClient")
    @patch("src.main.get_settings")
    def test_main_gmail_client_error(
        self,
        mock_get_settings,
        mock_gmail_client_class,
        mock_setup_logging,
        mock_get_metrics,
    ):
        """Test main with Gmail client initialization error."""
        # Setup
        mock_settings = Mock()
        mock_get_settings.return_value = mock_settings
        mock_gmail_client_class.side_effect = GmailCalendarSyncError(
            "Gmail auth failed"
        )

        # Execute
        with patch("sys.exit") as mock_exit:
            main()

        # Assert
        mock_exit.assert_called_once_with(1)

    @patch("src.main.get_metrics_collector")
    @patch("src.main.setup_logging")
    @patch("src.main.process_emails")
    @patch("src.main.EmailProcessorFactory")
    @patch("src.main.CalendarClient")
    @patch("src.main.GmailClient")
    @patch("src.main.get_settings")
    def test_main_processing_error(
        self,
        mock_get_settings,
        mock_gmail_client_class,
        mock_calendar_client_class,
        mock_processor_factory_class,
        mock_process_emails,
        mock_setup_logging,
        mock_get_metrics,
    ):
        """Test main with processing error."""
        # Setup
        mock_settings = Mock()
        mock_get_settings.return_value = mock_settings

        mock_gmail_client = Mock()
        mock_gmail_client_class.return_value = mock_gmail_client

        mock_calendar_client = Mock()
        mock_calendar_client_class.return_value = mock_calendar_client

        mock_processor_factory = Mock()
        mock_processor_factory_class.return_value = mock_processor_factory

        mock_metrics_collector = Mock()
        mock_get_metrics.return_value = mock_metrics_collector

        # Mock processing error
        mock_process_emails.side_effect = Exception("Processing failed")

        # Execute
        with patch("sys.exit") as mock_exit:
            main()

        # Assert
        mock_exit.assert_called_once_with(1)

    @patch("src.main.get_metrics_collector")
    @patch("src.main.setup_logging")
    @patch("src.main.process_emails")
    @patch("src.main.EmailProcessorFactory")
    @patch("src.main.CalendarClient")
    @patch("src.main.GmailClient")
    @patch("src.main.get_settings")
    def test_main_with_results_summary(
        self,
        mock_get_settings,
        mock_gmail_client_class,
        mock_calendar_client_class,
        mock_processor_factory_class,
        mock_process_emails,
        mock_setup_logging,
        mock_get_metrics,
    ):
        """Test main execution with different result types."""
        # Setup
        mock_settings = Mock()
        mock_get_settings.return_value = mock_settings

        mock_gmail_client = Mock()
        mock_gmail_client_class.return_value = mock_gmail_client

        mock_calendar_client = Mock()
        mock_calendar_client_class.return_value = mock_calendar_client

        mock_processor_factory = Mock()
        mock_processor_factory_class.return_value = mock_processor_factory

        mock_metrics_collector = Mock()
        mock_get_metrics.return_value = mock_metrics_collector

        # Mock mixed results
        mock_results = [
            ProcessingResult(
                email_id="success1",
                email_type=EmailType.FLIGHT,
                success=True,
                extracted_data={"flight": "data"},
                calendar_event_id="event1",
            ),
            ProcessingResult(
                email_id="success2",
                email_type=EmailType.CAR_SHARE,
                success=True,
                extracted_data={"carshare": "data"},
                calendar_event_id="event2",
            ),
            ProcessingResult(
                email_id="skipped1",
                email_type=EmailType.FLIGHT,
                success=False,
                error_message="Already exists",
            ),
            ProcessingResult(
                email_id="error1",
                email_type=EmailType.CAR_SHARE,
                success=False,
                error_message="Failed to parse: Invalid date format",
            ),
        ]
        mock_process_emails.return_value = mock_results

        # Execute
        with patch("sys.exit") as mock_exit:
            main()

        # Assert - should exit with 0 (success) even if some emails failed
        mock_exit.assert_called_once_with(0)

    @patch("src.main.get_metrics_collector")
    def test_main_metrics_collection_error(self, mock_get_metrics):
        """Test main when metrics collection fails."""
        # Setup
        mock_get_metrics.side_effect = Exception("Metrics error")

        # Execute
        with patch("sys.exit") as mock_exit:
            main()

        # Assert
        mock_exit.assert_called_once_with(1)
