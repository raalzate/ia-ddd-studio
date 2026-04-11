"""BDD step definitions for completeness_analysis.feature.

US-003: Domain Model Completeness Analysis
Test IDs: TS-007, TS-008, TS-009
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../../specs/004-reactive-refinement-agent/tests/features/completeness_analysis.feature")


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def context():
    return {}


def _make_aggregate(name, commands=True, events=True, with_edge=True):
    """Build a GrafoPorAgregado fixture."""
    from models.domain_analysis import AristaGrafo, GrafoPorAgregado, NodoGrafo

    nodes = []
    aristas = []

    cmd_id = None
    evt_id = None

    if commands:
        cmd_id = f"cmd_{name.lower()}_crear"
        nodes.append(
            NodoGrafo(
                id=cmd_id,
                tipo_elemento="Comando",
                nombre=f"Crear{name}",
                descripcion=f"Create {name}",
                nivel="process_level",
            )
        )
    if events:
        evt_id = f"evt_{name.lower()}_creado"
        nodes.append(
            NodoGrafo(
                id=evt_id,
                tipo_elemento="Evento",
                nombre=f"{name}Creado",
                descripcion=f"{name} created",
                nivel="process_level",
            )
        )

    # Always add a root entity to satisfy rule 4
    ent_id = f"ent_{name.lower()}"
    nodes.append(
        NodoGrafo(
            id=ent_id,
            tipo_elemento="Entidad Raíz",
            nombre=name,
            descripcion="Root entity",
            nivel="process_level",
        )
    )

    if with_edge and cmd_id:
        target_id = evt_id if evt_id else ent_id
        aristas.append(AristaGrafo(fuente=cmd_id, destino=target_id, descripcion="produces"))
        # Also connect cmd to root entity so root entity isn't stripped
        aristas.append(AristaGrafo(fuente=cmd_id, destino=ent_id, descripcion="creates"))

    if evt_id and ent_id and not cmd_id:
        aristas.append(AristaGrafo(fuente=evt_id, destino=ent_id, descripcion="updates"))

    if not aristas and ent_id:
        # Ensure root entity is connected so strip_orphan_nodes doesn't remove it
        if nodes:
            aristas.append(AristaGrafo(fuente=nodes[0].id, destino=ent_id, descripcion="references"))

    return GrafoPorAgregado(
        nombre_agregado=name,
        entidad_raiz=name,
        nodos=nodes,
        aristas=aristas,
    )


def _make_full_domain_model(aggregates=None, read_models=None):
    """Build a DomainAnalysis with given aggregates."""
    from models.domain_analysis import AristaGrafo, BigPicture, DomainAnalysis, NodoGrafo, ReadModel

    bp_nodes = [
        NodoGrafo(
            id="cmd_bp",
            tipo_elemento="Comando",
            nombre="Action",
            descripcion="BP action",
            nivel="big_picture",
        ),
        NodoGrafo(
            id="evt_bp",
            tipo_elemento="Evento",
            nombre="ActionDone",
            descripcion="BP event",
            nivel="big_picture",
        ),
    ]
    bp_edges = [AristaGrafo(fuente="cmd_bp", destino="evt_bp", descripcion="produces")]

    rm_list = read_models or []
    if rm_list and isinstance(rm_list[0], str):
        from models.domain_analysis import ReadModel

        rm_list = [ReadModel(nombre=name, descripcion=f"View for {name}", proyecta=[]) for name in rm_list]

    return DomainAnalysis(
        nombre_proyecto="CompletenessTest",
        version="1.0.0",
        fecha_analisis="2026-03-19",
        big_picture=BigPicture(descripcion="test", nodos=bp_nodes, aristas=bp_edges),
        agregados=aggregates or [],
        read_models=rm_list,
        politicas_inter_agregados=[],
    )


# ---------------------------------------------------------------------------
# Background steps
# ---------------------------------------------------------------------------


@given("a domain model is loaded in session state")
def domain_model_loaded(context):
    context["session_state"] = {}


@given("a refinement analysis has been triggered post-generation")
def refinement_triggered(context):
    context["analysis_triggered"] = True


# ---------------------------------------------------------------------------
# TS-007: Agent alerts about aggregate commands without events
# ---------------------------------------------------------------------------


@given(parsers.parse('the generated model contains an aggregate "{agg_name}" with commands but no events'))
def aggregate_with_commands_no_events(context, agg_name):
    agg = _make_aggregate(agg_name, commands=True, events=False)
    model = _make_full_domain_model(aggregates=[agg])
    context["model"] = model
    context["agg_name"] = agg_name


@when("the agent executes the post-generation completeness analysis")
def agent_executes_completeness(context):
    from services.completeness_analyzer import CompletenessAnalyzer

    analyzer = CompletenessAnalyzer()
    context["gaps"] = analyzer.analyze(context["model"])


@then(parsers.parse('the agent reports the gap identifying the aggregate "{agg_name}"'))
def gap_identifies_aggregate(context, agg_name):
    gaps = context["gaps"]
    agg_gaps = [g for g in gaps if g.affected_aggregate == agg_name]
    assert len(agg_gaps) >= 1


@then("the report specifies which commands lack associated events")
def report_specifies_commands(context):
    gaps = context["gaps"]
    event_gaps = [g for g in gaps if g.rule_name in ("aggregate_has_events", "command_produces_event")]
    assert len(event_gaps) >= 1


@then("the agent suggests event names based on DDD naming conventions")
def suggests_event_names(context):
    gaps = context["gaps"]
    for gap in gaps:
        assert gap.suggestion != ""


# ---------------------------------------------------------------------------
# TS-008: Agent signals absence of read models
# ---------------------------------------------------------------------------


@given("the generated model contains aggregates but no read models defined")
def aggregates_no_read_models(context):
    agg = _make_aggregate("Pedidos", commands=True, events=True, with_edge=True)
    model = _make_full_domain_model(aggregates=[agg], read_models=[])
    context["model"] = model


@when("the agent analyzes completeness")
def agent_analyzes_completeness(context):
    from services.completeness_analyzer import CompletenessAnalyzer

    analyzer = CompletenessAnalyzer()
    context["gaps"] = analyzer.analyze(context["model"])


@then("the agent signals the absence of read models")
def signals_no_read_models(context):
    gaps = context["gaps"]
    rm_gaps = [g for g in gaps if g.rule_name == "bounded_context_has_read_models"]
    assert len(rm_gaps) >= 1


@then("asks whether the context requires query views")
def suggests_read_models(context):
    gaps = context["gaps"]
    rm_gaps = [g for g in gaps if g.rule_name == "bounded_context_has_read_models"]
    assert all(g.suggestion != "" for g in rm_gaps)


# ---------------------------------------------------------------------------
# TS-009: Agent confirms model meets all completeness criteria
# ---------------------------------------------------------------------------


@given("the generated model satisfies all expected DDD structural patterns")
def model_satisfies_patterns(context):
    context["complete_model_setup"] = True


@given("every aggregate has at least one command and one event")
def every_agg_has_cmd_and_event(context):
    context["complete_model_setup"] = True


@given("every command has an associated event edge")
def every_cmd_has_event_edge(context):
    context["complete_model_setup"] = True


@given("read models are defined")
def read_models_defined(context):
    from models.domain_analysis import ReadModel

    agg = _make_aggregate("Pedidos", commands=True, events=True, with_edge=True)
    rm = ReadModel(nombre="PedidosView", descripcion="Read model for Pedidos", proyecta=[])
    model = _make_full_domain_model(aggregates=[agg], read_models=[rm])
    context["model"] = model


@when("the agent executes the completeness analysis")
def executes_completeness_analysis(context):
    from services.completeness_analyzer import CompletenessAnalyzer

    analyzer = CompletenessAnalyzer()
    context["gaps"] = analyzer.analyze(context["model"])


@then("the agent confirms the model meets completeness criteria")
def confirms_completeness(context):
    gaps = context["gaps"]
    structural_gaps = [
        g for g in gaps if g.rule_name in ("aggregate_has_commands", "aggregate_has_events", "command_produces_event")
    ]
    assert len(structural_gaps) == 0


@then("no structural alerts are generated")
def no_structural_alerts(context):
    gaps = context["gaps"]
    structural_gaps = [g for g in gaps if g.rule_name != "bounded_context_has_read_models"]
    assert len(structural_gaps) == 0
