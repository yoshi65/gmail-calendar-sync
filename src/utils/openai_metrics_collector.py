"""OpenAI API metrics collector for usage analysis."""

from collections import defaultdict
from typing import Any

import structlog

from ..models.openai_metrics import OpenAIMetrics

logger = structlog.get_logger()


class OpenAIMetricsCollector:
    """Singleton collector for OpenAI API usage metrics."""

    _instance = None
    _metrics: list[OpenAIMetrics] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._metrics = []
        return cls._instance

    def add_metrics(self, metrics: OpenAIMetrics) -> None:
        """Add OpenAI API usage metrics."""
        self._metrics.append(metrics)

    def get_all_metrics(self) -> list[OpenAIMetrics]:
        """Get all collected metrics."""
        return self._metrics.copy()

    def get_summary(self) -> dict:
        """Get comprehensive usage summary."""
        if not self._metrics:
            return {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_cost_usd": 0.0,
                "total_tokens": 0,
                "total_processing_time_ms": 0.0,
                "by_email_type": {},
                "average_processing_time_ms": 0.0,
                "average_cost_per_call_usd": 0.0,
            }

        # Overall statistics
        total_calls = len(self._metrics)
        successful_calls = sum(1 for m in self._metrics if m.success)
        failed_calls = total_calls - successful_calls
        total_cost = (
            sum(m.cost_usd for m in self._metrics if m.cost_usd is not None)
            if all(m.cost_usd is not None for m in self._metrics)
            else None
        )
        total_tokens = sum(m.usage.total_tokens for m in self._metrics)
        total_processing_time = sum(m.processing_time_ms for m in self._metrics)

        # Statistics by email type
        by_email_type: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "calls": 0,
                "successful": 0,
                "failed": 0,
                "cost_usd": 0.0,
                "tokens": 0,
                "processing_time_ms": 0.0,
            }
        )

        for metrics in self._metrics:
            email_type = metrics.email_type
            by_email_type[email_type]["calls"] += 1
            if metrics.cost_usd is None:
                by_email_type[email_type]["cost_usd"] = None
            elif by_email_type[email_type]["cost_usd"] is not None:
                by_email_type[email_type]["cost_usd"] += metrics.cost_usd
            by_email_type[email_type]["tokens"] += metrics.usage.total_tokens
            by_email_type[email_type]["processing_time_ms"] += (
                metrics.processing_time_ms
            )

            if metrics.success:
                by_email_type[email_type]["successful"] += 1
            else:
                by_email_type[email_type]["failed"] += 1

        # Convert defaultdict to regular dict for JSON serialization
        by_email_type_dict = dict(by_email_type)

        return {
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "total_cost_usd": round(total_cost, 6) if total_cost is not None else None,
            "total_tokens": total_tokens,
            "total_processing_time_ms": round(total_processing_time, 2),
            "by_email_type": by_email_type_dict,
            "average_processing_time_ms": round(total_processing_time / total_calls, 2)
            if total_calls > 0
            else 0.0,
            "average_cost_per_call_usd": round(total_cost / total_calls, 6)
            if total_calls > 0 and total_cost is not None
            else None,
        }

    def log_summary(self) -> None:
        """Log comprehensive usage summary."""
        summary = self.get_summary()

        if summary["total_calls"] == 0:
            logger.info(
                "OpenAI API usage summary",
                message="OpenAI API usage summary",
                total_calls=0,
                total_cost_usd=0.0,
            )
            return

        logger.info(
            "OpenAI API usage summary",
            message="OpenAI API usage summary",
            total_calls=summary["total_calls"],
            successful_calls=summary["successful_calls"],
            failed_calls=summary["failed_calls"],
            total_cost_usd=summary["total_cost_usd"],
            total_tokens=summary["total_tokens"],
            total_processing_time_ms=summary["total_processing_time_ms"],
            average_processing_time_ms=summary["average_processing_time_ms"],
            average_cost_per_call_usd=summary["average_cost_per_call_usd"],
        )

        # Log by email type
        for email_type, stats in summary["by_email_type"].items():
            logger.info(
                f"OpenAI API usage by email type: {email_type}",
                message=f"OpenAI API usage by email type: {email_type}",
                email_type=email_type,
                calls=stats["calls"],
                successful=stats["successful"],
                failed=stats["failed"],
                cost_usd=round(stats["cost_usd"], 6)
                if stats["cost_usd"] is not None
                else None,
                tokens=stats["tokens"],
                processing_time_ms=round(stats["processing_time_ms"], 2),
                average_cost_per_call_usd=round(stats["cost_usd"] / stats["calls"], 6)
                if stats["calls"] > 0 and stats["cost_usd"] is not None
                else None,
                average_processing_time_ms=round(
                    stats["processing_time_ms"] / stats["calls"], 2
                )
                if stats["calls"] > 0
                else 0.0,
            )

    def reset(self) -> None:
        """Reset all collected metrics (useful for testing)."""
        self._metrics.clear()

    def get_cost_breakdown(self) -> dict:
        """Get detailed cost breakdown."""
        if not self._metrics:
            return {}

        return {
            "total_cost_usd": self.get_summary()["total_cost_usd"],
            "total_prompt_tokens": sum(m.usage.prompt_tokens for m in self._metrics),
            "total_completion_tokens": sum(
                m.usage.completion_tokens for m in self._metrics
            ),
        }


def get_metrics_collector() -> OpenAIMetricsCollector:
    """Get the singleton OpenAI metrics collector."""
    return OpenAIMetricsCollector()
