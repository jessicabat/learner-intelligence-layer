"""Rule-based intervention planner for tutor responses."""

from core.learner_state import LearnerState

LOW_CONFIDENCE_THRESHOLD = 0.3
LOW_CONFIDENCE_MIN_TURNS = 2
GRAMMAR_DRILL_THRESHOLD = 3
REDIRECT_HESITATION_RATE_THRESHOLD = 0.25
HIGH_CONFIDENCE_THRESHOLD = 0.75
HIGH_CONFIDENCE_MIN_TURNS = 3


def choose_intervention(state: LearnerState) -> str:
    """Return the next tutor intervention type for the current learner state."""
    if state.turn_count == 0:
        return "continue"
    if (
        state.confidence_proxy < LOW_CONFIDENCE_THRESHOLD
        and state.turn_count >= LOW_CONFIDENCE_MIN_TURNS
    ):
        return "simplify"
    if any(count >= GRAMMAR_DRILL_THRESHOLD for count in state.grammar_errors.values()):
        return "drill"
    if (
        state.hesitation_count / max(state.total_words, 1)
        > REDIRECT_HESITATION_RATE_THRESHOLD
    ):
        return "redirect"
    if (
        state.confidence_proxy > HIGH_CONFIDENCE_THRESHOLD
        and state.turn_count >= HIGH_CONFIDENCE_MIN_TURNS
    ):
        return "push"
    if state.task_completed:
        return "defer"
    return "continue"
