"""OpenAI client helpers for learner analysis and tutor responses."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any

try:
    import streamlit as st
except ImportError:  # pragma: no cover - used only in minimal test environments
    class _StreamlitFallback:
        """Fallback object that preserves the cache_resource decorator interface."""

        @staticmethod
        def cache_resource(func: Any) -> Any:
            """Return the wrapped function unchanged when Streamlit is unavailable."""
            func.clear = lambda: None
            return func

    st = _StreamlitFallback()

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - fallback for minimal local environments
    def load_dotenv() -> bool:
        """No-op dotenv loader used when python-dotenv is unavailable."""
        return False

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - patched in tests or available at runtime
    class OpenAI:  # type: ignore[no-redef]
        """Fallback placeholder that raises when instantiated."""

        def __init__(self, *_: Any, **__: Any) -> None:
            raise ImportError("openai is not installed")


MODEL_NAME = "gpt-4o-mini"
ALLOWED_GRAMMAR_KEYS = {"tense", "article", "preposition", "subject_verb"}
EMPTY_TURN_ANALYSIS = {
    "grammar_errors": {},
    "vocabulary_flags": [],
    "filler_words": 0,
    "word_count": 0,
    "is_complete_sentence": False,
    "task_completed": False,
}
RESPONSE_FALLBACK_TEXT = "Let's keep going — you're doing well."
ANALYZE_TURN_SYSTEM_PROMPT = """
You are an expert English language evaluator.
Return your response as a json object with exactly these keys:
grammar_errors, vocabulary_flags, filler_words, word_count,
is_complete_sentence, task_completed.
grammar_errors must be a dict whose keys are limited to:
tense, article, preposition, subject_verb.
""".strip()
GENERATE_RESPONSE_SYSTEM_PROMPT = """
You are a warm, encouraging English tutor.
The intervention type is one of: continue, drill, simplify, redirect, push, defer.
Adjust your response style to match the intervention type.
Keep responses to 2-3 sentences max.
""".strip()


def _empty_turn_analysis() -> dict[str, object]:
    """Return a fresh empty turn-analysis payload."""
    return {
        "grammar_errors": {},
        "vocabulary_flags": [],
        "filler_words": 0,
        "word_count": 0,
        "is_complete_sentence": False,
        "task_completed": False,
    }


def _get_api_key() -> str | None:
    """Load environment variables and return the OpenAI API key."""
    load_dotenv()
    return os.environ.get("OPENAI_API_KEY")


@st.cache_resource
def _get_client() -> Any:
    """Create and cache the OpenAI client."""
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


def _analysis_user_prompt(
    transcript: str, target_sentence: str | None, scenario: str | None
) -> str:
    """Build the user prompt for structured turn analysis."""
    prompt = [f"Learner transcript: {transcript}"]
    if target_sentence:
        prompt.append(f"Target sentence: {target_sentence}")
        prompt.append("Evaluate how accurately the learner matched the target sentence.")
    if scenario:
        prompt.append(f"Scenario objective: {scenario}")
        prompt.append("Evaluate whether the learner met the scenario objective.")
    return "\n".join(prompt)


def _response_user_prompt(
    transcript: str, intervention_type: str, scenario: str | None, turn_count: int
) -> str:
    """Build the user prompt for tutor-response generation."""
    prompt = [
        f"Learner transcript: {transcript}",
        f"Intervention type: {intervention_type}",
        f"Turn count: {turn_count}",
    ]
    if scenario:
        prompt.append(f"Scenario: {scenario}")
    return "\n".join(prompt)


def _message_content(response: Any) -> str:
    """Extract message content from a chat completion response."""
    message = response.choices[0].message
    return message.content.strip() if isinstance(message.content, str) else ""


def _validated_turn_analysis(content: str) -> dict[str, object]:
    """Parse and validate a structured turn-analysis JSON payload."""
    payload = json.loads(content)
    if not isinstance(payload, Mapping):
        raise ValueError("Turn analysis must be a JSON object")
    required = set(EMPTY_TURN_ANALYSIS)
    if not required.issubset(payload):
        raise ValueError("Missing required turn-analysis keys")
    grammar_errors = _validated_grammar_errors(payload["grammar_errors"])
    vocabulary_flags = _validated_vocabulary_flags(payload["vocabulary_flags"])
    filler_words = _validated_int(payload["filler_words"])
    word_count = _validated_int(payload["word_count"])
    is_complete = _validated_bool(payload["is_complete_sentence"])
    task_completed = _validated_bool(payload["task_completed"])
    return {
        "grammar_errors": grammar_errors,
        "vocabulary_flags": vocabulary_flags,
        "filler_words": filler_words,
        "word_count": word_count,
        "is_complete_sentence": is_complete,
        "task_completed": task_completed,
    }


def _validated_grammar_errors(value: object) -> dict[str, int]:
    """Validate and sanitize grammar error counts."""
    if not isinstance(value, Mapping):
        raise ValueError("grammar_errors must be a dict")
    return {
        str(key): _validated_int(count)
        for key, count in value.items()
        if str(key) in ALLOWED_GRAMMAR_KEYS
    }


def _validated_vocabulary_flags(value: object) -> list[str]:
    """Validate the list of vocabulary flags."""
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("vocabulary_flags must be a list of strings")
    return value


def _validated_int(value: object) -> int:
    """Validate an integer field."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Expected integer value")
    return value


def _validated_bool(value: object) -> bool:
    """Validate a boolean field."""
    if not isinstance(value, bool):
        raise ValueError("Expected boolean value")
    return value


def analyze_turn(
    transcript: str, target_sentence: str | None, scenario: str | None
) -> dict[str, object]:
    """Analyze one learner turn and return structured session signals."""
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=MODEL_NAME,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": ANALYZE_TURN_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _analysis_user_prompt(transcript, target_sentence, scenario),
                },
            ],
        )
        return _validated_turn_analysis(_message_content(response))
    except Exception:
        return _empty_turn_analysis()


def generate_response(
    transcript: str, intervention_type: str, scenario: str | None, turn_count: int
) -> str:
    """Generate the tutor's next response for the learner."""
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": GENERATE_RESPONSE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _response_user_prompt(
                        transcript, intervention_type, scenario, turn_count
                    ),
                },
            ],
        )
        content = _message_content(response)
        return content or RESPONSE_FALLBACK_TEXT
    except Exception:
        return RESPONSE_FALLBACK_TEXT


if not hasattr(_get_client, "clear"):  # pragma: no cover - safety for minimal caching fallbacks
    _get_client.clear = lambda: None


__all__ = ["analyze_turn", "generate_response"]
