"""Unit tests for ChatAgentPort adapter (ReAct loop, tool dispatch, max iterations). [TS-018]

Tests the GeminiChatAgentAdapter with mocked LLM responses.
"""

from unittest.mock import MagicMock

from models.domain_analysis import (
    BigPicture,
    DomainAnalysis,
    NodoGrafo,
)


def _make_model() -> DomainAnalysis:
    return DomainAnalysis(
        nombre_proyecto="TestProject",
        version="1.0.0",
        fecha_analisis="2026-03-19",
        big_picture=BigPicture(
            descripcion="Test",
            nodos=[
                NodoGrafo(
                    id="cmd_test",
                    tipo_elemento="Comando",
                    nombre="Test",
                    descripcion="Test node",
                    nivel="big_picture",
                ),
            ],
            aristas=[],
        ),
        agregados=[],
    )


def _make_session_state(model: DomainAnalysis) -> dict:
    return {
        "analysis_result": {"analysis": model},
        "model_history": [],
    }


class TestChatAgentPortProtocol:
    """Verify ChatAgentPort is a proper protocol with run method."""

    def test_protocol_defines_run_method(self):
        from domain.ports import ChatAgentPort

        assert hasattr(ChatAgentPort, "run")


class TestGeminiChatAgentAdapter:
    """Tests for the ReAct loop adapter with mocked LLM."""

    def test_text_only_response_returns_agent_response(self):
        """When LLM returns text without tool calls, return AgentResponse with empty tool_executions."""
        from domain.models.tool_schemas import AgentResponse
        from infra.adapters.gemini_chat_agent import GeminiChatAgentAdapter
        from services.model_accessor import ModelAccessor

        model = _make_model()
        state = _make_session_state(model)
        accessor = ModelAccessor(state)

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "The model looks good."
        mock_response.tool_calls = []
        mock_llm.bind_tools.return_value.invoke.return_value = mock_response

        adapter = GeminiChatAgentAdapter(model="gemini-1.5-flash", api_key="fake-key")
        adapter._llm_instance = mock_llm
        result = adapter.run(
            user_message="How does the model look?",
            history=[],
            system_prompt="You are an architect.",
            model_accessor=accessor,
        )

        assert isinstance(result, AgentResponse)
        assert result.content == "The model looks good."
        assert result.tool_executions == []

    def test_tool_call_executes_and_returns_result(self):
        """When LLM returns tool_calls, execute them and return results."""
        from domain.models.tool_schemas import AgentResponse
        from infra.adapters.gemini_chat_agent import GeminiChatAgentAdapter
        from services.model_accessor import ModelAccessor

        model = _make_model()
        state = _make_session_state(model)
        accessor = ModelAccessor(state)

        # First invoke: LLM wants to call a tool
        tool_call_response = MagicMock()
        tool_call_response.content = ""
        tool_call_response.tool_calls = [
            {
                "name": "query_model",
                "args": {"section": "summary"},
                "id": "call_1",
            }
        ]

        # Second invoke: LLM gives final text
        final_response = MagicMock()
        final_response.content = "The model has 1 node."
        final_response.tool_calls = []

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value.invoke.side_effect = [tool_call_response, final_response]

        adapter = GeminiChatAgentAdapter(model="gemini-1.5-flash", api_key="fake-key")
        adapter._llm_instance = mock_llm
        result = adapter.run(
            user_message="How many nodes?",
            history=[],
            system_prompt="You are an architect.",
            model_accessor=accessor,
        )

        assert isinstance(result, AgentResponse)
        assert result.content == "The model has 1 node."
        assert len(result.tool_executions) == 1
        assert result.tool_executions[0].tool_name == "query_model"

    def test_max_iterations_prevents_infinite_loop(self):
        """ReAct loop must stop after MAX_ITERATIONS even if LLM keeps calling tools."""
        from infra.adapters.gemini_chat_agent import GeminiChatAgentAdapter
        from services.model_accessor import ModelAccessor

        model = _make_model()
        state = _make_session_state(model)
        accessor = ModelAccessor(state)

        # LLM always returns tool calls
        tool_call_response = MagicMock()
        tool_call_response.content = ""
        tool_call_response.tool_calls = [
            {
                "name": "query_model",
                "args": {"section": "summary"},
                "id": "call_loop",
            }
        ]

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value.invoke.return_value = tool_call_response

        adapter = GeminiChatAgentAdapter(model="gemini-1.5-flash", api_key="fake-key")
        adapter._llm_instance = mock_llm
        adapter.run(
            user_message="Loop forever",
            history=[],
            system_prompt="You are an architect.",
            model_accessor=accessor,
        )

        # Should stop after max iterations (5)
        assert mock_llm.bind_tools.return_value.invoke.call_count <= 7

    def test_agent_response_includes_operation_details(self):
        """TS-018: Agent confirms operation details after successful write."""
        from infra.adapters.gemini_chat_agent import GeminiChatAgentAdapter
        from services.model_accessor import ModelAccessor

        model = _make_model()
        state = _make_session_state(model)
        accessor = ModelAccessor(state)

        # Tool call for add_node
        tool_call_response = MagicMock()
        tool_call_response.content = ""
        tool_call_response.tool_calls = [
            {
                "name": "add_node",
                "args": {
                    "scope": "big_picture",
                    "aggregate_name": None,
                    "node_name": "NuevoEvento",
                    "node_type": "Evento",
                    "description": "A new event",
                },
                "id": "call_add",
            }
        ]

        final_response = MagicMock()
        final_response.content = "I've added NuevoEvento to the big picture."
        final_response.tool_calls = []

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value.invoke.side_effect = [tool_call_response, final_response]

        adapter = GeminiChatAgentAdapter(model="gemini-1.5-flash", api_key="fake-key")
        adapter._llm_instance = mock_llm
        result = adapter.run(
            user_message="Add NuevoEvento",
            history=[],
            system_prompt="You are an architect.",
            model_accessor=accessor,
        )

        assert len(result.tool_executions) == 1
        assert result.tool_executions[0].tool_name == "add_node"
        assert "NuevoEvento" in result.content
