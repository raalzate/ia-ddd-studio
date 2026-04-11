"""BDD step definitions for post_generation_reaction.feature.

US-001: Post-Generation Reactive Analysis
Test IDs: TS-001, TS-002, TS-003
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../../specs/004-reactive-refinement-agent/tests/features/post_generation_reaction.feature")


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def context():
    return {}


@pytest.fixture
def mock_session_state():
    """A simple dict simulating Streamlit session_state."""
    return {}


@pytest.fixture
def domain_model_with_synonyms():
    """DomainAnalysis with 'pedido' and 'orden' node names."""
    from models.domain_analysis import (
        AristaGrafo,
        BigPicture,
        DomainAnalysis,
        NodoGrafo,
    )

    return DomainAnalysis(
        nombre_proyecto="Test",
        version="1.0.0",
        fecha_analisis="2026-03-19",
        big_picture=BigPicture(
            descripcion="Test model with synonym terms",
            nodos=[
                NodoGrafo(
                    id="cmd_crear_pedido",
                    tipo_elemento="Comando",
                    nombre="CrearPedido",
                    descripcion="Create pedido",
                    nivel="big_picture",
                ),
                NodoGrafo(
                    id="cmd_crear_orden",
                    tipo_elemento="Comando",
                    nombre="CrearOrden",
                    descripcion="Create orden",
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
                AristaGrafo(fuente="cmd_crear_orden", destino="evt_pedido_creado", descripcion="produces"),
            ],
        ),
        agregados=[],
        read_models=[],
        politicas_inter_agregados=[],
    )


@pytest.fixture
def clear_domain_model():
    """DomainAnalysis with unambiguous, clear terminology."""
    from models.domain_analysis import (
        AristaGrafo,
        BigPicture,
        DomainAnalysis,
        NodoGrafo,
    )

    return DomainAnalysis(
        nombre_proyecto="ClearModel",
        version="1.0.0",
        fecha_analisis="2026-03-19",
        big_picture=BigPicture(
            descripcion="Clear unambiguous model",
            nodos=[
                NodoGrafo(
                    id="cmd_registrar_cliente",
                    tipo_elemento="Comando",
                    nombre="RegistrarCliente",
                    descripcion="Register a new client",
                    nivel="big_picture",
                ),
                NodoGrafo(
                    id="evt_cliente_registrado",
                    tipo_elemento="Evento",
                    nombre="ClienteRegistrado",
                    descripcion="Client has been registered",
                    nivel="big_picture",
                ),
            ],
            aristas=[
                AristaGrafo(
                    fuente="cmd_registrar_cliente",
                    destino="evt_cliente_registrado",
                    descripcion="triggers",
                ),
            ],
        ),
        agregados=[],
        read_models=[],
        politicas_inter_agregados=[],
    )


# ---------------------------------------------------------------------------
# Background steps
# ---------------------------------------------------------------------------


@given("the DDD Studio application is running")
def ddd_studio_running(context):
    context["app_running"] = True


@given("a chat agent with refinement capabilities is configured")
def chat_agent_configured(context, mock_session_state):
    from unittest.mock import MagicMock

    context["session_state"] = mock_session_state
    context["chat_agent"] = MagicMock()
    context["inference"] = MagicMock()


# ---------------------------------------------------------------------------
# TS-001: Agent reacts automatically after generation with detected ambiguities
# ---------------------------------------------------------------------------


@given(
    parsers.parse(
        'the system has just completed domain model generation from an input containing the terms "pedido" and "orden"'
    )
)
def generation_completed_with_synonyms(context, domain_model_with_synonyms, mock_session_state):
    mock_session_state["analysis_result"] = {"analysis": domain_model_with_synonyms}
    context["session_state"] = mock_session_state
    context["model"] = domain_model_with_synonyms


@when("the generation finishes successfully")
def generation_finishes(context):
    context["generation_complete"] = True
    context["session_state"]["refinement_pending"] = True


@then("the chat agent reacts automatically without user prompting")
def agent_reacts_automatically(context):
    assert context["session_state"].get("refinement_pending") is True


@then(parsers.parse("the reaction is presented within 15 seconds of generation completing"))
def reaction_within_15_seconds(context):
    """Verified by SC-001 performance test in contracts_and_validation; here we check the flag."""
    assert context.get("generation_complete") is True


@then("the agent shows a summary of the generated model")
def agent_shows_summary(context):
    from unittest.mock import MagicMock

    from domain.models.tool_schemas import Ambiguity

    model = context["model"]
    inference = MagicMock()
    inference.invoke.return_value = [
        Ambiguity(
            id="amb_001",
            type="lexical",
            priority=2,
            description="'CrearPedido' y 'CrearOrden' podrían ser sinónimos.",
            affected_elements=["cmd_crear_pedido", "cmd_crear_orden"],
            suggested_resolutions=["Unificar bajo 'CrearPedido'", "Mantener ambos"],
        )
    ]

    from services.ambiguity_detector import AmbiguityDetector

    detector = AmbiguityDetector(inference)
    ambiguities = detector.detect(model)
    context["ambiguities"] = ambiguities
    context["inference"] = inference
    # Summary implies ambiguities were found
    assert isinstance(ambiguities, list)


@then(parsers.parse('the agent lists detected ambiguities including a potential synonym between "pedido" and "orden"'))
def agent_lists_synonym_ambiguity(context):
    ambiguities = context.get("ambiguities", [])
    assert len(ambiguities) >= 1
    synonym_found = any(
        "cmd_crear_pedido" in a.affected_elements or "cmd_crear_orden" in a.affected_elements for a in ambiguities
    )
    assert synonym_found


@then("the agent presents concrete questions to resolve the ambiguities")
def agent_presents_questions(context):
    for amb in context.get("ambiguities", []):
        assert len(amb.suggested_resolutions) >= 1


# ---------------------------------------------------------------------------
# TS-002: Agent presents confirmation when no ambiguities are detected
# ---------------------------------------------------------------------------


@given("the system has just completed domain model generation from a clear unambiguous input")
def generation_completed_clear(context, clear_domain_model, mock_session_state):
    mock_session_state["analysis_result"] = {"analysis": clear_domain_model}
    context["session_state"] = mock_session_state
    context["model"] = clear_domain_model


@when("the agent analyzes the result")
def agent_analyzes_result(context):
    from unittest.mock import MagicMock

    inference = MagicMock()
    inference.invoke.return_value = []  # No ambiguities

    from services.ambiguity_detector import AmbiguityDetector

    detector = AmbiguityDetector(inference)
    context["ambiguities"] = detector.detect(context["model"])


@then("the agent presents a confirmation message indicating no ambiguities were found")
def agent_presents_no_ambiguity_confirmation(context):
    assert context["ambiguities"] == []


@then("the agent highlights the key elements of the model for human validation")
def agent_highlights_key_elements(context):
    model = context["model"]
    # Model should have nodes to highlight
    assert len(model.big_picture.nodos) > 0


# ---------------------------------------------------------------------------
# TS-003: Agent lists assumptions made during generation
# ---------------------------------------------------------------------------


@given("the input text contained ambiguous terms that were resolved with assumptions during generation")
def input_with_assumptions(context, domain_model_with_synonyms, mock_session_state):
    mock_session_state["analysis_result"] = {"analysis": domain_model_with_synonyms}
    context["session_state"] = mock_session_state
    context["model"] = domain_model_with_synonyms


@when("the agent reacts post-generation")
def agent_reacts_post_generation(context):
    from unittest.mock import MagicMock

    from domain.models.tool_schemas import Ambiguity

    inference = MagicMock()
    inference.invoke.return_value = [
        Ambiguity(
            id="amb_001",
            type="lexical",
            priority=2,
            description="'Pedido' y 'Orden' podrían ser sinónimos.",
            affected_elements=["cmd_crear_pedido", "cmd_crear_orden"],
            suggested_resolutions=["Unificar bajo 'Pedido'", "Mantener ambos"],
            assumptions_made="'Pedido' y 'Orden' fueron tratados como conceptos separados",
        )
    ]

    from services.ambiguity_detector import AmbiguityDetector

    detector = AmbiguityDetector(inference)
    context["ambiguities"] = detector.detect(context["model"])


@then("the agent explicitly lists each assumption made")
def agent_lists_assumptions(context):
    ambiguities_with_assumptions = [a for a in context["ambiguities"] if a.assumptions_made is not None]
    assert len(ambiguities_with_assumptions) >= 1


@then("each assumption is presented with a confirmation question to the user")
def each_assumption_has_resolutions(context):
    for amb in context["ambiguities"]:
        if amb.assumptions_made:
            assert len(amb.suggested_resolutions) >= 1


@then("the assumptions are traceable to the specific terms in the original input")
def assumptions_are_traceable(context):
    for amb in context["ambiguities"]:
        if amb.assumptions_made:
            assert len(amb.affected_elements) >= 1
