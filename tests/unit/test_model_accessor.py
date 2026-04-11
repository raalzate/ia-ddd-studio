"""Unit tests for ModelAccessor service.

Tests get, set, snapshot, undo, find_node, find_aggregate operations
on the DomainAnalysis model via a session-state-like dict wrapper.
"""

import pytest

from models.domain_analysis import (
    AristaGrafo,
    BigPicture,
    DomainAnalysis,
    GrafoPorAgregado,
    NodoGrafo,
)


def _make_node(id: str, name: str, tipo: str = "Comando", nivel: str = "big_picture") -> NodoGrafo:
    return NodoGrafo(
        id=id,
        tipo_elemento=tipo,
        nombre=name,
        descripcion=f"Test node {name}",
        nivel=nivel,
    )


def _make_edge(src: str, dst: str, desc: str = "flows") -> AristaGrafo:
    return AristaGrafo(fuente=src, destino=dst, descripcion=desc)


def _make_model() -> DomainAnalysis:
    """Create a minimal DomainAnalysis for testing."""
    return DomainAnalysis(
        nombre_proyecto="TestProject",
        version="1.0.0",
        fecha_analisis="2026-03-19",
        big_picture=BigPicture(
            descripcion="Test big picture",
            nodos=[
                _make_node("cmd_crear_pedido", "CrearPedido"),
                _make_node("evt_pedido_creado", "PedidoCreado", "Evento"),
                _make_node("svc_inventario", "Inventario", "Sistema Externo"),
            ],
            aristas=[
                _make_edge("cmd_crear_pedido", "evt_pedido_creado", "dispara"),
            ],
        ),
        agregados=[
            GrafoPorAgregado(
                nombre_agregado="Pedidos",
                entidad_raiz="Pedido",
                descripcion="Aggregate de pedidos",
                nodos=[
                    _make_node("cmd_crear_pedido", "CrearPedido", "Comando", "process_level"),
                    _make_node("evt_pedido_creado", "PedidoCreado", "Evento", "process_level"),
                ],
                aristas=[
                    _make_edge("cmd_crear_pedido", "evt_pedido_creado", "dispara"),
                ],
            ),
        ],
    )


def _make_session_state(model: DomainAnalysis | None = None) -> dict:
    """Create a dict that mimics st.session_state."""
    state = {}
    if model:
        state["analysis_result"] = {"analysis": model}
        state["model_history"] = []
    return state


class TestModelAccessorGet:
    def test_get_model_returns_domain_analysis(self):
        from services.model_accessor import ModelAccessor

        model = _make_model()
        state = _make_session_state(model)
        accessor = ModelAccessor(state)
        assert accessor.get_model() is model

    def test_get_model_raises_when_no_analysis(self):
        from services.model_accessor import ModelAccessor

        state = {}
        accessor = ModelAccessor(state)
        with pytest.raises(ValueError, match="No domain model"):
            accessor.get_model()


class TestModelAccessorSet:
    def test_set_model_updates_session_state(self):
        from services.model_accessor import ModelAccessor

        model = _make_model()
        state = _make_session_state(model)
        accessor = ModelAccessor(state)

        new_model = _make_model()
        new_model.nombre_proyecto = "Updated"
        accessor.set_model(new_model)
        assert state["analysis_result"]["analysis"].nombre_proyecto == "Updated"


class TestModelAccessorSnapshot:
    def test_snapshot_pushes_to_history(self):
        from services.model_accessor import ModelAccessor

        model = _make_model()
        state = _make_session_state(model)
        accessor = ModelAccessor(state)

        accessor.snapshot("add_node", "Add CrearPedido")
        assert len(state["model_history"]) == 1
        record = state["model_history"][0]
        assert record.tool_name == "add_node"
        assert record.description == "Add CrearPedido"

    def test_snapshot_caps_at_max_history(self):
        from services.model_accessor import ModelAccessor

        model = _make_model()
        state = _make_session_state(model)
        accessor = ModelAccessor(state)

        for i in range(12):
            accessor.snapshot("add_node", f"Op {i}")

        assert len(state["model_history"]) <= 10


class TestModelAccessorUndo:
    def test_undo_restores_previous_state(self):
        from services.model_accessor import ModelAccessor

        model = _make_model()
        state = _make_session_state(model)
        accessor = ModelAccessor(state)

        accessor.snapshot("add_node", "Add node")
        # Mutate the model
        model.nombre_proyecto = "Mutated"
        record = accessor.undo()

        assert record is not None
        assert record.tool_name == "add_node"
        assert accessor.get_model().nombre_proyecto == "TestProject"

    def test_undo_returns_none_when_no_history(self):
        from services.model_accessor import ModelAccessor

        model = _make_model()
        state = _make_session_state(model)
        accessor = ModelAccessor(state)

        assert accessor.undo() is None


class TestModelAccessorFindNode:
    def test_find_node_in_big_picture(self):
        from services.model_accessor import ModelAccessor

        model = _make_model()
        state = _make_session_state(model)
        accessor = ModelAccessor(state)

        results = accessor.find_node("CrearPedido")
        assert len(results) >= 1
        assert any(n.nombre == "CrearPedido" for n in results)

    def test_find_node_in_specific_scope(self):
        from services.model_accessor import ModelAccessor

        model = _make_model()
        state = _make_session_state(model)
        accessor = ModelAccessor(state)

        results = accessor.find_node("CrearPedido", scope="big_picture")
        assert len(results) == 1
        assert results[0].nombre == "CrearPedido"

    def test_find_node_returns_empty_for_nonexistent(self):
        from services.model_accessor import ModelAccessor

        model = _make_model()
        state = _make_session_state(model)
        accessor = ModelAccessor(state)

        results = accessor.find_node("Nonexistent")
        assert results == []


class TestModelAccessorFindAggregate:
    def test_find_aggregate_by_name(self):
        from services.model_accessor import ModelAccessor

        model = _make_model()
        state = _make_session_state(model)
        accessor = ModelAccessor(state)

        agg = accessor.find_aggregate("Pedidos")
        assert agg is not None
        assert agg.nombre_agregado == "Pedidos"

    def test_find_aggregate_returns_none_for_nonexistent(self):
        from services.model_accessor import ModelAccessor

        model = _make_model()
        state = _make_session_state(model)
        accessor = ModelAccessor(state)

        assert accessor.find_aggregate("Nonexistent") is None
