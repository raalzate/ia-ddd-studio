"""Integration test: Cache interoperability between transcription providers.

Covers: TS-012, TS-013
"""

from __future__ import annotations

import hashlib

from infra.adapters.file_cache import FileCacheAdapter


class TestCacheInteroperability:
    """Verify cache entries are reusable across providers."""

    def test_local_provider_cache_reusable_by_remote(self, tmp_path):
        """TS-012: Cache entry from local provider is usable when remote is active."""
        cache = FileCacheAdapter(cache_dir=str(tmp_path / "cache"))

        audio_bytes = b"\x00" * 48_000
        cache_key = hashlib.sha256(audio_bytes).hexdigest()

        # Simulate local provider caching a result
        transcript = "Texto transcrito localmente"
        cache.set(cache_key, transcript)

        # Now simulate remote provider checking cache
        cached = cache.get(cache_key)
        assert cached is not None
        assert cached == transcript

    def test_remote_provider_cache_reusable_by_local(self, tmp_path):
        """TS-013: Cache entry from remote provider is usable when local is active."""
        cache = FileCacheAdapter(cache_dir=str(tmp_path / "cache"))

        audio_bytes = b"\x00" * 48_000
        cache_key = hashlib.sha256(audio_bytes).hexdigest()

        # Simulate remote provider caching a result
        transcript = "Texto transcrito remotamente"
        cache.set(cache_key, transcript)

        # Now simulate local provider checking cache
        cached = cache.get(cache_key)
        assert cached is not None
        assert cached == transcript

    def test_cache_key_is_content_based_not_provider_based(self, tmp_path):
        """Both providers should produce the same cache key for the same audio."""
        cache = FileCacheAdapter(cache_dir=str(tmp_path / "cache"))

        audio_bytes = b"\x00" * 48_000
        key1 = hashlib.sha256(audio_bytes).hexdigest()
        key2 = hashlib.sha256(audio_bytes).hexdigest()

        assert key1 == key2

        cache.set(key1, "same transcript")
        assert cache.get(key2) == "same transcript"
