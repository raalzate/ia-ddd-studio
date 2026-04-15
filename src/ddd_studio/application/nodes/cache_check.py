"""Cache lookup node using CachePort.

Returns typed partial AgentState update with cache_path, cache_exists,
and optionally transcript if cached.
"""

from __future__ import annotations

import hashlib
from typing import Any

from domain.events import ProgressEvent
from domain.models.agent_state import NodeContract

CONTRACT = NodeContract(
    node_name="cache_check",
    required_inputs=["audio_path", "audio_name"],
    produced_outputs=["cache_path", "cache_exists", "transcript"],
    emits_events=["cache_check"],
)


def _noop_emitter(event: Any) -> None:
    pass


def cache_check(
    state: dict[str, Any],
    *,
    cache: Any,
    emitter: Any = None,
) -> dict[str, Any]:
    """Check if a cached transcription exists for the given audio."""
    emit = emitter or _noop_emitter
    emit(ProgressEvent(checkpoint="cache_check", node_name="cache_check", message="Verificando si hay cache"))

    audio_name = state.get("audio_name", "") or ""

    # Use only audio_name for the cache key. audio_path is a random tempfile
    # path that changes on every upload, which would make the cache always miss.
    key = hashlib.sha256(audio_name.encode()).hexdigest()
    cached_value = cache.get(key)

    if cached_value is not None:
        return {
            "cache_path": key,
            "cache_exists": True,
            "transcript": cached_value,
        }

    return {
        "cache_path": key,
        "cache_exists": False,
    }
