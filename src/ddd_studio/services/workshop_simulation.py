"""Inter-agent Event Storming workshop simulation service.

Two agents converse to surface domain elements:
- WorkshopFacilitator: follows a structured phase plan to extract DDD elements
  systematically from the document.
- WorkshopDomainExpert: answers grounded strictly in the provided document,
  identifying and labeling DDD element types explicitly.

The resulting conversation is a transcript ready for the semantic_analysis pipeline.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class WorkshopTurn:
    """A single exchange in the workshop conversation."""

    turn_number: int
    facilitator: str
    expert: str


@dataclass
class WorkshopSimulation:
    """Complete result of an inter-agent workshop simulation."""

    turns: list[WorkshopTurn] = field(default_factory=list)

    @property
    def transcript(self) -> str:
        """Return the full conversation as a plain transcript for the analysis pipeline."""
        lines = []
        for t in self.turns:
            lines.append(f"Facilitador: {t.facilitator}")
            lines.append(f"Experto de Dominio: {t.expert}")
            lines.append("")
        return "\n".join(lines).strip()

    def conversation_history_up_to(self, turn_index: int) -> str:
        """Return formatted history for turns before turn_index."""
        if turn_index == 0:
            return "Ninguna todavía. Esta es la primera pregunta del taller."
        lines = []
        for t in self.turns[:turn_index]:
            lines.append(f"Facilitador (turno {t.turn_number}): {t.facilitator}")
            lines.append(f"Experto (turno {t.turn_number}): {t.expert}")
        return "\n".join(lines)


# ── Phase plan for deterministic element extraction ──────────────────────

_PHASE_PLAN = [
    {
        "phase": "Contexto Operativo",
        "focus": "Identificar el flujo de trabajo funcional y los actores reales del negocio",
        "target_elements": "Actor, Sistema Externo",
        "question_guide": "¿Cuál es el proceso de negocio principal? ¿Quién opera realmente el sistema?",
    },
    {
        "phase": "Acciones de Negocio (Comandos)",
        "focus": "Extraer las intenciones que disparan lógica de negocio real",
        "target_elements": "Comando",
        "question_guide": "¿Qué acciones funcionales cambian el estado del negocio? Ignorar trámites administrativos.",
    },
    {
        "phase": "Hitos de Negocio (Eventos)",
        "focus": "Identificar hechos significativos para la operación",
        "target_elements": "Evento de Dominio",
        "question_guide": "¿Qué resultados funcionales son críticos para el éxito del proceso?",
    },
    {
        "phase": "Entidades de Dominio (Agregados)",
        "focus": "Identificar los conceptos de negocio que encapsulan lógica",
        "target_elements": "Agregado",
        "question_guide": "¿Qué concepto de negocio es dueño de esta lógica y protege sus reglas?",
    },
    {
        "phase": "Reglas Reactivas (Políticas)",
        "focus": "Descubrir automatizaciones y disparadores de flujo",
        "target_elements": "Política",
        "question_guide": "¿Qué lógica de negocio se dispara automáticamente tras un hito funcional?",
    },
    {
        "phase": "Información para Decisiones (Read Models)",
        "focus": "Identificar qué datos funcionales necesita el usuario",
        "target_elements": "Read Model",
        "question_guide": "¿Qué información del dominio es vital para que el actor tome su siguiente decisión?",
    },
    {
        "phase": "Ecosistema Técnico (Sistemas Externos)",
        "focus": "Identificar integraciones que aportan o consumen datos de negocio",
        "target_elements": "Sistema Externo",
        "question_guide": "¿Con qué plataformas funcionales debe interactuar el sistema?",
    },
    {
        "phase": "Riesgos y Vacíos Funcionales (Hotspots)",
        "focus": "Identificar incertidumbres en los requerimientos de negocio",
        "target_elements": "Hotspot",
        "question_guide": "¿Qué parte de la lógica funcional está incompleta o es ambigua?",
    },
    {
        "phase": "Síntesis de Capacidades (Cierre)",
        "focus": "Consolidar el alcance funcional descubierto",
        "target_elements": "Resumen de Capacidades",
        "question_guide": "¿Cómo resumirías las capacidades funcionales clave de este dominio?",
    },
]


def _get_phase_for_turn(turn_number: int, total_turns: int) -> dict:
    """Map a turn number to a phase from the plan, distributing evenly."""
    num_phases = len(_PHASE_PLAN)
    # Use proportional distribution to avoid getting stuck in the last phase
    phase_index = int(((turn_number - 1) / total_turns) * num_phases)
    return _PHASE_PLAN[min(phase_index, num_phases - 1)]


def _build_discovered_summary(conversation_history: str) -> str:
    """Build a structured summary of elements discovered so far from conversation text."""
    if not conversation_history or "primera pregunta" in conversation_history:
        return "Nada descubierto todavía."

    lower = conversation_history.lower()

    # More comprehensive keywords tied to DDD element types
    element_checks = {
        "Actor": [
            "actor:",
            "[actor]",
            "**actor**",
            "rol:",
            "usuario:",
            "cliente",
            "operador",
            "administrador",
        ],
        "Comando": [
            "comando:",
            "[comando]",
            "**comando**",
            "acción:",
            "solicitar",
            "crear",
            "procesar",
            "ejecutar",
            "aprobar",
            "enviar",
        ],
        "Evento de Dominio": [
            "evento:",
            "[evento]",
            "**evento**",
            "fue creado",
            "fue procesado",
            "fue enviado",
            "ocurrió",
            "se generó",
            "se registró",
        ],
        "Agregado": [
            "agregado:",
            "[agregado]",
            "**agregado**",
            "entidad raíz",
            "entidad:",
            "gestiona el estado",
        ],
        "Política": [
            "política:",
            "[política]",
            "**política**",
            "regla de negocio",
            "cuando ocurre",
            "siempre que",
            "entonces ejecutar",
        ],
        "Read Model": [
            "read model:",
            "[read model]",
            "vista:",
            "reporte:",
            "dashboard",
            "pantalla:",
            "consulta:",
        ],
        "Sistema Externo": [
            "sistema externo:",
            "[sistema externo]",
            "api:",
            "gateway",
            "integración",
            "servicio externo",
            "crm",
        ],
        "Hotspot": [
            "hotspot:",
            "[hotspot]",
            "**hotspot**",
            "no está claro",
            "riesgo:",
            "pendiente",
            "incertidumbre",
            "duda:",
        ],
    }

    found = []
    for element, keywords in element_checks.items():
        if any(kw in lower for kw in keywords):
            found.append(f"- {element}: DESCUBIERTO")
        else:
            found.append(f"- {element}: pendiente")

    return "\n".join(found)


class WorkshopSimulator:
    """Orchestrates an inter-agent Event Storming workshop simulation.

    Follows a deterministic phase plan to systematically extract DDD elements
    from the provided document. Each turn targets a specific element type.
    """

    def __init__(self, inference) -> None:
        self._inference = inference

    def simulate(
        self,
        context: str,
        num_turns: int = 8,
        on_turn: Callable[[WorkshopTurn], None] | None = None,
    ) -> WorkshopSimulation:
        """Run the inter-agent simulation.

        Args:
            context: Business/domain description the expert agent uses as knowledge base.
            num_turns: Number of facilitator-expert exchanges (default 8, max 20).
            on_turn: Optional callback invoked after each turn completes.

        Returns:
            WorkshopSimulation with all turns and a `.transcript` property.
        """
        from prompts import registry

        num_turns = min(max(num_turns, 2), 20)
        simulation = WorkshopSimulation()

        for i in range(num_turns):
            turn_number = i + 1
            history = simulation.conversation_history_up_to(i)
            discovered = _build_discovered_summary(history)
            phase = _get_phase_for_turn(turn_number, num_turns)

            # NLP anchoring removed — spaCy extractor deleted.

            # ── Facilitator generates question ──────────────────────────
            # Enhanced prompt to avoid redundancy and follow the proportional phase plan
            facilitator_base_prompt = (
                registry.get("workshop_facilitator_agent")
                .render(
                    context=context,
                    conversation_history=history,
                    discovered_elements=discovered,
                    turn_number=str(turn_number),
                    total_turns=str(num_turns),
                    current_phase=phase["phase"],
                    phase_focus=phase["focus"],
                    target_elements=phase["target_elements"],
                    question_guide=phase["question_guide"],
                )
                .to_string()
            )

            # Add a dynamic constraint to avoid repeating discovered elements
            facilitator_prompt = (
                "STRICT CONSTRAINT: Do NOT ask about elements already marked as 'DESCUBIERTO' in the summary below. "
                "Instead, move to the next logical step in the phase plan.\n\n"
                f"{facilitator_base_prompt}"
            )

            facilitator_question = self._inference.invoke_text(facilitator_prompt).strip()

            # ── Expert generates answer ─────────────────────────────────
            # Ground the expert with deterministic NLP anchors from the source document
            base_expert_prompt = (
                registry.get("workshop_domain_expert_agent")
                .render(
                    context=context,
                    conversation_history=history,
                    facilitator_question=facilitator_question,
                    current_phase=phase["phase"],
                    target_elements=phase["target_elements"],
                )
                .to_string()
            )

            expert_prompt = base_expert_prompt

            expert_answer = self._inference.invoke_text(expert_prompt).strip()

            turn = WorkshopTurn(
                turn_number=turn_number,
                facilitator=facilitator_question,
                expert=expert_answer,
            )
            simulation.turns.append(turn)

            if on_turn:
                on_turn(turn)

        return simulation
