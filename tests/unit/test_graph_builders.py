"""Unit tests for graph builder functions in src/ui/visualization/graph.py.

Tests the pure graph-building logic (no Streamlit rendering).
"""

import graphviz

from models.domain_analysis import (
    AristaGrafo,
    BigPicture,
    DomainAnalysis,
    GrafoPorAgregado,
    NodoGrafo,
    ReadModel,
)


def _make_node(id, tipo, nombre, nivel="big_picture"):
    return NodoGrafo(id=id, tipo_elemento=tipo, nombre=nombre, descripcion=f"{nombre} desc", nivel=nivel)


def _make_edge(src, dst, desc="triggers"):
    return AristaGrafo(fuente=src, destino=dst, descripcion=desc)


def _make_analysis(bp_nodes=None, bp_edges=None, aggregates=None, read_models=None, policies=None):
    bp_nodes = bp_nodes or [
        _make_node("cmd-1", "Comando", "CreateOrder"),
        _make_node("evt-1", "Evento", "OrderCreated"),
    ]
    bp_edges = bp_edges or [_make_edge("cmd-1", "evt-1")]
    aggregates = aggregates or []
    read_models = read_models or []
    policies = policies or []

    return DomainAnalysis(
        nombre_proyecto="TestProject",
        version="1.0",
        fecha_analisis="2025-01-01",
        big_picture=BigPicture(descripcion="Test BP", nodos=bp_nodes, aristas=bp_edges),
        agregados=aggregates,
        read_models=read_models,
        politicas_inter_agregados=policies,
    )


class TestAddNode:
    def test_add_node_standard(self):
        from ui.visualization.graph import _add_node

        g = graphviz.Digraph()
        node = _make_node("n1", "Evento", "OrderCreated")
        _add_node(g, node)
        src = g.source
        assert "n1" in src

    def test_add_node_compact(self):
        from ui.visualization.graph import _add_node

        g = graphviz.Digraph()
        node = _make_node("n1", "Comando", "CreateOrder")
        _add_node(g, node, compact=True)
        src = g.source
        assert "n1" in src

    def test_add_node_with_state_badge(self):
        from ui.visualization.graph import _add_node

        g = graphviz.Digraph()
        node = _make_node("n1", "Evento", "OrderCreated")
        node.estado_comparativo = "nuevo"
        _add_node(g, node, show_state=True)
        src = g.source
        assert "n1" in src

    def test_add_node_unknown_type_uses_default(self):
        from ui.visualization.graph import _add_node

        g = graphviz.Digraph()
        node = NodoGrafo(
            id="n1",
            tipo_elemento="Hotspot",
            nombre="Something",
            descripcion="Something desc",
            nivel="big_picture",
        )
        _add_node(g, node)
        src = g.source
        assert "n1" in src


class TestAddEdge:
    def test_add_edge_standard(self):
        from ui.visualization.graph import _add_edge

        g = graphviz.Digraph()
        edge = _make_edge("n1", "n2", "dispara el proceso")
        _add_edge(g, edge)
        src = g.source
        assert "n1" in src
        assert "n2" in src

    def test_add_edge_policy_style(self):
        from ui.visualization.graph import _add_edge

        g = graphviz.Digraph()
        edge = _make_edge("n1", "n2", "policy flow")
        _add_edge(g, edge, is_policy=True)
        src = g.source
        assert "7C4DFF" in src  # policy color

    def test_add_edge_long_description_truncated(self):
        from ui.visualization.graph import _add_edge

        g = graphviz.Digraph()
        long_desc = "a" * 50
        edge = _make_edge("n1", "n2", long_desc)
        _add_edge(g, edge)
        src = g.source
        assert "..." in src

    def test_add_edge_with_custom_style(self):
        from ui.visualization.graph import _add_edge

        g = graphviz.Digraph()
        edge = _make_edge("n1", "n2", "custom")
        _add_edge(g, edge, color="#FF0000", style="dashed", penwidth="3.0")
        src = g.source
        assert "FF0000" in src


class TestFlowGraph:
    def test_creates_digraph(self):
        from ui.visualization.graph import _flow_graph

        g = _flow_graph(title="Test Graph")
        assert isinstance(g, graphviz.Digraph)

    def test_sets_title(self):
        from ui.visualization.graph import _flow_graph

        g = _flow_graph(title="My Title")
        src = g.source
        assert "My Title" in src


class TestEnforceRanks:
    def test_groups_nodes_by_rank(self):
        from ui.visualization.graph import _enforce_ranks

        g = graphviz.Digraph()
        nodes = [
            _make_node("n1", "Actor", "User"),
            _make_node("n2", "Comando", "Create"),
            _make_node("n3", "Evento", "Created"),
        ]
        for n in nodes:
            g.node(n.id)
        _enforce_ranks(g, nodes)
        src = g.source
        assert "rank=same" in src


class TestBuildBigPicture:
    def test_returns_digraph(self):
        from ui.visualization.graph import _build_big_picture

        analysis = _make_analysis()
        g = _build_big_picture(analysis)
        assert isinstance(g, graphviz.Digraph)

    def test_includes_nodes(self):
        from ui.visualization.graph import _build_big_picture

        analysis = _make_analysis()
        g = _build_big_picture(analysis)
        src = g.source
        assert "cmd-1" in src
        assert "evt-1" in src

    def test_includes_read_models(self):
        from ui.visualization.graph import _build_big_picture

        rms = [ReadModel(nombre="Dashboard", descripcion="Shows stuff", proyecta=["evt-1"])]
        analysis = _make_analysis(read_models=rms)
        g = _build_big_picture(analysis)
        src = g.source
        assert "Dashboard" in src


class TestBuildAggregate:
    def test_returns_digraph(self):
        from ui.visualization.graph import _build_aggregate

        agg = GrafoPorAgregado(
            nombre_agregado="OrderAgg",
            entidad_raiz="Order",
            nodos=[_make_node("agg-1", "Agregado", "OrderAgg", "process_level")],
            aristas=[],
        )
        g = _build_aggregate(agg)
        assert isinstance(g, graphviz.Digraph)

    def test_includes_aggregate_nodes(self):
        from ui.visualization.graph import _build_aggregate

        agg = GrafoPorAgregado(
            nombre_agregado="OrderAgg",
            entidad_raiz="Order",
            nodos=[
                _make_node("agg-1", "Agregado", "OrderAgg", "process_level"),
                _make_node("cmd-1", "Comando", "CreateOrder", "process_level"),
            ],
            aristas=[_make_edge("agg-1", "cmd-1")],
        )
        g = _build_aggregate(agg)
        src = g.source
        assert "agg-1" in src
        assert "cmd-1" in src

    def test_includes_read_models_when_analysis_provided(self):
        from ui.visualization.graph import _build_aggregate

        agg_node = _make_node("agg-1", "Agregado", "OrderAgg", "process_level")
        evt_node = _make_node("evt-agg-1", "Evento", "OrderCreated", "process_level")
        agg = GrafoPorAgregado(
            nombre_agregado="OrderAgg",
            entidad_raiz="Order",
            nodos=[agg_node, evt_node],
            aristas=[_make_edge("agg-1", "evt-agg-1")],
        )
        rms = [ReadModel(nombre="OrderView", descripcion="Shows orders", proyecta=["evt-agg-1"])]
        analysis = _make_analysis(read_models=rms, aggregates=[agg])
        g = _build_aggregate(agg, analysis)
        src = g.source
        assert "OrderView" in src


class TestBuildAllAggregates:
    def test_returns_digraph(self):
        from ui.visualization.graph import _build_all_aggregates

        agg = GrafoPorAgregado(
            nombre_agregado="OrderAgg",
            entidad_raiz="Order",
            nodos=[_make_node("agg-1", "Agregado", "OrderAgg", "process_level")],
            aristas=[],
        )
        analysis = _make_analysis(aggregates=[agg])
        g = _build_all_aggregates(analysis)
        assert isinstance(g, graphviz.Digraph)

    def test_includes_clusters(self):
        from ui.visualization.graph import _build_all_aggregates

        agg = GrafoPorAgregado(
            nombre_agregado="OrderAgg",
            entidad_raiz="Order",
            nodos=[_make_node("agg-1", "Agregado", "OrderAgg", "process_level")],
            aristas=[],
        )
        analysis = _make_analysis(aggregates=[agg])
        g = _build_all_aggregates(analysis)
        src = g.source
        assert "cluster_OrderAgg" in src

    def test_includes_policies(self):
        from ui.visualization.graph import _build_all_aggregates

        agg1 = GrafoPorAgregado(
            nombre_agregado="Agg1",
            entidad_raiz="Root1",
            nodos=[_make_node("a1", "Agregado", "Agg1", "process_level")],
            aristas=[],
        )
        agg2 = GrafoPorAgregado(
            nombre_agregado="Agg2",
            entidad_raiz="Root2",
            nodos=[_make_node("a2", "Agregado", "Agg2", "process_level")],
            aristas=[],
        )
        policy = _make_edge("a1", "a2", "activa compensación")
        analysis = _make_analysis(aggregates=[agg1, agg2], policies=[policy])
        g = _build_all_aggregates(analysis)
        src = g.source
        assert "a1" in src
        assert "a2" in src


class TestBuildReadModels:
    def test_returns_digraph(self):
        from ui.visualization.graph import _build_read_models

        rms = [ReadModel(nombre="Dashboard", descripcion="Shows stuff", proyecta=[])]
        analysis = _make_analysis(read_models=rms)
        g = _build_read_models(analysis)
        assert isinstance(g, graphviz.Digraph)

    def test_includes_read_model_nodes(self):
        from ui.visualization.graph import _build_read_models

        rms = [ReadModel(nombre="OrderView", descripcion="Shows orders", proyecta=[], tecnologias=["React"])]
        analysis = _make_analysis(read_models=rms)
        g = _build_read_models(analysis)
        src = g.source
        assert "OrderView" in src
        assert "React" in src


class TestBuildUserJourney:
    def test_returns_digraph(self):
        from ui.visualization.graph import _build_user_journey

        analysis = _make_analysis()
        g = _build_user_journey(analysis)
        assert isinstance(g, graphviz.Digraph)

    def test_includes_bp_and_agg_nodes(self):
        from ui.visualization.graph import _build_user_journey

        agg = GrafoPorAgregado(
            nombre_agregado="OrderAgg",
            entidad_raiz="Order",
            nodos=[
                _make_node("agg-1", "Agregado", "OrderAgg", "process_level"),
                _make_node("cmd-agg-1", "Comando", "Place", "process_level"),
            ],
            aristas=[_make_edge("agg-1", "cmd-agg-1")],
        )
        analysis = _make_analysis(aggregates=[agg])
        g = _build_user_journey(analysis)
        src = g.source
        assert "cmd-1" in src  # BP node
        assert "cmd-agg-1" in src  # Aggregate node


class TestRenderZoomableGraph:
    def test_renders_html(self):
        from unittest.mock import MagicMock, patch

        from ui.visualization.graph import _render_zoomable_graph

        g = MagicMock(spec=graphviz.Digraph)
        g.pipe.return_value = b'<svg xmlns="http://www.w3.org/2000/svg"><g>test</g></svg>'

        with patch("ui.visualization.graph.components") as mock_comp:
            _render_zoomable_graph(g, height=500)
            g.pipe.assert_called_once_with(format="svg")
            mock_comp.html.assert_called_once()
            html = mock_comp.html.call_args[0][0]
            assert "container" in html
            assert "zoom" in html.lower()


class TestRenderLegend:
    def test_renders_without_error(self):
        from unittest.mock import patch

        from ui.visualization.graph import _render_legend

        with patch("ui.visualization.graph.st") as mock_st:
            _render_legend()
            assert mock_st.markdown.call_count >= 4
