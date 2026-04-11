"""AmbiguityDetector service — LLM-powered lexical ambiguity detection.

Uses InferencePort.invoke() with structured output (list[Ambiguity]) to detect
synonym candidates, homonyms, and vague terms in a DomainAnalysis model.
"""

from __future__ import annotations

import logging

from domain.models.tool_schemas import Ambiguity
from models.domain_analysis import DomainAnalysis

logger = logging.getLogger(__name__)


class AmbiguityDetector:
    """LLM-powered lexical ambiguity detection for domain models."""

    def __init__(self, inference: object) -> None:
        """Initialize with an InferencePort for LLM calls."""
        self._inference = inference

    def detect(
        self,
        model: DomainAnalysis,
        *,
        transcript: str | None = None,
        context: str | None = None,
    ) -> list[Ambiguity]:
        """Analyze the domain model for lexical ambiguities.

        Inspects node names and descriptions across all scopes to find:
        - Potential synonyms (different names for the same concept)
        - Homonyms (same name used differently across contexts)
        - Vague or generic terms
        - Gaps between what was discussed (transcript/context) and what was modeled

        Args:
            model: The domain analysis model to inspect.
            transcript: Stage-1 source text (workshop transcript or uploaded document).
            context: Stage-2 additional context (official documentation or PDF content).

        Returns:
            List of Ambiguity objects sorted by priority (1=highest).
            Empty list if no ambiguities detected or LLM fails.
        """
        prompt = self._build_prompt(model, transcript=transcript, context=context)
        try:
            result = self._inference.invoke(prompt, output_schema=list[Ambiguity])
            if not isinstance(result, list):
                return []
            ambiguities = [a for a in result if isinstance(a, Ambiguity)]
            ambiguities.sort(key=lambda a: a.priority)
            return ambiguities
        except Exception:
            logger.warning("AmbiguityDetector: LLM call failed, returning empty list", exc_info=True)
            return []

    def _build_prompt(
        self,
        model: DomainAnalysis,
        *,
        transcript: str | None = None,
        context: str | None = None,
    ) -> str:
        """Build the detection prompt with all node names and descriptions."""
        lines = []

        # Skip big_picture — post-generation analysis only refines
        # aggregates, read models, and inter-aggregate policies.

        # Collect nodes from all aggregates
        for agg in model.agregados:
            lines.append(f"\nAggregate: {agg.nombre_agregado}")
            for node in agg.nodos:
                lines.append(f"  [{node.tipo_elemento}] {node.nombre}: {node.descripcion}")
            for edge in agg.aristas:
                lines.append(f"  Edge: {edge.fuente} -> {edge.destino} ({edge.descripcion})")

        # Collect inter-aggregate policies
        for policy in model.politicas_inter_agregados:
            lines.append(f"\nPolicy: {policy.fuente} -> {policy.destino} ({policy.descripcion})")

        # Collect read models
        for rm in model.read_models:
            lines.append(f"\nRead Model: {rm.nombre} — {rm.descripcion or ''} (projects: {', '.join(rm.proyecta)})")

        node_list = "\n".join(lines) if lines else "(no nodes)"

        # Build optional source sections
        source_sections = ""
        if transcript and transcript.strip():
            trimmed = transcript.strip()[:3000]
            source_sections += f"\n\nSTAGE-1 SOURCE (workshop transcript / input document):\n{trimmed}"
        if context and context.strip():
            trimmed = context.strip()[:3000]
            source_sections += f"\n\nSTAGE-2 CONTEXT (official documentation / additional context):\n{trimmed}"

        extra_instructions = ""
        if source_sections:
            extra_instructions = (
                "\n6. Cross-reference the model nodes against the source inputs: "
                "flag any concept mentioned in the source that is missing or significantly "
                "different in the model (e.g., a business rule described in the transcript "
                "that has no corresponding Policy or Command node)."
            )

        return f"""Analyze the following domain model for lexical ambiguities and logical inconsistencies.

SCOPE: Aggregates, Read Models, and Inter-Aggregate Policies ONLY.
DO NOT analyze or suggest changes to the Big Picture — it is read-only.

MODEL ELEMENTS:
{node_list}{source_sections}

INSTRUCTIONS:
1. Identify potential synonyms: different names that may refer to the same domain concept within aggregates.
2. Identify homonyms: same or similar names used in different aggregates with potentially different meanings.
3. Flag vague or generic terms that should be more specific in a DDD model (e.g., "Sistema", "Proceso", "Datos").
4. Resolve ambiguities with logical relation to aggregate graphs, read models, policies, and edges. Suggestions must be structurally coherent with the existing graph connections.
5. For each ambiguity, suggest 2-4 concrete resolution options.
6. Assign priority: 1 if the ambiguity affects aggregate graph structure (e.g., missing events, broken edges), 2 for naming issues, 3 for description-only issues.{extra_instructions}

Return ONLY the list of ambiguities found. If none, return an empty list."""
