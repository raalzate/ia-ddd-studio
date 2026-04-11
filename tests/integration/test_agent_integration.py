"""Integration tests for agent turns via ChatAgentPort. [TS-004, TS-018]

Tests full agent turn: user message → tool calls → model mutation → response.
Uses mocked LLM but real tools and ModelAccessor.
"""

from unittest.mock import MagicMock

from models.domain_analysis import (
    AristaGrafo,
    BigPicture,
    DomainAnalysis,
    GrafoPorAgregado,
    NodoGrafo,
)


def _make_model() -> DomainAnalysis:
    return DomainAnalysis(
        nombre_proyecto="IntegrationTest",
        version="1.0.0",
        fecha_analisis="2026-03-19",
        big_picture=BigPicture(
            descripcion="Test big picture",
            nodos=[
                NodoGrafo(
                    id="cmd_crear_pedido",
                    tipo_elemento="Comando",
                    nombre="CrearPedido",
                    descripcion="Crea pedido",
                    nivel="big_picture",
                ),
                NodoGrafo(
                    id="evt_pedido_creado",
                    tipo_elemento="Evento",
                    nombre="PedidoCreado",
                    descripcion="Pedido creado",
                    nivel="big_picture",
                ),
                NodoGrafo(
                    id="svc_inventario",
                    tipo_elemento="Sistema Externo",
                    nombre="Inventario",
                    descripcion="Inventario",
                    nivel="big_picture",
                ),
            ],
            aristas=[
                AristaGrafo(fuente="cmd_crear_pedido", destino="evt_pedido_creado", descripcion="dispara"),
                AristaGrafo(fuente="evt_pedido_creado", destino="svc_inventario", descripcion="notifica"),
            ],
        ),
        agregados=[
            GrafoPorAgregado(
                nombre_agregado="Pedidos",
                entidad_raiz="Pedido",
                descripcion="Pedidos aggregate",
                nodos=[
                    NodoGrafo(
                        id="cmd_crear_pedido",
                        tipo_elemento="Comando",
                        nombre="CrearPedido",
                        descripcion="Crea",
                        nivel="process_level",
                    ),
                    NodoGrafo(
                        id="evt_pedido_creado",
                        tipo_elemento="Evento",
                        nombre="PedidoCreado",
                        descripcion="Creado",
                        nivel="process_level",
                    ),
                ],
                aristas=[
                    AristaGrafo(
                        fuente="cmd_crear_pedido",
                        destino="evt_pedido_creado",
                        descripcion="dispara",
                    ),
                ],
            ),
        ],
    )


def _make_state(model: DomainAnalysis) -> dict:
    return {"analysis_result": {"analysis": model}, "model_history": []}


class TestAgentAddNodeIntegration:
    """TS-004: Session state updates in real time after tool execution."""

    def test_add_node_via_agent_mutates_session_state(self):
        from infra.adapters.gemini_chat_agent import GeminiChatAgentAdapter
        from services.model_accessor import ModelAccessor

        model = _make_model()
        state = _make_state(model)
        accessor = ModelAccessor(state)

        # Simulate LLM deciding to call add_node, then giving final text
        tool_call = MagicMock()
        tool_call.content = ""
        tool_call.tool_calls = [
            {
                "name": "add_node",
                "args": {
                    "scope": "aggregate",
                    "aggregate_name": "Pedidos",
                    "node_name": "CancelarPedido",
                    "node_type": "Comando",
                    "description": "Cancela un pedido existente",
                },
                "id": "call_1",
            }
        ]

        final = MagicMock()
        final.content = "He agregado el comando 'CancelarPedido' al agregado 'Pedidos'."
        final.tool_calls = []

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value.invoke.side_effect = [tool_call, final]

        adapter = GeminiChatAgentAdapter(llm=mock_llm)
        result = adapter.run(
            user_message="Agrega un comando CancelarPedido al agregado Pedidos",
            history=[],
            system_prompt="You are an architect.",
            model_accessor=accessor,
        )

        # Verify session state was mutated
        updated_model = state["analysis_result"]["analysis"]
        agg = next(a for a in updated_model.agregados if a.nombre_agregado == "Pedidos")
        assert any(n.nombre == "CancelarPedido" for n in agg.nodos)
        assert len(result.tool_executions) == 1
        assert result.tool_executions[0].success is True

    def test_rename_via_agent_updates_model_and_edges(self):
        from infra.adapters.gemini_chat_agent import GeminiChatAgentAdapter
        from services.model_accessor import ModelAccessor

        model = _make_model()
        state = _make_state(model)
        accessor = ModelAccessor(state)

        tool_call = MagicMock()
        tool_call.content = ""
        tool_call.tool_calls = [
            {
                "name": "rename_element",
                "args": {
                    "element_type": "node",
                    "current_name": "Inventario",
                    "new_name": "GestiónDeStock",
                    "scope": "big_picture",
                },
                "id": "call_rename",
            }
        ]

        final = MagicMock()
        final.content = "Renombré 'Inventario' a 'GestiónDeStock'."
        final.tool_calls = []

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value.invoke.side_effect = [tool_call, final]

        adapter = GeminiChatAgentAdapter(llm=mock_llm)
        adapter.run(
            user_message="Renombra Inventario a GestiónDeStock",
            history=[],
            system_prompt="You are an architect.",
            model_accessor=accessor,
        )

        updated = state["analysis_result"]["analysis"]
        assert any(n.nombre == "GestiónDeStock" for n in updated.big_picture.nodos)
        assert not any(n.nombre == "Inventario" for n in updated.big_picture.nodos)


class TestAgentResponseContract:
    """TS-018: Agent confirms operation details after successful write."""

    def test_agent_response_contains_operation_and_elements(self):
        from domain.models.tool_schemas import AgentResponse
        from infra.adapters.gemini_chat_agent import GeminiChatAgentAdapter
        from services.model_accessor import ModelAccessor

        model = _make_model()
        state = _make_state(model)
        accessor = ModelAccessor(state)

        tool_call = MagicMock()
        tool_call.content = ""
        tool_call.tool_calls = [
            {
                "name": "add_node",
                "args": {
                    "scope": "big_picture",
                    "node_name": "NuevoEvento",
                    "node_type": "Evento",
                    "description": "A new event",
                },
                "id": "call_add",
            }
        ]

        final = MagicMock()
        final.content = "He agregado el evento 'NuevoEvento' al big picture."
        final.tool_calls = []

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value.invoke.side_effect = [tool_call, final]

        adapter = GeminiChatAgentAdapter(llm=mock_llm)
        result = adapter.run(
            user_message="Agrega un evento NuevoEvento",
            history=[],
            system_prompt="You are an architect.",
            model_accessor=accessor,
        )

        assert isinstance(result, AgentResponse)
        assert len(result.tool_executions) == 1
        exec = result.tool_executions[0]
        assert exec.tool_name == "add_node"
        assert exec.success is True
        assert "NuevoEvento" in result.content
