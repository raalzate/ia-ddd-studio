"""FileCacheAdapter implementing CachePort.

SHA-256 key derivation, JSON storage. Supports both transcription strings
and arbitrary JSON-serializable payloads (used for analysis cache).
"""

from __future__ import annotations

import json
import os
from typing import Any


class FileCacheAdapter:
    """CachePort implementation using file-based JSON storage."""

    def __init__(self, cache_dir: str = ".cache") -> None:
        self._cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _key_path(self, key: str) -> str:
        return os.path.join(self._cache_dir, f"{key}.cache.json")

    def _json_path(self, key: str) -> str:
        return os.path.join(self._cache_dir, f"{key}.json")

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

    def get_json(self, key: str) -> dict[str, Any] | None:
        """Retrieve cached JSON payload by key. Used for analysis cache."""
        path = self._json_path(key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def set_json(self, key: str, value: dict[str, Any]) -> None:
        """Store a JSON payload by key. Used for analysis cache."""
        path = self._json_path(key)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False)
        os.replace(tmp, path)
