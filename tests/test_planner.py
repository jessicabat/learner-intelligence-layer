"""Tests for the intervention planner."""

from core.intervention_planner import choose_intervention
from core.learner_state import LearnerState


def test_choose_intervention_returns_continue_with_no_turns() -> None:
    """A new session should continue because there is no learner data yet."""
    state = LearnerState(session_id="session-123", learner_id="learner-123")

    assert choose_intervention(state) == "continue"


def test_choose_intervention_returns_simplify_for_low_confidence() -> None:
    """Low confidence after enough turns should simplify the next response."""
    state = LearnerState(
        session_id="session-123",
        learner_id="learner-123",
        turn_count=2,
        confidence_proxy=0.2,
    )

    assert choose_intervention(state) == "simplify"


def test_choose_intervention_prioritizes_simplify_before_drill() -> None:
    """Simplify should win when low confidence and repeated grammar errors coexist."""
    state = LearnerState(
        session_id="session-123",
        learner_id="learner-123",
        turn_count=2,
        confidence_proxy=0.2,
        grammar_errors={"tense": 3},
    )

    assert choose_intervention(state) == "simplify"


def test_choose_intervention_returns_drill_at_grammar_threshold() -> None:
    """A single grammar error count of three should trigger a drill."""
    state = LearnerState(
        session_id="session-123",
        learner_id="learner-123",
        turn_count=1,
        grammar_errors={"article": 3},
    )

    assert choose_intervention(state) == "drill"


def test_choose_intervention_does_not_drill_below_grammar_threshold() -> None:
    """Two errors on one grammar key should not trigger drilling."""
    state = LearnerState(
        session_id="session-123",
        learner_id="learner-123",
        turn_count=1,
        grammar_errors={"article": 2},
    )

    assert choose_intervention(state) == "continue"


def test_choose_intervention_returns_redirect_above_hesitation_threshold() -> None:
    """High hesitation rate should redirect the learner to break the pattern."""
    state = LearnerState(
        session_id="session-123",
        learner_id="learner-123",
        turn_count=1,
        hesitation_count=3,
        total_words=10,
    )

    assert choose_intervention(state) == "redirect"


def test_choose_intervention_does_not_redirect_at_hesitation_boundary() -> None:
    """A hesitation rate of exactly one quarter should not redirect."""
    state = LearnerState(
        session_id="session-123",
        learner_id="learner-123",
        turn_count=1,
        hesitation_count=1,
        total_words=4,
    )

    assert choose_intervention(state) == "continue"


def test_choose_intervention_returns_push_above_confidence_threshold() -> None:
    """Strong confidence after enough turns should increase the challenge."""
    state = LearnerState(
        session_id="session-123",
        learner_id="learner-123",
        turn_count=3,
        confidence_proxy=0.8,
    )

    assert choose_intervention(state) == "push"


def test_choose_intervention_prioritizes_push_before_defer() -> None:
    """Push should win over defer when both rules match."""
    state = LearnerState(
        session_id="session-123",
        learner_id="learner-123",
        turn_count=3,
        confidence_proxy=0.8,
        task_completed=True,
    )

    assert choose_intervention(state) == "push"


def test_choose_intervention_does_not_push_at_confidence_boundary() -> None:
    """Confidence must be strictly greater than the push threshold."""
    state = LearnerState(
        session_id="session-123",
        learner_id="learner-123",
        turn_count=3,
        confidence_proxy=0.75,
    )

    assert choose_intervention(state) == "continue"


def test_choose_intervention_returns_defer_when_task_is_complete() -> None:
    """Completed tasks should defer when no higher-priority rule applies."""
    state = LearnerState(
        session_id="session-123",
        learner_id="learner-123",
        turn_count=1,
        task_completed=True,
    )

    assert choose_intervention(state) == "defer"


def test_choose_intervention_defaults_to_continue() -> None:
    """Unremarkable states should keep the conversation moving."""
    state = LearnerState(
        session_id="session-123",
        learner_id="learner-123",
        turn_count=1,
        confidence_proxy=0.5,
        grammar_errors={"tense": 1},
        hesitation_count=1,
        total_words=10,
    )

    assert choose_intervention(state) == "continue"
