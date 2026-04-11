"""CompletenessAnalyzer service — deterministic DDD structural completeness validation.

Validates a DomainAnalysis model against DDD patterns without requiring an LLM.
"""

from __future__ import annotations

from domain.models.tool_schemas import CompletenessGap
from models.domain_analysis import DomainAnalysis


class CompletenessAnalyzer:
    """Deterministic DDD completeness validation — no LLM required."""

    def analyze(self, model: DomainAnalysis) -> list[CompletenessGap]:
        """Check the model against DDD structural completeness rules.

        Returns:
            List of CompletenessGap objects sorted by severity.
            Empty list if all rules pass.
        """
        gaps: list[CompletenessGap] = []

        for agg in model.agregados:
            agg_name = agg.nombre_agregado

            # Rule 1: aggregate_has_commands
            commands = [n for n in agg.nodos if n.tipo_elemento == "Comando"]
            if not commands:
                gaps.append(
                    CompletenessGap(
                        rule_name="aggregate_has_commands",
                        description=(
                            f"Agregado '{agg_name}' no tiene comandos. "
                            "Considere agregar comandos que representen las acciones del dominio."
                        ),
                        affected_aggregate=agg_name,
                        affected_elements=[agg_name],
                        suggestion=(f"Agregue al menos un comando al agregado '{agg_name}'."),
                    )
                )

            # Rule 2: aggregate_has_events
            events = [n for n in agg.nodos if n.tipo_elemento == "Evento"]
            if not events:
                gaps.append(
                    CompletenessGap(
                        rule_name="aggregate_has_events",
                        description=(
                            f"Agregado '{agg_name}' no tiene eventos. "
                            "Todo agregado DDD debe producir al menos un evento de dominio."
                        ),
                        affected_aggregate=agg_name,
                        affected_elements=[agg_name],
                        suggestion=(
                            f"Agregue al menos un evento (e.g., '{agg_name[:-1]}Creado' "
                            f"si el agregado termina en 's') al agregado '{agg_name}'."
                        ),
                    )
                )

            # Rule 3: command_produces_event
            event_ids = {n.id for n in agg.nodos if n.tipo_elemento == "Evento"}
            {e.destino for e in agg.aristas}
            for cmd in commands:
                # Check if this command has an outgoing edge to any event
                cmd_targets = {e.destino for e in agg.aristas if e.fuente == cmd.id}
                if not cmd_targets.intersection(event_ids):
                    suggested_event = (
                        cmd.nombre.replace("Crear", "Creado")
                        .replace("Actualizar", "Actualizado")
                        .replace("Eliminar", "Eliminado")
                    )
                    gaps.append(
                        CompletenessGap(
                            rule_name="command_produces_event",
                            description=(f"Comando '{cmd.nombre}' en agregado '{agg_name}' no produce ningún evento."),
                            affected_aggregate=agg_name,
                            affected_elements=[cmd.id],
                            suggestion=(
                                f"Agregue un evento '{suggested_event}' y una arista desde '{cmd.nombre}' hacia él."
                            ),
                        )
                    )

            # Rule 4: aggregate_has_root_entity
            if not agg.entidad_raiz:
                gaps.append(
                    CompletenessGap(
                        rule_name="aggregate_has_root_entity",
                        description=f"Agregado '{agg_name}' no tiene entidad raíz definida.",
                        affected_aggregate=agg_name,
                        affected_elements=[agg_name],
                        suggestion=f"Defina la entidad raíz del agregado '{agg_name}'.",
                    )
                )
            else:
                node_names = {n.nombre for n in agg.nodos}
                if agg.entidad_raiz not in node_names:
                    gaps.append(
                        CompletenessGap(
                            rule_name="aggregate_has_root_entity",
                            description=(
                                f"Agregado '{agg_name}' tiene entidad raíz '{agg.entidad_raiz}' "
                                "que no coincide con ningún nodo del agregado."
                            ),
                            affected_aggregate=agg_name,
                            affected_elements=[agg_name],
                            suggestion=(
                                f"Asegúrese de que '{agg.entidad_raiz}' existe como nodo en el agregado '{agg_name}'."
                            ),
                        )
                    )

        # Rule 5: bounded_context_has_read_models (soft check)
        if model.agregados and not model.read_models:
            gaps.append(
                CompletenessGap(
                    rule_name="bounded_context_has_read_models",
                    description="El modelo no define Read Models.",
                    affected_aggregate="_global",
                    affected_elements=[],
                    suggestion="Considere agregar vistas de lectura para los flujos de consulta.",
                )
            )

        return gaps

    @staticmethod
    def get_rules() -> list[str]:
        """Return the list of registered completeness rule names."""
        return [
            "aggregate_has_commands",
            "aggregate_has_events",
            "command_produces_event",
            "aggregate_has_root_entity",
            "bounded_context_has_read_models",
        ]
