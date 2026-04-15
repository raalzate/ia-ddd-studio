"""Functional tests for the domain_model_specs prompt — verifies PlantUML output format."""

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


def _invoke_domain_model_specs(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> str:
    template = registry.get("domain_model_specs")
    rendered = template.render(data_context=sample_domain_analysis_json)
    return llm_adapter.invoke_text(rendered.to_string(language="es"))


def test_starts_with_startuml(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> None:
    output = _invoke_domain_model_specs(llm_adapter, sample_domain_analysis_json)
    assert output.strip().startswith("@startuml"), (
        f"Expected output to start with '@startuml', got: {output.strip()[:80]!r}"
    )


def test_ends_with_enduml(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> None:
    output = _invoke_domain_model_specs(llm_adapter, sample_domain_analysis_json)
    assert output.strip().endswith("@enduml"), (
        f"Expected output to end with '@enduml', got: ...{output.strip()[-80:]!r}"
    )


def test_contains_package_blocks(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> None:
    output = _invoke_domain_model_specs(llm_adapter, sample_domain_analysis_json)
    assert "package " in output, "Expected 'package ' blocks in PlantUML output"


def test_no_markdown_fences(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> None:
    output = _invoke_domain_model_specs(llm_adapter, sample_domain_analysis_json)
    assert "```" not in output, "Output must not contain markdown code fences"


def test_contains_component_or_arrow(llm_adapter: GeminiInferenceAdapter, sample_domain_analysis_json: str) -> None:
    output = _invoke_domain_model_specs(llm_adapter, sample_domain_analysis_json)
    has_arrow = "-->" in output or "..>" in output
    assert has_arrow, "Expected at least one arrow ('-->' or '..>') in PlantUML output"
