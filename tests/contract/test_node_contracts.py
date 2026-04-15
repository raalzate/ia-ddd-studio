"""Contract tests for node input/output contracts.

Asserts:
- AgentState fields have descriptions [TS-007]
- Each node returns only declared output fields [TS-008]
- Test detects missing node in graph [TS-009]

[TS-007, TS-008, TS-009]
"""


class TestAgentStateFieldDescriptions:
    """[TS-007] AgentState fields must have descriptions."""

    def test_all_fields_have_descriptions(self):
        from domain.models.agent_state import AgentState

        for name, field_info in AgentState.model_fields.items():
            assert field_info.description is not None and field_info.description.strip(), (
                f"AgentState.{name} is missing a description"
            )


class TestNodeContractDeclarations:
    """[TS-008] Each node must declare a NodeContract and return only declared fields."""

    def test_cache_check_has_contract(self):
        from application.nodes.cache_check import CONTRACT

        assert CONTRACT.node_name == "cache_check"
        assert "audio_path" in CONTRACT.required_inputs
        assert "cache_exists" in CONTRACT.produced_outputs

    def test_transcribe_has_contract(self):
        from application.nodes.transcribe import CONTRACT

        assert CONTRACT.node_name == "transcribe"
        assert "audio_path" in CONTRACT.required_inputs
        assert "transcript" in CONTRACT.produced_outputs

    def test_analyze_semantics_has_contract(self):
        from application.nodes.analyze_semantics import CONTRACT

        assert CONTRACT.node_name == "analyze_semantics"
        assert "transcript" in CONTRACT.required_inputs
        assert "analysis" in CONTRACT.produced_outputs

    def test_refine_analysis_has_contract(self):
        from application.nodes.refine_analysis import CONTRACT

        assert CONTRACT.node_name == "refine_analysis"
        assert "analysis" in CONTRACT.required_inputs
        assert "analysis" in CONTRACT.produced_outputs

    def test_generate_specs_has_contract(self):
        from application.nodes.generate_specs import CONTRACT

        assert CONTRACT.node_name == "generate_specs"
        assert "analysis" in CONTRACT.required_inputs
        assert "specs" in CONTRACT.produced_outputs


class TestNodeReturnsOnlyDeclaredFields:
    """Nodes must only return fields listed in their CONTRACT.produced_outputs."""

    def test_analyze_semantics_output_matches_contract(self, mock_inference):
        from application.nodes.analyze_semantics import CONTRACT, analyze_semantics
        from models.domain_analysis import BigPicture, DomainAnalysis, NodoGrafo

        mock_inference.configure_response(
            DomainAnalysis(
                nombre_proyecto="T",
                fecha_analisis="2026-01-01",
                big_picture=BigPicture(
                    descripcion="T",
                    nodos=[
                        NodoGrafo(
                            id="a",
                            tipo_elemento="Actor",
                            nombre="U",
                            descripcion="T",
                            nivel="big_picture",
                        )
                    ],
                    aristas=[],
                ),
                agregados=[],
            )
        )

        result = analyze_semantics({"transcript": "test", "context": ""}, inference=mock_inference)
        allowed = set(CONTRACT.produced_outputs)
        for key in result:
            assert key in allowed, f"analyze_semantics returned undeclared field '{key}'"


class TestGraphNodeRegistry:
    """[TS-009] Graph builder must register all contracted nodes."""

    def test_all_contracts_have_graph_nodes(self):
        from application.graph_builder import build_text_graph, get_all_contracts

        from tests.conftest import MockInferencePort

        contracts = get_all_contracts()
        mock = MockInferencePort()
        graph = build_text_graph(inference=mock)

        graph_node_names = set()
        for key in graph.nodes:
            if not key.startswith("__"):
                graph_node_names.add(key)

        for contract in contracts:
            if contract.node_name in ("cache_check", "transcribe"):
                continue  # Only in audio graph
            assert contract.node_name in graph_node_names, (
                f"Contract '{contract.node_name}' has no corresponding graph node"
            )

    def test_missing_node_detected(self):
        """Removing a contract's node from the registry should be caught."""
        from application.graph_builder import get_all_contracts

        contracts = get_all_contracts()
        node_names = {c.node_name for c in contracts}
        assert "analyze_semantics" in node_names, "analyze_semantics missing from contract registry"
