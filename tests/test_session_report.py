"""Tests for session summary helpers."""

from core.learner_state import LearnerState
from core.session_report import build_close_session_payload


def test_build_close_session_payload_uses_safe_zero_turn_denominator() -> None:
    """Zero-turn sessions should still produce a valid fluency score."""
    state = LearnerState(session_id="session-123", learner_id="learner-123")

    payload = build_close_session_payload(state)

    assert payload["fluency_score"] == 0.0


def test_build_close_session_payload_uses_total_grammar_error_sum() -> None:
    """Grammar score should subtract the sum of all grammar error counts."""
    state = LearnerState(
        session_id="session-123",
        learner_id="learner-123",
        grammar_errors={"article": 2, "tense": 3},
    )

    payload = build_close_session_payload(state)

    assert payload["grammar_score"] == 75.0


def test_build_close_session_payload_caps_grammar_score_at_zero() -> None:
    """Large grammar error totals should not make the score negative."""
    state = LearnerState(
        session_id="session-123",
        learner_id="learner-123",
        grammar_errors={"article": 25},
    )

    payload = build_close_session_payload(state)

    assert payload["grammar_score"] == 0.0


def test_build_close_session_payload_orders_top_errors_descending() -> None:
    """Top grammar errors should be sorted by count and limited to three."""
    state = LearnerState(
        session_id="session-123",
        learner_id="learner-123",
        grammar_errors={"article": 2, "tense": 5, "preposition": 3, "subject_verb": 1},
    )

    payload = build_close_session_payload(state)

    assert payload["top_errors"] == ["tense", "preposition", "article"]


def test_build_close_session_payload_recommends_focused_practice() -> None:
    """Repeated grammar problems should produce a targeted recommendation."""
    state = LearnerState(
        session_id="session-123",
        learner_id="learner-123",
        grammar_errors={"subject_verb": 3, "article": 1},
    )

    payload = build_close_session_payload(state)

    assert payload["recommended_next"] == "Focus on subject_verb in your next session."


def test_build_close_session_payload_recommends_general_practice_otherwise() -> None:
    """Learners without repeated grammar errors should get the default recommendation."""
    state = LearnerState(
        session_id="session-123",
        learner_id="learner-123",
        grammar_errors={"subject_verb": 2, "article": 1},
    )

    payload = build_close_session_payload(state)

    assert payload["recommended_next"] == "Keep practicing — your fluency is improving."
    assert payload["improvement_delta"] == {"fluency": 0.0, "grammar": 0.0}
