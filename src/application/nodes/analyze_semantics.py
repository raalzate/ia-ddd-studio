"""Semantic analysis node using InferencePort.

Returns typed partial update with DomainAnalysis.
"""

from __future__ import annotations

from typing import Any

from domain.events import ErrorEvent, ProgressEvent
from domain.models.agent_state import NodeContract
from models.domain_analysis import DomainAnalysis
from prompts import registry

CONTRACT = NodeContract(
    node_name="analyze_semantics",
    required_inputs=["transcript"],
    produced_outputs=["analysis", "transcript", "has_refine", "context"],
    emits_events=["analysis_start", "analysis_complete"],
)


def _noop_emitter(event: Any) -> None:
    pass


def analyze_semantics(
    state: dict[str, Any],
    *,
    inference: Any,
    emitter: Any = None,
) -> dict[str, Any]:
    """Analyze transcript semantically using the injected InferencePort."""
    emit = emitter or _noop_emitter
    emit(
        ProgressEvent(
            checkpoint="analysis_start",
            node_name="analyze_semantics",
            message="Inicia proceso de análisis semántico - construcción de grafos",
        )
    )

    transcript = state.get("transcript", "") or ""
    context = state.get("context", "") or ""

    try:
        # --- Deterministic NLP anchoring (spaCy) ---
        from services.nlp_extractor import extract_anchors, inject_anchors_to_prompt, is_available

        if is_available():
            print("🧠 [Analyze] spaCy ACTIVO — extrayendo anclas NLP del transcript...")
            nlp_anchors = extract_anchors(transcript)
        else:
            print("⚠️ [Analyze] spaCy NO disponible — enviando prompt sin anclas.")
            nlp_anchors = {}

        base_prompt = registry.get("semantic_analysis").render(transcript=transcript).to_string()
        prompt = inject_anchors_to_prompt(nlp_anchors, base_prompt)
        has_anchors = any(nlp_anchors.get(k) for k in ("actors", "domain_terms", "potential_commands"))
        print(
            f"📤 [Analyze] Prompt enviado al LLM ({len(prompt)} chars, anclas: {'SÍ' if has_anchors else 'NO'})"
        )

        analysis: DomainAnalysis = inference.invoke(prompt, DomainAnalysis)
    except Exception as e:
        error_type = (
            "service"
            if "unavailable" in type(e).__name__.lower() or "service" in type(e).__name__.lower()
            else "validation"
        )
        emit(
            ErrorEvent(
                node_name="analyze_semantics",
                error_type=error_type,
                message=str(e),
                recoverable=False,
            )
        )
        return {"error": str(e), "transcript": transcript, "has_refine": False, "context": context}

    has_refine = bool(context.strip())

    emit(
        ProgressEvent(
            checkpoint="analysis_complete",
            node_name="analyze_semantics",
            message="Analisis de grafos completado",
        )
    )

    return {
        "analysis": analysis,
        "transcript": transcript,
        "has_refine": has_refine,
        "context": context,
    }
