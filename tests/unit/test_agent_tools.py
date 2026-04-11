"""Unit tests for agent tool functions.

Tests add_node, add_edge, rename_element, delete_node, delete_edge,
query_model, and undo_last_change tools with mocked model.
"""

import json

from models.domain_analysis import (
    AristaGrafo,
    BigPicture,
    DomainAnalysis,
    GrafoPorAgregado,
    NodoGrafo,
)
from services.model_accessor import ModelAccessor


def _make_node(id: str, name: str, tipo: str = "Comando", nivel: str = "big_picture") -> NodoGrafo:
    return NodoGrafo(id=id, tipo_elemento=tipo, nombre=name, descripcion=f"Test {name}", nivel=nivel)


def _make_edge(src: str, dst: str, desc: str = "flows") -> AristaGrafo:
    return AristaGrafo(fuente=src, destino=dst, descripcion=desc)


def _make_model() -> DomainAnalysis:
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
                _make_edge("evt_pedido_creado", "svc_inventario", "notifica"),
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


def _make_accessor(model: DomainAnalysis | None = None) -> ModelAccessor:
    model = model or _make_model()
    state = {
        "analysis_result": {"analysis": model},
        "model_history": [],
    }
    return ModelAccessor(state)


def _get_tools(accessor: ModelAccessor) -> dict:
    from services.agent_tools import create_tools

    tools = create_tools(accessor)
    return {t.name: t for t in tools}


# ============================================================
# T010: add_node tests [TS-001, TS-012]
# ============================================================
class TestAddNode:
    """Tests for add_node tool."""

    def test_add_node_to_aggregate(self):
        """TS-001: Add a command node to an aggregate."""
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        result_str = tools["add_node"].invoke(
            {
                "scope": "aggregate",
                "aggregate_name": "Pedidos",
                "node_name": "CancelarPedido",
                "node_type": "Comando",
                "description": "Cancels an order",
            }
        )
        result = json.loads(result_str)
        assert result["success"] is True
        assert any("cancelarpedido" in el for el in result["affected_elements"])
        # Verify node exists in aggregate
        agg = accessor.find_aggregate("Pedidos")
        assert any(n.nombre == "CancelarPedido" for n in agg.nodos)

    def test_add_node_to_big_picture(self):
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        result_str = tools["add_node"].invoke(
            {
                "scope": "big_picture",
                "aggregate_name": None,
                "node_name": "NuevoServicio",
                "node_type": "Sistema Externo",
                "description": "A new external system",
            }
        )
        result = json.loads(result_str)
        assert result["success"] is True
        model = accessor.get_model()
        assert any(n.nombre == "NuevoServicio" for n in model.big_picture.nodos)

    def test_add_node_rejects_duplicate_id(self):
        """TS-012: Reject adding a node with a duplicate ID."""
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        # First add a node
        tools["add_node"].invoke(
            {
                "scope": "big_picture",
                "aggregate_name": None,
                "node_name": "NuevoNodo",
                "node_type": "Evento",
                "description": "First",
            }
        )
        # Try to add the same node again
        result_str = tools["add_node"].invoke(
            {
                "scope": "big_picture",
                "aggregate_name": None,
                "node_name": "NuevoNodo",
                "node_type": "Evento",
                "description": "Duplicate",
            }
        )
        result = json.loads(result_str)
        assert result["success"] is False
        assert "already exists" in result["message"].lower() or "duplicate" in result["message"].lower()

    def test_add_node_creates_snapshot_for_undo(self):
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        tools["add_node"].invoke(
            {
                "scope": "big_picture",
                "aggregate_name": None,
                "node_name": "Temporal",
                "node_type": "Evento",
                "description": "Temp",
            }
        )
        assert len(accessor._state["model_history"]) == 1


# ============================================================
# T011: add_edge tests [TS-003, TS-014, TS-015]
# ============================================================
class TestAddEdge:
    """Tests for add_edge tool."""

    def test_add_edge_between_existing_nodes(self):
        """TS-003: Add an edge between two nodes in an aggregate."""
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        result_str = tools["add_edge"].invoke(
            {
                "scope": "aggregate",
                "aggregate_name": "Pedidos",
                "source_name": "CrearPedido",
                "target_name": "PedidoCreado",
                "description": "dispara evento",
            }
        )
        result = json.loads(result_str)
        assert result["success"] is True

    def test_add_edge_rejects_nonexistent_source(self):
        """TS-014: Reject edge when source node does not exist."""
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        result_str = tools["add_edge"].invoke(
            {
                "scope": "aggregate",
                "aggregate_name": "Pedidos",
                "source_name": "NodoInexistente",
                "target_name": "PedidoCreado",
                "description": "invalid",
            }
        )
        result = json.loads(result_str)
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_add_edge_rejects_nonexistent_target(self):
        """TS-015: Reject edge when target node does not exist."""
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        result_str = tools["add_edge"].invoke(
            {
                "scope": "aggregate",
                "aggregate_name": "Pedidos",
                "source_name": "CrearPedido",
                "target_name": "NodoInexistente",
                "description": "invalid",
            }
        )
        result = json.loads(result_str)
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_add_edge_to_big_picture(self):
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        result_str = tools["add_edge"].invoke(
            {
                "scope": "big_picture",
                "aggregate_name": None,
                "source_name": "PedidoCreado",
                "target_name": "Inventario",
                "description": "notifies",
            }
        )
        result = json.loads(result_str)
        assert result["success"] is True


# ============================================================
# T012: rename_element tests [TS-002]
# ============================================================
class TestRenameElement:
    """Tests for rename_element tool."""

    def test_rename_node_in_big_picture(self):
        """TS-002: Rename a node in the big picture."""
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        result_str = tools["rename_element"].invoke(
            {
                "element_type": "node",
                "current_name": "Inventario",
                "new_name": "GestiónDeStock",
                "scope": "big_picture",
            }
        )
        result = json.loads(result_str)
        assert result["success"] is True
        model = accessor.get_model()
        assert any(n.nombre == "GestiónDeStock" for n in model.big_picture.nodos)
        assert not any(n.nombre == "Inventario" for n in model.big_picture.nodos)

    def test_rename_node_updates_edge_references(self):
        """Renaming a node should update edges that reference its old ID."""
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        result_str = tools["rename_element"].invoke(
            {
                "element_type": "node",
                "current_name": "CrearPedido",
                "new_name": "CrearOrden",
                "scope": "big_picture",
            }
        )
        result = json.loads(result_str)
        assert result["success"] is True
        model = accessor.get_model()
        # The edge that had fuente=cmd_crear_pedido should now reference the new ID
        renamed_node = next(n for n in model.big_picture.nodos if n.nombre == "CrearOrden")
        assert any(e.fuente == renamed_node.id for e in model.big_picture.aristas)

    def test_rename_nonexistent_element_fails(self):
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        result_str = tools["rename_element"].invoke(
            {
                "element_type": "node",
                "current_name": "Nonexistent",
                "new_name": "NewName",
                "scope": "big_picture",
            }
        )
        result = json.loads(result_str)
        assert result["success"] is False


# ============================================================
# T018: delete_node tests [TS-005, TS-007]
# ============================================================
class TestDeleteNode:
    """Tests for delete_node tool."""

    def test_delete_node_with_cascade_edge_removal(self):
        """TS-005: Delete a node and cascade-remove referencing edges."""
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        result_str = tools["delete_node"].invoke(
            {
                "scope": "big_picture",
                "aggregate_name": None,
                "node_name": "CrearPedido",
            }
        )
        result = json.loads(result_str)
        assert result["success"] is True
        model = accessor.get_model()
        assert not any(n.nombre == "CrearPedido" for n in model.big_picture.nodos)
        # Edge from CrearPedido should be removed
        assert not any(
            e.fuente == "cmd_crear_pedido" or e.destino == "cmd_crear_pedido" for e in model.big_picture.aristas
        )

    def test_delete_nonexistent_node_fails(self):
        """TS-007: Attempt to delete a non-existent node."""
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        result_str = tools["delete_node"].invoke(
            {
                "scope": "big_picture",
                "aggregate_name": None,
                "node_name": "ServicioFantasma",
            }
        )
        result = json.loads(result_str)
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_delete_node_preserves_other_nodes(self):
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        model = accessor.get_model()
        original_count = len(model.big_picture.nodos)
        tools["delete_node"].invoke(
            {
                "scope": "big_picture",
                "aggregate_name": None,
                "node_name": "Inventario",
            }
        )
        assert len(model.big_picture.nodos) == original_count - 1
        assert any(n.nombre == "CrearPedido" for n in model.big_picture.nodos)

    def test_delete_node_does_not_modify_on_failure(self):
        accessor = _make_accessor()
        model = accessor.get_model()
        original_count = len(model.big_picture.nodos)
        tools = _get_tools(accessor)
        tools["delete_node"].invoke(
            {
                "scope": "big_picture",
                "aggregate_name": None,
                "node_name": "Nonexistent",
            }
        )
        assert len(model.big_picture.nodos) == original_count


# ============================================================
# T019: delete_edge tests [TS-006]
# ============================================================
class TestDeleteEdge:
    """Tests for delete_edge tool."""

    def test_delete_edge_leaves_nodes_intact(self):
        """TS-006: Delete only an edge leaving nodes intact."""
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        result_str = tools["delete_edge"].invoke(
            {
                "scope": "big_picture",
                "aggregate_name": None,
                "source_name": "CrearPedido",
                "target_name": "PedidoCreado",
            }
        )
        result = json.loads(result_str)
        assert result["success"] is True
        model = accessor.get_model()
        # Nodes should still exist
        assert any(n.nombre == "CrearPedido" for n in model.big_picture.nodos)
        assert any(n.nombre == "PedidoCreado" for n in model.big_picture.nodos)
        # Edge should be gone
        assert not any(
            e.fuente == "cmd_crear_pedido" and e.destino == "evt_pedido_creado" for e in model.big_picture.aristas
        )

    def test_delete_nonexistent_edge_fails(self):
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        result_str = tools["delete_edge"].invoke(
            {
                "scope": "big_picture",
                "aggregate_name": None,
                "source_name": "Inventario",
                "target_name": "PedidoCreado",
            }
        )
        result = json.loads(result_str)
        assert result["success"] is False


# ============================================================
# T023: query_model tests [TS-008, TS-009, TS-017]
# ============================================================
class TestQueryModel:
    """Tests for query_model tool."""

    def test_query_aggregate_returns_aggregate_data(self):
        """TS-008: Query aggregate nodes."""
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        result_str = tools["query_model"].invoke(
            {
                "section": "aggregate",
                "aggregate_name": "Pedidos",
            }
        )
        data = json.loads(result_str)
        assert data.get("nombre_agregado") == "Pedidos"

    def test_query_policies(self):
        """TS-009: Query inter-aggregate policies."""
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        result_str = tools["query_model"].invoke(
            {
                "section": "policies",
            }
        )
        data = json.loads(result_str)
        assert isinstance(data, list)

    def test_query_summary_returns_counts(self):
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        result_str = tools["query_model"].invoke(
            {
                "section": "summary",
            }
        )
        data = json.loads(result_str)
        assert "big_picture_nodes" in data
        assert data["big_picture_nodes"] == 3

    def test_query_aggregate_without_name_fails(self):
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        result_str = tools["query_model"].invoke(
            {
                "section": "aggregate",
            }
        )
        result = json.loads(result_str)
        assert result["success"] is False

    def test_query_returns_filtered_section_not_full_model(self):
        """TS-017: Only the requested section is returned."""
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        result_str = tools["query_model"].invoke(
            {
                "section": "aggregate",
                "aggregate_name": "Pedidos",
            }
        )
        data = json.loads(result_str)
        # Should have aggregate fields, not full model fields
        assert "nombre_agregado" in data
        assert "nombre_proyecto" not in data


# ============================================================
# T031: undo_last_change tests [TS-010, TS-011]
# ============================================================
class TestUndoLastChange:
    """Tests for undo_last_change tool."""

    def test_undo_reverts_last_write(self):
        """TS-010: Undo the last write operation."""
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        model = accessor.get_model()
        original_count = len(model.big_picture.nodos)

        # Add a node
        tools["add_node"].invoke(
            {
                "scope": "big_picture",
                "node_name": "Temporal",
                "node_type": "Evento",
                "description": "Temporary",
            }
        )
        assert len(model.big_picture.nodos) == original_count + 1

        # Undo
        result_str = tools["undo_last_change"].invoke({})
        result = json.loads(result_str)
        assert result["success"] is True
        assert (
            "reverted" in result["message"].lower()
            or "undone" in result["message"].lower()
            or "add_node" in result["message"].lower()
        )
        # Model should be back to original
        assert len(accessor.get_model().big_picture.nodos) == original_count

    def test_undo_with_no_history(self):
        """TS-011: Undo when no changes have been made."""
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        result_str = tools["undo_last_change"].invoke({})
        result = json.loads(result_str)
        assert result["success"] is False
        assert "no" in result["message"].lower()

    def test_undo_creates_no_snapshot(self):
        """Undo itself should not push to history."""
        accessor = _make_accessor()
        tools = _get_tools(accessor)
        tools["add_node"].invoke(
            {
                "scope": "big_picture",
                "node_name": "Temp",
                "node_type": "Evento",
                "description": "Temp",
            }
        )
        assert len(accessor._state["model_history"]) == 1
        tools["undo_last_change"].invoke({})
        # History should be empty now (popped the one entry)
        assert len(accessor._state["model_history"]) == 0
