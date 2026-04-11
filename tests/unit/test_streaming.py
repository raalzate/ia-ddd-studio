"""Unit tests for src/infra/streaming.py — NullEventEmitter."""

from domain.events import ErrorEvent, ProgressEvent
from infra.streaming import NullEventEmitter


def test_null_event_emitter_accepts_progress_event():
    emitter = NullEventEmitter()
    event = ProgressEvent(node_name="test_node", message="processing", checkpoint="start")
    emitter(event)  # Should not raise


def test_null_event_emitter_accepts_error_event():
    emitter = NullEventEmitter()
    event = ErrorEvent(
        node_name="test_node",
        message="error occurred",
        error_type="validation",
        recoverable=True,
    )
    emitter(event)  # Should not raise


def test_null_event_emitter_is_callable():
    emitter = NullEventEmitter()
    assert callable(emitter)


def test_null_event_emitter_returns_none():
    emitter = NullEventEmitter()
    result = emitter(ProgressEvent(node_name="x", message="y", checkpoint="z"))
    assert result is None
