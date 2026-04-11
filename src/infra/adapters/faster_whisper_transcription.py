"""FasterWhisperTranscriptionAdapter implementing TranscriptionPort.

Uses faster-whisper (CTranslate2-based) for local audio transcription.
Validates file size before processing, raises FileTooLargeError.
"""

from __future__ import annotations

import io

from domain.exceptions import FileTooLargeError, TranscriptionError

# Default max 10MB (same as GoogleTranscriptionAdapter)
DEFAULT_MAX_BYTES = 10 * 1024 * 1024

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None  # type: ignore[assignment,misc]


class FasterWhisperTranscriptionAdapter:
    """TranscriptionPort implementation using faster-whisper for local transcription."""

    def __init__(
        self,
        model_name: str,
        max_bytes: int = DEFAULT_MAX_BYTES,
    ) -> None:
        if WhisperModel is None:
            raise TranscriptionError("faster-whisper is not installed. Install it with: pip install faster-whisper")

        self._max_bytes = max_bytes

        try:
            self._model = WhisperModel(model_name, device="cpu", compute_type="int8")
        except ImportError as e:
            raise TranscriptionError(
                "faster-whisper is not installed. Install it with: pip install faster-whisper"
            ) from e
        except (ValueError, RuntimeError, OSError) as e:
            raise TranscriptionError(f"Failed to load Whisper model '{model_name}': {e}") from e

    def transcribe(self, audio_bytes: bytes, language: str = "es") -> str:
        """Convert audio bytes to text using faster-whisper.

        Validates size before processing. Raises FileTooLargeError if exceeded.
        """
        if len(audio_bytes) > self._max_bytes:
            raise FileTooLargeError(
                f"Audio file ({len(audio_bytes)} bytes) exceeds the size limit ({self._max_bytes} bytes)"
            )

        try:
            audio_stream = io.BytesIO(audio_bytes)
            segments, _info = self._model.transcribe(audio_stream, language=language)
            return "".join(segment.text for segment in segments).strip()
        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {e}") from e
