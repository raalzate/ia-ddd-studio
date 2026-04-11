"""Unit tests for ToolResult and OperationRecord models. [TS-016]

Tests the standardized tool result contract and operation history records.
"""

import json


class TestToolResult:
    """Tests for ToolResult model — standardized tool execution result."""

    def test_success_result_has_required_fields(self):
        from domain.models.tool_schemas import ToolResult

        result = ToolResult(
            success=True,
            message="Node 'CrearPedido' added to aggregate 'Pedidos'",
            affected_elements=["cmd_crear_pedido"],
        )
        assert result.success is True
        assert result.message == "Node 'CrearPedido' added to aggregate 'Pedidos'"
        assert result.affected_elements == ["cmd_crear_pedido"]

    def test_failure_result(self):
        from domain.models.tool_schemas import ToolResult

        result = ToolResult(
            success=False,
            message="Node 'LegacyService' not found in big_picture",
            affected_elements=[],
        )
        assert result.success is False
        assert result.affected_elements == []

    def test_serializes_to_json_with_required_keys(self):
        """TS-016: All write tools return standardized ToolResult JSON."""
        from domain.models.tool_schemas import ToolResult

        result = ToolResult(
            success=True,
            message="Operation completed",
            affected_elements=["node_a", "node_b"],
        )
        json_str = result.model_dump_json()
        parsed = json.loads(json_str)
        assert "success" in parsed
        assert "message" in parsed
        assert "affected_elements" in parsed

    def test_default_affected_elements_is_empty_list(self):
        from domain.models.tool_schemas import ToolResult

        result = ToolResult(success=True, message="ok")
        assert result.affected_elements == []


class TestOperationRecord:
    """Tests for OperationRecord — undo history entry."""

    def test_stores_snapshot_and_metadata(self):
        from domain.models.tool_schemas import OperationRecord

        snapshot = {"nombre_proyecto": "Test", "version": "1.0.0"}
        record = OperationRecord(
            timestamp="2026-03-19T10:00:00",
            tool_name="add_node",
            description="Add node CrearPedido",
            snapshot=snapshot,
        )
        assert record.tool_name == "add_node"
        assert record.description == "Add node CrearPedido"
        assert record.snapshot == snapshot

    def test_timestamp_is_string(self):
        from domain.models.tool_schemas import OperationRecord

        record = OperationRecord(
            timestamp="2026-03-19T10:00:00",
            tool_name="delete_node",
            description="Delete LegacyService",
            snapshot={},
        )
        assert isinstance(record.timestamp, str)


class TestToolExecution:
    """Tests for ToolExecution — record of a tool call within an agent turn."""

    def test_captures_tool_call_details(self):
        from domain.models.tool_schemas import ToolExecution

        execution = ToolExecution(
            tool_name="add_node",
            arguments={"scope": "aggregate", "node_name": "CrearPedido"},
            result='{"success": true, "message": "ok", "affected_elements": []}',
            success=True,
        )
        assert execution.tool_name == "add_node"
        assert execution.arguments["scope"] == "aggregate"
        assert execution.success is True


class TestAgentResponse:
    """Tests for AgentResponse — complete agent turn response."""

    def test_contains_content_and_tool_executions(self):
        from domain.models.tool_schemas import AgentResponse, ToolExecution

        execution = ToolExecution(
            tool_name="add_node",
            arguments={"node_name": "X"},
            result='{"success": true, "message": "ok", "affected_elements": []}',
            success=True,
        )
        response = AgentResponse(
            content="I've added the node X.",
            tool_executions=[execution],
        )
        assert response.content == "I've added the node X."
        assert len(response.tool_executions) == 1

    def test_empty_tool_executions_for_text_only_response(self):
        from domain.models.tool_schemas import AgentResponse

        response = AgentResponse(
            content="The model has 5 nodes.",
            tool_executions=[],
        )
        assert response.tool_executions == []
