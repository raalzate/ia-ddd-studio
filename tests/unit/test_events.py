"""Unit tests for ProgressEvent and ErrorEvent models.

Tests:
- Required fields present
- Timestamp auto-generation
- Event type discrimination
"""

from datetime import datetime

import pytest

pytestmark = pytest.mark.offline


class TestProgressEvent:
    """Verify ProgressEvent model per data-model.md."""

    def test_progress_event_required_fields(self):
        from domain.events import ProgressEvent

        event = ProgressEvent(
            checkpoint="transcription_start",
            node_name="transcribe",
            message="Starting transcription",
        )
        assert event.checkpoint == "transcription_start"
        assert event.node_name == "transcribe"
        assert event.message == "Starting transcription"

    def test_progress_event_timestamp_auto_generated(self):
        from domain.events import ProgressEvent

        before = datetime.now()
        event = ProgressEvent(
            checkpoint="analysis_start",
            node_name="analyze_semantics",
            message="Starting analysis",
        )
        after = datetime.now()
        assert before <= event.timestamp <= after

    def test_progress_event_percentage_optional(self):
        from domain.events import ProgressEvent

        event = ProgressEvent(
            checkpoint="analysis_start",
            node_name="analyze_semantics",
            message="Starting",
        )
        assert event.percentage is None

        event_with_pct = ProgressEvent(
            checkpoint="analysis_start",
            node_name="analyze_semantics",
            message="Starting",
            percentage=0.5,
        )
        assert event_with_pct.percentage == 0.5


class TestErrorEvent:
    """Verify ErrorEvent model per data-model.md."""

    def test_error_event_required_fields(self):
        from domain.events import ErrorEvent

        event = ErrorEvent(
            node_name="transcribe",
            error_type="service",
            message="Service unavailable",
            recoverable=False,
        )
        assert event.node_name == "transcribe"
        assert event.error_type == "service"
        assert event.message == "Service unavailable"
        assert event.recoverable is False

    def test_error_event_timestamp_auto_generated(self):
        from domain.events import ErrorEvent

        before = datetime.now()
        event = ErrorEvent(
            node_name="analyze_semantics",
            error_type="validation",
            message="Schema mismatch",
            recoverable=True,
        )
        after = datetime.now()
        assert before <= event.timestamp <= after

    def test_progress_and_error_events_are_distinguishable(self):
        from domain.events import ErrorEvent, ProgressEvent

        progress = ProgressEvent(checkpoint="start", node_name="n", message="m")
        error = ErrorEvent(node_name="n", error_type="t", message="m", recoverable=True)
        assert isinstance(progress, ProgressEvent)
        assert isinstance(error, ErrorEvent)
        assert not isinstance(progress, ErrorEvent)
        assert not isinstance(error, ProgressEvent)
