"""Functional tests for the gherkin_generation prompt — verifies BDD output format."""

from __future__ import annotations

import os

import pytest
from infra.adapters.gemini_inference import GeminiInferenceAdapter
from prompts.catalog import registry

pytestmark = [
    pytest.mark.ai,
    pytest.mark.skipif(
        not os.environ.get("GOOGLE_API_KEY"),
        reason="GOOGLE_API_KEY not set — skipping AI prompt tests",
    ),
]


def _invoke_gherkin_generation(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> str:
    template = registry.get("gherkin_generation")
    rendered = template.render(data_context=sample_domain_analysis_json)
    return llm_adapter.invoke_text(rendered.to_string(language="es"))


def test_contains_feature_keyword(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> None:
    output = _invoke_gherkin_generation(llm_adapter, sample_domain_analysis_json)
    assert "Feature:" in output, "Expected 'Feature:' keyword in Gherkin output"


def test_contains_scenario_keyword(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> None:
    output = _invoke_gherkin_generation(llm_adapter, sample_domain_analysis_json)
    assert "Scenario:" in output, "Expected 'Scenario:' keyword in Gherkin output"


def test_contains_given_when_then(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> None:
    output = _invoke_gherkin_generation(llm_adapter, sample_domain_analysis_json)
    assert "Given" in output, "Expected 'Given' step in Gherkin output"
    assert "When" in output, "Expected 'When' step in Gherkin output"
    assert "Then" in output, "Expected 'Then' step in Gherkin output"


def test_no_markdown_fences(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> None:
    output = _invoke_gherkin_generation(llm_adapter, sample_domain_analysis_json)
    assert "```" not in output, "Output must not contain markdown code fences"


def test_no_preamble(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> None:
    output = _invoke_gherkin_generation(llm_adapter, sample_domain_analysis_json)
    assert output.strip().startswith("Feature:"), (
        f"Expected output to start with 'Feature:', got: {output.strip()[:80]!r}"
    )
