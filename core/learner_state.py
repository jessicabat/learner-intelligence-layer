"""Session-level learner state tracking."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass
class LearnerState:
    """Represents a learner's progress within a single session."""

    session_id: str
    learner_id: str
    turn_count: int = 0
    grammar_errors: dict[str, int] = field(default_factory=dict)
    vocabulary_flags: list[str] = field(default_factory=list)
    hesitation_count: int = 0
    total_words: int = 0
    complete_sentences: int = 0
    task_completed: bool = False
    confidence_proxy: float = 0.0


def _as_int(value: object) -> int:
    """Return an integer count or zero for unsupported values."""
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _as_bool(value: object) -> bool:
    """Return a boolean flag with a safe default."""
    return value if isinstance(value, bool) else False


def _as_string_list(value: object) -> list[str]:
    """Return a filtered list of strings from loose input data."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _as_error_counts(value: object) -> dict[str, int]:
    """Return grammar error counts from a loose mapping."""
    if not isinstance(value, Mapping):
        return {}
    return {str(key): _as_int(count) for key, count in value.items()}


def _merge_error_counts(
    grammar_errors: dict[str, int], new_counts: Mapping[str, int]
) -> None:
    """Add this turn's error counts into the running totals."""
    for key, count in new_counts.items():
        grammar_errors[key] = grammar_errors.get(key, 0) + count


def _hesitation_rate(state: LearnerState) -> float:
    """Compute the learner's running hesitation rate."""
    return state.hesitation_count / max(state.total_words, 1)


def _compute_confidence_proxy(state: LearnerState) -> float:
    """Compute the learner's confidence proxy score."""
    if state.turn_count == 0:
        return 0.0
    completion_rate = state.complete_sentences / state.turn_count
    return completion_rate * (1 - _hesitation_rate(state))


def update_state(
    state: LearnerState, turn_analysis: Mapping[str, object]
) -> LearnerState:
    """Merge one turn analysis into the running learner state."""
    errors = _as_error_counts(turn_analysis.get("grammar_errors", {}))
    vocabulary_flags = _as_string_list(turn_analysis.get("vocabulary_flags", []))
    filler_words = _as_int(turn_analysis.get("filler_words", 0))
    word_count = _as_int(turn_analysis.get("word_count", 0))
    is_complete = _as_bool(turn_analysis.get("is_complete_sentence", False))
    task_done = _as_bool(turn_analysis.get("task_completed", False))
    _merge_error_counts(state.grammar_errors, errors)
    state.vocabulary_flags.extend(vocabulary_flags)
    state.hesitation_count += filler_words
    state.total_words += word_count
    state.complete_sentences += int(is_complete)
    state.task_completed = state.task_completed or task_done
    state.turn_count += 1
    state.confidence_proxy = _compute_confidence_proxy(state)
    return state


def to_fluency_signals(state: LearnerState) -> dict[str, float | int]:
    """Return flat fluency metrics suitable for database logging."""
    avg_word_count = state.total_words / max(state.turn_count, 1)
    completion_rate = state.complete_sentences / max(state.turn_count, 1)
    return {
        "turn_count": state.turn_count,
        "hesitation_rate": _hesitation_rate(state),
        "avg_word_count": avg_word_count,
        "sentence_completion_rate": completion_rate,
        "confidence_proxy": state.confidence_proxy,
    }


__all__ = ["LearnerState", "to_fluency_signals", "update_state"]
