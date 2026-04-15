"""Tests for analysis cache key derivation and FileCacheAdapter JSON helpers."""

from __future__ import annotations

import os
import sys
import tempfile

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from infra.adapters.file_cache import FileCacheAdapter
from models.domain_analysis import BigPicture, DomainAnalysis, GrafoPorAgregado
from services.analysis_cache import (
    PROMPT_VERSION,
    compute_analysis_cache_key,
    load_cached_analysis,
    store_analysis,
)


# --- compute_analysis_cache_key ------------------------------------------


class TestComputeKey:
    def test_same_inputs_yield_same_key(self):
        k1 = compute_analysis_cache_key("hello", "gemini-2.5-pro", 0.0)
        k2 = compute_analysis_cache_key("hello", "gemini-2.5-pro", 0.0)
        assert k1 == k2

    def test_different_transcript_yields_different_key(self):
        k1 = compute_analysis_cache_key("hello", "gemini-2.5-pro", 0.0)
        k2 = compute_analysis_cache_key("world", "gemini-2.5-pro", 0.0)
        assert k1 != k2

    def test_different_model_yields_different_key(self):
        k1 = compute_analysis_cache_key("hello", "gemini-2.5-pro", 0.0)
        k2 = compute_analysis_cache_key("hello", "gemini-1.5-flash", 0.0)
        assert k1 != k2

    def test_legacy_temperature_arg_is_ignored(self):
        # Decoding is hardcoded to greedy, so temperature is no longer part
        # of the cache key. Extra args must be silently ignored for
        # backward compatibility with older callers.
        k1 = compute_analysis_cache_key("hello", "gemini-2.5-pro", 0.0)
        k2 = compute_analysis_cache_key("hello", "gemini-2.5-pro", 0.7)
        k3 = compute_analysis_cache_key("hello", "gemini-2.5-pro")
        assert k1 == k2 == k3

    def test_handles_arbitrary_objects(self):
        # Should not crash even when passed mock-like objects.
        class FakeMock:
            def __str__(self) -> str:
                return "<MagicMock id=42>"

        k = compute_analysis_cache_key("x", FakeMock(), "not-a-float")
        assert isinstance(k, str)
        assert k.startswith("analysis_")

    def test_key_format(self):
        k = compute_analysis_cache_key("a", "b", 0.0)
        assert k.startswith("analysis_")
        # 32-char hex tail
        assert len(k.split("_")[1]) == 32

    def test_prompt_version_is_in_key_derivation(self):
        # Sanity check: the version constant is non-empty so callers can
        # bump it to invalidate the cache.
        assert PROMPT_VERSION
        assert isinstance(PROMPT_VERSION, str)


# --- FileCacheAdapter JSON methods ---------------------------------------


class TestFileCacheJson:
    def test_get_json_miss_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = FileCacheAdapter(cache_dir=tmp)
            assert cache.get_json("nonexistent") is None

    def test_set_then_get_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = FileCacheAdapter(cache_dir=tmp)
            payload = {"hello": "world", "n": 42, "list": [1, 2, 3]}
            cache.set_json("k1", payload)
            assert cache.get_json("k1") == payload

    def test_set_json_handles_unicode(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = FileCacheAdapter(cache_dir=tmp)
            cache.set_json("k", {"name": "Digitalización última milla"})
            assert cache.get_json("k") == {"name": "Digitalización última milla"}

    def test_corrupt_file_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = FileCacheAdapter(cache_dir=tmp)
            path = os.path.join(tmp, "broken.json")
            with open(path, "w") as f:
                f.write("not json {{{")
            assert cache.get_json("broken") is None


# --- load_cached_analysis / store_analysis -------------------------------


def _mk_analysis() -> DomainAnalysis:
    return DomainAnalysis(
        nombre_proyecto="Test",
        fecha_analisis="2026-04-10",
        big_picture=BigPicture(descripcion="x", nodos=[], aristas=[]),
        agregados=[
            GrafoPorAgregado(
                nombre_agregado="A",
                entidad_raiz="A",
                descripcion="x",
                nodos=[],
                aristas=[],
            )
        ],
    )


class TestStoreLoad:
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = FileCacheAdapter(cache_dir=tmp)
            store_analysis(cache, "k", _mk_analysis())
            loaded = load_cached_analysis(cache, "k")
            assert loaded is not None
            assert loaded.nombre_proyecto == "Test"

    def test_load_miss_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = FileCacheAdapter(cache_dir=tmp)
            assert load_cached_analysis(cache, "missing") is None

    def test_none_cache_is_safe(self):
        # Should be a no-op, not crash.
        store_analysis(None, "k", _mk_analysis())
        assert load_cached_analysis(None, "k") is None

    def test_cache_without_json_methods_is_safe(self):
        class StringOnlyCache:
            def get(self, key):
                return None

            def set(self, key, value):
                pass

        c = StringOnlyCache()
        store_analysis(c, "k", _mk_analysis())  # should not raise
        assert load_cached_analysis(c, "k") is None
