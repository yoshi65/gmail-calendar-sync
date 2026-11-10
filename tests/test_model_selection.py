"""Configured model propagation and honest cost estimates."""

from unittest.mock import Mock, patch

import pytest

from src.models.openai_metrics import OpenAIMetrics, OpenAIUsage
from src.services.openai_client import OpenAIClient
from src.utils.config import Settings
from src.utils.openai_metrics_collector import get_metrics_collector


@pytest.mark.parametrize("kind", ["flight", "carshare"])
def test_environment_model_used_for_request_and_metrics(monkeypatch, kind):
    monkeypatch.setenv("OPENAI_MODEL", "test-configured-model")
    settings = Settings(_env_file=None, openai_api_key="test-key")
    collector = get_metrics_collector()
    collector.reset()
    with patch("src.services.openai_client.OpenAI"):
        client = OpenAIClient(settings)
    response = Mock()
    response.usage.prompt_tokens = 10
    response.usage.completion_tokens = 5
    response.usage.total_tokens = 15
    response.choices = [Mock(message=Mock(content='{"no_booking_found": true}'))]
    client.client.chat.completions.create.return_value = response
    if kind == "flight":
        client.extract_flight_info("test body")
    else:
        client.extract_carshare_info("test body", provider="times_car")
    args = client.client.chat.completions.create.call_args.kwargs
    assert args["model"] == "test-configured-model"
    assert "max_tokens" not in args and "temperature" not in args
    assert args["max_completion_tokens"] == 8192
    assert collector.get_all_metrics()[0].model == "test-configured-model"
    assert collector.get_summary()["total_cost_usd"] is None
    assert collector.get_cost_breakdown()["total_cost_usd"] is None
    collector.log_summary()
    collector.reset()


@pytest.mark.parametrize(
    "model,prompt,expected",
    [
        ("gpt-5.6-terra", 1000, 0.014),
        ("gpt-5.6-terra", 300000, 1.218),
        ("unknown-model", 1000, None),
    ],
)
def test_estimate_uses_known_model_and_context_tier(model, prompt, expected):
    metric = OpenAIMetrics(
        model=model,
        email_type="flight",
        processing_time_ms=1,
        usage=OpenAIUsage(
            prompt_tokens=prompt, completion_tokens=1000, total_tokens=prompt + 1000
        ),
        success=True,
    )
    if expected is None:
        assert metric.calculate_cost() is None
    else:
        assert metric.calculate_cost() == pytest.approx(expected)
