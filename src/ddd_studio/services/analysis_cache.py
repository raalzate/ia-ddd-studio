"""Helpers for caching DomainAnalysis results by transcript hash.

The cache key is derived from (transcript, model, prompt_version).
Temperature is no longer part of the key: decoding is hardcoded to greedy
(temperature=0, top_k=1) at the adapter level, so it is a constant of the
system, not an input. Bumping `PROMPT_VERSION` invalidates all cached
entries when prompts or decoding config change in a meaningful way.
"""

from __future__ import annotations

import hashlib
from typing import Any

from models.domain_analysis import DomainAnalysis

# Bump this whenever the semantic_analysis prompt, normalization rules, or
# decoding configuration change in a way that should invalidate previously
# cached results.
PROMPT_VERSION = "2026-04-14.v4-greedy-decoding"


def compute_analysis_cache_key(
    transcript: Any,
    model: Any,
    *_ignored: Any,
) -> str:
    """Build a deterministic cache key for an analysis run.

    Extra positional args are accepted and ignored for backward compatibility
    with callers that used to pass `temperature`.
    """
    transcript_s = str(transcript or "")
    model_s = str(model) if model else "unknown"

    h = hashlib.sha256()
    h.update(transcript_s.encode("utf-8"))
    h.update(b"|")
    h.update(model_s.encode("utf-8"))
    h.update(b"|")
    h.update(PROMPT_VERSION.encode("utf-8"))
    return f"analysis_{h.hexdigest()[:32]}"


def load_cached_analysis(cache: Any, key: str) -> DomainAnalysis | None:
    """Try to load and validate a cached analysis. Returns None on miss/error."""
    if cache is None or not hasattr(cache, "get_json"):
        return None
    payload = cache.get_json(key)
    if not payload:
        return None
    try:
        return DomainAnalysis.model_validate(payload)
    except Exception:
        return None


def store_analysis(cache: Any, key: str, analysis: DomainAnalysis) -> None:
    """Persist an analysis to cache. No-op if cache is unavailable."""
    if cache is None or not hasattr(cache, "set_json"):
        return
    try:
        cache.set_json(key, analysis.model_dump(mode="json"))
    except Exception:
        # Cache failures must never break the pipeline.
        return
