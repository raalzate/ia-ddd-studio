"""Unit tests for CompletenessAnalyzer service.

Tests deterministic DDD rule fixtures — no LLM mock needed, as required by T017.
"""

from __future__ import annotations


def _make_agg(name, tipos_nodos, aristas=None):
    """Build a GrafoPorAgregado for testing."""
    from models.domain_analysis import GrafoPorAgregado, NodoGrafo

    nodes = []
    for i, (tipo, nombre) in enumerate(tipos_nodos):
        nodes.append(
            NodoGrafo(
                id=f"node_{i}_{nombre.lower().replace(' ', '_')}",
                tipo_elemento=tipo,
                nombre=nombre,
                descripcion=f"Test node {nombre}",
                nivel="process_level",
            )
        )

    edges = aristas or []

    return GrafoPorAgregado(
        nombre_agregado=name,
        entidad_raiz=nombre if tipos_nodos else "Unknown",
        nodos=nodes,
        aristas=edges,
    )


def _make_simple_model(aggs=None, read_models=None):
    from models.domain_analysis import AristaGrafo, BigPicture, DomainAnalysis, NodoGrafo

    return DomainAnalysis(
        nombre_proyecto="Test",
        version="1.0.0",
        fecha_analisis="2026-03-19",
        big_picture=BigPicture(
            descripcion="test",
            nodos=[
                NodoGrafo(
                    id="cmd_bp",
                    tipo_elemento="Comando",
                    nombre="Action",
                    descripcion="action",
                    nivel="big_picture",
                ),
                NodoGrafo(
                    id="evt_bp",
                    tipo_elemento="Evento",
                    nombre="ActionDone",
                    descripcion="done",
                    nivel="big_picture",
                ),
            ],
            aristas=[AristaGrafo(fuente="cmd_bp", destino="evt_bp", descripcion="produces")],
        ),
        agregados=aggs or [],
        read_models=read_models or [],
        politicas_inter_agregados=[],
    )


class TestCompletenessAnalyzerInit:
    def test_initializes_without_arguments(self):
        from services.completeness_analyzer import CompletenessAnalyzer

        analyzer = CompletenessAnalyzer()
        assert analyzer is not None

    def test_get_rules_returns_all_rules(self):
        from services.completeness_analyzer import CompletenessAnalyzer

        rules = CompletenessAnalyzer.get_rules()
        assert "aggregate_has_commands" in rules
        assert "aggregate_has_events" in rules
        assert "command_produces_event" in rules
        assert "aggregate_has_root_entity" in rules
        assert "bounded_context_has_read_models" in rules


class TestRuleAggregateHasCommands:
    """Tests for aggregate_has_commands rule."""

    def test_flags_aggregate_with_no_commands(self):
        from models.domain_analysis import AristaGrafo, GrafoPorAgregado, NodoGrafo
        from services.completeness_analyzer import CompletenessAnalyzer

        agg = GrafoPorAgregado(
            nombre_agregado="Pedidos",
            entidad_raiz="Pedido",
            nodos=[
                NodoGrafo(
                    id="ent_pedido",
                    tipo_elemento="Entidad Raíz",
                    nombre="Pedido",
                    descripcion="root",
                    nivel="process_level",
                ),
                NodoGrafo(
                    id="evt_pedido_creado",
                    tipo_elemento="Evento",
                    nombre="PedidoCreado",
                    descripcion="event",
                    nivel="process_level",
                ),
            ],
            aristas=[AristaGrafo(fuente="ent_pedido", destino="evt_pedido_creado", descripcion="emits")],
        )
        model = _make_simple_model(aggs=[agg])
        gaps = CompletenessAnalyzer().analyze(model)

        cmd_gaps = [g for g in gaps if g.rule_name == "aggregate_has_commands"]
        assert any(g.affected_aggregate == "Pedidos" for g in cmd_gaps)

    def test_no_gap_when_aggregate_has_commands(self):
        from models.domain_analysis import AristaGrafo, GrafoPorAgregado, NodoGrafo
        from services.completeness_analyzer import CompletenessAnalyzer

        agg = GrafoPorAgregado(
            nombre_agregado="Pedidos",
            entidad_raiz="Pedido",
            nodos=[
                NodoGrafo(
                    id="cmd_crear",
                    tipo_elemento="Comando",
                    nombre="CrearPedido",
                    descripcion="create",
                    nivel="process_level",
                ),
                NodoGrafo(
                    id="evt_creado",
                    tipo_elemento="Evento",
                    nombre="PedidoCreado",
                    descripcion="event",
                    nivel="process_level",
                ),
                NodoGrafo(
                    id="ent_pedido",
                    tipo_elemento="Entidad Raíz",
                    nombre="Pedido",
                    descripcion="root",
                    nivel="process_level",
                ),
            ],
            aristas=[
                AristaGrafo(fuente="cmd_crear", destino="evt_creado", descripcion="produces"),
                AristaGrafo(fuente="cmd_crear", destino="ent_pedido", descripcion="creates"),
            ],
        )
        model = _make_simple_model(aggs=[agg])
        gaps = CompletenessAnalyzer().analyze(model)

        cmd_gaps = [g for g in gaps if g.rule_name == "aggregate_has_commands"]
        assert len(cmd_gaps) == 0


class TestRuleAggregateHasEvents:
    """Tests for aggregate_has_events rule."""

    def test_flags_aggregate_with_no_events(self):
        from models.domain_analysis import AristaGrafo, GrafoPorAgregado, NodoGrafo
        from services.completeness_analyzer import CompletenessAnalyzer

        agg = GrafoPorAgregado(
            nombre_agregado="Pedidos",
            entidad_raiz="Pedido",
            nodos=[
                NodoGrafo(
                    id="cmd_crear",
                    tipo_elemento="Comando",
                    nombre="CrearPedido",
                    descripcion="create",
                    nivel="process_level",
                ),
                NodoGrafo(
                    id="ent_pedido",
                    tipo_elemento="Entidad Raíz",
                    nombre="Pedido",
                    descripcion="root",
                    nivel="process_level",
                ),
            ],
            aristas=[AristaGrafo(fuente="cmd_crear", destino="ent_pedido", descripcion="creates")],
        )
        model = _make_simple_model(aggs=[agg])
        gaps = CompletenessAnalyzer().analyze(model)

        evt_gaps = [g for g in gaps if g.rule_name == "aggregate_has_events"]
        assert any(g.affected_aggregate == "Pedidos" for g in evt_gaps)

    def test_gap_includes_suggestion(self):
        from models.domain_analysis import AristaGrafo, GrafoPorAgregado, NodoGrafo
        from services.completeness_analyzer import CompletenessAnalyzer

        agg = GrafoPorAgregado(
            nombre_agregado="Pedidos",
            entidad_raiz="Pedido",
            nodos=[
                NodoGrafo(
                    id="cmd_crear",
                    tipo_elemento="Comando",
                    nombre="CrearPedido",
                    descripcion="create",
                    nivel="process_level",
                ),
                NodoGrafo(
                    id="ent_pedido",
                    tipo_elemento="Entidad Raíz",
                    nombre="Pedido",
                    descripcion="root",
                    nivel="process_level",
                ),
            ],
            aristas=[AristaGrafo(fuente="cmd_crear", destino="ent_pedido", descripcion="creates")],
        )
        model = _make_simple_model(aggs=[agg])
        gaps = CompletenessAnalyzer().analyze(model)

        evt_gaps = [g for g in gaps if g.rule_name == "aggregate_has_events"]
        assert all(g.suggestion != "" for g in evt_gaps)


class TestRuleCommandProducesEvent:
    """Tests for command_produces_event rule."""

    def test_flags_command_with_no_event_edge(self):
        from models.domain_analysis import AristaGrafo, GrafoPorAgregado, NodoGrafo
        from services.completeness_analyzer import CompletenessAnalyzer

        agg = GrafoPorAgregado(
            nombre_agregado="Pedidos",
            entidad_raiz="Pedido",
            nodos=[
                NodoGrafo(
                    id="cmd_crear",
                    tipo_elemento="Comando",
                    nombre="CrearPedido",
                    descripcion="create",
                    nivel="process_level",
                ),
                NodoGrafo(
                    id="ent_pedido",
                    tipo_elemento="Entidad Raíz",
                    nombre="Pedido",
                    descripcion="root",
                    nivel="process_level",
                ),
                NodoGrafo(
                    id="evt_creado",
                    tipo_elemento="Evento",
                    nombre="PedidoCreado",
                    descripcion="event",
                    nivel="process_level",
                ),
            ],
            aristas=[
                # Command connects to entity, NOT to event
                AristaGrafo(fuente="cmd_crear", destino="ent_pedido", descripcion="creates"),
                AristaGrafo(fuente="ent_pedido", destino="evt_creado", descripcion="emits"),
            ],
        )
        model = _make_simple_model(aggs=[agg])
        gaps = CompletenessAnalyzer().analyze(model)

        cmd_evt_gaps = [g for g in gaps if g.rule_name == "command_produces_event"]
        assert any(g.affected_aggregate == "Pedidos" for g in cmd_evt_gaps)

    def test_no_gap_when_command_directly_produces_event(self):
        from models.domain_analysis import AristaGrafo, GrafoPorAgregado, NodoGrafo
        from services.completeness_analyzer import CompletenessAnalyzer

        agg = GrafoPorAgregado(
            nombre_agregado="Pedidos",
            entidad_raiz="Pedido",
            nodos=[
                NodoGrafo(
                    id="cmd_crear",
                    tipo_elemento="Comando",
                    nombre="CrearPedido",
                    descripcion="create",
                    nivel="process_level",
                ),
                NodoGrafo(
                    id="evt_creado",
                    tipo_elemento="Evento",
                    nombre="PedidoCreado",
                    descripcion="event",
                    nivel="process_level",
                ),
                NodoGrafo(
                    id="ent_pedido",
                    tipo_elemento="Entidad Raíz",
                    nombre="Pedido",
                    descripcion="root",
                    nivel="process_level",
                ),
            ],
            aristas=[
                AristaGrafo(fuente="cmd_crear", destino="evt_creado", descripcion="produces"),
                AristaGrafo(fuente="cmd_crear", destino="ent_pedido", descripcion="creates"),
            ],
        )
        model = _make_simple_model(aggs=[agg])
        gaps = CompletenessAnalyzer().analyze(model)

        cmd_evt_gaps = [g for g in gaps if g.rule_name == "command_produces_event"]
        assert len(cmd_evt_gaps) == 0


class TestRuleBoundedContextHasReadModels:
    """Tests for bounded_context_has_read_models rule."""

    def test_flags_model_with_aggregates_but_no_read_models(self):
        from models.domain_analysis import AristaGrafo, GrafoPorAgregado, NodoGrafo
        from services.completeness_analyzer import CompletenessAnalyzer

        agg = GrafoPorAgregado(
            nombre_agregado="Pedidos",
            entidad_raiz="Pedido",
            nodos=[
                NodoGrafo(
                    id="cmd_crear",
                    tipo_elemento="Comando",
                    nombre="CrearPedido",
                    descripcion="create",
                    nivel="process_level",
                ),
                NodoGrafo(
                    id="evt_creado",
                    tipo_elemento="Evento",
                    nombre="PedidoCreado",
                    descripcion="event",
                    nivel="process_level",
                ),
                NodoGrafo(
                    id="ent_pedido",
                    tipo_elemento="Entidad Raíz",
                    nombre="Pedido",
                    descripcion="root",
                    nivel="process_level",
                ),
            ],
            aristas=[
                AristaGrafo(fuente="cmd_crear", destino="evt_creado", descripcion="produces"),
                AristaGrafo(fuente="cmd_crear", destino="ent_pedido", descripcion="creates"),
            ],
        )
        model = _make_simple_model(aggs=[agg], read_models=[])
        gaps = CompletenessAnalyzer().analyze(model)

        rm_gaps = [g for g in gaps if g.rule_name == "bounded_context_has_read_models"]
        assert len(rm_gaps) >= 1

    def test_no_gap_when_read_models_exist(self):
        from models.domain_analysis import AristaGrafo, GrafoPorAgregado, NodoGrafo, ReadModel
        from services.completeness_analyzer import CompletenessAnalyzer

        agg = GrafoPorAgregado(
            nombre_agregado="Pedidos",
            entidad_raiz="Pedido",
            nodos=[
                NodoGrafo(
                    id="cmd_crear",
                    tipo_elemento="Comando",
                    nombre="CrearPedido",
                    descripcion="create",
                    nivel="process_level",
                ),
                NodoGrafo(
                    id="evt_creado",
                    tipo_elemento="Evento",
                    nombre="PedidoCreado",
                    descripcion="event",
                    nivel="process_level",
                ),
                NodoGrafo(
                    id="ent_pedido",
                    tipo_elemento="Entidad Raíz",
                    nombre="Pedido",
                    descripcion="root",
                    nivel="process_level",
                ),
            ],
            aristas=[
                AristaGrafo(fuente="cmd_crear", destino="evt_creado", descripcion="produces"),
                AristaGrafo(fuente="cmd_crear", destino="ent_pedido", descripcion="creates"),
            ],
        )
        rm = ReadModel(nombre="PedidosView", descripcion="View", proyecta=[])
        model = _make_simple_model(aggs=[agg], read_models=[rm])
        gaps = CompletenessAnalyzer().analyze(model)

        rm_gaps = [g for g in gaps if g.rule_name == "bounded_context_has_read_models"]
        assert len(rm_gaps) == 0

    def test_no_gap_when_no_aggregates(self):
        from services.completeness_analyzer import CompletenessAnalyzer

        model = _make_simple_model(aggs=[], read_models=[])
        gaps = CompletenessAnalyzer().analyze(model)
        rm_gaps = [g for g in gaps if g.rule_name == "bounded_context_has_read_models"]
        assert len(rm_gaps) == 0


class TestCompletenessAnalyzerFullModel:
    """Integration-style tests for analyze() on complete/incomplete models."""

    def test_returns_empty_list_for_compliant_model(self):
        from models.domain_analysis import AristaGrafo, GrafoPorAgregado, NodoGrafo, ReadModel
        from services.completeness_analyzer import CompletenessAnalyzer

        agg = GrafoPorAgregado(
            nombre_agregado="Pedidos",
            entidad_raiz="Pedido",
            nodos=[
                NodoGrafo(
                    id="cmd_crear",
                    tipo_elemento="Comando",
                    nombre="CrearPedido",
                    descripcion="create",
                    nivel="process_level",
                ),
                NodoGrafo(
                    id="evt_creado",
                    tipo_elemento="Evento",
                    nombre="PedidoCreado",
                    descripcion="event",
                    nivel="process_level",
                ),
                NodoGrafo(
                    id="ent_pedido",
                    tipo_elemento="Entidad Raíz",
                    nombre="Pedido",
                    descripcion="root",
                    nivel="process_level",
                ),
            ],
            aristas=[
                AristaGrafo(fuente="cmd_crear", destino="evt_creado", descripcion="produces"),
                AristaGrafo(fuente="cmd_crear", destino="ent_pedido", descripcion="creates"),
            ],
        )
        rm = ReadModel(nombre="PedidosView", descripcion="View", proyecta=[])
        model = _make_simple_model(aggs=[agg], read_models=[rm])
        gaps = CompletenessAnalyzer().analyze(model)

        # No structural gaps should be reported
        structural = [g for g in gaps if g.rule_name != "bounded_context_has_read_models"]
        assert len(structural) == 0

    def test_returns_multiple_gaps_for_non_compliant_model(self):
        from models.domain_analysis import AristaGrafo, GrafoPorAgregado, NodoGrafo
        from services.completeness_analyzer import CompletenessAnalyzer

        # Aggregate with no events and command not producing event
        agg = GrafoPorAgregado(
            nombre_agregado="Pedidos",
            entidad_raiz="Pedido",
            nodos=[
                NodoGrafo(
                    id="cmd_crear",
                    tipo_elemento="Comando",
                    nombre="CrearPedido",
                    descripcion="create",
                    nivel="process_level",
                ),
                NodoGrafo(
                    id="ent_pedido",
                    tipo_elemento="Entidad Raíz",
                    nombre="Pedido",
                    descripcion="root",
                    nivel="process_level",
                ),
            ],
            aristas=[AristaGrafo(fuente="cmd_crear", destino="ent_pedido", descripcion="creates")],
        )
        model = _make_simple_model(aggs=[agg])
        gaps = CompletenessAnalyzer().analyze(model)

        assert len(gaps) >= 2  # At minimum: aggregate_has_events + bounded_context_has_read_models
