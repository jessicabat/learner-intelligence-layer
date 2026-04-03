"""Database query helpers for the learner intelligence MVP."""

from __future__ import annotations

import os
from typing import Any

try:
    import psycopg2
    from psycopg2.extras import Json, RealDictCursor
except ImportError:  # pragma: no cover - fallback for minimal local environments
    class Json:  # type: ignore[no-redef]
        """Minimal stand-in for psycopg2.extras.Json in test-only environments."""

        def __init__(self, adapted: Any) -> None:
            self.adapted = adapted

    class RealDictCursor:  # type: ignore[no-redef]
        """Minimal stand-in for psycopg2.extras.RealDictCursor."""

    class _Psycopg2Fallback:
        """Fallback object that raises if a real connection is attempted."""

        @staticmethod
        def connect(_: str) -> Any:
            raise ImportError("psycopg2 is not installed")

    psycopg2 = _Psycopg2Fallback()  # type: ignore[assignment]

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - fallback for minimal local environments
    def load_dotenv() -> bool:
        """No-op dotenv loader used when python-dotenv is unavailable."""
        return False


CREATE_LEARNER_SQL = "INSERT INTO learners (display_name) VALUES (%s) RETURNING learner_id"
CREATE_SESSION_SQL = """
INSERT INTO sessions (learner_id, mode, scenario)
VALUES (%s, %s, %s)
RETURNING session_id
"""
INSERT_TURN_SQL = """
INSERT INTO turns (
    session_id, turn_number, transcript, target_sentence,
    grammar_errors, fluency_signals, intervention_type,
    tutor_response, accuracy_score
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""
CLOSE_SESSION_SQL = """
UPDATE sessions
SET ended_at = NOW(),
    fluency_score = %s,
    grammar_score = %s,
    task_completed = %s,
    top_errors = %s,
    recommended_next = %s,
    improvement_delta = %s
WHERE session_id = %s
"""
GET_LAST_SESSION_SQL = """
SELECT session_id, fluency_score, grammar_score, task_completed,
       top_errors, recommended_next, improvement_delta, ended_at
FROM sessions
WHERE learner_id = %s
ORDER BY started_at DESC
LIMIT 1
"""


def _get_db_url() -> str | None:
    """Load environment variables and return the Supabase database URL."""
    load_dotenv()
    return os.environ.get("SUPABASE_DB_URL")


def create_learner(display_name: str) -> str | None:
    """Insert a learner row and return the new learner ID."""
    db_url = _get_db_url()
    if not db_url:
        print("Database error in create_learner: SUPABASE_DB_URL is not set")
        return None

    conn = None
    try:
        conn = psycopg2.connect(db_url)
        with conn:
            with conn.cursor() as cur:
                cur.execute(CREATE_LEARNER_SQL, (display_name or "Learner",))
                row = cur.fetchone()
                return str(row[0]) if row else None
    except Exception as exc:
        print(f"Database error in create_learner: {exc}")
        return None
    finally:
        if conn is not None:
            conn.close()


def create_session(learner_id: str, mode: str, scenario: str | None) -> str | None:
    """Insert a session row and return the new session ID."""
    db_url = _get_db_url()
    if not db_url:
        print("Database error in create_session: SUPABASE_DB_URL is not set")
        return None

    conn = None
    try:
        conn = psycopg2.connect(db_url)
        with conn:
            with conn.cursor() as cur:
                cur.execute(CREATE_SESSION_SQL, (learner_id, mode, scenario))
                row = cur.fetchone()
                return str(row[0]) if row else None
    except Exception as exc:
        print(f"Database error in create_session: {exc}")
        return None
    finally:
        if conn is not None:
            conn.close()


def insert_turn(
    session_id: str,
    turn_number: int,
    transcript: str,
    target_sentence: str | None,
    grammar_errors: dict,
    fluency_signals: dict,
    intervention_type: str,
    tutor_response: str, accuracy_score: float | None,
) -> None:
    """Insert one turn for the current session."""
    db_url = _get_db_url()
    if not db_url:
        print("Database error in insert_turn: SUPABASE_DB_URL is not set")
        return None

    conn = None
    try:
        conn = psycopg2.connect(db_url)
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    INSERT_TURN_SQL,
                    (
                        session_id,
                        turn_number,
                        transcript,
                        target_sentence,
                        Json(grammar_errors),
                        Json(fluency_signals),
                        intervention_type,
                        tutor_response,
                        accuracy_score,
                    ),
                )
    except Exception as exc:
        print(f"Database error in insert_turn: {exc}")
    finally:
        if conn is not None:
            conn.close()


def close_session(
    session_id: str,
    fluency_score: float,
    grammar_score: float,
    task_completed: bool,
    top_errors: list,
    recommended_next: str,
    improvement_delta: dict,
) -> None:
    """Update a session with final analytics and mark it as ended."""
    db_url = _get_db_url()
    if not db_url:
        print("Database error in close_session: SUPABASE_DB_URL is not set")
        return None

    conn = None
    try:
        conn = psycopg2.connect(db_url)
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    CLOSE_SESSION_SQL,
                    (
                        fluency_score,
                        grammar_score,
                        task_completed,
                        Json(top_errors),
                        recommended_next,
                        Json(improvement_delta),
                        session_id,
                    ),
                )
    except Exception as exc:
        print(f"Database error in close_session: {exc}")
    finally:
        if conn is not None:
            conn.close()


def get_last_session(learner_id: str) -> dict | None:
    """Return the most recent session summary for a learner."""
    db_url = _get_db_url()
    if not db_url:
        print("Database error in get_last_session: SUPABASE_DB_URL is not set")
        return None

    conn = None
    try:
        conn = psycopg2.connect(db_url)
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(GET_LAST_SESSION_SQL, (learner_id,))
                row = cur.fetchone()
                return dict(row) if row else None
    except Exception as exc:
        print(f"Database error in get_last_session: {exc}")
        return None
    finally:
        if conn is not None:
            conn.close()
