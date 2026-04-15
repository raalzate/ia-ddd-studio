"""Application layer entry points: run_analysis and stream_analysis.

Invocable without any UI framework. Accepts port instances via DI.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from application.graph_builder import build_audio_graph, build_text_graph
from domain.events import ErrorEvent, ProgressEvent
from models.domain_analysis import DomainAnalysis
from pydantic import BaseModel, Field, model_validator


class AnalysisRequest(BaseModel):
    """Input to the agent pipeline."""

    transcript: str | None = None
    audio_bytes: bytes | None = None
    audio_name: str | None = None
    context: str | None = None
    language: str = "es"

    @model_validator(mode="after")
    def require_input(self) -> AnalysisRequest:
        if not self.transcript and not self.audio_bytes:
            raise ValueError("Either transcript or audio_bytes must be provided")
        return self


class AnalysisResult(BaseModel):
    """Output from the agent pipeline."""

    analysis: DomainAnalysis
    transcript: str
    specs: dict | None = None
    events: list[ProgressEvent] = Field(default_factory=list)
    errors: list[ErrorEvent] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


class _EventCollector:
    """Collects events emitted during pipeline execution."""

    def __init__(self, forward_to: Callable | None = None) -> None:
        self.events: list[ProgressEvent] = []
        self.errors: list[ErrorEvent] = []
        self._forward = forward_to

    def __call__(self, event: ProgressEvent | ErrorEvent) -> None:
        if isinstance(event, ErrorEvent):
            self.errors.append(event)
        elif isinstance(event, ProgressEvent):
            self.events.append(event)
        if self._forward:
            self._forward(event)


_STATE_DEFAULTS = {
    "audio_path": None,
    "audio_name": None,
    "transcript": None,
    "context": None,
    "analysis": None,
    "specs": None,
    "has_refine": False,
    "cache_path": None,
    "cache_exists": False,
    "error": None,
}


def run_analysis(
    request: AnalysisRequest,
    inference: Any,
    cache: Any | None = None,
    transcription: Any | None = None,
    emitter: Any | None = None,
) -> AnalysisResult:
    """Run the agent pipeline synchronously.

    Args:
        request: Analysis request with either transcript or audio.
        inference: InferencePort implementation.
        cache: CachePort implementation (optional).
        transcription: TranscriptionPort implementation (required for audio).
        emitter: EventEmitter implementation (optional).

    Returns:
        AnalysisResult with analysis, transcript, specs, and events.
    """
    collector = _EventCollector(forward_to=emitter)

    if request.transcript:
        initial_state = {
            **_STATE_DEFAULTS,
            "transcript": request.transcript,
            "context": request.context or "",
            "has_refine": bool(request.context),
        }
        graph = build_text_graph(inference=inference, cache=cache, emitter=collector)
    else:
        import os
        import tempfile

        fd, audio_path = tempfile.mkstemp(suffix=f"_{request.audio_name or 'audio'}")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(request.audio_bytes)

            initial_state = {
                **_STATE_DEFAULTS,
                "audio_path": audio_path,
                "audio_name": request.audio_name or "audio",
                "context": request.context or "",
            }
            graph = build_audio_graph(
                inference=inference,
                transcription=transcription,
                cache=cache,
                emitter=collector,
            )
        except Exception:
            os.unlink(audio_path)
            raise

    result_state = graph.invoke(initial_state)

    return AnalysisResult(
        analysis=result_state["analysis"],
        transcript=result_state.get("transcript", request.transcript or ""),
        specs=result_state.get("specs"),
        events=collector.events,
        errors=collector.errors,
    )


def stream_analysis(
    request: AnalysisRequest,
    inference: Any,
    cache: Any | None = None,
    transcription: Any | None = None,
    on_event: Callable | None = None,
) -> AnalysisResult:
    """Run the agent pipeline with event streaming."""
    return run_analysis(
        request=request,
        inference=inference,
        cache=cache,
        transcription=transcription,
        emitter=on_event,
    )
