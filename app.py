"""Streamlit front end for the Agentic Fluency Coach."""

from __future__ import annotations

import json
import os
import tempfile
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import streamlit as st

from core.intervention_planner import choose_intervention
from core.learner_state import LearnerState, to_fluency_signals, update_state
from core.llm_client import analyze_turn, generate_response
from core.session_report import build_close_session_payload
from core.transcriber import transcribe_audio
from db.queries import close_session, create_learner, create_session, insert_turn

APP_TITLE = "Agentic Fluency Coach"
DEFAULT_TARGET_SENTENCE = "I would like to book a table for two people tonight."
FALLBACK_SCENARIOS = [
    "You are at a cafe ordering a drink and asking for the price.",
    "You are at an airport check-in desk asking about your seat.",
    "You are introducing yourself in a job interview.",
]
MODE_A_LABEL = "Mode A (Repeat After Me)"
MODE_B_LABEL = "Mode B (Open Roleplay)"
MODE_A_VALUE = "repeat"
MODE_B_VALUE = "roleplay"
SCENARIO_FILE = Path(__file__).parent / "data" / "scenarios.json"

if "learner_id" not in st.session_state:
    st.session_state.learner_id = None
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "learner_state" not in st.session_state:
    st.session_state.learner_state = LearnerState(session_id="", learner_id="")
if "turn_history" not in st.session_state:
    st.session_state.turn_history = []
if "session_active" not in st.session_state:
    st.session_state.session_active = False
if "session_summary" not in st.session_state:
    st.session_state.session_summary = None


def _load_scenarios() -> list[str]:
    """Load scenario prompt strings with a safe fallback."""
    try:
        with SCENARIO_FILE.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        scenarios = [item["prompt"] for item in payload if isinstance(item, dict) and item.get("prompt")]
        return scenarios or FALLBACK_SCENARIOS
    except Exception:
        return FALLBACK_SCENARIOS


def _ensure_learner() -> None:
    """Create the demo learner once per browser session."""
    if st.session_state.learner_id is None:
        st.session_state.learner_id = create_learner("Demo Learner")


def _start_session(mode: str, scenario: str | None) -> None:
    """Start a new practice session when the learner has been created."""
    learner_id = st.session_state.learner_id
    if learner_id is None:
        st.error("Unable to create a learner record. Check your database configuration.")
        return
    session_id = create_session(learner_id, mode, scenario)
    if session_id is None:
        st.error("Unable to start a session right now. Please try again.")
        return
    st.session_state.session_id = session_id
    st.session_state.session_active = True
    st.session_state.turn_history = []
    st.session_state.session_summary = None
    st.session_state.learner_state = LearnerState(session_id=session_id, learner_id=learner_id)


def _save_audio_file(audio_file: Any) -> str | None:
    """Persist an uploaded audio clip to a temporary file."""
    if audio_file is None:
        return None
    suffix = Path(getattr(audio_file, "name", "recording.wav")).suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
        handle.write(audio_file.getbuffer())
        return handle.name


def _accuracy_score(transcript: str, target_sentence: str | None) -> float | None:
    """Return a simple similarity score for repeat-after-me turns."""
    if not target_sentence:
        return None
    return SequenceMatcher(None, transcript.lower(), target_sentence.lower()).ratio() * 100


def _process_turn(audio_file: Any, target_sentence: str | None, scenario: str | None) -> None:
    """Run one learner turn through transcription, analysis, planning, and logging."""
    if audio_file is None:
        st.warning("Record audio before submitting a turn.")
        return
    temp_path = _save_audio_file(audio_file)
    if temp_path is None:
        st.error("Unable to save the recorded audio.")
        return
    try:
        transcript = transcribe_audio(temp_path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    if not transcript:
        st.warning("No speech was detected. Please try another recording.")
        return
    state = st.session_state.learner_state
    turn_analysis = analyze_turn(transcript, target_sentence, scenario)
    update_state(state, turn_analysis)
    intervention_type = choose_intervention(state)
    tutor_response = generate_response(transcript, intervention_type, scenario, state.turn_count)
    _log_turn(state, transcript, target_sentence, intervention_type, tutor_response)
    st.session_state.turn_history.append(
        {
            "transcript": transcript,
            "tutor_response": tutor_response,
            "intervention_type": intervention_type,
        }
    )


def _log_turn(
    state: LearnerState,
    transcript: str,
    target_sentence: str | None,
    intervention_type: str,
    tutor_response: str,
) -> None:
    """Persist a turn when the current session has a database ID."""
    session_id = st.session_state.session_id
    if session_id is not None:
        insert_turn(
            session_id=session_id,
            turn_number=state.turn_count,
            transcript=transcript,
            target_sentence=target_sentence,
            grammar_errors=state.grammar_errors,
            fluency_signals=to_fluency_signals(state),
            intervention_type=intervention_type,
            tutor_response=tutor_response,
            accuracy_score=_accuracy_score(transcript, target_sentence),
        )


def _end_session() -> None:
    """Close the current session and store the visible summary card data."""
    state = st.session_state.learner_state
    summary = build_close_session_payload(state)
    session_id = st.session_state.session_id
    if session_id is not None:
        close_session(session_id=session_id, **summary)
    st.session_state.session_summary = {
        **summary,
        "confidence_proxy": state.confidence_proxy,
    }
    st.session_state.session_id = None
    st.session_state.session_active = False


def _render_sidebar(scenarios: list[str]) -> tuple[str, str | None, str | None]:
    """Render sidebar controls and return the current mode inputs."""
    st.sidebar.header("Session Setup")
    mode_label = st.sidebar.radio(
        "Practice Mode",
        [MODE_A_LABEL, MODE_B_LABEL],
        disabled=st.session_state.session_active,
    )
    target_sentence = None
    scenario = None
    if mode_label == MODE_A_LABEL:
        target_sentence = st.sidebar.text_area(
            "Target sentence",
            value=DEFAULT_TARGET_SENTENCE,
            disabled=st.session_state.session_active,
        )
    else:
        scenario = st.sidebar.selectbox(
            "Scenario", scenarios, disabled=st.session_state.session_active
        )
    if st.sidebar.button("Start Session", disabled=st.session_state.session_active):
        _start_session(MODE_A_VALUE if mode_label == MODE_A_LABEL else MODE_B_VALUE, scenario)
    if st.sidebar.button("End Session", disabled=not st.session_state.session_active):
        _end_session()
    return mode_label, target_sentence, scenario


def _render_metrics() -> None:
    """Render the current learner-state metrics."""
    state = st.session_state.learner_state
    hesitation_rate = state.hesitation_count / max(state.total_words, 1)
    turn_col, confidence_col, hesitation_col = st.columns(3)
    turn_col.metric("Turn Count", state.turn_count)
    confidence_col.metric("Confidence Proxy", f"{state.confidence_proxy:.2f}")
    hesitation_col.metric("Hesitation Rate", f"{hesitation_rate:.2f}")


def _render_turn_history() -> None:
    """Render the transcript and tutor reply pairs in chat format."""
    for turn in st.session_state.turn_history:
        with st.chat_message("user"):
            st.write(turn["transcript"])
        with st.chat_message("assistant"):
            st.write(turn["tutor_response"])
            st.caption(f"Intervention: {turn['intervention_type']}")


def _render_summary() -> None:
    """Render the session summary card after the learner ends a session."""
    summary = st.session_state.session_summary
    if summary is None:
        return
    st.subheader("Session Summary")
    fluency_col, grammar_col = st.columns(2)
    fluency_col.metric("Fluency Score", f"{summary['fluency_score']:.1f}")
    grammar_col.metric("Grammar Score", f"{summary['grammar_score']:.1f}")
    top_errors = summary["top_errors"] or ["None"]
    st.write(f"Top grammar errors: {', '.join(top_errors)}")
    st.write(f"Confidence proxy: {summary['confidence_proxy']:.2f}")
    st.write(f"Recommended next step: {summary['recommended_next']}")


def main() -> None:
    """Render the Streamlit application."""
    _ensure_learner()
    st.title(APP_TITLE)
    if st.session_state.learner_id is None:
        st.warning("Learner setup failed. Check your database configuration before starting.")
    scenarios = _load_scenarios()
    mode_label, target_sentence, scenario = _render_sidebar(scenarios)
    if mode_label == MODE_A_LABEL and target_sentence:
        st.info(f"Repeat this sentence: {target_sentence}")
    if mode_label == MODE_B_LABEL and scenario:
        st.info(f"Scenario: {scenario}")
    _render_metrics()
    audio_file = st.audio_input("Record your response", disabled=not st.session_state.session_active)
    if st.button("Submit Turn", disabled=not st.session_state.session_active):
        _process_turn(audio_file, target_sentence, scenario)
    _render_turn_history()
    _render_summary()


main()
