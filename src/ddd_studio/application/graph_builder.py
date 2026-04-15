"""LangGraph StateGraph construction.

No @st.cache_resource, no Streamlit imports. Pure application logic.
Builds the agent pipeline graph with typed AgentState.
"""

import functools
from typing import Any, Literal

from application.nodes.analyze_semantics import CONTRACT as ANALYZE_CONTRACT
from application.nodes.analyze_semantics import analyze_semantics
from application.nodes.cache_check import CONTRACT as CACHE_CONTRACT
from application.nodes.cache_check import cache_check
from application.nodes.refine_analysis import CONTRACT as REFINE_CONTRACT
from application.nodes.refine_analysis import refine_analysis
from application.nodes.transcribe import CONTRACT as TRANSCRIBE_CONTRACT
from application.nodes.transcribe import transcribe
from domain.models.agent_state import NodeContract
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict


class _PipelineState(TypedDict):
    """Internal state schema for LangGraph merge semantics."""

    audio_path: str | None
    audio_name: str | None
    transcript: str | None
    context: str | None
    analysis: Any
    specs: dict | None
    has_refine: bool
    cache_path: str | None
    cache_exists: bool
    error: str | None


_ALL_CONTRACTS = [
    CACHE_CONTRACT,
    TRANSCRIBE_CONTRACT,
    ANALYZE_CONTRACT,
    REFINE_CONTRACT,
]


def get_all_contracts() -> list[NodeContract]:
    """Return all registered node contracts."""
    return list(_ALL_CONTRACTS)


def _decide_transcription_route(
    state: dict[str, Any],
) -> Literal["transcribe", "analyze_semantics"]:
    """Route after cache_check: skip transcription if cache hit."""
    if state.get("cache_exists", False):
        return "analyze_semantics"
    return "transcribe"


def _decide_refinement(state: dict[str, Any]) -> Literal["refine_analysis", END]:
    """Route after analysis: refine if context provided, otherwise finish."""
    if state.get("has_refine", False):
        return "refine_analysis"
    return END


def build_audio_graph(
    *,
    inference: Any,
    transcription: Any,
    cache: Any,
    emitter: Any = None,
) -> Any:
    """Build the audio pipeline graph.

    Args:
        inference: InferencePort implementation.
        transcription: TranscriptionPort implementation.
        cache: CachePort implementation.
        emitter: EventEmitter implementation (optional).

    Returns:
        Compiled LangGraph StateGraph.
    """
    workflow = StateGraph(_PipelineState)

    # Bind dependencies to nodes via functools.partial
    workflow.add_node("cache_check", functools.partial(cache_check, cache=cache, emitter=emitter))
    workflow.add_node(
        "transcribe", functools.partial(transcribe, transcription=transcription, cache=cache, emitter=emitter)
    )
    workflow.add_node(
        "analyze_semantics",
        functools.partial(analyze_semantics, inference=inference, cache=cache, emitter=emitter),
    )
    workflow.add_node("refine_analysis", functools.partial(refine_analysis, inference=inference, emitter=emitter))

    workflow.set_entry_point("cache_check")

    workflow.add_conditional_edges(
        "cache_check",
        _decide_transcription_route,
        {"transcribe": "transcribe", "analyze_semantics": "analyze_semantics"},
    )
    workflow.add_edge("transcribe", "analyze_semantics")
    workflow.add_conditional_edges(
        "analyze_semantics",
        _decide_refinement,
        {"refine_analysis": "refine_analysis", END: END},
    )
    workflow.add_edge("refine_analysis", END)

    return workflow.compile()


def build_text_graph(*, inference: Any, cache: Any = None, emitter: Any = None) -> Any:
    """Build the text-only pipeline graph.

    Args:
        inference: InferencePort implementation.
        cache: CachePort implementation (optional). Used to cache the analysis
            output by transcript hash so identical inputs reuse identical outputs.
        emitter: EventEmitter implementation (optional).

    Returns:
        Compiled LangGraph StateGraph.
    """
    workflow = StateGraph(_PipelineState)

    workflow.add_node(
        "analyze_semantics",
        functools.partial(analyze_semantics, inference=inference, cache=cache, emitter=emitter),
    )
    workflow.add_node("refine_analysis", functools.partial(refine_analysis, inference=inference, emitter=emitter))

    workflow.set_entry_point("analyze_semantics")

    workflow.add_conditional_edges(
        "analyze_semantics",
        _decide_refinement,
        {"refine_analysis": "refine_analysis", END: END},
    )
    workflow.add_edge("refine_analysis", END)

    return workflow.compile()
