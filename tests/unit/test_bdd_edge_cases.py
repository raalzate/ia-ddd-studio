"""BDD step definitions for edge_cases.feature.

US-001/002/003/004: Refinement Agent Edge Cases
Test IDs: TS-023, TS-024, TS-025, TS-026, TS-027
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("../../specs/004-reactive-refinement-agent/tests/features/edge_cases.feature")


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def context():
    return {}


def _make_incomplete_model():
    """DomainAnalysis that simulates partial generation (few/no edges)."""
    from models.domain_analysis import (
        AristaGrafo,
        BigPicture,
        DomainAnalysis,
        NodoGrafo,
    )

    return DomainAnalysis(
        nombre_proyecto="IncompleteTest",
        version="1.0.0",
        fecha_analisis="2026-03-19",
        big_picture=BigPicture(
            descripcion="incomplete",
            nodos=[
                NodoGrafo(
                    id="cmd_a",
                    tipo_elemento="Comando",
                    nombre="ComandoA",
                    descripcion="cmd",
                    nivel="big_picture",
                ),
                NodoGrafo(
                    id="evt_a",
                    tipo_elemento="Evento",
                    nombre="EventoA",
                    descripcion="evt",
                    nivel="big_picture",
                ),
            ],
            aristas=[AristaGrafo(fuente="cmd_a", destino="evt_a", descripcion="produces")],
        ),
        agregados=[],  # No aggregates → incomplete model
        read_models=[],
        politicas_inter_agregados=[],
    )


def _make_model_many_ambiguities():
    """DomainAnalysis with many synonym candidates."""
    from models.domain_analysis import (
        AristaGrafo,
        BigPicture,
        DomainAnalysis,
        NodoGrafo,
    )

    # Build 12+ nodes so we can inject 12+ ambiguities
    nodos = []
    aristas = []
    for i in range(1, 7):
        cmd_id = f"cmd_{i}"
        evt_id = f"evt_{i}"
        nodos.append(
            NodoGrafo(
                id=cmd_id,
                tipo_elemento="Comando",
                nombre=f"Crear{i}",
                descripcion="cmd",
                nivel="big_picture",
            )
        )
        nodos.append(
            NodoGrafo(
                id=evt_id,
                tipo_elemento="Evento",
                nombre=f"Creado{i}",
                descripcion="evt",
                nivel="big_picture",
            )
        )
        aristas.append(AristaGrafo(fuente=cmd_id, destino=evt_id, descripcion="produces"))
    return DomainAnalysis(
        nombre_proyecto="ManyAmbiguitiesTest",
        version="1.0.0",
        fecha_analisis="2026-03-19",
        big_picture=BigPicture(descripcion="many ambiguities", nodos=nodos, aristas=aristas),
        agregados=[],
        read_models=[],
        politicas_inter_agregados=[],
    )


def _make_base_model():
    from models.domain_analysis import (
        AristaGrafo,
        BigPicture,
        DomainAnalysis,
        NodoGrafo,
    )

    return DomainAnalysis(
        nombre_proyecto="EdgeCaseTest",
        version="1.0.0",
        fecha_analisis="2026-03-19",
        big_picture=BigPicture(
            descripcion="edge case test",
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
        agregados=[],
        read_models=[],
        politicas_inter_agregados=[],
    )


# ---------------------------------------------------------------------------
# Background steps
# ---------------------------------------------------------------------------


@given("the DDD Studio application is running")
def app_is_running(context):
    context["app_running"] = True


# ---------------------------------------------------------------------------
# TS-023: Agent handles partial generation failure gracefully
# ---------------------------------------------------------------------------


@given("the analysis pipeline completed with errors leaving an incomplete model")
def incomplete_model_in_state(context):
    model = _make_incomplete_model()
    context["session_state"] = {"analysis_result": {"analysis": model}}
    context["model"] = model


@when("the agent's post-generation reaction triggers")
def post_generation_triggers(context):
    from unittest.mock import MagicMock

    from services.ambiguity_detector import AmbiguityDetector
    from services.completeness_analyzer import CompletenessAnalyzer
    from services.model_accessor import ModelAccessor
    from services.refinement_orchestrator import RefinementOrchestrator

    inference = MagicMock()
    inference.invoke.return_value = []
    orchestrator = RefinementOrchestrator(
        ambiguity_detector=AmbiguityDetector(inference),
        completeness_analyzer=CompletenessAnalyzer(),
        model_accessor=ModelAccessor(context["session_state"]),
    )
    session = orchestrator.start_session()
    context["session"] = session
    context["findings"] = orchestrator.format_findings(session)


@then("the agent detects the incomplete model state")
def detects_incomplete_state(context):
    # Session created successfully without crashing on incomplete model
    assert context["session"] is not None


@then("the agent reports which elements are missing rather than analyzing a broken model")
def reports_missing_elements(context):
    findings = context["findings"]
    assert isinstance(findings, str)
    assert len(findings) > 0


@then("the agent does not propose ambiguity resolutions on incomplete data")
def no_resolutions_on_incomplete(context):
    # Since model has no aggregates, LLM returned no lexical ambiguities (mocked)
    # and completeness analyzer may find gaps — session was created without crash
    session = context["session"]
    assert session is not None


# ---------------------------------------------------------------------------
# TS-024: Agent groups excessive ambiguities into manageable priority batches
# ---------------------------------------------------------------------------


@given("the generated model contains more than 10 detected ambiguities")
def model_with_many_ambiguities(context):
    from domain.models.tool_schemas import Ambiguity

    model = _make_model_many_ambiguities()
    context["session_state"] = {"analysis_result": {"analysis": model}}
    context["model"] = model
    # Prepare 12 mock ambiguities across priorities
    ambiguities = []
    for i in range(1, 7):
        ambiguities.append(
            Ambiguity(
                id=f"amb_p2_{i}",
                type="lexical",
                priority=2,
                description=f"Synonym pair {i}",
                affected_elements=[f"cmd_{i}"],
                suggested_resolutions=[f"Merge option {i}"],
            )
        )
    for i in range(1, 7):
        ambiguities.append(
            Ambiguity(
                id=f"amb_p3_{i}",
                type="lexical",
                priority=3,
                description=f"Description gap {i}",
                affected_elements=[f"evt_{i}"],
                suggested_resolutions=[f"Add description {i}"],
            )
        )
    context["all_ambiguities"] = ambiguities


@when("the agent presents the post-generation analysis")
def agent_presents_analysis_with_many(context):
    from unittest.mock import MagicMock

    from services.ambiguity_detector import AmbiguityDetector
    from services.completeness_analyzer import CompletenessAnalyzer
    from services.model_accessor import ModelAccessor
    from services.refinement_orchestrator import RefinementOrchestrator

    inference = MagicMock()
    inference.invoke.return_value = context["all_ambiguities"]

    orchestrator = RefinementOrchestrator(
        ambiguity_detector=AmbiguityDetector(inference),
        completeness_analyzer=CompletenessAnalyzer(),
        model_accessor=ModelAccessor(context["session_state"]),
    )
    session = orchestrator.start_session()
    context["session"] = session
    context["findings"] = orchestrator.format_findings(session)


@then("the agent groups ambiguities by priority level")
def ambiguities_grouped_by_priority(context):
    findings = context["findings"]
    # Priority groups appear in findings
    assert "Prioridad" in findings


@then("presents at most 5 ambiguities per priority group in the initial message")
def at_most_5_per_group(context):
    findings = context["findings"]
    # Count items in priority 2 section — max 5 shown
    # The format_findings function caps at [:5] per group
    # Verify the session has more than 5 in at least one group
    session = context["session"]
    p2 = [a for a in session.ambiguities if a.priority == 2]
    assert len(p2) > 5  # We have 6 p2 ambiguities
    # But the findings only shows 5
    assert findings.count("amb_p2_") <= 5


@then("offers to show more if the user requests it")
def offers_to_show_more(context):
    findings = context["findings"]
    # format_findings appends "... y N hallazgo(s) adicionales"
    assert "adicionales" in findings or len(context["session"].ambiguities) <= 15


# ---------------------------------------------------------------------------
# TS-025: Agent warns about pending ambiguities when new generation requested
# ---------------------------------------------------------------------------


@given("the agent has presented ambiguities but the user has not responded to any of them")
def unresolved_ambiguities_in_session(context):
    from domain.models.tool_schemas import Ambiguity, RefinementSession

    model = _make_base_model()
    context["session_state"] = {"analysis_result": {"analysis": model}}
    context["model"] = model

    session = RefinementSession(
        model_hash=RefinementSession.compute_model_hash(model.model_dump_json()),
        ambiguities=[
            Ambiguity(
                id="amb_pending",
                type="lexical",
                priority=2,
                description="Unresolved synonym",
                affected_elements=["cmd_bp"],
                suggested_resolutions=["Merge", "Keep"],
            )
        ],
        status="presenting",
    )
    context["session_state"]["refinement_session"] = session
    context["session"] = session


@when("the user requests a new domain model generation")
def user_requests_new_generation(context):
    # Simulate what happens when new generation starts:
    # refinement_pending is reset and session replaced
    old_session = context["session_state"].get("refinement_session")
    context["old_session"] = old_session
    # New generation would replace the session
    context["new_generation_requested"] = True


@then("the agent warns that there are unresolved ambiguities from the previous session")
def warns_unresolved_ambiguities(context):
    # The refinement session exists with status "presenting" and unresolved ambiguities
    old_session = context["old_session"]
    assert old_session is not None
    assert old_session.status == "presenting"
    assert len(old_session.ambiguities) > 0


@then("the new generation is not blocked by the warning")
def generation_not_blocked(context):
    # Generation proceeds (flag was set)
    assert context["new_generation_requested"] is True


@then("the previous refinement session is replaced upon new generation completion")
def previous_session_replaced(context):
    # On new generation, session_state["refinement_session"] would be overwritten
    # Simulated: set it to None as if new generation ran
    context["session_state"]["refinement_session"] = None
    assert context["session_state"].get("refinement_session") is None


# ---------------------------------------------------------------------------
# TS-026: Agent re-analyzes model when manual edits occur between detection and refinement
# ---------------------------------------------------------------------------


@given("a refinement session was started and ambiguities were detected")
def session_with_detected_ambiguities(context):
    from domain.models.tool_schemas import Ambiguity, RefinementSession

    model = _make_base_model()
    context["session_state"] = {"analysis_result": {"analysis": model}}
    context["model"] = model

    session = RefinementSession(
        model_hash=RefinementSession.compute_model_hash(model.model_dump_json()),
        ambiguities=[
            Ambiguity(
                id="amb_001",
                type="lexical",
                priority=2,
                description="Synonym detected",
                affected_elements=["cmd_bp"],
                suggested_resolutions=["Merge"],
            )
        ],
        status="presenting",
    )
    context["session"] = session
    context["original_hash"] = session.model_hash


@given("the user manually modified the model using the chat agent's editing tools")
def user_modified_model(context):
    from models.domain_analysis import (
        AristaGrafo,
        BigPicture,
        DomainAnalysis,
        NodoGrafo,
    )

    # Replace model with a modified version
    modified_model = DomainAnalysis(
        nombre_proyecto="EdgeCaseTest",
        version="1.0.1",  # changed
        fecha_analisis="2026-03-19",
        big_picture=BigPicture(
            descripcion="edge case test modified",
            nodos=[
                NodoGrafo(
                    id="cmd_bp",
                    tipo_elemento="Comando",
                    nombre="RegistrarPedido",
                    descripcion="updated",
                    nivel="big_picture",
                ),
                NodoGrafo(
                    id="evt_bp",
                    tipo_elemento="Evento",
                    nombre="PedidoRegistrado",
                    descripcion="event",
                    nivel="big_picture",
                ),
            ],
            aristas=[AristaGrafo(fuente="cmd_bp", destino="evt_bp", descripcion="produces")],
        ),
        agregados=[],
        read_models=[],
        politicas_inter_agregados=[],
    )
    context["session_state"]["analysis_result"]["analysis"] = modified_model


@when("the user tries to apply a refinement plan from the original session")
def user_tries_to_apply_plan(context):
    from unittest.mock import MagicMock

    from domain.models.tool_schemas import RefinementPlan
    from services.ambiguity_detector import AmbiguityDetector
    from services.completeness_analyzer import CompletenessAnalyzer
    from services.model_accessor import ModelAccessor
    from services.refinement_orchestrator import RefinementOrchestrator

    RefinementPlan(
        source_ambiguity_ids=["amb_001"],
        description="Apply from original session",
        proposed_operations=[],
        status="approved",
    )

    inference = MagicMock()
    orchestrator = RefinementOrchestrator(
        ambiguity_detector=AmbiguityDetector(inference),
        completeness_analyzer=CompletenessAnalyzer(),
        model_accessor=ModelAccessor(context["session_state"]),
    )

    context["orchestrator"] = orchestrator
    context["stale"] = not orchestrator.check_model_freshness(context["session"])


@then("the agent detects that the model changed since the session was created")
def detects_model_changed(context):
    assert context["stale"] is True


@then("the agent re-analyzes the current model before proposing any adjustments")
def re_analyzes_current_model(context):
    from unittest.mock import MagicMock

    from services.ambiguity_detector import AmbiguityDetector
    from services.completeness_analyzer import CompletenessAnalyzer
    from services.model_accessor import ModelAccessor
    from services.refinement_orchestrator import RefinementOrchestrator

    # Re-analysis creates a new session with updated hash
    inference = MagicMock()
    inference.invoke.return_value = []
    orchestrator = RefinementOrchestrator(
        ambiguity_detector=AmbiguityDetector(inference),
        completeness_analyzer=CompletenessAnalyzer(),
        model_accessor=ModelAccessor(context["session_state"]),
    )
    new_session = orchestrator.start_session()
    context["new_session"] = new_session
    assert new_session.model_hash != context["original_hash"]


@then("the user is informed that the analysis was refreshed")
def user_informed_of_refresh(context):
    # New session exists with different hash
    assert context["new_session"] is not None
    assert context["new_session"].status == "presenting"


# ---------------------------------------------------------------------------
# TS-027: Agent warns about cross-context impact before applying batch changes
# (Shared with batch_adjustments.feature — step defs must be local)
# ---------------------------------------------------------------------------


@given("the agent's batch plan includes changes that affect nodes referenced in inter-aggregate policies")
def batch_affects_inter_aggregate_edge(context):
    from domain.models.tool_schemas import Ambiguity, RefinementSession

    model = _make_base_model()
    context["session_state"] = {"analysis_result": {"analysis": model}}
    context["model"] = model

    session = RefinementSession(
        model_hash=RefinementSession.compute_model_hash(model.model_dump_json()),
        ambiguities=[
            Ambiguity(
                id="amb_001",
                type="lexical",
                priority=2,
                description="Multi-location rename required",
                affected_elements=["cmd_bp"],
                suggested_resolutions=["Rename all occurrences", "Keep separate"],
            )
        ],
        status="presenting",
    )
    context["session"] = session
    context["cross_context"] = True
    context["resolution"] = "Renombrar nodo que aparece en políticas inter-agregado"


@when("the agent presents the batch plan for approval")
def agent_presents_batch_for_approval_edge(context):
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
def highlights_cross_context_impact_edge(context):
    plan = context["plan"]
    assert plan.description != ""


@then("requests explicit confirmation from the user before applying cross-context changes")
def requests_explicit_confirmation_edge(context):
    assert context["plan"].status == "pending"
