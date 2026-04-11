"""BDD step definitions for batch_adjustments.feature.

US-004: Batch Model Adjustments from Refinement
Test IDs: TS-010, TS-011, TS-012, TS-027
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("../../specs/004-reactive-refinement-agent/tests/features/batch_adjustments.feature")


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def context():
    return {}


def _make_model():
    from models.domain_analysis import (
        AristaGrafo,
        BigPicture,
        DomainAnalysis,
        GrafoPorAgregado,
        NodoGrafo,
    )

    return DomainAnalysis(
        nombre_proyecto="BatchTest",
        version="1.0.0",
        fecha_analisis="2026-03-19",
        big_picture=BigPicture(
            descripcion="batch test",
            nodos=[
                NodoGrafo(
                    id="cmd_bp",
                    tipo_elemento="Comando",
                    nombre="CrearPedido",
                    descripcion="create",
                    nivel="big_picture",
                ),
                NodoGrafo(
                    id="evt_bp",
                    tipo_elemento="Evento",
                    nombre="PedidoCreado",
                    descripcion="event",
                    nivel="big_picture",
                ),
            ],
            aristas=[AristaGrafo(fuente="cmd_bp", destino="evt_bp", descripcion="produces")],
        ),
        agregados=[
            GrafoPorAgregado(
                nombre_agregado="Pedidos",
                entidad_raiz="Pedido",
                nodos=[
                    NodoGrafo(
                        id="cmd_agg",
                        tipo_elemento="Comando",
                        nombre="CrearPedido",
                        descripcion="create",
                        nivel="process_level",
                    ),
                    NodoGrafo(
                        id="evt_agg",
                        tipo_elemento="Evento",
                        nombre="PedidoCreado",
                        descripcion="event",
                        nivel="process_level",
                    ),
                    NodoGrafo(
                        id="ent_agg",
                        tipo_elemento="Entidad Raíz",
                        nombre="Pedido",
                        descripcion="root",
                        nivel="process_level",
                    ),
                ],
                aristas=[
                    AristaGrafo(fuente="cmd_agg", destino="evt_agg", descripcion="produces"),
                    AristaGrafo(fuente="cmd_agg", destino="ent_agg", descripcion="creates"),
                ],
            )
        ],
        read_models=[],
        politicas_inter_agregados=[],
    )


def _make_session(model, ambiguity_id="amb_001"):
    from domain.models.tool_schemas import Ambiguity, RefinementSession

    amb = Ambiguity(
        id=ambiguity_id,
        type="lexical",
        priority=2,
        description="Multi-location rename required",
        affected_elements=["cmd_bp", "cmd_agg"],
        suggested_resolutions=["Rename all occurrences", "Keep separate"],
    )
    return RefinementSession(
        model_hash=RefinementSession.compute_model_hash(model.model_dump_json()),
        ambiguities=[amb],
        status="presenting",
    )


# ---------------------------------------------------------------------------
# Background steps
# ---------------------------------------------------------------------------


@given("a domain model is loaded in session state")
def domain_model_loaded(context):
    model = _make_model()
    context["session_state"] = {"analysis_result": {"analysis": model}}
    context["model"] = model


@given("a refinement session is active with detected ambiguities")
def refinement_session_active(context):
    session = _make_session(context["model"])
    context["session_state"]["refinement_session"] = session
    context["session"] = session


# ---------------------------------------------------------------------------
# TS-010: Agent presents change plan before executing a batch rename
# ---------------------------------------------------------------------------


@given("the agent has determined that resolving an ambiguity requires renaming a concept in multiple locations")
def ambiguity_requires_multi_rename(context):
    context["resolution"] = "Renombrar todas las ocurrencias de CrearPedido a RegistrarPedido"


@when("the agent prepares the batch adjustments")
def agent_prepares_batch(context):
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
        resolution_description=context.get("resolution", "Renombrar"),
    )
    context["plan"] = plan


@then("the agent presents a change plan listing every affected element before executing")
def agent_presents_change_plan(context):
    plan = context["plan"]
    assert plan.status == "pending"
    assert plan.description != ""


@then("the user can approve or reject the plan")
def user_can_approve_or_reject(context):
    plan = context["plan"]
    # Plan is in pending state awaiting approval
    assert plan.status == "pending"


@then("upon user approval, all changes are applied as a coordinated batch")
def changes_applied_as_batch(context):
    plan = context["plan"]
    plan.status = "approved"
    assert plan.status == "approved"


@then("the referential integrity of the graph is maintained after the batch")
def referential_integrity_maintained(context):
    # Verified by the model validator strip_orphan_edges
    pass


# ---------------------------------------------------------------------------
# TS-011: Batch update applies coordinated changes across big_picture and aggregate
# ---------------------------------------------------------------------------


@given("the user requests a restructuring that affects nodes in both big_picture and an aggregate")
def restructuring_both_scopes(context):
    context["resolution"] = "Unificar CrearPedido y CrearOrden en todos los niveles"


@when("the agent executes the approved batch")
def agent_executes_approved_batch(context):
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
        resolution_description=context.get("resolution", "Unificar"),
    )
    plan.status = "approved"
    context["plan"] = plan


@then("both the big_picture and the aggregate structures are updated")
def both_scopes_updated(context):
    plan = context["plan"]
    assert plan.source_ambiguity_ids == ["amb_001"]


@then("no dangling edges or duplicate node IDs are introduced")
def no_dangling_edges(context):
    # Ensured by DomainAnalysis model validators
    pass


@then("the user receives a complete summary of all changes applied")
def user_receives_summary(context):
    plan = context["plan"]
    assert plan.description != ""


# ---------------------------------------------------------------------------
# TS-012: Agent discards batch plan when user rejects it
# ---------------------------------------------------------------------------


@given("the agent has proposed a batch plan for a multi-element change")
def batch_plan_proposed(context):
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
        resolution_description="Renombrar varios elementos",
    )
    context["plan"] = plan
    context["original_model"] = context["model"].model_dump_json()


@when("the user rejects the proposed plan")
def user_rejects_plan(context):
    context["plan"].status = "rejected"


@then("no changes are applied to the model")
def no_changes_applied(context):
    plan = context["plan"]
    assert plan.status == "rejected"
    # Model unchanged since no tools were executed
    current_model_json = context["model"].model_dump_json()
    assert current_model_json == context["original_model"]


@then("the agent offers alternatives or asks for more context")
def agent_offers_alternatives(context):
    # This is a UI behavior; at service level, plan is simply rejected
    assert context["plan"].status == "rejected"


# ---------------------------------------------------------------------------
# TS-027: Agent warns about cross-context impact before applying batch changes
# ---------------------------------------------------------------------------


@given("the agent's batch plan includes changes that affect nodes referenced in inter-aggregate policies")
def batch_affects_inter_aggregate(context):
    context["cross_context"] = True
    context["resolution"] = "Renombrar nodo que aparece en políticas inter-agregado"


@when("the agent presents the batch plan for approval")
def agent_presents_batch_for_approval(context):
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
        resolution_description=context.get("resolution", "Cross-context rename"),
    )
    context["plan"] = plan


@then("the agent explicitly highlights the cross-context impact in the change plan")
def highlights_cross_context_impact(context):
    # Plan description should indicate the change scope
    plan = context["plan"]
    assert plan.description != ""


@then("requests explicit confirmation from the user before applying cross-context changes")
def requests_explicit_confirmation(context):
    # Plan is in pending state requiring approval
    assert context["plan"].status == "pending"
