"""Tests for error handling: FileTooLargeError raised before upload.

[TS-016]
"""

import pytest

pytestmark = pytest.mark.offline

from domain.exceptions import FileTooLargeError


class TestFileTooLargeError:
    """[TS-016] FileTooLargeError raised before upload when audio exceeds size limit."""

    def test_google_transcription_adapter_raises_on_oversized_file(self):
        from infra.adapters.google_transcription import GoogleTranscriptionAdapter

        adapter = GoogleTranscriptionAdapter(max_bytes=100)
        oversized_audio = b"x" * 200

        with pytest.raises(FileTooLargeError):
            adapter.transcribe(oversized_audio)

    def test_file_too_large_error_is_exception(self):
        assert issubclass(FileTooLargeError, Exception)

    def test_error_message_is_descriptive(self):
        from infra.adapters.google_transcription import GoogleTranscriptionAdapter

        adapter = GoogleTranscriptionAdapter(max_bytes=100)

        with pytest.raises(FileTooLargeError, match="exceeds.*limit"):
            adapter.transcribe(b"x" * 200)
