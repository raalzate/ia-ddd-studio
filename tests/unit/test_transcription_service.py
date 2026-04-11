"""Unit tests for Whisper transcription service."""

from __future__ import annotations

from unittest.mock import MagicMock, mock_open, patch

import pytest

from services.transcription_service import transcribe_audio


@pytest.fixture
def mock_whisper():
    """Mock WhisperModel instance."""
    mock = MagicMock()
    # segments is an iterable of objects with .text and .end
    segment = MagicMock()
    segment.text = "Hello domain experts"
    segment.end = 10.0

    mock_info = MagicMock()
    mock_info.duration = 10.0

    mock.transcribe.return_value = ([segment], mock_info)
    return mock


@pytest.fixture
def mock_writer():
    """Mock writer instance."""
    return MagicMock()


@patch("services.transcription_service.load_whisper_model")
@patch("services.transcription_service.load_writer")
@patch("builtins.open", new_callable=mock_open)
def test_transcribe_audio_success(mock_file, mock_writer_loader, mock_whisper_loader, mock_whisper, mock_writer):
    """Verify transcription flow from audio to JSON cache."""
    mock_whisper_loader.return_value = mock_whisper
    mock_writer_loader.return_value = mock_writer

    state = {
        "audio_path": "test.wav",
        "cache_path": "test.cache.json",
        "context": "Workshop context",
        "has_refine": True,
    }

    # transcribe_audio is a generator
    result_iter = transcribe_audio(state)
    result = next(result_iter)

    assert "transcription" in result
    assert result["transcription"] == "Hello domain experts"
    assert result["has_refine"] is True

    # Check that Whisper was called
    mock_whisper.transcribe.assert_called_once_with("test.wav", beam_size=5)

    # Check that writer was called for progress
    assert mock_writer.called

    # Check that cache was saved
    mock_file.assert_called_once_with("test.cache.json", "w", encoding="utf-8")


@patch("services.transcription_service.load_whisper_model")
@patch("services.transcription_service.load_writer")
def test_transcribe_audio_failure(mock_writer_loader, mock_whisper_loader, mock_whisper, mock_writer):
    """Verify error handling when transcription fails."""
    mock_whisper_loader.return_value = mock_whisper
    mock_writer_loader.return_value = mock_writer

    # Force failure
    mock_whisper.transcribe.side_effect = Exception("Whisper error")

    state = {"audio_path": "fail.wav"}

    result_iter = transcribe_audio(state)
    result = next(result_iter)

    assert "error" in result
    assert "Whisper error" in result["error"]
