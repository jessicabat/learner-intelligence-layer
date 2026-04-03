"""Audio transcription helpers built on faster-whisper."""

from __future__ import annotations

import os
from typing import Any

try:
    import streamlit as st
except ImportError:  # pragma: no cover - used only in minimal test environments
    class _StreamlitFallback:
        """Fallback object that preserves the cache_resource decorator interface."""

        @staticmethod
        def cache_resource(func: Any) -> Any:
            """Return the wrapped function unchanged when Streamlit is unavailable."""
            return func

    st = _StreamlitFallback()

try:
    from faster_whisper import WhisperModel
except ImportError:  # pragma: no cover - exercised via _load_model fallback
    WhisperModel = None  # type: ignore[assignment]


@st.cache_resource
def _load_model() -> Any:
    """Load and cache the faster-whisper base model for transcription."""
    if WhisperModel is None:
        raise ImportError("faster-whisper is not installed")

    return WhisperModel("base", device="cpu", compute_type="int8")


def transcribe_audio(path: str) -> str:
    """Return a transcript for the audio file at ``path`` or an empty string."""
    if not path or not os.path.isfile(path):
        return ""

    try:
        model = _load_model()
    except Exception:
        return ""

    try:
        segments, _ = model.transcribe(path)
        transcript = " ".join(
            segment.text.strip() for segment in segments if getattr(segment, "text", "").strip()
        )
    except Exception:
        return ""

    return transcript.strip()
