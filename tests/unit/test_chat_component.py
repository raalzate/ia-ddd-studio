"""Unit tests for src/ui/components/chat.py — pure logic helpers."""

from unittest.mock import MagicMock, patch


class TestGetOptimizedDomainContext:
    """Tests for get_optimized_domain_context (pure function, no Streamlit rendering)."""

    def _make_domain_dict(self):
        return {
            "big_picture": {
                "nodos": [
                    {
                        "id": "evt-1",
                        "tipo_elemento": "Evento",
                        "nombre": "OrderCreated",
                        "descripcion": "Order was created",
                        "tags_tecnologia": ["Kafka"],
                        "estado_comparativo": "nuevo",
                    },
                    {
                        "id": "cmd-1",
                        "tipo_elemento": "Comando",
                        "nombre": "CreateOrder",
                        "descripcion": "Creates an order",
                        "tags_tecnologia": [],
                        "estado_comparativo": "",
                    },
                ],
                "aristas": [
                    {
                        "fuente": "cmd-1",
                        "destino": "evt-1",
                        "descripcion": "triggers",
                    }
                ],
            },
            "agregados": [
                {
                    "nombre_agregado": "OrderAggregate",
                    "entidad_raiz": "Order",
                    "nodos": [
                        {
                            "id": "agg-1",
                            "tipo_elemento": "Agregado",
                            "nombre": "OrderAggregate",
                            "descripcion": "Order aggregate",
                            "tags_tecnologia": [],
                            "estado_comparativo": "",
                        }
                    ],
                    "aristas": [],
                }
            ],
            "read_models": [
                {
                    "nombre": "OrderDashboard",
                    "descripcion": "Shows orders",
                    "proyecta": ["evt-1"],
                    "ui_policies": [],
                    "tecnologias": [],
                }
            ],
            "politicas_inter_agregados": [
                {
                    "fuente": "evt-1",
                    "destino": "cmd-1",
                    "descripcion": "policy flow",
                }
            ],
        }

    @patch("ui.components.chat.st")
    def test_includes_big_picture_when_enabled(self, mock_st):
        # Bypass st.cache_data by calling the underlying function
        from ui.components.chat import get_optimized_domain_context

        # st.cache_data acts as passthrough in test
        mock_st.cache_data = lambda **kwargs: lambda fn: fn

        # Need to reimport to apply the mock - use the function directly
        domain_dict = self._make_domain_dict()
        # Call the wrapped function - in tests, Streamlit cache may not work,
        # so we call the function logic directly
        result = get_optimized_domain_context.__wrapped__(
            domain_dict, {"bp": True, "aggs": False, "rms": False, "policies": False}
        )
        assert "big_picture:" in result
        assert "OrderCreated" in result

    @patch("ui.components.chat.st")
    def test_excludes_big_picture_when_disabled(self, mock_st):
        from ui.components.chat import get_optimized_domain_context

        mock_st.cache_data = lambda **kwargs: lambda fn: fn
        domain_dict = self._make_domain_dict()
        result = get_optimized_domain_context.__wrapped__(
            domain_dict, {"bp": False, "aggs": False, "rms": False, "policies": False}
        )
        assert "big_picture:" not in result

    @patch("ui.components.chat.st")
    def test_includes_aggregates_when_enabled(self, mock_st):
        from ui.components.chat import get_optimized_domain_context

        mock_st.cache_data = lambda **kwargs: lambda fn: fn
        domain_dict = self._make_domain_dict()
        result = get_optimized_domain_context.__wrapped__(
            domain_dict, {"bp": False, "aggs": True, "rms": False, "policies": False}
        )
        assert "aggregates:" in result
        assert "OrderAggregate" in result

    @patch("ui.components.chat.st")
    def test_includes_read_models_when_enabled(self, mock_st):
        from ui.components.chat import get_optimized_domain_context

        mock_st.cache_data = lambda **kwargs: lambda fn: fn
        domain_dict = self._make_domain_dict()
        result = get_optimized_domain_context.__wrapped__(
            domain_dict, {"bp": False, "aggs": False, "rms": True, "policies": False}
        )
        assert "read_models:" in result
        assert "OrderDashboard" in result

    @patch("ui.components.chat.st")
    def test_includes_policies_when_enabled(self, mock_st):
        from ui.components.chat import get_optimized_domain_context

        mock_st.cache_data = lambda **kwargs: lambda fn: fn
        domain_dict = self._make_domain_dict()
        result = get_optimized_domain_context.__wrapped__(
            domain_dict, {"bp": False, "aggs": False, "rms": False, "policies": True}
        )
        assert "global_policies:" in result

    @patch("ui.components.chat.st")
    def test_includes_specs_when_provided(self, mock_st):
        from ui.components.chat import get_optimized_domain_context

        mock_st.cache_data = lambda **kwargs: lambda fn: fn
        domain_dict = self._make_domain_dict()
        specs = {"domain_models": "class Order { ... }"}
        opts = {"bp": False, "aggs": False, "rms": False, "policies": False, "domain_models": True}
        result = get_optimized_domain_context.__wrapped__(domain_dict, opts, specs)
        assert "Modelo de Dominio" in result
        assert "class Order" in result

    @patch("ui.components.chat.st")
    def test_filters_policy_nodes_when_disabled(self, mock_st):
        from ui.components.chat import get_optimized_domain_context

        mock_st.cache_data = lambda **kwargs: lambda fn: fn
        domain_dict = self._make_domain_dict()
        domain_dict["big_picture"]["nodos"].append(
            {
                "id": "pol-1",
                "tipo_elemento": "Política",
                "nombre": "RetryPolicy",
                "descripcion": "Retry on failure",
                "tags_tecnologia": [],
                "estado_comparativo": "",
            }
        )
        result = get_optimized_domain_context.__wrapped__(
            domain_dict,
            {"bp": True, "aggs": False, "rms": False, "policies": False},
        )
        assert "RetryPolicy" not in result


class TestRenderToolExecutions:
    @patch("ui.components.chat.st")
    def test_render_with_empty_list(self, mock_st):
        from ui.components.chat import _render_tool_executions

        _render_tool_executions([])  # Should not raise, no-op

    @patch("ui.components.chat.st")
    @patch("ui.components.chat.json")
    def test_render_with_write_tools(self, mock_json, mock_st):
        from domain.models.tool_schemas import ToolExecution
        from ui.components.chat import _render_tool_executions

        mock_st.expander.return_value.__enter__ = MagicMock()
        mock_st.expander.return_value.__exit__ = MagicMock()

        execs = [
            ToolExecution(
                tool_name="add_node",
                arguments={"name": "test"},
                result='{"success": true, "message": "Node added"}',
                success=True,
            )
        ]
        _render_tool_executions(execs)
        mock_st.expander.assert_called_once()

    @patch("ui.components.chat.st")
    def test_render_none_input(self, mock_st):
        from ui.components.chat import _render_tool_executions

        _render_tool_executions(None)  # Should not raise
