"""Functional tests for the architectural_chat prompt — verifies DDD analysis output."""

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

_USER_MESSAGE = "Analiza el modelo de dominio e identifica riesgos o gaps desde la perspectiva DDD."


def _invoke_architectural_chat(llm_adapter: GeminiInferenceAdapter, sample_csv_context: str) -> str:
    template = registry.get("architectural_chat")
    rendered = template.render(csv_context=sample_csv_context)
    combined_prompt = rendered.to_string(language="es") + f"\n\nUSER: {_USER_MESSAGE}"
    return llm_adapter.invoke_text(combined_prompt)


def test_output_is_non_empty(llm_adapter: GeminiInferenceAdapter, sample_csv_context: str) -> None:
    output = _invoke_architectural_chat(llm_adapter, sample_csv_context)
    assert len(output.strip()) > 50, "Expected non-trivial architectural analysis output"


def test_output_contains_markdown_structure(llm_adapter: GeminiInferenceAdapter, sample_csv_context: str) -> None:
    output = _invoke_architectural_chat(llm_adapter, sample_csv_context)
    has_markdown = "#" in output or "**" in output or "- " in output
    assert has_markdown, "Expected Markdown structure (headings, bold text, or list items) in output"


def test_references_domain_elements(llm_adapter: GeminiInferenceAdapter, sample_csv_context: str) -> None:
    output = _invoke_architectural_chat(llm_adapter, sample_csv_context)
    domain_terms = ["Poliza", "Comando", "Evento", "poliza", "comando", "evento"]
    found = any(term in output for term in domain_terms)
    assert found, f"Expected at least one domain term {domain_terms} referenced in output"


def test_no_preamble_restating_system(llm_adapter: GeminiInferenceAdapter, sample_csv_context: str) -> None:
    output = _invoke_architectural_chat(llm_adapter, sample_csv_context)
    first_100_chars = output.upper()[:100]
    assert "YOU ARE" not in first_100_chars, "Output must not restate the system prompt in the first 100 characters"
