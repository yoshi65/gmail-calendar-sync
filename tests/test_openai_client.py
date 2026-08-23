"""Tests for OpenAIClient extraction logic (prompt-injection hardening).

These guard the two hardening measures added for prompt injection:
JSON-object response mode and the ``{"no_booking_found": true}`` sentinel that
replaces bare ``null`` (which json_object mode cannot return).
"""

from unittest.mock import Mock, patch

from src.services.openai_client import OpenAIClient


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
