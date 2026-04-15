"""Semantic analysis node using InferencePort.

Single-shot extraction:  one LLM call with the
`semantic_analysis` prompt → DomainAnalysis (edges already embedded in
the schema). Deterministic post-processing via `analysis_normalizer`.
"""

from __future__ import annotations

from typing import Any

from domain.events import ErrorEvent, ProgressEvent
from domain.models.agent_state import NodeContract
from models.domain_analysis import DomainAnalysis

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
    cache: Any = None,
    emitter: Any = None,
) -> dict[str, Any]:
    """Analyze transcript semantically using the injected InferencePort.

    Flow:
        1. One LLM call produces a full DomainAnalysis (nodes + edges).
        2. `analysis_normalizer` canonicalizes IDs, dedupes nodes, re-orders
           by transcript appearance.
        3. `integrity_validator` reports structural warnings via the emitter.
    """
    emit = emitter or _noop_emitter
    emit(
        ProgressEvent(
            checkpoint="analysis_start",
            node_name="analyze_semantics",
            message="Inicia análisis semántico (single-shot)",
        )
    )

    transcript = state.get("transcript", "") or ""
    context = state.get("context", "") or ""
    has_refine = bool(context.strip())

    try:
        from prompts import registry
        from services.analysis_cache import (
            compute_analysis_cache_key,
            load_cached_analysis,
            store_analysis,
        )
        from services.analysis_normalizer import normalize_analysis
        from services.integrity_validator import summarize, validate
       

        model_name = getattr(inference, "_model_name", None) or type(inference).__name__
        cache_key = compute_analysis_cache_key(transcript, model_name)
        cached = load_cached_analysis(cache, cache_key)
        if cached is not None:
            print(f"⚡ [Analyze] Cache HIT ({cache_key[:16]}…) — saltando LLM.")
            emit(
                ProgressEvent(
                    checkpoint="analysis_complete",
                    node_name="analyze_semantics",
                    message="Análisis recuperado de cache",
                    percentage=1.0,
                )
            )
            return {
                "analysis": cached,
                "transcript": transcript,
                "has_refine": has_refine,
                "context": context,
            }

        annotated_transcript = transcript
        

        prompt = registry.get("semantic_analysis").render(transcript=annotated_transcript).to_string()

        emit(
            ProgressEvent(
                checkpoint="extraction.llm_call",
                node_name="analyze_semantics",
                message="Invocando LLM para extracción DDD",
                percentage=0.4,
            )
        )

        analysis: DomainAnalysis = inference.invoke(prompt, DomainAnalysis)
        analysis = normalize_analysis(analysis, transcript)
        store_analysis(cache, cache_key, analysis)       

        issues = validate(analysis)
        counts = summarize(issues)
        if issues:
            emit(
                ProgressEvent(
                    checkpoint="integrity.report",
                    node_name="analyze_semantics",
                    message=(
                        f"Integridad: {counts['error']} errores, {counts['warning']} warnings, {counts['info']} info"
                    ),
                    percentage=0.95,
                )
            )
            for issue in issues:
                if issue.severity != "info":
                    emit(
                        ProgressEvent(
                            checkpoint="integrity.issue",
                            node_name="analyze_semantics",
                            message=f"[{issue.code}] {issue.message}",
                        )
                    )

        print(f"✅ [Analyze] {len(analysis.big_picture.nodos)} nodos · {len(analysis.big_picture.aristas)} aristas")

    except Exception as e:
        import traceback

        print("❌ [Analyze] Excepción en extracción:")
        traceback.print_exc()
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
        return {
            "error": str(e),
            "transcript": annotated_transcript,
            "has_refine": False,
            "context": context,
        }

    emit(
        ProgressEvent(
            checkpoint="analysis_complete",
            node_name="analyze_semantics",
            message="Análisis de grafos completado",
            percentage=1.0,
        )
    )

    return {
        "analysis": analysis,
        "transcript": annotated_transcript,
        "has_refine": has_refine,
        "context": context,
    }
