"""Functional tests for the semantic_analysis prompt — verifies real LLM output structure."""

from __future__ import annotations

import json
import os

import pytest
from infra.adapters.gemini_inference import GeminiInferenceAdapter
from models.domain_analysis import DomainAnalysis
from prompts.catalog import registry

pytestmark = [
    pytest.mark.ai,
    pytest.mark.skipif(
        not os.environ.get("GOOGLE_API_KEY"),
        reason="GOOGLE_API_KEY not set — skipping AI prompt tests",
    ),
]


def _invoke_semantic_analysis(llm_adapter: GeminiInferenceAdapter, sample_transcript: str) -> str:
    template = registry.get("semantic_analysis")
    rendered = template.render(transcript=sample_transcript)
    return llm_adapter.invoke_text(rendered.to_string(language="es"))


def test_output_is_raw_json_without_fences(llm_adapter: GeminiInferenceAdapter, sample_transcript: str) -> None:
    output = _invoke_semantic_analysis(llm_adapter, sample_transcript)
    stripped = output.strip()
    assert stripped.startswith("{"), f"Expected output to start with '{{', got: {stripped[:50]!r}"
    assert not stripped.startswith("```"), "Output must not start with markdown fences"


def test_parses_as_valid_domain_analysis(llm_adapter: GeminiInferenceAdapter, sample_transcript: str) -> None:
    output = _invoke_semantic_analysis(llm_adapter, sample_transcript)
    parsed = json.loads(output.strip())
    model = DomainAnalysis.model_validate(parsed)
    assert model.nombre_proyecto, "nombre_proyecto must be non-empty"


def test_contains_at_least_one_aggregate(llm_adapter: GeminiInferenceAdapter, sample_transcript: str) -> None:
    output = _invoke_semantic_analysis(llm_adapter, sample_transcript)
    parsed = json.loads(output.strip())
    model = DomainAnalysis.model_validate(parsed)
    assert len(model.agregados) >= 1, "Expected at least one aggregate"


def test_contains_domain_events(llm_adapter: GeminiInferenceAdapter, sample_transcript: str) -> None:
    output = _invoke_semantic_analysis(llm_adapter, sample_transcript)
    parsed = json.loads(output.strip())
    model = DomainAnalysis.model_validate(parsed)

    all_nodes = list(model.big_picture.nodos)
    for agg in model.agregados:
        all_nodes.extend(agg.nodos)

    event_nodes = [n for n in all_nodes if n.tipo_elemento == "Evento"]
    assert len(event_nodes) >= 1, "Expected at least one node with tipo_elemento=='Evento'"


def test_edges_reference_valid_node_ids(llm_adapter: GeminiInferenceAdapter, sample_transcript: str) -> None:
    output = _invoke_semantic_analysis(llm_adapter, sample_transcript)
    parsed = json.loads(output.strip())
    model = DomainAnalysis.model_validate(parsed)

    node_ids = {n.id for n in model.big_picture.nodos}
    for edge in model.big_picture.aristas:
        assert edge.fuente in node_ids, f"Edge source '{edge.fuente}' not found in big_picture node IDs: {node_ids}"
        assert edge.destino in node_ids, (
            f"Edge destination '{edge.destino}' not found in big_picture node IDs: {node_ids}"
        )
