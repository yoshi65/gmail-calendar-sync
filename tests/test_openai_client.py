"""Tests for OpenAIClient extraction logic (prompt-injection hardening).

These guard the two hardening measures added for prompt injection:
JSON-object response mode and the ``{"no_booking_found": true}`` sentinel that
replaces bare ``null`` (which json_object mode cannot return).
"""

from unittest.mock import Mock, patch

import pytest

from src.services.openai_client import OpenAIClient
from src.utils.config import Settings
from src.utils.exceptions import DataExtractionError
from src.utils.openai_metrics_collector import get_metrics_collector


def _mock_response(content: str) -> Mock:
    """Build a minimal OpenAI chat-completion response with the given content."""
    message = Mock()
    message.content = content
    response = Mock()
    response.choices = [Mock(message=message)]
    usage = Mock()
    usage.prompt_tokens = 10
    usage.completion_tokens = 5
    usage.total_tokens = 15
    response.usage = usage
    return response


@patch("src.services.openai_client.get_metrics_collector")
@patch("src.services.openai_client.OpenAI")
class TestOpenAIClientExtraction:
    """JSON mode + sentinel behaviour for both flight and car sharing paths."""

    @staticmethod
    def _client() -> OpenAIClient:
        settings = Mock()
        settings.openai_api_key = "test-key"
        settings.openai_model = "gpt-5.6-terra"
        return OpenAIClient(settings)

    def test_flight_sentinel_returns_none(self, _mock_openai, _mock_collector):
        client = self._client()
        client.client.chat.completions.create = Mock(
            return_value=_mock_response('{"no_booking_found": true}')
        )

        assert client.extract_flight_info("body", "subject") is None

    def test_carshare_sentinel_returns_none(self, _mock_openai, _mock_collector):
        client = self._client()
        client.client.chat.completions.create = Mock(
            return_value=_mock_response('{"no_booking_found": true}')
        )

        assert client.extract_carshare_info("body", "subject", "times_car") is None

    def test_flight_request_forces_json_object(self, _mock_openai, _mock_collector):
        client = self._client()
        create = Mock(return_value=_mock_response('{"no_booking_found": true}'))
        client.client.chat.completions.create = create

        client.extract_flight_info("body", "subject")

        assert create.call_args.kwargs["response_format"] == {"type": "json_object"}

    def test_carshare_request_forces_json_object(self, _mock_openai, _mock_collector):
        client = self._client()
        create = Mock(return_value=_mock_response('{"no_booking_found": true}'))
        client.client.chat.completions.create = create

        client.extract_carshare_info("body", "subject", "times_car")

        assert create.call_args.kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.parametrize("kind", ["flight", "carshare"])
@pytest.mark.parametrize("content", ["", "broken", "{}"])
def test_failed_response_counted_once_with_actual_usage(kind, content):
    collector = get_metrics_collector()
    collector.reset()
    try:
        with patch("src.services.openai_client.OpenAI"):
            client = OpenAIClient(Settings(_env_file=None, openai_api_key="test-key"))
        client.client.chat.completions.create.return_value = _mock_response(content)
        with pytest.raises(DataExtractionError):
            if kind == "flight":
                client.extract_flight_info("body")
            else:
                client.extract_carshare_info("body", provider="times_car")
        summary = collector.get_summary()
        assert summary["total_calls"] == 1
        assert summary["successful_calls"] == 0
        assert summary["failed_calls"] == 1
        assert summary["total_tokens"] == 15
        assert summary["total_cost_usd"] > 0
    finally:
        collector.reset()


@pytest.mark.parametrize("kind", ["flight", "carshare"])
def test_invalid_extracted_values_are_not_logged(kind):
    marker = "SYNTHETIC_PRIVATE_VALUE"
    with (
        patch("src.services.openai_client.OpenAI"),
        patch("src.services.openai_client.logger") as log,
    ):
        client = OpenAIClient(Settings(_env_file=None, openai_api_key="test-key"))
        if kind == "carshare":
            data: dict = {"station": {"station_name": {"private": marker}}}
            assert client._convert_to_carshare_booking(data, "times_car") is None
        else:
            data = {
                "confirmation_code": "TEST",
                "passenger_name": {"private": marker},
                "outbound_segments": [{}],
            }
            with patch.object(client, "_create_flight_segment", return_value=Mock()):
                assert client._convert_to_flight_booking(data) is None
        assert log.error.called
        assert marker not in str(log.mock_calls)
