"""Session summary helpers for closing learner sessions."""

from __future__ import annotations

from core.learner_state import LearnerState

DEFAULT_IMPROVEMENT_DELTA = {"fluency": 0.0, "grammar": 0.0}
GRAMMAR_PENALTY_PER_ERROR = 5
MAX_TOP_ERRORS = 3
RECOMMENDATION_ERROR_THRESHOLD = 3
DEFAULT_RECOMMENDATION = "Keep practicing — your fluency is improving."


def _top_errors(state: LearnerState) -> list[str]:
    """Return the top grammar error keys sorted by descending count."""
    ranked_errors = sorted(
        state.grammar_errors.items(), key=lambda item: (-item[1], item[0])
    )
    return [error for error, _ in ranked_errors[:MAX_TOP_ERRORS]]


def _recommended_next(state: LearnerState, top_errors: list[str]) -> str:
    """Return the next-step recommendation for the learner."""
    if not top_errors:
        return DEFAULT_RECOMMENDATION
    top_error = top_errors[0]
    if state.grammar_errors.get(top_error, 0) >= RECOMMENDATION_ERROR_THRESHOLD:
        return f"Focus on {top_error} in your next session."
    return DEFAULT_RECOMMENDATION


def build_close_session_payload(state: LearnerState) -> dict[str, object]:
    """Build the close-session payload expected by the DB helper."""
    top_errors = _top_errors(state)
    total_grammar_errors = sum(state.grammar_errors.values())
    fluency_score = (state.complete_sentences / max(state.turn_count, 1)) * 100
    grammar_score = max(0.0, 100 - total_grammar_errors * GRAMMAR_PENALTY_PER_ERROR)
    # TODO: Compare against get_last_session() once cross-session deltas are wired in.
    return {
        "fluency_score": fluency_score,
        "grammar_score": grammar_score,
        "task_completed": state.task_completed,
        "top_errors": top_errors,
        "recommended_next": _recommended_next(state, top_errors),
        "improvement_delta": DEFAULT_IMPROVEMENT_DELTA.copy(),
    }


__all__ = ["build_close_session_payload"]
