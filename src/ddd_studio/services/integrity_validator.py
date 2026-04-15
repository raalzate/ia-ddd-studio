"""Post-assembly graph integrity validator.

After the step-by-step pipeline assembles a DomainAnalysis, this module
checks structural invariants that the extraction layer is expected to
honor (every Command has an executor, every Event has a producer, every
Aggregate has at least one Command/Event, etc.).

Pure Python. No LLM calls. Deterministic by construction.

The validator is observational, not corrective: it returns a list of
issues with severities so the orchestrator can surface them as warnings
(via the event emitter) or, later, feed them into a repair loop.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from models.domain_analysis import DomainAnalysis

Severity = Literal["error", "warning", "info"]


@dataclass(frozen=True)
class IntegrityIssue:
    code: str
    severity: Severity
    message: str
    node_id: str | None = None


def _edge_sources(analysis: DomainAnalysis) -> set[str]:
    return {e.fuente for e in analysis.big_picture.aristas}


def _edge_destinations(analysis: DomainAnalysis) -> set[str]:
    return {e.destino for e in analysis.big_picture.aristas}


def validate(analysis: DomainAnalysis) -> list[IntegrityIssue]:
    """Return the list of integrity issues found in `analysis`."""
    issues: list[IntegrityIssue] = []
    sources = _edge_sources(analysis)
    destinations = _edge_destinations(analysis)
    all_ids = {n.id for n in analysis.big_picture.nodos}

    for node in analysis.big_picture.nodos:
        tipo = node.tipo_elemento

        # Every Command MUST have an actor edge pointing at it.
        if tipo == "Comando" and node.id not in destinations:
            issues.append(
                IntegrityIssue(
                    code="orphan_command",
                    severity="warning",
                    message=f"Comando '{node.nombre}' no tiene actor que lo ejecute.",
                    node_id=node.id,
                )
            )

        # Every Event MUST have exactly one producing Command edge.
        if tipo == "Evento" and node.id not in destinations:
            issues.append(
                IntegrityIssue(
                    code="orphan_event",
                    severity="warning",
                    message=f"Evento '{node.nombre}' no tiene comando que lo produzca.",
                    node_id=node.id,
                )
            )

        # Every Aggregate SHOULD be the target/source of ≥1 command/event edge.
        if tipo == "Agregado":
            touches = any(e.fuente == node.id or e.destino == node.id for e in analysis.big_picture.aristas)
            if not touches:
                issues.append(
                    IntegrityIssue(
                        code="isolated_aggregate",
                        severity="warning",
                        message=f"Agregado '{node.nombre}' no conecta con comandos ni eventos.",
                        node_id=node.id,
                    )
                )

        # Actors that never execute anything are suspicious (info only).
        if tipo in ("Actor", "Sistema Externo") and node.id not in sources:
            issues.append(
                IntegrityIssue(
                    code="idle_actor",
                    severity="info",
                    message=f"Actor '{node.nombre}' extraído pero no ejecuta ningún comando.",
                    node_id=node.id,
                )
            )

    # Read models that project zero events are dead views.
    for rm in analysis.read_models:
        if not rm.proyecta:
            issues.append(
                IntegrityIssue(
                    code="empty_read_model",
                    severity="warning",
                    message=f"Read model '{rm.nombre}' no proyecta ningún evento.",
                )
            )
        else:
            # Every projected event ID must actually exist in the graph.
            missing = [eid for eid in rm.proyecta if eid not in all_ids]
            for eid in missing:
                issues.append(
                    IntegrityIssue(
                        code="dangling_read_model_projection",
                        severity="warning",
                        message=f"Read model '{rm.nombre}' proyecta '{eid}' inexistente.",
                    )
                )

    # Inter-aggregate policies must connect real event → real command.
    for edge in analysis.politicas_inter_agregados:
        if edge.fuente not in all_ids:
            issues.append(
                IntegrityIssue(
                    code="dangling_policy_source",
                    severity="warning",
                    message=f"Política referencia evento inexistente '{edge.fuente}'.",
                )
            )
        if edge.destino not in all_ids:
            issues.append(
                IntegrityIssue(
                    code="dangling_policy_target",
                    severity="warning",
                    message=f"Política referencia comando inexistente '{edge.destino}'.",
                )
            )

    return issues


def summarize(issues: list[IntegrityIssue]) -> dict[str, int]:
    """Return counts grouped by severity — useful for KPIs and logs."""
    out: dict[str, int] = {"error": 0, "warning": 0, "info": 0}
    for i in issues:
        out[i.severity] = out.get(i.severity, 0) + 1
    return out
