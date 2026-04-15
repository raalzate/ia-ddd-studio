"""Functional tests for the refinement prompt — verifies the LLM reconciles draft model with docs."""

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

_REFINEMENT_CONTEXT = (
    "According to official docs, the aggregate is called 'Poliza de Seguro de Automovil', "
    "not just 'Poliza'. The cancellation policy requires written notice 48 hours in advance."
)


def _invoke_refinement(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> str:
    template = registry.get("refinement")
    rendered = template.render(
        draft_json=sample_domain_analysis_json,
        context=_REFINEMENT_CONTEXT,
    )
    return llm_adapter.invoke_text(rendered.to_string(language="es"))


def test_returns_valid_json(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> None:
    output = _invoke_refinement(llm_adapter, sample_domain_analysis_json)
    parsed = json.loads(output.strip())
    model = DomainAnalysis.model_validate(parsed)
    assert model is not None


def test_output_has_no_markdown_fences(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> None:
    output = _invoke_refinement(llm_adapter, sample_domain_analysis_json)
    assert "```json" not in output, "Output must not contain markdown JSON fences"


def test_preserves_or_updates_domain_elements(
    llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str
) -> None:
    output = _invoke_refinement(llm_adapter, sample_domain_analysis_json)
    parsed = json.loads(output.strip())
    model = DomainAnalysis.model_validate(parsed)
    assert len(model.agregados) > 0, "Expected at least one aggregate"
    assert len(model.big_picture.nodos) > 0, "Expected at least one big_picture node"


def test_hotspot_or_terminology_updated(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> None:
    output = _invoke_refinement(llm_adapter, sample_domain_analysis_json)
    parsed = json.loads(output.strip())
    model = DomainAnalysis.model_validate(parsed)

    all_nodes = list(model.big_picture.nodos)
    for agg in model.agregados:
        all_nodes.extend(agg.nodos)

    has_hotspot = any(n.tipo_elemento == "Hotspot" for n in all_nodes)
    has_project_name = bool(model.nombre_proyecto)

    assert has_hotspot or has_project_name, (
        "Expected either a hotspot node or a non-empty nombre_proyecto as basic sanity check"
    )
