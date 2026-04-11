"""FileCacheAdapter implementing CachePort.

SHA-256 key derivation, JSON storage.
"""

from __future__ import annotations

import hashlib
import json
import os


class FileCacheAdapter:
    """CachePort implementation using file-based JSON storage."""

    def __init__(self, cache_dir: str = ".cache") -> None:
        self._cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _key_path(self, key: str) -> str:
        # Key is already a hex-safe hash from the caller; use it directly.
        return os.path.join(self._cache_dir, f"{key}.cache.json")

    def get(self, key: str) -> str | None:
        """Retrieve cached transcription by key."""
        path = self._key_path(key)
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("transcription")

    def set(self, key: str, value: str) -> None:
        """Store transcription in cache."""
        path = self._key_path(key)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"transcription": value}, f, ensure_ascii=False)
