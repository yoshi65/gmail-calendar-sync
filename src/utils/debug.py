"""Debug utilities for Gmail Calendar Sync development."""

import cProfile
import pstats
import time
from collections.abc import Callable
from functools import wraps
from io import StringIO
from typing import Any

import structlog

logger = structlog.get_logger()


def profile_function(func: Callable) -> Callable:
    """Decorator to profile function performance."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        start_time = time.time()

        try:
            profiler.enable()
            result = func(*args, **kwargs)
            profiler.disable()

            end_time = time.time()
            execution_time = end_time - start_time

            # Create string buffer for profile output
            s = StringIO()
            stats = pstats.Stats(profiler, stream=s)
            stats.sort_stats("cumulative")
            stats.print_stats(10)  # Top 10 functions

            logger.debug(
                "Function profiling completed",
                function=func.__name__,
                execution_time=f"{execution_time:.4f}s",
                profile_stats=s.getvalue(),
            )

            return result

        except Exception as e:
            profiler.disable()
            logger.error(
                "Function profiling failed", function=func.__name__, error=str(e)
            )
            raise

    return wrapper


def time_function(func: Callable) -> Callable:
    """Simple timing decorator for functions."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            execution_time = end_time - start_time

            logger.debug(
                "Function timing",
                function=func.__name__,
                execution_time=f"{execution_time:.4f}s",
            )

            return result

        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time

            logger.error(
                "Function timing (with error)",
                function=func.__name__,
                execution_time=f"{execution_time:.4f}s",
                error=str(e),
            )
            raise

    return wrapper


class PerformanceMonitor:
    """Monitor and track performance metrics."""

    def __init__(self):
        self.metrics: dict[str, Any] = {}
        self.start_times: dict[str, float] = {}

    def start_timer(self, name: str) -> None:
        """Start timing an operation."""
        self.start_times[name] = time.time()
        logger.debug("Performance timer started", operation=name)

    def end_timer(self, name: str) -> float:
        """End timing an operation and return duration."""
        if name not in self.start_times:
            logger.warning("Timer not found", operation=name)
            return 0.0

        duration = time.time() - self.start_times[name]
        self.metrics[name] = duration

        logger.debug(
            "Performance timer completed", operation=name, duration=f"{duration:.4f}s"
        )

        return duration

    def get_metrics(self) -> dict[str, Any]:
        """Get all collected metrics."""
        return self.metrics.copy()

    def log_summary(self) -> None:
        """Log performance summary."""
        if not self.metrics:
            logger.info("No performance metrics collected")
            return

        total_time = sum(self.metrics.values())

        logger.info(
            "Performance summary",
            total_operations=len(self.metrics),
            total_time=f"{total_time:.4f}s",
            metrics=self.metrics,
        )


def debug_email_processing(
    email_id: str, email_content: str, processor_name: str
) -> None:
    """Debug specific email processing with detailed output."""

    logger.debug(
        "Email processing debug",
        email_id=email_id,
        processor=processor_name,
        content_length=len(email_content),
        content_preview=email_content[:200] + "..."
        if len(email_content) > 200
        else email_content,
    )


def log_memory_usage() -> None:
    """Log current memory usage (requires psutil)."""
    try:
        import os

        import psutil

        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()

        logger.debug(
            "Memory usage",
            rss_mb=f"{memory_info.rss / 1024 / 1024:.2f}",
            vms_mb=f"{memory_info.vms / 1024 / 1024:.2f}",
            percent=f"{process.memory_percent():.2f}%",
        )

    except ImportError:
        logger.debug("psutil not available for memory monitoring")
    except Exception as e:
        logger.error("Failed to get memory usage", error=str(e))


def debug_api_call(
    api_name: str,
    request_data: dict | None = None,
    response_data: dict | None = None,
    duration: float | None = None,
) -> None:
    """Debug API call with request/response details."""

    log_data: dict[str, str | dict | list | None] = {
        "api": api_name,
        "duration": f"{duration:.4f}s" if duration else None,
    }

    if request_data:
        # Mask sensitive data
        masked_request = {}
        for key, value in request_data.items():
            if any(
                sensitive in key.lower()
                for sensitive in ["token", "key", "secret", "password"]
            ):
                masked_request[key] = "***MASKED***"
            else:
                masked_request[key] = value
        log_data["request"] = masked_request

    if response_data:
        log_data["response_keys"] = (
            list(response_data.keys())
            if isinstance(response_data, dict)
            else str(type(response_data))
        )

    logger.debug("API call debug", **log_data)


class DebugContext:
    """Context manager for debugging operations."""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time: float | None = None
        self.monitor = PerformanceMonitor()

    def __enter__(self):
        self.start_time = time.time()
        logger.debug("Debug context started", operation=self.operation_name)
        log_memory_usage()
        return self.monitor

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time if self.start_time else 0

        if exc_type:
            logger.error(
                "Debug context ended with error",
                operation=self.operation_name,
                duration=f"{duration:.4f}s",
                error_type=exc_type.__name__,
                error_message=str(exc_val),
            )
        else:
            logger.debug(
                "Debug context completed",
                operation=self.operation_name,
                duration=f"{duration:.4f}s",
            )

        log_memory_usage()


# Global performance monitor instance
performance_monitor = PerformanceMonitor()
