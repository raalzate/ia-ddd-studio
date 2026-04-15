"""Event emitter implementations.

NullEventEmitter (no-op) and LangGraph stream_writer bridge.
"""

from __future__ import annotations

from domain.events import ErrorEvent, ProgressEvent


class NullEventEmitter:
    """No-op EventEmitter for headless/batch execution."""

    def __call__(self, event: ProgressEvent | ErrorEvent) -> None:
        pass
