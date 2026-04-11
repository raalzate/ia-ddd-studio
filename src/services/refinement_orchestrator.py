"""RefinementOrchestrator service — coordinates the post-generation refinement cycle.

Detects ambiguities → presents findings → translates user responses into plans →
executes approved plans via existing agent tools.
"""

from __future__ import annotations

import logging

from domain.models.tool_schemas import (
    Ambiguity,
    RefinementPlan,
    RefinementSession,
    ToolExecution,
)
from models.domain_analysis import DomainAnalysis

logger = logging.getLogger(__name__)


class StaleModelError(Exception):
    """Raised when the domain model changed since the refinement session was created."""


class RefinementOrchestrator:
    """Coordinates the post-generation refinement workflow."""

    def __init__(
        self,
        ambiguity_detector: object,
        completeness_analyzer: object,
        model_accessor: object,
    ) -> None:
        self._detector = ambiguity_detector
        self._completeness = completeness_analyzer
        self._accessor = model_accessor

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_session(self) -> RefinementSession:
        """Create a new refinement session and run detection.

        1. Snapshot the current model hash
        2. Run AmbiguityDetector.detect()
        3. Run CompletenessAnalyzer.analyze()
        4. Convert CompletenessGaps to Ambiguities
        5. Merge and sort by priority
        6. Return the session with status="presenting"
        """
        model: DomainAnalysis = self._accessor.get_model()
        model_hash = RefinementSession.compute_model_hash(model.model_dump_json())

        # Lexical ambiguities (LLM-powered)
        lexical_ambiguities = self._detector.detect(model)

        # Structural gaps (deterministic)
        gaps = self._completeness.analyze(model)
        structural_ambiguities = [self._gap_to_ambiguity(g) for g in gaps]

        all_ambiguities = lexical_ambiguities + structural_ambiguities
        all_ambiguities.sort(key=lambda a: a.priority)

        session = RefinementSession(
            model_hash=model_hash,
            ambiguities=all_ambiguities,
            status="presenting",
        )
        return session

    def format_findings(self, session: RefinementSession) -> str:
        """Format detected ambiguities as a structured Markdown chat message.

        Groups by priority (P1→P2→P3), max 5 per group.
        """
        ambiguities = session.ambiguities
        if not ambiguities:
            return (
                "## 🔍 Análisis Post-Generación\n\n"
                "✅ **No se detectaron ambigüedades** en el modelo generado.\n\n"
                "El modelo cumple con las expectativas estructurales. "
                "Puedes validar los elementos clave o hacer preguntas sobre el modelo."
            )

        lines = ["## 🔍 Análisis Post-Generación\n"]
        total = len(ambiguities)

        p1 = [a for a in ambiguities if a.priority == 1][:5]
        p2 = [a for a in ambiguities if a.priority == 2][:5]
        p3 = [a for a in ambiguities if a.priority == 3][:5]

        if p1:
            lines.append("### ⚠️ Prioridad Alta (Estructura)")
            for i, a in enumerate(p1, 1):
                lines.append(f"{i}. **[{a.id}]** {a.description}")
                for j, opt in enumerate(a.suggested_resolutions, 1):
                    lines.append(f"   - Opción {j}: {opt}")
                if a.assumptions_made:
                    lines.append(f"   > *Supuesto: {a.assumptions_made}*")
            lines.append("")

        if p2:
            lines.append("### 🔤 Prioridad Media (Léxico)")
            for i, a in enumerate(p2, 1):
                lines.append(f"{i}. **[{a.id}]** {a.description}")
                for j, opt in enumerate(a.suggested_resolutions, 1):
                    lines.append(f"   - Opción {j}: {opt}")
            lines.append("")

        if p3:
            lines.append("### 💬 Prioridad Baja (Descripciones)")
            for i, a in enumerate(p3, 1):
                lines.append(f"{i}. **[{a.id}]** {a.description}")
                for j, opt in enumerate(a.suggested_resolutions, 1):
                    lines.append(f"   - Opción {j}: {opt}")
            lines.append("")

        shown = len(p1) + len(p2) + len(p3)
        if total > shown:
            lines.append(f"*... y {total - shown} hallazgo(s) adicionales. Escribe 'mostrar más'.*\n")

        lines.append("---")
        lines.append(
            'Responde con la resolución que prefieras, o escribe **"todo ok"** si el modelo es correcto tal como está.'
        )
        return "\n".join(lines)

    def create_plan(
        self,
        session: RefinementSession,
        ambiguity_ids: list[str],
        resolution_description: str,
    ) -> RefinementPlan:
        """Create a refinement plan from the user's resolution choice.

        Translates natural language resolution into proposed tool operations.
        Does NOT execute — returns plan with status="pending" for user approval.
        """
        ambiguities = {a.id: a for a in session.ambiguities}
        target_ambiguities = [ambiguities[aid] for aid in ambiguity_ids if aid in ambiguities]

        operations = self._build_operations(target_ambiguities, resolution_description)

        description = f"Resolve {', '.join(ambiguity_ids)}: {resolution_description}"
        plan = RefinementPlan(
            source_ambiguity_ids=ambiguity_ids,
            description=description,
            proposed_operations=operations,
            status="pending",
        )
        return plan

    def execute_plan(
        self,
        session: RefinementSession,
        plan: RefinementPlan,
    ) -> RefinementPlan:
        """Execute an approved refinement plan.

        1. Verify model hash hasn't changed (FR-009)
        2. Take a single snapshot for atomic rollback
        3. Execute operations sequentially via agent tools
        4. On failure: undo to pre-batch state
        5. Update plan status

        Raises:
            StaleModelError: If model hash changed since session start.
        """
        if not self.check_model_freshness(session):
            raise StaleModelError(
                "Model changed since refinement session was created. Please re-run analysis before applying changes."
            )

        self._accessor.snapshot("refinement_batch", plan.description)

        tool_map = self._build_tool_map()

        for op in plan.proposed_operations:
            tool_name = op.get("tool", "")
            args = op.get("args", {})
            tool_fn = tool_map.get(tool_name)

            if tool_fn is None:
                self._accessor.undo()
                plan.status = "failed"
                return plan

            try:
                result = tool_fn.invoke(args)
                execution = ToolExecution(
                    tool_name=tool_name,
                    arguments=args,
                    result=result.model_dump_json() if hasattr(result, "model_dump_json") else str(result),
                    success=result.success if hasattr(result, "success") else True,
                )
                plan.executed_results.append(execution)

                if not execution.success:
                    self._accessor.undo()
                    plan.status = "failed"
                    return plan

            except Exception as exc:
                logger.warning("Tool execution failed: %s — %s", tool_name, exc, exc_info=True)
                self._accessor.undo()
                plan.status = "failed"
                return plan

        plan.status = "executed"
        return plan

    def check_model_freshness(self, session: RefinementSession) -> bool:
        """Check if the model has changed since the session was created.

        Returns:
            True if model is unchanged (fresh), False if stale.
        """
        try:
            model = self._accessor.get_model()
            current_hash = RefinementSession.compute_model_hash(model.model_dump_json())
            return current_hash == session.model_hash
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _gap_to_ambiguity(gap) -> Ambiguity:
        """Convert a CompletenessGap to an Ambiguity for uniform handling."""
        return Ambiguity(
            id=f"gap_{gap.rule_name}_{gap.affected_aggregate}",
            type="structural",
            priority=1,
            description=gap.description,
            affected_elements=gap.affected_elements,
            suggested_resolutions=[gap.suggestion],
            assumptions_made=None,
        )

    def _build_operations(
        self,
        ambiguities: list[Ambiguity],
        resolution_description: str,
    ) -> list[dict]:
        """Translate ambiguities + resolution into a list of tool operations.

        Uses simple heuristics:
        - If resolution says to keep/mantener/separate: no operations (user rejects)
        - If resolution mentions add/agregar + event: add_node + add_edge
        - If resolution mentions merge/unify/rename: rename_element
        """
        lower = resolution_description.lower()

        # Rejection: user wants to keep things as they are
        rejection_signals = [
            "mantener",
            "keep",
            "separado",
            "separate",
            "distinct",
            "distinto",
            "no son sinónimos",
            "not synonyms",
            "no cambiar",
            "no change",
        ]
        if any(sig in lower for sig in rejection_signals):
            return []

        operations = []

        for amb in ambiguities:
            if amb.type == "structural" and "command_produces_event" in amb.id:
                # Add an event node and edge
                agg_name = amb.id.split("_")[-1] if "_" in amb.id else "default"
                event_name = "EventoGenerado"
                for word in resolution_description.split():
                    if word[0].isupper() and len(word) > 3:
                        event_name = word
                        break

                # Never modify big_picture — only aggregate scope
                operations.append(
                    {
                        "tool": "add_node",
                        "args": {
                            "scope": "aggregate",
                            "aggregate_name": agg_name,
                            "node_id": f"evt_{event_name.lower()}",
                            "node_type": "Evento",
                            "node_name": event_name,
                            "description": f"Event produced by {amb.affected_elements[0] if amb.affected_elements else 'command'}",
                        },
                    }
                )
                if amb.affected_elements:
                    operations.append(
                        {
                            "tool": "add_edge",
                            "args": {
                                "scope": "aggregate",
                                "aggregate_name": agg_name,
                                "source_id": amb.affected_elements[0],
                                "target_id": f"evt_{event_name.lower()}",
                                "description": "produces",
                            },
                        }
                    )

            elif amb.type in ("lexical", "semantic") and amb.affected_elements:
                # Merge/rename: identify target from resolution
                merge_signals = [
                    "unificar",
                    "unify",
                    "merge",
                    "rename",
                    "renombrar",
                    "usar solo",
                    "use only",
                    "sinónimos",
                ]
                if any(sig in lower for sig in merge_signals):
                    operations.append(
                        {
                            "tool": "rename_element",
                            "args": {
                                "old_name": amb.affected_elements[-1]
                                if len(amb.affected_elements) > 1
                                else amb.affected_elements[0],
                                "new_name": amb.affected_elements[0],
                                "scope": "aggregate",
                            },
                        }
                    )

        return operations

    def _build_tool_map(self) -> dict:
        """Build a map of tool_name → callable tool from agent_tools."""
        try:
            from services.agent_tools import create_tools

            tools = create_tools(self._accessor)
            return {t.name: t for t in tools}
        except (ImportError, AttributeError, Exception):
            return {}
