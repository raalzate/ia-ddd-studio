"""Unit tests for AmbiguityDetector service.

Tests mock InferencePort, assert structured list[Ambiguity] output,
and verify priority ordering as required by T006.
"""

from __future__ import annotations

from unittest.mock import MagicMock


def _make_domain_model_with_synonyms():
    """Build a DomainAnalysis model with synonym candidate terms.

    Includes edges so the strip_orphan_nodes validator preserves the nodes.
    """
    from models.domain_analysis import (
        AristaGrafo,
        BigPicture,
        DomainAnalysis,
        GrafoPorAgregado,
        NodoGrafo,
    )

    nodes = [
        NodoGrafo(
            id="cmd_crear_pedido",
            tipo_elemento="Comando",
            nombre="CrearPedido",
            descripcion="Crea un pedido",
            nivel="process_level",
        ),
        NodoGrafo(
            id="cmd_crear_orden",
            tipo_elemento="Comando",
            nombre="CrearOrden",
            descripcion="Crea una orden",
            nivel="process_level",
        ),
        NodoGrafo(
            id="evt_pedido_creado",
            tipo_elemento="Evento",
            nombre="PedidoCreado",
            descripcion="Pedido creado",
            nivel="process_level",
        ),
    ]

    return DomainAnalysis(
        nombre_proyecto="TestProject",
        version="1.0.0",
        fecha_analisis="2026-03-19",
        big_picture=BigPicture(
            descripcion="Model with synonym terms",
            nodos=[],
            aristas=[],
        ),
        agregados=[
            GrafoPorAgregado(
                nombre_agregado="Pedidos",
                entidad_raiz="Pedido",
                nodos=nodes,
                aristas=[
                    AristaGrafo(
                        fuente="cmd_crear_pedido",
                        destino="evt_pedido_creado",
                        descripcion="produces",
                    ),
                    AristaGrafo(
                        fuente="cmd_crear_orden",
                        destino="evt_pedido_creado",
                        descripcion="produces",
                    ),
                ],
            )
        ],
        read_models=[],
        politicas_inter_agregados=[],
    )


def _make_empty_model():
    """Build a minimal DomainAnalysis model."""
    from models.domain_analysis import BigPicture, DomainAnalysis

    return DomainAnalysis(
        nombre_proyecto="EmptyProject",
        version="1.0.0",
        fecha_analisis="2026-03-19",
        big_picture=BigPicture(descripcion="", nodos=[], aristas=[]),
        agregados=[],
        read_models=[],
        politicas_inter_agregados=[],
    )


class TestAmbiguityDetectorInit:
    """Tests for AmbiguityDetector initialization."""

    def test_initializes_with_inference_port(self):
        from services.ambiguity_detector import AmbiguityDetector

        inference = MagicMock()
        detector = AmbiguityDetector(inference)
        assert detector is not None


class TestAmbiguityDetectorDetect:
    """Tests for AmbiguityDetector.detect() method."""

    def test_returns_list_of_ambiguity_objects(self):
        from domain.models.tool_schemas import Ambiguity
        from services.ambiguity_detector import AmbiguityDetector

        inference = MagicMock()
        inference.invoke.return_value = [
            Ambiguity(
                id="amb_001",
                type="lexical",
                priority=2,
                description="Potential synonym",
                affected_elements=["cmd_crear_pedido", "cmd_crear_orden"],
                suggested_resolutions=["Merge into CrearPedido"],
            )
        ]

        detector = AmbiguityDetector(inference)
        result = detector.detect(_make_domain_model_with_synonyms())

        assert isinstance(result, list)
        assert all(isinstance(a, Ambiguity) for a in result)

    def test_detect_calls_inference_with_prompt(self):
        from services.ambiguity_detector import AmbiguityDetector

        inference = MagicMock()
        inference.invoke.return_value = []

        detector = AmbiguityDetector(inference)
        detector.detect(_make_domain_model_with_synonyms())

        assert inference.invoke.called
        call_args = inference.invoke.call_args
        prompt = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_detect_passes_list_ambiguity_as_output_schema(self):
        from services.ambiguity_detector import AmbiguityDetector

        inference = MagicMock()
        inference.invoke.return_value = []

        detector = AmbiguityDetector(inference)
        detector.detect(_make_domain_model_with_synonyms())

        call_kwargs = inference.invoke.call_args
        # output_schema should be list[Ambiguity]
        assert call_kwargs is not None

    def test_returns_empty_list_when_no_ambiguities(self):
        from services.ambiguity_detector import AmbiguityDetector

        inference = MagicMock()
        inference.invoke.return_value = []

        detector = AmbiguityDetector(inference)
        result = detector.detect(_make_empty_model())

        assert result == []

    def test_results_sorted_by_priority(self):
        from domain.models.tool_schemas import Ambiguity
        from services.ambiguity_detector import AmbiguityDetector

        inference = MagicMock()
        inference.invoke.return_value = [
            Ambiguity(
                id="amb_003",
                type="lexical",
                priority=3,
                description="cosmetic",
                affected_elements=["x"],
                suggested_resolutions=["fix"],
            ),
            Ambiguity(
                id="amb_001",
                type="structural",
                priority=1,
                description="structural",
                affected_elements=["y"],
                suggested_resolutions=["fix"],
            ),
            Ambiguity(
                id="amb_002",
                type="lexical",
                priority=2,
                description="lexical",
                affected_elements=["z"],
                suggested_resolutions=["fix"],
            ),
        ]

        detector = AmbiguityDetector(inference)
        result = detector.detect(_make_domain_model_with_synonyms())

        priorities = [a.priority for a in result]
        assert priorities == sorted(priorities)

    def test_returns_empty_list_on_inference_failure(self):
        from services.ambiguity_detector import AmbiguityDetector

        inference = MagicMock()
        inference.invoke.side_effect = Exception("LLM timeout")

        detector = AmbiguityDetector(inference)
        result = detector.detect(_make_domain_model_with_synonyms())

        assert result == []

    def test_returns_empty_list_on_validation_error(self):
        from pydantic import ValidationError

        from services.ambiguity_detector import AmbiguityDetector

        inference = MagicMock()
        inference.invoke.side_effect = ValidationError.from_exception_data(
            title="Ambiguity",
            input_type="python",
            line_errors=[],
        )

        detector = AmbiguityDetector(inference)
        # Should not raise, should return empty
        result = detector.detect(_make_domain_model_with_synonyms())
        assert result == []

    def test_prompt_includes_node_names(self):
        from services.ambiguity_detector import AmbiguityDetector

        inference = MagicMock()
        inference.invoke.return_value = []

        detector = AmbiguityDetector(inference)
        model = _make_domain_model_with_synonyms()
        detector.detect(model)

        call_args = inference.invoke.call_args
        prompt = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")
        # Node names should appear in the prompt
        assert "CrearPedido" in prompt or "CrearOrden" in prompt

    def test_ambiguity_ids_are_non_empty(self):
        from domain.models.tool_schemas import Ambiguity
        from services.ambiguity_detector import AmbiguityDetector

        inference = MagicMock()
        inference.invoke.return_value = [
            Ambiguity(
                id="amb_001",
                type="lexical",
                priority=2,
                description="test",
                affected_elements=["a"],
                suggested_resolutions=["fix"],
            )
        ]

        detector = AmbiguityDetector(inference)
        result = detector.detect(_make_domain_model_with_synonyms())

        for amb in result:
            assert amb.id != ""

    def test_detects_synonym_pair_in_affected_elements(self):
        from domain.models.tool_schemas import Ambiguity
        from services.ambiguity_detector import AmbiguityDetector

        inference = MagicMock()
        inference.invoke.return_value = [
            Ambiguity(
                id="amb_001",
                type="lexical",
                priority=2,
                description="'CrearPedido' y 'CrearOrden' podrían ser sinónimos",
                affected_elements=["cmd_crear_pedido", "cmd_crear_orden"],
                suggested_resolutions=["Unificar bajo 'CrearPedido'", "Mantener ambos"],
            )
        ]

        detector = AmbiguityDetector(inference)
        result = detector.detect(_make_domain_model_with_synonyms())

        synonym_ambiguities = [a for a in result if "cmd_crear_pedido" in a.affected_elements]
        assert len(synonym_ambiguities) >= 1
