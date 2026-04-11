"""Unit tests for CacheService."""

from __future__ import annotations

from unittest.mock import mock_open, patch

from services.cache_service import check_cache, load_cache


@patch("os.path.exists")
def test_check_cache_found(mock_exists):
    """Verify check_cache correctly identifies an existing cache file."""
    # First call: audio_path exists
    # Second call: cache_path exists
    mock_exists.side_effect = [True, True]

    state = {"audio_name": "test.wav", "audio_path": "/path/test.wav", "context": "test context"}

    result = check_cache(state)

    assert result["cache_existe"] is True
    assert result["cache_path"] == "test.cache.json"
    assert result["context"] == "test context"


@patch("os.path.exists")
def test_check_cache_not_found(mock_exists):
    """Verify check_cache correctly identifies a missing cache file."""
    # Audio exists but cache doesn't
    mock_exists.side_effect = [True, False]

    state = {"audio_name": "test.wav", "audio_path": "/path/test.wav"}

    result = check_cache(state)

    assert result["cache_existe"] is False
    assert result["cache_path"] == "test.cache.json"


@patch("os.path.exists")
def test_check_cache_file_not_found_error(mock_exists):
    """Verify check_cache returns an error if the audio doesn't exist."""
    mock_exists.return_value = False

    state = {"audio_path": "/invalid/audio.wav"}

    result = check_cache(state)

    assert "error" in result
    assert "does not exist" in result["error"]


@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data='{"transcription": "Mocked transcription content"}',
)
def test_load_cache_success(mock_file):
    """Verify load_cache correctly reads and returns transcription data."""
    state = {"cache_path": "test.cache.json", "context": "Loaded context"}

    result = load_cache(state)

    assert result["transcription"] == "Mocked transcription content"
    assert result["context"] == "Loaded context"
    mock_file.assert_called_once_with("test.cache.json", encoding="utf-8")


@patch("builtins.open", side_effect=Exception("Read error"))
def test_load_cache_failure(mock_file):
    """Verify error handling when cache reading fails."""
    state = {"cache_path": "test.cache.json"}

    result = load_cache(state)

    assert "error" in result
    assert "Read error" in result["error"]
