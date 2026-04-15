"""Spec generation node using InferencePort.

Returns typed partial update with specs dict.
"""

from __future__ import annotations

from typing import Any

from domain.events import ErrorEvent, ProgressEvent
from domain.models.agent_state import NodeContract
from models.domain_analysis import DomainAnalysis
from prompts import registry

CONTRACT = NodeContract(
    node_name="generate_specs",
    required_inputs=["analysis"],
    produced_outputs=["specs"],
    emits_events=["spec_generation_start", "spec_generation_complete"],
)


def _noop_emitter(event: Any) -> None:
    pass


def generate_specs(
    state: dict[str, Any],
    *,
    inference: Any,
    emitter: Any = None,
) -> dict[str, Any]:
    """Generate Gherkin and domain model specs from the analysis."""
    emit = emitter or _noop_emitter
    emit(
        ProgressEvent(
            checkpoint="spec_generation_start",
            node_name="generate_specs",
            message="Generando especificaciones para DDD",
        )
    )

    analysis: DomainAnalysis = state.get("analysis")

    try:
        data_context = analysis.model_dump_json(exclude={"read_models", "big_picture"})

        gherkin = inference.invoke_text(
            registry.get("gherkin_generation").render(data_context=data_context).to_string()
        )

        domain_models = inference.invoke_text(
            registry.get("domain_model_specs").render(data_context=data_context).to_string()
        )
    except Exception as e:
        emit(ErrorEvent(node_name="generate_specs", error_type="service", message=str(e), recoverable=True))
        return {"specs": {}, "error": str(e)}

    emit(
        ProgressEvent(
            checkpoint="spec_generation_complete",
            node_name="generate_specs",
            message="Specifications generated",
        )
    )

    return {
        "specs": {
            "gherkin": gherkin,
            "domain_models": domain_models,
        }
    }
