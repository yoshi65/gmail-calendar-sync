"""Logging configuration."""

import logging
import sys

import structlog


def configure_logging(log_level: str = "INFO", json_format: bool = True) -> None:
    """Configure structured logging for the application."""

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    # Configure structlog processors
    processors = [
        # Add timestamp
        structlog.processors.TimeStamper(fmt="ISO"),
        # Add log level
        structlog.stdlib.add_log_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
    ]

    if json_format:
        # JSON output for production (easier to parse in log aggregation systems)
        processors.extend([
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ])
    else:
        # Human-readable output for development
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True)
        ])

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def mask_sensitive_data(data: dict) -> dict:
    """Mask sensitive information in log data."""
    sensitive_keys = {
        "password", "token", "secret", "key", "credential",
        "authorization", "api_key", "refresh_token", "access_token"
    }

    masked_data = data.copy()

    for key, value in data.items():
        if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
            if isinstance(value, str) and len(value) > 8:
                # Show first 4 and last 4 characters
                masked_data[key] = f"{value[:4]}***{value[-4:]}"
            else:
                masked_data[key] = "***"

    return masked_data
