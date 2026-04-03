"""Tests for session-level learner state tracking."""

from core.learner_state import LearnerState, to_fluency_signals, update_state


def test_learner_state_accepts_required_ids_only() -> None:
    """The state should be easy to instantiate with just session identifiers."""
    state = LearnerState(session_id="session-123", learner_id="learner-123")

    assert state.turn_count == 0
    assert state.grammar_errors == {}
    assert state.vocabulary_flags == []
    assert state.confidence_proxy == 0.0


def test_update_state_accumulates_grammar_errors_across_turns() -> None:
    """Grammar error counts should sum across multiple turns."""
    state = LearnerState(session_id="session-123", learner_id="learner-123")

    update_state(state, {"grammar_errors": {"tense": 1, "subject_verb": 2}})
    update_state(state, {"grammar_errors": {"tense": 2, "article": 1}})

    assert state.grammar_errors == {"tense": 3, "subject_verb": 2, "article": 1}


def test_confidence_proxy_is_zero_for_new_state() -> None:
    """A fresh state should report zero confidence before any turns."""
    state = LearnerState(session_id="session-123", learner_id="learner-123")

    assert state.confidence_proxy == 0.0


def test_update_state_recomputes_confidence_after_incrementing_turn_count() -> None:
    """Confidence should use the incremented turn count as its denominator."""
    state = LearnerState(session_id="session-123", learner_id="learner-123")

    update_state(
        state,
        {"word_count": 4, "filler_words": 1, "is_complete_sentence": True},
    )

    assert state.turn_count == 1
    assert state.confidence_proxy == 0.75


def test_update_state_increments_running_counters() -> None:
    """Turn metrics should update the running session totals."""
    state = LearnerState(session_id="session-123", learner_id="learner-123")

    update_state(
        state,
        {
            "vocabulary_flags": ["airport", "reservation"],
            "filler_words": 2,
            "word_count": 10,
            "is_complete_sentence": True,
        },
    )

    assert state.turn_count == 1
    assert state.hesitation_count == 2
    assert state.total_words == 10
    assert state.complete_sentences == 1
    assert state.vocabulary_flags == ["airport", "reservation"]


def test_to_fluency_signals_returns_expected_numeric_keys() -> None:
    """Fluency signals should be flat numeric values for DB logging."""
    state = LearnerState(session_id="session-123", learner_id="learner-123")
    update_state(
        state,
        {"word_count": 8, "filler_words": 2, "is_complete_sentence": True},
    )

    signals = to_fluency_signals(state)

    assert set(signals) == {
        "turn_count",
        "hesitation_rate",
        "avg_word_count",
        "sentence_completion_rate",
        "confidence_proxy",
    }
    assert all(isinstance(value, (int, float)) for value in signals.values())


def test_task_completed_stays_true_once_reached() -> None:
    """Task completion should remain true after later incomplete turns."""
    state = LearnerState(session_id="session-123", learner_id="learner-123")

    update_state(state, {"task_completed": True})
    update_state(state, {"task_completed": False})

    assert state.task_completed is True


def test_zero_word_updates_do_not_cause_division_errors() -> None:
    """Zero-word turns should still produce valid fluency metrics."""
    state = LearnerState(session_id="session-123", learner_id="learner-123")

    update_state(state, {})
    signals = to_fluency_signals(state)

    assert signals["turn_count"] == 1
    assert signals["hesitation_rate"] == 0.0
    assert signals["avg_word_count"] == 0.0
    assert signals["sentence_completion_rate"] == 0.0
    assert signals["confidence_proxy"] == 0.0
