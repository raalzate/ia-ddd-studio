"""Contract test: FasterWhisperTranscriptionAdapter satisfies TranscriptionPort.

Covers: TS-015
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from domain.ports import TranscriptionPort


class TestTranscriptionPortConformance:
    """Verify adapter satisfies the TranscriptionPort protocol at runtime."""

    def test_faster_whisper_adapter_is_transcription_port(self):
        """TS-015: FasterWhisperTranscriptionAdapter passes isinstance check."""
        from infra.adapters.faster_whisper_transcription import (
            FasterWhisperTranscriptionAdapter,
        )

        mock_model = MagicMock()
        with patch(
            "infra.adapters.faster_whisper_transcription.WhisperModel",
            return_value=mock_model,
        ):
            adapter = FasterWhisperTranscriptionAdapter(model_name="base")

        assert isinstance(adapter, TranscriptionPort)

    def test_google_adapter_is_transcription_port(self):
        """Verify GoogleTranscriptionAdapter also satisfies TranscriptionPort."""
        from infra.adapters.google_transcription import GoogleTranscriptionAdapter

        adapter = GoogleTranscriptionAdapter()
        assert isinstance(adapter, TranscriptionPort)

    def test_adapter_has_transcribe_method(self):
        """TS-015: Adapter has transcribe(audio_bytes, language) -> str signature."""
        from infra.adapters.faster_whisper_transcription import (
            FasterWhisperTranscriptionAdapter,
        )

        mock_model = MagicMock()
        with patch(
            "infra.adapters.faster_whisper_transcription.WhisperModel",
            return_value=mock_model,
        ):
            adapter = FasterWhisperTranscriptionAdapter(model_name="base")

        assert hasattr(adapter, "transcribe")
        assert callable(adapter.transcribe)
