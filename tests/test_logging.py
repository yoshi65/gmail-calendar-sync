"""Tests for logging module."""

from unittest.mock import Mock, patch

import structlog

from src.utils.logging import configure_logging


class TestConfigureLogging:
    """Test logging configuration."""

    def test_configure_logging_info_level(self):
        """Test logging configuration with INFO level."""
        with patch("structlog.configure") as mock_configure:
            configure_logging("INFO")

            mock_configure.assert_called_once()
            call_args = mock_configure.call_args

            # Check that processors include timestamper and JSONRenderer for JSON format
            processors = call_args[1]["processors"]
            assert len(processors) > 0

            # Check wrapper class
            assert call_args[1][
                "wrapper_class"
            ] == structlog.make_filtering_bound_logger(20)  # INFO level

            # Check context class
            assert call_args[1]["context_class"] is dict

            # Check logger factory
            assert callable(call_args[1]["logger_factory"])

    def test_configure_logging_debug_level(self):
        """Test logging configuration with DEBUG level."""
        with patch("structlog.configure") as mock_configure:
            configure_logging("DEBUG")

            mock_configure.assert_called_once()
            call_args = mock_configure.call_args

            # Check wrapper class for DEBUG level
            assert call_args[1][
                "wrapper_class"
            ] == structlog.make_filtering_bound_logger(10)  # DEBUG level

    def test_configure_logging_warning_level(self):
        """Test logging configuration with WARNING level."""
        with patch("structlog.configure") as mock_configure:
            configure_logging("WARNING")

            mock_configure.assert_called_once()
            call_args = mock_configure.call_args

            # Check wrapper class for WARNING level
            assert call_args[1][
                "wrapper_class"
            ] == structlog.make_filtering_bound_logger(30)  # WARNING level

    def test_configure_logging_error_level(self):
        """Test logging configuration with ERROR level."""
        with patch("structlog.configure") as mock_configure:
            configure_logging("ERROR")

            mock_configure.assert_called_once()
            call_args = mock_configure.call_args

            # Check wrapper class for ERROR level
            assert call_args[1][
                "wrapper_class"
            ] == structlog.make_filtering_bound_logger(40)  # ERROR level

    def test_configure_logging_json_format(self):
        """Test logging configuration with JSON format."""
        with patch("structlog.configure") as mock_configure:
            configure_logging("INFO", json_format=True)

            mock_configure.assert_called_once()
            call_args = mock_configure.call_args

            # Check that processors are configured for JSON output
            processors = call_args[1]["processors"]
            assert len(processors) > 0

            # The last processor should be JSONRenderer when json_format=True
            # Check that JSONRenderer is in the processors
            processor_types = [type(p).__name__ for p in processors]
            assert any("JSON" in p_type for p_type in processor_types)

    def test_configure_logging_console_format(self):
        """Test logging configuration with console format."""
        with patch("structlog.configure") as mock_configure:
            configure_logging("INFO", json_format=False)

            mock_configure.assert_called_once()
            call_args = mock_configure.call_args

            # Check that processors are configured for console output
            processors = call_args[1]["processors"]
            assert len(processors) > 0

            # When json_format=False, should use ConsoleRenderer or similar
            processor_types = [type(p).__name__ for p in processors]
            # Should not have JSONRenderer when json_format=False
            assert not any("JSON" in p_type for p_type in processor_types)

    def test_configure_logging_default_format(self):
        """Test logging configuration with default format (json_format not specified)."""
        with patch("structlog.configure") as mock_configure:
            configure_logging("INFO")

            mock_configure.assert_called_once()
            call_args = mock_configure.call_args

            # Default should be JSON format
            processors = call_args[1]["processors"]
            assert len(processors) > 0

    def test_configure_logging_invalid_level(self):
        """Test logging configuration with invalid level."""
        with patch("structlog.configure") as mock_configure:
            # Should not raise an error, but might default to INFO
            configure_logging("INVALID")

            mock_configure.assert_called_once()

    def test_configure_logging_lowercase_level(self):
        """Test logging configuration with lowercase level."""
        with patch("structlog.configure") as mock_configure:
            configure_logging("debug")

            mock_configure.assert_called_once()
            call_args = mock_configure.call_args

            # Should handle lowercase level names
            assert call_args[1][
                "wrapper_class"
            ] == structlog.make_filtering_bound_logger(10)  # DEBUG level

    def test_configure_logging_processors_include_timestamper(self):
        """Test that processors include timestamper."""
        with patch("structlog.configure") as mock_configure:
            configure_logging("INFO")

            mock_configure.assert_called_once()
            call_args = mock_configure.call_args

            processors = call_args[1]["processors"]

            # Check that timestamper is included
            processor_types = [type(p).__name__ for p in processors]
            assert any(
                "TimeStamper" in p_type or "timestamp" in p_type.lower()
                for p_type in processor_types
            )

    def test_configure_logging_processors_include_level_filter(self):
        """Test that processors include appropriate level filtering."""
        with patch("structlog.configure") as mock_configure:
            configure_logging("WARNING")

            mock_configure.assert_called_once()
            call_args = mock_configure.call_args

            # Check that the wrapper class filters at WARNING level
            wrapper_class = call_args[1]["wrapper_class"]
            assert wrapper_class == structlog.make_filtering_bound_logger(
                30
            )  # WARNING level

    def test_configure_logging_multiple_calls(self):
        """Test that multiple calls to configure_logging work properly."""
        with patch("structlog.configure") as mock_configure:
            configure_logging("DEBUG")
            configure_logging("ERROR")

            # Should be called twice
            assert mock_configure.call_count == 2

            # Last call should be with ERROR level
            last_call_args = mock_configure.call_args
            assert last_call_args[1][
                "wrapper_class"
            ] == structlog.make_filtering_bound_logger(40)  # ERROR level

    @patch("structlog.get_logger")
    def test_logging_integration(self, mock_get_logger):
        """Test that logging can be used after configuration."""
        # Mock logger instance
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Configure logging
        configure_logging("INFO")

        # Get logger and use it
        logger = structlog.get_logger()
        logger.info("Test message", extra_field="test_value")

        # Verify logger was obtained
        mock_get_logger.assert_called_once()
        mock_logger.info.assert_called_once_with(
            "Test message", extra_field="test_value"
        )
