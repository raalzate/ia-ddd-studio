"""Extended tests for RefinementSession iteration helpers in tool_schemas.py."""

from domain.models.tool_schemas import (
    Ambiguity,
    CompletenessGap,
    RefinementPlan,
    RefinementSession,
    ToolExecution,
)


def _make_ambiguity(id: str, status: str = "pending") -> Ambiguity:
    return Ambiguity(
        id=id,
        type="lexical",
        priority=2,
        description=f"Ambiguity {id}",
        affected_elements=["elem1"],
        suggested_resolutions=["fix it"],
        status=status,
    )


class TestRefinementSession:
    def test_current_ambiguity_returns_first_pending(self):
        session = RefinementSession(
            model_hash="abc",
            ambiguities=[
                _make_ambiguity("a1", "resolved"),
                _make_ambiguity("a2", "pending"),
                _make_ambiguity("a3", "pending"),
            ],
        )
        assert session.current_ambiguity().id == "a2"

    def test_current_ambiguity_returns_none_when_all_resolved(self):
        session = RefinementSession(
            model_hash="abc",
            ambiguities=[
                _make_ambiguity("a1", "resolved"),
                _make_ambiguity("a2", "skipped"),
            ],
        )
        assert session.current_ambiguity() is None

    def test_pending_count(self):
        session = RefinementSession(
            model_hash="abc",
            ambiguities=[
                _make_ambiguity("a1", "pending"),
                _make_ambiguity("a2", "resolved"),
                _make_ambiguity("a3", "pending"),
            ],
        )
        assert session.pending_count() == 2

    def test_resolved_count(self):
        session = RefinementSession(
            model_hash="abc",
            ambiguities=[
                _make_ambiguity("a1", "resolved"),
                _make_ambiguity("a2", "skipped"),
                _make_ambiguity("a3", "pending"),
            ],
        )
        assert session.resolved_count() == 2

    def test_total_count(self):
        session = RefinementSession(
            model_hash="abc",
            ambiguities=[_make_ambiguity("a1"), _make_ambiguity("a2")],
        )
        assert session.total_count() == 2

    def test_is_complete_true(self):
        session = RefinementSession(
            model_hash="abc",
            ambiguities=[
                _make_ambiguity("a1", "resolved"),
                _make_ambiguity("a2", "skipped"),
            ],
        )
        assert session.is_complete() is True

    def test_is_complete_false(self):
        session = RefinementSession(
            model_hash="abc",
            ambiguities=[
                _make_ambiguity("a1", "resolved"),
                _make_ambiguity("a2", "pending"),
            ],
        )
        assert session.is_complete() is False

    def test_is_complete_with_no_ambiguities(self):
        session = RefinementSession(model_hash="abc", ambiguities=[])
        assert session.is_complete() is True

    def test_resolve_current_marks_resolved(self):
        session = RefinementSession(
            model_hash="abc",
            ambiguities=[_make_ambiguity("a1"), _make_ambiguity("a2")],
        )
        next_amb = session.resolve_current()
        assert session.ambiguities[0].status == "resolved"
        assert next_amb.id == "a2"

    def test_resolve_current_marks_skipped(self):
        session = RefinementSession(
            model_hash="abc",
            ambiguities=[_make_ambiguity("a1"), _make_ambiguity("a2")],
        )
        next_amb = session.resolve_current(skipped=True)
        assert session.ambiguities[0].status == "skipped"
        assert next_amb.id == "a2"

    def test_resolve_current_returns_none_when_last(self):
        session = RefinementSession(
            model_hash="abc",
            ambiguities=[_make_ambiguity("a1")],
        )
        next_amb = session.resolve_current()
        assert next_amb is None

    def test_compute_model_hash(self):
        hash1 = RefinementSession.compute_model_hash('{"key": "value1"}')
        hash2 = RefinementSession.compute_model_hash('{"key": "value2"}')
        assert hash1 != hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_compute_model_hash_deterministic(self):
        data = '{"key": "value"}'
        assert RefinementSession.compute_model_hash(data) == RefinementSession.compute_model_hash(data)


class TestCompletenessGap:
    def test_creation(self):
        gap = CompletenessGap(
            rule_name="aggregate_has_commands",
            description="Aggregate has no commands",
            affected_aggregate="OrderAggregate",
            affected_elements=["OrderAggregate"],
            suggestion="Add a command to the aggregate",
        )
        assert gap.rule_name == "aggregate_has_commands"
        assert gap.affected_aggregate == "OrderAggregate"


class TestRefinementPlan:
    def test_auto_generated_id(self):
        plan = RefinementPlan(
            source_ambiguity_ids=["a1"],
            description="Fix naming",
            proposed_operations=[{"op": "rename"}],
        )
        assert plan.id.startswith("plan_")
        assert plan.status == "pending"

    def test_default_executed_results_empty(self):
        plan = RefinementPlan(
            source_ambiguity_ids=["a1"],
            description="Fix",
            proposed_operations=[],
        )
        assert plan.executed_results == []


class TestToolExecution:
    def test_creation(self):
        te = ToolExecution(
            tool_name="add_node",
            arguments={"name": "test"},
            result='{"success": true}',
            success=True,
        )
        assert te.tool_name == "add_node"
        assert te.success is True
