"""GoogleTranscriptionAdapter implementing TranscriptionPort.

Validates file size before upload, raises FileTooLargeError.
"""

from __future__ import annotations

from domain.exceptions import FileTooLargeError, TranscriptionError

# Default max 10MB
DEFAULT_MAX_BYTES = 10 * 1024 * 1024


class GoogleTranscriptionAdapter:
    """TranscriptionPort implementation using Google Cloud Speech / Gemini multimodal."""

    def __init__(self, max_bytes: int = DEFAULT_MAX_BYTES) -> None:
        self._max_bytes = max_bytes

    def transcribe(self, audio_bytes: bytes, language: str = "es") -> str:
        """Convert audio bytes to text.

        Validates size before upload. Raises FileTooLargeError if exceeded.
        """
        if len(audio_bytes) > self._max_bytes:
            raise FileTooLargeError(
                f"Audio file ({len(audio_bytes)} bytes) exceeds the service size limit ({self._max_bytes} bytes)"
            )

        try:
            # TODO: Implement actual Google Cloud Speech-to-Text API call
            # For now, this is a placeholder that will be wired in integration
            raise NotImplementedError("GoogleTranscriptionAdapter.transcribe requires Google Cloud Speech API setup")
        except NotImplementedError:
            raise
        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {e}") from e
