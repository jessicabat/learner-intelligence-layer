"""Tests for the OpenAI LLM client wrapper."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core import llm_client


def _mock_chat_response(content: str) -> MagicMock:
    """Build a minimal chat completion response with message content."""
    response = MagicMock()
    response.choices = [SimpleNamespace(message=SimpleNamespace(content=content))]
    return response


def test_analyze_turn_returns_parsed_dict_on_valid_json() -> None:
    """Structured analysis should parse valid JSON content."""
    llm_client._get_client.clear()
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_chat_response(
        """
        {
          "grammar_errors": {"tense": 1, "subject_verb": 2, "ignored": 4},
          "vocabulary_flags": ["reservation"],
          "filler_words": 2,
          "word_count": 9,
          "is_complete_sentence": true,
          "task_completed": false
        }
        """
    )

    with patch("core.llm_client.load_dotenv"), patch(
        "core.llm_client.os.environ.get", return_value="test-key"
    ), patch("core.llm_client.OpenAI", return_value=mock_client):
        result = llm_client.analyze_turn("I go airport", None, "Book a hotel")

    assert result == {
        "grammar_errors": {"tense": 1, "subject_verb": 2},
        "vocabulary_flags": ["reservation"],
        "filler_words": 2,
        "word_count": 9,
        "is_complete_sentence": True,
        "task_completed": False,
    }


def test_analyze_turn_returns_empty_dict_on_api_error() -> None:
    """API failures should return the safe empty analysis payload."""
    llm_client._get_client.clear()
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("api failed")

    with patch("core.llm_client.load_dotenv"), patch(
        "core.llm_client.os.environ.get", return_value="test-key"
    ), patch("core.llm_client.OpenAI", return_value=mock_client):
        result = llm_client.analyze_turn("hello", "hello", None)

    assert result == llm_client.EMPTY_TURN_ANALYSIS


def test_analyze_turn_returns_empty_dict_on_malformed_json() -> None:
    """Malformed JSON should return the safe empty analysis payload."""
    llm_client._get_client.clear()
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_chat_response("not json")

    with patch("core.llm_client.load_dotenv"), patch(
        "core.llm_client.os.environ.get", return_value="test-key"
    ), patch("core.llm_client.OpenAI", return_value=mock_client):
        result = llm_client.analyze_turn("hello", None, "Order coffee")

    assert result == llm_client.EMPTY_TURN_ANALYSIS


def test_generate_response_returns_content_on_success() -> None:
    """Tutor response generation should return assistant text content."""
    llm_client._get_client.clear()
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_chat_response("Nice job. Try again.")

    with patch("core.llm_client.load_dotenv"), patch(
        "core.llm_client.os.environ.get", return_value="test-key"
    ), patch("core.llm_client.OpenAI", return_value=mock_client):
        result = llm_client.generate_response("I need ticket", "push", "Buy a ticket", 3)

    assert result == "Nice job. Try again."


def test_generate_response_returns_fallback_on_api_error() -> None:
    """Tutor response generation should fall back safely on API errors."""
    llm_client._get_client.clear()
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("api failed")

    with patch("core.llm_client.load_dotenv"), patch(
        "core.llm_client.os.environ.get", return_value="test-key"
    ), patch("core.llm_client.OpenAI", return_value=mock_client):
        result = llm_client.generate_response("I need ticket", "continue", None, 1)

    assert result == llm_client.RESPONSE_FALLBACK_TEXT
