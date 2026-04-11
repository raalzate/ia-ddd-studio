"""Functional tests for the gherkin_specs prompt — verifies production-ready Gherkin output."""

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


def _invoke_gherkin_specs(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> str:
    template = registry.get("gherkin_specs")
    rendered = template.render(data_context=sample_domain_analysis_json)
    return llm_adapter.invoke_text(rendered.to_string(language="es"))


def test_contains_feature_with_business_goal(
    llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str
) -> None:
    output = _invoke_gherkin_specs(llm_adapter, sample_domain_analysis_json)
    assert "Feature:" in output, "Expected 'Feature:' keyword in Gherkin output"
    has_business_goal = "In order to" in output or "Para" in output or "Como" in output
    assert has_business_goal, "Expected a business goal keyword ('In order to', 'Para', or 'Como') in Feature block"


def test_contains_scenario(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> None:
    output = _invoke_gherkin_specs(llm_adapter, sample_domain_analysis_json)
    assert "Scenario:" in output, "Expected 'Scenario:' keyword in Gherkin output"


def test_given_when_then_present(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> None:
    output = _invoke_gherkin_specs(llm_adapter, sample_domain_analysis_json)
    assert "Given" in output, "Expected 'Given' step in Gherkin output"
    assert "When" in output, "Expected 'When' step in Gherkin output"
    assert "Then" in output, "Expected 'Then' step in Gherkin output"


def test_no_markdown_fences(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> None:
    output = _invoke_gherkin_specs(llm_adapter, sample_domain_analysis_json)
    assert "```" not in output, "Output must not contain markdown code fences"


def test_no_implementation_details(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> None:
    output = _invoke_gherkin_specs(llm_adapter, sample_domain_analysis_json)
    assert "HTTP" not in output, "Output must not contain implementation details like 'HTTP'"
    assert "database" not in output.lower(), "Output must not contain implementation details like 'database'"
    assert "class " not in output, "Output must not contain 'class ' code syntax"
