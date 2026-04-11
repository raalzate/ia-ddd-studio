"""Unit tests for FileCacheAdapter."""

from __future__ import annotations

import os

from infra.adapters.file_cache import FileCacheAdapter


def test_file_cache_initialization(tmp_path):
    """Verify FileCacheAdapter creates the cache directory."""
    cache_dir = tmp_path / ".test_cache"
    adapter = FileCacheAdapter(str(cache_dir))
    assert os.path.exists(str(cache_dir))
    assert adapter._cache_dir == str(cache_dir)


def test_file_cache_set_and_get(tmp_path):
    """Verify set and get roundtrip."""
    adapter = FileCacheAdapter(str(tmp_path))
    key = "workshop_audio_123"
    value = "Detailed transcription of the event storming session."

    adapter.set(key, value)

    # Verify file exists
    files = list(tmp_path.glob("*.cache.json"))
    assert len(files) == 1

    # Retrieve
    retrieved = adapter.get(key)
    assert retrieved == value


def test_file_cache_get_nonexistent(tmp_path):
    """Verify get returns None for missing keys."""
    adapter = FileCacheAdapter(str(tmp_path))
    assert adapter.get("missing_key") is None


def test_file_cache_overwrite(tmp_path):
    """Verify set overwrites existing keys."""
    adapter = FileCacheAdapter(str(tmp_path))
    key = "key1"
    adapter.set(key, "first")
    adapter.set(key, "second")

    assert adapter.get(key) == "second"
