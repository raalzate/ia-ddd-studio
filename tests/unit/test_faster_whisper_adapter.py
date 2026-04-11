"""Unit tests for FasterWhisperTranscriptionAdapter.

Covers: TS-001, TS-002, TS-003, TS-004, TS-005, TS-016
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from domain.exceptions import FileTooLargeError, TranscriptionError

# ---------------------------------------------------------------------------
# TS-001: Local transcription activated when WHISPER_MODEL is set
# ---------------------------------------------------------------------------


class TestFasterWhisperAdapterInit:
    """Tests for adapter construction and model loading."""

    def test_adapter_creates_with_valid_model_name(self):
        """TS-001: Adapter constructs successfully with a valid model name."""
        from infra.adapters.faster_whisper_transcription import (
            FasterWhisperTranscriptionAdapter,
        )

        with patch("infra.adapters.faster_whisper_transcription.WhisperModel") as mock_whisper:
            mock_whisper.return_value = MagicMock()
            adapter = FasterWhisperTranscriptionAdapter(model_name="base")
            assert adapter is not None


# ---------------------------------------------------------------------------
# TS-002: Local transcription succeeds for valid model names
# ---------------------------------------------------------------------------


class TestFasterWhisperTranscribe:
    """Tests for the transcribe() method."""

    def test_transcribe_returns_plain_text(self):
        """TS-002: transcribe() returns a non-empty plain text string."""
        from infra.adapters.faster_whisper_transcription import (
            FasterWhisperTranscriptionAdapter,
        )

        mock_segment_1 = MagicMock()
        mock_segment_1.text = "Hola mundo"
        mock_segment_2 = MagicMock()
        mock_segment_2.text = " esto es una prueba"

        mock_model = MagicMock()
        mock_model.transcribe.return_value = (
            iter([mock_segment_1, mock_segment_2]),
            MagicMock(),  # info
        )

        with patch(
            "infra.adapters.faster_whisper_transcription.WhisperModel",
            return_value=mock_model,
        ):
            adapter = FasterWhisperTranscriptionAdapter(model_name="base")
            result = adapter.transcribe(b"fake-audio-bytes", language="es")

        assert isinstance(result, str)
        assert len(result) > 0
        assert "Hola mundo" in result
        assert "esto es una prueba" in result

    def test_transcribe_passes_language_parameter(self):
        """TS-002: Language parameter is forwarded to whisper model."""
        from infra.adapters.faster_whisper_transcription import (
            FasterWhisperTranscriptionAdapter,
        )

        mock_segment = MagicMock()
        mock_segment.text = "test"

        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter([mock_segment]), MagicMock())

        with patch(
            "infra.adapters.faster_whisper_transcription.WhisperModel",
            return_value=mock_model,
        ):
            adapter = FasterWhisperTranscriptionAdapter(model_name="base")
            adapter.transcribe(b"fake-audio", language="en")

        mock_model.transcribe.assert_called_once()
        call_kwargs = mock_model.transcribe.call_args
        assert call_kwargs[1].get("language") == "en" or call_kwargs[0][1:] == ("en",)


# ---------------------------------------------------------------------------
# TS-003: Transcript compatible with downstream analysis
# ---------------------------------------------------------------------------


class TestTranscriptFormat:
    """Tests for output format compatibility."""

    def test_transcript_is_plain_text_no_timestamps(self):
        """TS-003: Output is plain text with no timestamps or metadata."""
        from infra.adapters.faster_whisper_transcription import (
            FasterWhisperTranscriptionAdapter,
        )

        mock_segment = MagicMock()
        mock_segment.text = "Texto limpio sin marcas de tiempo"

        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter([mock_segment]), MagicMock())

        with patch(
            "infra.adapters.faster_whisper_transcription.WhisperModel",
            return_value=mock_model,
        ):
            adapter = FasterWhisperTranscriptionAdapter(model_name="base")
            result = adapter.transcribe(b"fake-audio", language="es")

        # No timestamp patterns like [00:00:00] or 0.0 - 1.5
        import re

        assert not re.search(r"\[\d{2}:\d{2}", result)
        assert not re.search(r"\d+\.\d+\s*-\s*\d+\.\d+", result)


# ---------------------------------------------------------------------------
# TS-004: Invalid model name produces a clear error
# ---------------------------------------------------------------------------


class TestInvalidModelName:
    """Tests for invalid model name handling."""

    def test_invalid_model_raises_transcription_error(self):
        """TS-004: Invalid model name raises TranscriptionError."""
        from infra.adapters.faster_whisper_transcription import (
            FasterWhisperTranscriptionAdapter,
        )

        with patch(
            "infra.adapters.faster_whisper_transcription.WhisperModel",
            side_effect=ValueError("Invalid model name: nonexistent-model"),
        ):
            with pytest.raises(TranscriptionError, match="nonexistent-model"):
                FasterWhisperTranscriptionAdapter(model_name="nonexistent-model")


# ---------------------------------------------------------------------------
# TS-005: Missing faster-whisper package produces a clear error
# ---------------------------------------------------------------------------


class TestMissingPackage:
    """Tests for missing faster-whisper package."""

    def test_missing_package_raises_transcription_error(self):
        """TS-005: Missing faster-whisper raises TranscriptionError with install instructions."""
        from infra.adapters.faster_whisper_transcription import (
            FasterWhisperTranscriptionAdapter,
        )

        with patch(
            "infra.adapters.faster_whisper_transcription.WhisperModel",
            side_effect=ImportError("No module named 'faster_whisper'"),
        ):
            with pytest.raises(TranscriptionError, match="faster-whisper"):
                FasterWhisperTranscriptionAdapter(model_name="base")


# ---------------------------------------------------------------------------
# TS-016: Audio exceeding size limit raises FileTooLargeError
# ---------------------------------------------------------------------------


class TestFileSizeLimit:
    """Tests for file size validation."""

    def test_oversized_audio_raises_file_too_large_error(self):
        """TS-016: Audio exceeding max_bytes raises FileTooLargeError."""
        from infra.adapters.faster_whisper_transcription import (
            FasterWhisperTranscriptionAdapter,
        )

        mock_model = MagicMock()

        with patch(
            "infra.adapters.faster_whisper_transcription.WhisperModel",
            return_value=mock_model,
        ):
            adapter = FasterWhisperTranscriptionAdapter(model_name="base", max_bytes=100)

        oversized_audio = b"x" * 200
        with pytest.raises(FileTooLargeError, match="200"):
            adapter.transcribe(oversized_audio)

    def test_audio_within_limit_succeeds(self):
        """TS-016: Audio within limit does not raise."""
        from infra.adapters.faster_whisper_transcription import (
            FasterWhisperTranscriptionAdapter,
        )

        mock_segment = MagicMock()
        mock_segment.text = "ok"

        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter([mock_segment]), MagicMock())

        with patch(
            "infra.adapters.faster_whisper_transcription.WhisperModel",
            return_value=mock_model,
        ):
            adapter = FasterWhisperTranscriptionAdapter(model_name="base", max_bytes=1000)

        result = adapter.transcribe(b"x" * 100, language="es")
        assert result == "ok"
