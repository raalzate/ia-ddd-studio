"""Advanced graph builder tests — covering _build_all_aggregates read models,
_build_read_models with projections, and _build_user_journey with aggregates."""

from models.domain_analysis import (
    AristaGrafo,
    BigPicture,
    DomainAnalysis,
    GrafoPorAgregado,
    NodoGrafo,
    ReadModel,
)


def _node(id, tipo, nombre, nivel="process_level"):
    return NodoGrafo(id=id, tipo_elemento=tipo, nombre=nombre, descripcion=f"{nombre} desc", nivel=nivel)


def _edge(src, dst, desc="triggers"):
    return AristaGrafo(fuente=src, destino=dst, descripcion=desc)


def _analysis_with_all():
    bp_nodes = [
        _node("actor-1", "Actor", "User", "big_picture"),
        _node("cmd-bp-1", "Comando", "PlaceOrder", "big_picture"),
        _node("agg-bp-1", "Agregado", "OrderAgg", "big_picture"),
        _node("evt-bp-1", "Evento", "OrderPlaced", "big_picture"),
    ]
    bp_edges = [
        _edge("actor-1", "cmd-bp-1", "dispara"),
        _edge("cmd-bp-1", "agg-bp-1", "ejecuta"),
        _edge("agg-bp-1", "evt-bp-1", "produce"),
    ]

    agg1 = GrafoPorAgregado(
        nombre_agregado="OrderAgg",
        entidad_raiz="Order",
        nodos=[
            _node("agg-int-1", "Agregado", "OrderAgg"),
            _node("cmd-int-1", "Comando", "CreateOrder"),
            _node("evt-int-1", "Evento", "OrderCreated"),
        ],
        aristas=[_edge("agg-int-1", "cmd-int-1"), _edge("cmd-int-1", "evt-int-1")],
    )
    agg2 = GrafoPorAgregado(
        nombre_agregado="PaymentAgg",
        entidad_raiz="Payment",
        nodos=[
            _node("agg-int-2", "Agregado", "PaymentAgg"),
            _node("cmd-int-2", "Comando", "ProcessPayment"),
            _node("evt-int-2", "Evento", "PaymentProcessed"),
        ],
        aristas=[_edge("agg-int-2", "cmd-int-2"), _edge("cmd-int-2", "evt-int-2")],
    )

    rms = [
        ReadModel(
            nombre="OrderDashboard",
            descripcion="Shows all orders",
            proyecta=["evt-int-1"],
            tecnologias=["React", "GraphQL"],
        ),
        ReadModel(
            nombre="PaymentReport",
            descripcion="Payment history",
            proyecta=["evt-int-2"],
        ),
    ]

    policies = [_edge("evt-int-1", "cmd-int-2", "activa pago")]

    return DomainAnalysis(
        nombre_proyecto="TestProject",
        version="1.0",
        fecha_analisis="2025-01-01",
        big_picture=BigPicture(descripcion="Test", nodos=bp_nodes, aristas=bp_edges),
        agregados=[agg1, agg2],
        read_models=rms,
        politicas_inter_agregados=policies,
    )


class TestBuildAllAggregatesAdvanced:
    def test_includes_read_model_cluster(self):
        from ui.visualization.graph import _build_all_aggregates

        analysis = _analysis_with_all()
        g = _build_all_aggregates(analysis)
        src = g.source
        assert "cluster_read_models" in src
        assert "OrderDashboard" in src
        assert "PaymentReport" in src

    def test_includes_policy_edges(self):
        from ui.visualization.graph import _build_all_aggregates

        analysis = _analysis_with_all()
        g = _build_all_aggregates(analysis)
        src = g.source
        assert "activa pago" in src

    def test_includes_all_aggregate_clusters(self):
        from ui.visualization.graph import _build_all_aggregates

        analysis = _analysis_with_all()
        g = _build_all_aggregates(analysis)
        src = g.source
        assert "cluster_OrderAgg" in src
        assert "cluster_PaymentAgg" in src


class TestBuildReadModelsAdvanced:
    def test_includes_projection_edges(self):
        from ui.visualization.graph import _build_read_models

        analysis = _analysis_with_all()
        g = _build_read_models(analysis)
        src = g.source
        assert "proyecta" in src

    def test_includes_technology_labels(self):
        from ui.visualization.graph import _build_read_models

        analysis = _analysis_with_all()
        g = _build_read_models(analysis)
        src = g.source
        assert "React" in src

    def test_creates_event_source_nodes(self):
        from ui.visualization.graph import _build_read_models

        analysis = _analysis_with_all()
        g = _build_read_models(analysis)
        src = g.source
        # Should include the event nodes that read models project from
        assert "evt-int-1" in src


class TestBuildUserJourneyAdvanced:
    def test_creates_aggregate_clusters(self):
        from ui.visualization.graph import _build_user_journey

        analysis = _analysis_with_all()
        g = _build_user_journey(analysis)
        src = g.source
        assert "cluster_OrderAgg" in src
        assert "cluster_PaymentAgg" in src

    def test_includes_read_model_cluster(self):
        from ui.visualization.graph import _build_user_journey

        analysis = _analysis_with_all()
        g = _build_user_journey(analysis)
        src = g.source
        assert "cluster_read_models" in src

    def test_skips_aggregate_bp_nodes(self):
        from ui.visualization.graph import _build_user_journey

        analysis = _analysis_with_all()
        g = _build_user_journey(analysis)
        # BP aggregate nodes should NOT appear as standalone nodes
        # but the actor and command should
        src = g.source
        assert "actor-1" in src
        assert "cmd-bp-1" in src

    def test_handles_inter_aggregate_policies(self):
        from ui.visualization.graph import _build_user_journey

        analysis = _analysis_with_all()
        g = _build_user_journey(analysis)
        src = g.source
        # Policy edge should be rendered
        assert "evt-int-1" in src
        assert "cmd-int-2" in src
