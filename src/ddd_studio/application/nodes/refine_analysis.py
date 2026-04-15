"""Refinement node using InferencePort.

Conditional routing: only executes when has_refine=True.
Returns typed partial update with refined DomainAnalysis.
"""

from __future__ import annotations

from typing import Any

from domain.events import ErrorEvent, ProgressEvent
from domain.models.agent_state import NodeContract
from models.domain_analysis import DomainAnalysis
from prompts import registry

CONTRACT = NodeContract(
    node_name="refine_analysis",
    required_inputs=["analysis", "context"],
    produced_outputs=["analysis", "context"],
    emits_events=["refinement_start", "refinement_complete"],
)


def _noop_emitter(event: Any) -> None:
    pass


def refine_analysis(
    state: dict[str, Any],
    *,
    inference: Any,
    emitter: Any = None,
) -> dict[str, Any]:
    """Refine domain analysis using context document."""
    emit = emitter or _noop_emitter
    emit(
        ProgressEvent(
            checkpoint="refinement_start",
            node_name="refine_analysis",
            message="Starting refinement",
        )
    )

    analysis: DomainAnalysis = state.get("analysis")
    context = state.get("context", "")

    try:
        draft_json = analysis.model_dump_json(indent=2)
        prompt = registry.get("refinement").render(context=context, draft_json=draft_json).to_string()
        refined: DomainAnalysis = inference.invoke(prompt, DomainAnalysis)
    except Exception as e:
        emit(ErrorEvent(node_name="refine_analysis", error_type="service", message=str(e), recoverable=True))
        return {"analysis": analysis, "context": context}

    emit(
        ProgressEvent(
            checkpoint="refinement_complete",
            node_name="refine_analysis",
            message="Refinement complete",
        )
    )

    return {
        "analysis": refined,
        "context": context,
    }
