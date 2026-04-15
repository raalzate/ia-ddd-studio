"""Transcription node using TranscriptionPort.

Accepts typed state, returns typed partial update with transcript.
"""

from __future__ import annotations

from typing import Any

from domain.events import ErrorEvent, ProgressEvent
from domain.models.agent_state import NodeContract

CONTRACT = NodeContract(
    node_name="transcribe",
    required_inputs=["audio_path"],
    produced_outputs=["transcript"],
    emits_events=["transcription_start", "transcription_complete"],
)


def _noop_emitter(event: Any) -> None:
    pass


def transcribe(
    state: dict[str, Any],
    *,
    transcription: Any,
    cache: Any = None,
    emitter: Any = None,
) -> dict[str, Any]:
    """Transcribe audio using the injected TranscriptionPort."""
    emit = emitter or _noop_emitter
    emit(
        ProgressEvent(
            checkpoint="transcription_start",
            node_name="transcribe",
            message="Iniciando transcripción",
        )
    )

    audio_path = state.get("audio_path", "")

    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        text = transcription.transcribe(audio_bytes)
    except Exception as e:
        error_type = "validation" if "too large" in str(e).lower() or "size" in str(e).lower() else "service"
        emit(ErrorEvent(node_name="transcribe", error_type=error_type, message=str(e), recoverable=False))
        return {"error": str(e)}

    # Persist transcription in cache for future runs
    cache_path = state.get("cache_path")
    if cache is not None and cache_path:
        cache.set(cache_path, text)

    emit(
        ProgressEvent(
            checkpoint="transcription_complete",
            node_name="transcribe",
            message="Transcripción completa",
        )
    )
    return {"transcript": text}
