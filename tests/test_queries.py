"""Tests for the PostgreSQL query helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from db import queries


def _make_connection(
    fetchone_result: object | None = None,
    execute_side_effect: Exception | None = None,
) -> tuple[MagicMock, MagicMock]:
    """Build a mocked psycopg2 connection and cursor pair."""
    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = False

    cursor = MagicMock()
    cursor.fetchone.return_value = fetchone_result
    if execute_side_effect is not None:
        cursor.execute.side_effect = execute_side_effect

    cursor_manager = MagicMock()
    cursor_manager.__enter__.return_value = cursor
    cursor_manager.__exit__.return_value = False
    conn.cursor.return_value = cursor_manager
    return conn, cursor


def test_create_learner_returns_id_and_closes_connection() -> None:
    """Successful learner creation should return the UUID string and close the connection."""
    conn, cursor = _make_connection(fetchone_result=("learner-123",))

    with patch("db.queries.load_dotenv"), patch(
        "db.queries.os.environ.get", return_value="postgres://db-url"
    ), patch("db.queries.psycopg2.connect", return_value=conn):
        learner_id = queries.create_learner("Ada")

    assert learner_id == "learner-123"
    cursor.execute.assert_called_once_with(
        "INSERT INTO learners (display_name) VALUES (%s) RETURNING learner_id",
        ("Ada",),
    )
    conn.close.assert_called_once()


def test_create_session_returns_none_when_env_missing() -> None:
    """Missing DB configuration should return None without opening a connection."""
    with patch("db.queries.load_dotenv"), patch(
        "db.queries.os.environ.get", return_value=None
    ), patch("db.queries.psycopg2.connect") as mock_connect, patch("builtins.print") as mock_print:
        session_id = queries.create_session("learner-123", "repeat", None)

    assert session_id is None
    mock_connect.assert_not_called()
    mock_print.assert_called_once()


def test_create_session_returns_none_and_logs_on_db_error() -> None:
    """Database exceptions should be caught and logged for session creation."""
    conn, _ = _make_connection()
    conn.cursor.side_effect = RuntimeError("boom")

    with patch("db.queries.load_dotenv"), patch(
        "db.queries.os.environ.get", return_value="postgres://db-url"
    ), patch("db.queries.psycopg2.connect", return_value=conn), patch("builtins.print") as mock_print:
        session_id = queries.create_session("learner-123", "roleplay", "interview")

    assert session_id is None
    conn.close.assert_called_once()
    mock_print.assert_called_once()


def test_insert_turn_uses_parameterized_query_and_json_wrappers() -> None:
    """Turn inserts should wrap JSONB fields with Json and keep SQL parameterized."""
    conn, cursor = _make_connection()

    with patch("db.queries.load_dotenv"), patch(
        "db.queries.os.environ.get", return_value="postgres://db-url"
    ), patch("db.queries.psycopg2.connect", return_value=conn):
        queries.insert_turn(
            session_id="session-123",
            turn_number=2,
            transcript="hello there",
            target_sentence="hello there",
            grammar_errors={"article": 1},
            fluency_signals={"hesitation_rate": 0.2},
            intervention_type="continue",
            tutor_response="Nice work.",
            accuracy_score=98.0,
        )

    sql, params = cursor.execute.call_args[0]
    assert "%s" in sql
    assert params[0:4] == ("session-123", 2, "hello there", "hello there")
    assert getattr(params[4], "adapted", None) == {"article": 1}
    assert getattr(params[5], "adapted", None) == {"hesitation_rate": 0.2}
    assert params[6:] == ("continue", "Nice work.", 98.0)
    conn.close.assert_called_once()


def test_close_session_uses_json_wrappers_and_closes_connection() -> None:
    """Session close updates should serialize JSONB values and close the connection."""
    conn, cursor = _make_connection()

    with patch("db.queries.load_dotenv"), patch(
        "db.queries.os.environ.get", return_value="postgres://db-url"
    ), patch("db.queries.psycopg2.connect", return_value=conn):
        queries.close_session(
            session_id="session-123",
            fluency_score=85.0,
            grammar_score=90.0,
            task_completed=True,
            top_errors=["article"],
            recommended_next="Practice articles.",
            improvement_delta={"grammar": 5},
        )

    sql, params = cursor.execute.call_args[0]
    assert "UPDATE sessions" in sql
    assert "%s" in sql
    assert params[0:3] == (85.0, 90.0, True)
    assert getattr(params[3], "adapted", None) == ["article"]
    assert params[4] == "Practice articles."
    assert getattr(params[5], "adapted", None) == {"grammar": 5}
    assert params[6] == "session-123"
    conn.close.assert_called_once()


def test_get_last_session_returns_dict_and_uses_real_dict_cursor() -> None:
    """The latest session lookup should use RealDictCursor and return a dict."""
    row = {
        "session_id": "session-123",
        "fluency_score": 80.0,
        "grammar_score": 75.0,
        "task_completed": True,
        "top_errors": ["tense"],
        "recommended_next": "Practice tense consistency.",
        "improvement_delta": {"fluency": 3},
        "ended_at": "2026-04-03T15:00:00",
    }
    conn, cursor = _make_connection(fetchone_result=row)

    with patch("db.queries.load_dotenv"), patch(
        "db.queries.os.environ.get", return_value="postgres://db-url"
    ), patch("db.queries.psycopg2.connect", return_value=conn):
        result = queries.get_last_session("learner-123")

    assert result == row
    assert conn.cursor.call_args.kwargs["cursor_factory"] is queries.RealDictCursor
    cursor.execute.assert_called_once()
    conn.close.assert_called_once()


def test_get_last_session_returns_none_on_no_row() -> None:
    """A learner with no sessions should get None."""
    conn, _ = _make_connection(fetchone_result=None)

    with patch("db.queries.load_dotenv"), patch(
        "db.queries.os.environ.get", return_value="postgres://db-url"
    ), patch("db.queries.psycopg2.connect", return_value=conn):
        result = queries.get_last_session("learner-123")

    assert result is None
    conn.close.assert_called_once()


def test_insert_turn_logs_error_and_still_closes_connection() -> None:
    """Turn insert failures should be swallowed after logging and cleanup."""
    conn, _ = _make_connection(execute_side_effect=RuntimeError("write failed"))

    with patch("db.queries.load_dotenv"), patch(
        "db.queries.os.environ.get", return_value="postgres://db-url"
    ), patch("db.queries.psycopg2.connect", return_value=conn), patch("builtins.print") as mock_print:
        result = queries.insert_turn(
            session_id="session-123",
            turn_number=1,
            transcript="hi",
            target_sentence=None,
            grammar_errors={},
            fluency_signals={},
            intervention_type="continue",
            tutor_response="Hello",
            accuracy_score=None,
        )

    assert result is None
    conn.close.assert_called_once()
    mock_print.assert_called_once()
