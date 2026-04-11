"""Unit tests for Ambiguity, CompletenessGap, RefinementPlan, and RefinementSession models.

Tests lifecycle, field constraints, and hash generation as required by T004.
"""

from __future__ import annotations

import pytest


class TestAmbiguity:
    """Tests for Ambiguity model — lifecycle and field constraints."""

    def test_creates_with_required_fields(self):
        from domain.models.tool_schemas import Ambiguity

        amb = Ambiguity(
            id="amb_001",
            type="lexical",
            priority=2,
            description="'CrearPedido' y 'CrearOrden' podrían ser sinónimos.",
            affected_elements=["cmd_crear_pedido", "cmd_crear_orden"],
            suggested_resolutions=["Unificar bajo 'CrearPedido'", "Unificar bajo 'CrearOrden'"],
        )
        assert amb.id == "amb_001"
        assert amb.type == "lexical"
        assert amb.priority == 2
        assert amb.assumptions_made is None

    def test_accepts_all_type_literals(self):
        from domain.models.tool_schemas import Ambiguity

        for t in ("lexical", "structural", "semantic"):
            amb = Ambiguity(
                id=f"amb_{t}",
                type=t,
                priority=1,
                description="desc",
                affected_elements=["x"],
                suggested_resolutions=["fix"],
            )
            assert amb.type == t

    def test_rejects_invalid_type(self):
        from pydantic import ValidationError

        from domain.models.tool_schemas import Ambiguity

        with pytest.raises(ValidationError):
            Ambiguity(
                id="bad",
                type="unknown",
                priority=1,
                description="d",
                affected_elements=[],
                suggested_resolutions=[],
            )

    def test_rejects_invalid_priority(self):
        from pydantic import ValidationError

        from domain.models.tool_schemas import Ambiguity

        with pytest.raises(ValidationError):
            Ambiguity(
                id="bad",
                type="lexical",
                priority=5,
                description="d",
                affected_elements=[],
                suggested_resolutions=[],
            )

    def test_assumptions_made_optional(self):
        from domain.models.tool_schemas import Ambiguity

        amb = Ambiguity(
            id="amb_001",
            type="structural",
            priority=1,
            description="missing event",
            affected_elements=["agg_pedidos"],
            suggested_resolutions=["add event"],
            assumptions_made="assumed as new",
        )
        assert amb.assumptions_made == "assumed as new"

    def test_serializes_to_json(self):
        from domain.models.tool_schemas import Ambiguity

        amb = Ambiguity(
            id="amb_001",
            type="lexical",
            priority=2,
            description="test",
            affected_elements=["a"],
            suggested_resolutions=["fix"],
        )
        data = amb.model_dump()
        assert data["id"] == "amb_001"
        assert data["type"] == "lexical"
        assert data["priority"] == 2


class TestCompletenessGap:
    """Tests for CompletenessGap model — structural gap representation."""

    def test_creates_with_required_fields(self):
        from domain.models.tool_schemas import CompletenessGap

        gap = CompletenessGap(
            rule_name="aggregate_has_events",
            description="Agregado 'Pedidos' no tiene eventos.",
            affected_aggregate="Pedidos",
            affected_elements=["Pedidos"],
            suggestion="Agregue al menos un evento al agregado.",
        )
        assert gap.rule_name == "aggregate_has_events"
        assert gap.affected_aggregate == "Pedidos"

    def test_affected_elements_can_be_empty(self):
        from domain.models.tool_schemas import CompletenessGap

        gap = CompletenessGap(
            rule_name="bounded_context_has_read_models",
            description="No read models defined.",
            affected_aggregate="_global",
            affected_elements=[],
            suggestion="Add read models.",
        )
        assert gap.affected_elements == []

    def test_serializes_to_dict(self):
        from domain.models.tool_schemas import CompletenessGap

        gap = CompletenessGap(
            rule_name="command_produces_event",
            description="Command has no event.",
            affected_aggregate="Pedidos",
            affected_elements=["cmd_crear"],
            suggestion="Add PedidoCreado event.",
        )
        data = gap.model_dump()
        assert "rule_name" in data
        assert "suggestion" in data


class TestRefinementPlan:
    """Tests for RefinementPlan model — lifecycle and status transitions."""

    def test_creates_with_default_id_and_status(self):
        from domain.models.tool_schemas import RefinementPlan

        plan = RefinementPlan(
            source_ambiguity_ids=["amb_001"],
            description="Rename 'Orden' to 'Pedido' across model.",
            proposed_operations=[{"tool": "rename_element", "args": {"old_name": "Orden", "new_name": "Pedido"}}],
        )
        assert plan.status == "pending"
        assert plan.id.startswith("plan_")
        assert plan.executed_results == []

    def test_accepts_all_status_literals(self):
        from domain.models.tool_schemas import RefinementPlan

        for status in ("pending", "approved", "rejected", "executed", "failed"):
            plan = RefinementPlan(
                source_ambiguity_ids=["amb_001"],
                description="test",
                proposed_operations=[],
                status=status,
            )
            assert plan.status == status

    def test_rejects_invalid_status(self):
        from pydantic import ValidationError

        from domain.models.tool_schemas import RefinementPlan

        with pytest.raises(ValidationError):
            RefinementPlan(
                source_ambiguity_ids=[],
                description="test",
                proposed_operations=[],
                status="running",
            )

    def test_executed_results_default_empty(self):
        from domain.models.tool_schemas import RefinementPlan

        plan = RefinementPlan(
            source_ambiguity_ids=[],
            description="empty",
            proposed_operations=[],
        )
        assert plan.executed_results == []

    def test_can_append_tool_executions(self):
        from domain.models.tool_schemas import RefinementPlan, ToolExecution

        plan = RefinementPlan(
            source_ambiguity_ids=["amb_001"],
            description="test",
            proposed_operations=[],
        )
        exec_ = ToolExecution(
            tool_name="rename_element",
            arguments={"old_name": "Orden"},
            result='{"success": true, "message": "ok", "affected_elements": []}',
            success=True,
        )
        plan.executed_results.append(exec_)
        assert len(plan.executed_results) == 1


class TestRefinementSession:
    """Tests for RefinementSession model — lifecycle and hash generation."""

    def test_creates_with_auto_id_and_timestamp(self):
        from domain.models.tool_schemas import RefinementSession

        session = RefinementSession(model_hash="abc123")
        assert session.id != ""
        assert session.created_at != ""
        assert session.status == "analyzing"
        assert session.ambiguities == []
        assert session.plans == []

    def test_model_hash_required(self):
        from pydantic import ValidationError

        from domain.models.tool_schemas import RefinementSession

        with pytest.raises(ValidationError):
            RefinementSession()

    def test_status_transitions(self):
        from domain.models.tool_schemas import RefinementSession

        for status in ("analyzing", "presenting", "resolving", "completed"):
            session = RefinementSession(model_hash="h", status=status)
            assert session.status == status

    def test_compute_model_hash_deterministic(self):
        from domain.models.tool_schemas import RefinementSession

        json_str = '{"nombre_proyecto": "Test", "version": "1.0.0"}'
        hash1 = RefinementSession.compute_model_hash(json_str)
        hash2 = RefinementSession.compute_model_hash(json_str)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_compute_model_hash_differs_for_different_inputs(self):
        from domain.models.tool_schemas import RefinementSession

        h1 = RefinementSession.compute_model_hash("model_v1")
        h2 = RefinementSession.compute_model_hash("model_v2")
        assert h1 != h2

    def test_can_add_ambiguities_and_plans(self):
        from domain.models.tool_schemas import Ambiguity, RefinementPlan, RefinementSession

        session = RefinementSession(model_hash="abc")
        amb = Ambiguity(
            id="amb_001",
            type="lexical",
            priority=2,
            description="test",
            affected_elements=["x"],
            suggested_resolutions=["fix"],
        )
        plan = RefinementPlan(
            source_ambiguity_ids=["amb_001"],
            description="fix it",
            proposed_operations=[],
        )
        session.ambiguities.append(amb)
        session.plans.append(plan)
        assert len(session.ambiguities) == 1
        assert len(session.plans) == 1

    def test_unique_ids_generated(self):
        from domain.models.tool_schemas import RefinementSession

        s1 = RefinementSession(model_hash="h")
        s2 = RefinementSession(model_hash="h")
        assert s1.id != s2.id
