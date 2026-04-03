"""Tests for the faster-whisper transcription wrapper."""

from types import SimpleNamespace
from unittest.mock import patch

from core.transcriber import transcribe_audio


def test_transcribe_audio_returns_empty_for_empty_path() -> None:
    """An empty path should return an empty transcript."""
    assert transcribe_audio("") == ""


def test_transcribe_audio_returns_empty_for_missing_file() -> None:
    """A missing file should return an empty transcript."""
    with patch("core.transcriber.os.path.isfile", return_value=False):
        assert transcribe_audio("missing.webm") == ""


def test_transcribe_audio_returns_empty_when_model_load_fails() -> None:
    """Model load failures should return an empty transcript."""
    with patch("core.transcriber.os.path.isfile", return_value=True):
        with patch("core.transcriber._load_model", side_effect=RuntimeError("load failed")):
            assert transcribe_audio("sample.webm") == ""


def test_transcribe_audio_returns_joined_segment_text() -> None:
    """Successful transcription should join segment text into one string."""
    segments = [
        SimpleNamespace(text=" hello "),
        SimpleNamespace(text="world"),
        SimpleNamespace(text=" "),
    ]

    with patch("core.transcriber.os.path.isfile", return_value=True):
        with patch("core.transcriber._load_model") as mock_load_model:
            mock_load_model.return_value.transcribe.return_value = (segments, SimpleNamespace())
            assert transcribe_audio("sample.webm") == "hello world"


def test_transcribe_audio_returns_empty_when_transcription_fails() -> None:
    """Transcription errors should return an empty transcript."""
    with patch("core.transcriber.os.path.isfile", return_value=True):
        with patch("core.transcriber._load_model") as mock_load_model:
            mock_load_model.return_value.transcribe.side_effect = RuntimeError("transcribe failed")
            assert transcribe_audio("sample.webm") == ""
