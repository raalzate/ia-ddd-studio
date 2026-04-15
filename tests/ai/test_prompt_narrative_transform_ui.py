"""Functional tests for the narrative_transform_ui prompt — verifies workshop dialogue output."""

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


def _invoke_narrative_transform_ui(llm_adapter: GeminiInferenceAdapter, sample_transcript: str) -> str:
    template = registry.get("narrative_transform_ui")
    rendered = template.render(transcript=sample_transcript)
    return llm_adapter.invoke_text(rendered.to_string(language="es"))


def test_output_is_non_empty(llm_adapter: GeminiInferenceAdapter, sample_transcript: str) -> None:
    output = _invoke_narrative_transform_ui(llm_adapter, sample_transcript)
    assert len(output.strip()) > 100, "Expected substantial narrative output (more than 100 characters)"


def test_no_json_structure(llm_adapter: GeminiInferenceAdapter, sample_transcript: str) -> None:
    output = _invoke_narrative_transform_ui(llm_adapter, sample_transcript)
    assert not output.strip().startswith("{"), "Narrative output must not be a JSON object"


def test_preserves_domain_concepts(llm_adapter: GeminiInferenceAdapter, sample_transcript: str) -> None:
    output = _invoke_narrative_transform_ui(llm_adapter, sample_transcript)
    domain_terms = ["Poliza", "Cancelacion", "Cliente", "poliza", "cancelacion", "cliente"]
    found = any(term in output for term in domain_terms)
    assert found, f"Expected at least one domain term {domain_terms} in narrative output"


def test_no_meta_commentary(llm_adapter: GeminiInferenceAdapter, sample_transcript: str) -> None:
    output = _invoke_narrative_transform_ui(llm_adapter, sample_transcript)
    assert "Here is" not in output, "Output must not contain meta-commentary 'Here is'"
    assert "This is" not in output, "Output must not contain meta-commentary 'This is'"
    assert "I have" not in output, "Output must not contain meta-commentary 'I have'"
