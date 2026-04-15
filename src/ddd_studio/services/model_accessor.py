"""ModelAccessor service — wraps session state access to DomainAnalysis.

Provides get/set/snapshot/undo/find operations for agent tools.
"""

from __future__ import annotations

from datetime import datetime, timezone

from domain.models.tool_schemas import OperationRecord
from models.domain_analysis import DomainAnalysis, GrafoPorAgregado, NodoGrafo

MAX_HISTORY = 10


class ModelAccessor:
    """Provides atomic-ish access to the domain model in session state."""

    def __init__(self, session_state: dict) -> None:
        self._state = session_state

    def get_model(self) -> DomainAnalysis:
        """Return the current DomainAnalysis from session state."""
        result = self._state.get("analysis_result")
        if not result or "analysis" not in result:
            raise ValueError("No domain model loaded in session state")
        return result["analysis"]

    def set_model(self, model: DomainAnalysis) -> None:
        """Replace the current DomainAnalysis in session state."""
        if "analysis_result" not in self._state:
            self._state["analysis_result"] = {}
        self._state["analysis_result"]["analysis"] = model

        # Auto-update the linked draft when the model changes
        generation_id = self._state.get("current_generation_id")
        if generation_id:
            draft_service = self._state.get("_draft_service")
            if draft_service:
                try:
                    draft_service.update_draft_snapshot(generation_id, model)
                except Exception:
                    pass  # Draft update failure must not block model changes

    def snapshot(self, tool_name: str, description: str) -> None:
        """Push a snapshot of the current model state to history for undo."""
        model = self.get_model()
        record = OperationRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            tool_name=tool_name,
            description=description,
            snapshot=model.model_dump(),
        )
        history = self._state.setdefault("model_history", [])
        history.append(record)
        if len(history) > MAX_HISTORY:
            self._state["model_history"] = history[-MAX_HISTORY:]

    def undo(self) -> OperationRecord | None:
        """Pop the last snapshot and restore the model. Returns the record or None."""
        history = self._state.get("model_history", [])
        if not history:
            return None
        record = history.pop()
        restored = DomainAnalysis.model_validate(record.snapshot)
        self.set_model(restored)
        return record

    def find_node(self, name: str, scope: str | None = None) -> list[NodoGrafo]:
        """Find nodes matching name across scopes. If scope is given, restrict search."""
        model = self.get_model()
        results: list[NodoGrafo] = []

        if scope is None or scope == "big_picture":
            results.extend(n for n in model.big_picture.nodos if n.nombre == name)

        if scope is None or scope == "aggregate":
            for agg in model.agregados:
                results.extend(n for n in agg.nodos if n.nombre == name)

        return results

    def find_aggregate(self, name: str) -> GrafoPorAgregado | None:
        """Find an aggregate by name."""
        model = self.get_model()
        for agg in model.agregados:
            if agg.nombre_agregado == name:
                return agg
        return None
