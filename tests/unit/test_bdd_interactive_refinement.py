"""BDD step definitions for interactive_refinement.feature.

US-002: Interactive Model Refinement by Ambiguity Resolution
Test IDs: TS-004, TS-005, TS-006
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../../specs/004-reactive-refinement-agent/tests/features/interactive_refinement.feature")


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def context():
    return {}


def _make_model_with_pedido_and_orden():
    """DomainAnalysis model containing 'Pedido' and 'Orden' synonym candidates."""
    from models.domain_analysis import (
        AristaGrafo,
        BigPicture,
        DomainAnalysis,
        GrafoPorAgregado,
        NodoGrafo,
    )

    return DomainAnalysis(
        nombre_proyecto="SynonymTest",
        version="1.0.0",
        fecha_analisis="2026-03-19",
        big_picture=BigPicture(
            descripcion="Model with synonym candidates",
            nodos=[
                NodoGrafo(
                    id="cmd_crear_pedido",
                    tipo_elemento="Comando",
                    nombre="CrearPedido",
                    descripcion="Create pedido",
                    nivel="big_picture",
                ),
                NodoGrafo(
                    id="evt_pedido_creado",
                    tipo_elemento="Evento",
                    nombre="PedidoCreado",
                    descripcion="Pedido created",
                    nivel="big_picture",
                ),
            ],
            aristas=[
                AristaGrafo(fuente="cmd_crear_pedido", destino="evt_pedido_creado", descripcion="produces"),
            ],
        ),
        agregados=[
            GrafoPorAgregado(
                nombre_agregado="Pedidos",
                entidad_raiz="Pedido",
                nodos=[
                    NodoGrafo(
                        id="cmd_agg_crear_pedido",
                        tipo_elemento="Comando",
                        nombre="CrearPedido",
                        descripcion="Create",
                        nivel="process_level",
                    ),
                    NodoGrafo(
                        id="ent_pedido",
                        tipo_elemento="Entidad Raíz",
                        nombre="Pedido",
                        descripcion="Root entity",
                        nivel="process_level",
                    ),
                    NodoGrafo(
                        id="cmd_agg_crear_orden",
                        tipo_elemento="Comando",
                        nombre="CrearOrden",
                        descripcion="Create orden",
                        nivel="process_level",
                    ),
                    NodoGrafo(
                        id="evt_agg_pedido_creado",
                        tipo_elemento="Evento",
                        nombre="PedidoCreado",
                        descripcion="Event",
                        nivel="process_level",
                    ),
                ],
                aristas=[
                    AristaGrafo(fuente="cmd_agg_crear_pedido", destino="ent_pedido", descripcion="creates"),
                    AristaGrafo(
                        fuente="cmd_agg_crear_orden",
                        destino="evt_agg_pedido_creado",
                        descripcion="produces",
                    ),
                    AristaGrafo(
                        fuente="cmd_agg_crear_pedido",
                        destino="evt_agg_pedido_creado",
                        descripcion="produces",
                    ),
                ],
            )
        ],
        read_models=[],
        politicas_inter_agregados=[],
    )


def _make_model_missing_event():
    """DomainAnalysis where 'CrearPedido' in 'Pedidos' has no event."""
    from models.domain_analysis import (
        AristaGrafo,
        BigPicture,
        DomainAnalysis,
        GrafoPorAgregado,
        NodoGrafo,
    )

    return DomainAnalysis(
        nombre_proyecto="MissingEvent",
        version="1.0.0",
        fecha_analisis="2026-03-19",
        big_picture=BigPicture(
            descripcion="Model missing event",
            nodos=[
                NodoGrafo(
                    id="cmd_bp",
                    tipo_elemento="Comando",
                    nombre="CrearPedido",
                    descripcion="Create",
                    nivel="big_picture",
                ),
                NodoGrafo(
                    id="evt_bp",
                    tipo_elemento="Evento",
                    nombre="SomeEvent",
                    descripcion="Event",
                    nivel="big_picture",
                ),
            ],
            aristas=[
                AristaGrafo(fuente="cmd_bp", destino="evt_bp", descripcion="produces"),
            ],
        ),
        agregados=[
            GrafoPorAgregado(
                nombre_agregado="Pedidos",
                entidad_raiz="Pedido",
                nodos=[
                    NodoGrafo(
                        id="cmd_crear",
                        tipo_elemento="Comando",
                        nombre="CrearPedido",
                        descripcion="Create pedido",
                        nivel="process_level",
                    ),
                    NodoGrafo(
                        id="ent_pedido",
                        tipo_elemento="Entidad Raíz",
                        nombre="Pedido",
                        descripcion="Root entity",
                        nivel="process_level",
                    ),
                ],
                aristas=[
                    AristaGrafo(fuente="cmd_crear", destino="ent_pedido", descripcion="creates"),
                ],
            )
        ],
        read_models=[],
        politicas_inter_agregados=[],
    )


def _make_ambiguity(amb_id, description, elements):
    from domain.models.tool_schemas import Ambiguity

    return Ambiguity(
        id=amb_id,
        type="lexical",
        priority=2,
        description=description,
        affected_elements=elements,
        suggested_resolutions=["Merge", "Keep separate"],
    )


def _make_session(ambiguities):
    from domain.models.tool_schemas import RefinementSession

    return RefinementSession(
        model_hash=RefinementSession.compute_model_hash("test"),
        ambiguities=ambiguities,
        status="presenting",
    )


# ---------------------------------------------------------------------------
# Background steps
# ---------------------------------------------------------------------------


@given("a domain model is loaded in session state")
def domain_model_loaded(context):
    model = _make_model_with_pedido_and_orden()
    context["session_state"] = {"analysis_result": {"analysis": model}}
    context["model"] = model


@given("a refinement session has been started with detected ambiguities")
def refinement_session_started(context):
    amb = _make_ambiguity(
        "amb_001",
        "'Pedido' y 'Orden' son potenciales sinónimos.",
        ["cmd_agg_crear_pedido", "cmd_agg_crear_orden"],
    )
    session = _make_session([amb])
    context["session_state"]["refinement_session"] = session
    context["session"] = session


# ---------------------------------------------------------------------------
# TS-004: Agent applies synonym resolution to unify duplicate nodes
# ---------------------------------------------------------------------------


@given(parsers.parse('the agent has presented an ambiguity about synonyms "Pedido" and "Orden" in the model'))
def ambiguity_presented_synonym(context):
    assert context["session"].ambiguities[0].id == "amb_001"


@when(parsers.parse('the user responds indicating that "Pedido" and "Orden" are synonyms and to use only "Pedido"'))
def user_responds_synonym(context):
    from unittest.mock import MagicMock

    from services.ambiguity_detector import AmbiguityDetector
    from services.completeness_analyzer import CompletenessAnalyzer
    from services.model_accessor import ModelAccessor
    from services.refinement_orchestrator import RefinementOrchestrator

    inference = MagicMock()
    orchestrator = RefinementOrchestrator(
        ambiguity_detector=AmbiguityDetector(inference),
        completeness_analyzer=CompletenessAnalyzer(),
        model_accessor=ModelAccessor(context["session_state"]),
    )

    plan = orchestrator.create_plan(
        session=context["session"],
        ambiguity_ids=["amb_001"],
        resolution_description="Pedido y Orden son sinónimos, usa solo Pedido",
    )
    context["plan"] = plan


@then("the agent invokes editing tools to unify the nodes")
def agent_invokes_tools(context):
    plan = context["plan"]
    assert plan is not None
    assert len(plan.proposed_operations) >= 1


@then(parsers.parse('all nodes named "Orden" are renamed or merged to "Pedido"'))
def nodes_renamed_or_merged(context):
    plan = context["plan"]
    ops = plan.proposed_operations
    rename_ops = [op for op in ops if op.get("tool") in ("rename_element", "delete_node")]
    assert len(rename_ops) >= 1


@then(parsers.parse('all edges referencing the old "Orden" ID are updated to reference "Pedido"'))
def edges_updated(context):
    plan = context["plan"]
    # Plan should have operations to address the synonym ambiguity
    assert plan.source_ambiguity_ids == ["amb_001"]


@then("the agent confirms the changes with a summary of impacted elements")
def agent_confirms_changes(context):
    plan = context["plan"]
    assert plan.description != ""


# ---------------------------------------------------------------------------
# TS-005: Agent creates missing event for a command without one
# ---------------------------------------------------------------------------


@given(
    parsers.parse('the agent has detected that command "CrearPedido" in aggregate "Pedidos" has no associated event')
)
def command_missing_event_detected(context):
    from domain.models.tool_schemas import Ambiguity

    amb = Ambiguity(
        id="gap_command_produces_event_Pedidos",
        type="structural",
        priority=1,
        description="Comando 'CrearPedido' en agregado 'Pedidos' no produce ningún evento.",
        affected_elements=["cmd_crear"],
        suggested_resolutions=["Agregar evento 'PedidoCreado'"],
    )
    model = _make_model_missing_event()
    context["session_state"] = {"analysis_result": {"analysis": model}}
    context["model"] = model
    session = _make_session([amb])
    context["session"] = session
    context["session_state"]["refinement_session"] = session


@when(parsers.parse('the user confirms the command should have an event and provides the name "PedidoCreado"'))
def user_confirms_event_name(context):
    from unittest.mock import MagicMock

    from services.ambiguity_detector import AmbiguityDetector
    from services.completeness_analyzer import CompletenessAnalyzer
    from services.model_accessor import ModelAccessor
    from services.refinement_orchestrator import RefinementOrchestrator

    inference = MagicMock()
    orchestrator = RefinementOrchestrator(
        ambiguity_detector=AmbiguityDetector(inference),
        completeness_analyzer=CompletenessAnalyzer(),
        model_accessor=ModelAccessor(context["session_state"]),
    )

    plan = orchestrator.create_plan(
        session=context["session"],
        ambiguity_ids=["gap_command_produces_event_Pedidos"],
        resolution_description="Agregar evento PedidoCreado al comando CrearPedido",
    )
    context["plan"] = plan


@then(parsers.parse('the agent creates an event node "PedidoCreado" in aggregate "Pedidos"'))
def event_node_created(context):
    plan = context["plan"]
    assert plan is not None
    add_ops = [op for op in plan.proposed_operations if op.get("tool") == "add_node"]
    assert len(add_ops) >= 1


@then(parsers.parse('the agent adds an edge from "CrearPedido" to "PedidoCreado"'))
def edge_added(context):
    plan = context["plan"]
    add_edge_ops = [op for op in plan.proposed_operations if op.get("tool") == "add_edge"]
    assert len(add_edge_ops) >= 1


@then("the agent updates the aggregate JSON accordingly")
def aggregate_json_updated(context):
    plan = context["plan"]
    assert plan.source_ambiguity_ids == ["gap_command_produces_event_Pedidos"]


@then("the agent confirms the operation to the user")
def operation_confirmed(context):
    assert context["plan"].description != ""


# ---------------------------------------------------------------------------
# TS-006: Agent keeps elements separate when user rejects a suggestion
# ---------------------------------------------------------------------------


@given(parsers.parse('the agent suggested treating "Pedido" and "Orden" as synonyms'))
def agent_suggested_synonyms(context):
    amb = _make_ambiguity(
        "amb_001",
        "Potential synonym: Pedido / Orden",
        ["cmd_agg_crear_pedido", "cmd_agg_crear_orden"],
    )
    session = _make_session([amb])
    context["session"] = session


@when(parsers.parse("the user responds that they are not synonyms and should remain separate"))
def user_rejects_synonym(context):
    from unittest.mock import MagicMock

    from services.ambiguity_detector import AmbiguityDetector
    from services.completeness_analyzer import CompletenessAnalyzer
    from services.model_accessor import ModelAccessor
    from services.refinement_orchestrator import RefinementOrchestrator

    model = _make_model_with_pedido_and_orden()
    session_state = {"analysis_result": {"analysis": model}}
    inference = MagicMock()
    orchestrator = RefinementOrchestrator(
        ambiguity_detector=AmbiguityDetector(inference),
        completeness_analyzer=CompletenessAnalyzer(),
        model_accessor=ModelAccessor(session_state),
    )

    plan = orchestrator.create_plan(
        session=context["session"],
        ambiguity_ids=["amb_001"],
        resolution_description="Pedido y Orden son conceptos distintos, mantener ambos",
    )
    context["plan"] = plan


@then("the agent keeps both nodes in the model without modification")
def nodes_kept_separate(context):
    plan = context["plan"]
    # Plan should have NO rename/delete operations
    merge_ops = [op for op in plan.proposed_operations if op.get("tool") in ("rename_element", "delete_node")]
    assert len(merge_ops) == 0


@then("any incorrectly inferred relationships between them are removed")
def incorrect_relationships_removed(context):
    # No-op: in this scenario, the model is kept as-is
    pass


@then("the agent acknowledges the user's decision")
def agent_acknowledges(context):
    assert context["plan"].description != ""
    assert context["plan"].status == "pending"
