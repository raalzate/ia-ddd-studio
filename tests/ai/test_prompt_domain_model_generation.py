"""Functional tests for the domain_model_generation prompt — verifies UML-style text output."""

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


def _invoke_domain_model_generation(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> str:
    template = registry.get("domain_model_generation")
    rendered = template.render(data_context=sample_domain_analysis_json)
    return llm_adapter.invoke_text(rendered.to_string(language="es"))


def test_contains_aggregate_root_marker(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> None:
    output = _invoke_domain_model_generation(llm_adapter, sample_domain_analysis_json)
    assert "[Aggregate Root]" in output, "Expected '[Aggregate Root]' marker in UML output"


def test_no_markdown_fences(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> None:
    output = _invoke_domain_model_generation(llm_adapter, sample_domain_analysis_json)
    assert "```" not in output, "Output must not contain markdown code fences"


def test_no_code_syntax(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> None:
    output = _invoke_domain_model_generation(llm_adapter, sample_domain_analysis_json)
    assert "class " not in output, "Output must not contain 'class ' code syntax"
    assert "def " not in output, "Output must not contain 'def ' code syntax"


def test_output_is_non_empty(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> None:
    output = _invoke_domain_model_generation(llm_adapter, sample_domain_analysis_json)
    assert len(output.strip()) > 50, "Expected non-trivial output (more than 50 characters)"
