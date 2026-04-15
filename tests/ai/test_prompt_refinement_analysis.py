"""Functional tests for the refinement_analysis prompt — verifies single-ambiguity resolution."""

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

_PROGRESS = "1 de 3 ambigüedades resueltas"
_CURRENT_AMBIGUITY = "¿El proceso de reembolso debe ser parte del agregado Poliza o un agregado separado Reembolso?"
_USER_MESSAGE = "Prefiero que sea un agregado separado llamado Reembolso para mantener la cohesión."


def _invoke_refinement_analysis(llm_adapter: GeminiInferenceAdapter, sample_csv_context: str) -> str:
    template = registry.get("refinement_analysis")
    rendered = template.render(
        csv_context=sample_csv_context,
        progress=_PROGRESS,
        current_ambiguity=_CURRENT_AMBIGUITY,
    )
    combined_prompt = rendered.to_string(language="es") + f"\n\nUSER: {_USER_MESSAGE}"
    return llm_adapter.invoke_text(combined_prompt)


def test_output_is_non_empty(llm_adapter: GeminiInferenceAdapter, sample_csv_context: str) -> None:
    output = _invoke_refinement_analysis(llm_adapter, sample_csv_context)
    assert len(output.strip()) > 30, "Expected non-trivial refinement analysis response"


def test_responds_to_current_ambiguity(llm_adapter: GeminiInferenceAdapter, sample_csv_context: str) -> None:
    output = _invoke_refinement_analysis(llm_adapter, sample_csv_context)
    relevant_terms = ["Reembolso", "reembolso", "agregado", "separado"]
    found = any(term in output for term in relevant_terms)
    assert found, f"Expected at least one term from {relevant_terms} in response to current ambiguity"


def test_contains_confirmation(llm_adapter: GeminiInferenceAdapter, sample_csv_context: str) -> None:
    output = _invoke_refinement_analysis(llm_adapter, sample_csv_context)
    has_confirmation = (
        "✓" in output or "resuelto" in output.lower() or "aplicado" in output.lower() or "cambio" in output.lower()
    )
    assert has_confirmation, "Expected confirmation signal ('✓', 'resuelto', 'aplicado', or 'cambio') in output"


def test_does_not_address_other_ambiguities(llm_adapter: GeminiInferenceAdapter, sample_csv_context: str) -> None:
    output = _invoke_refinement_analysis(llm_adapter, sample_csv_context)
    assert len(output.strip()) < 2000, "Output should be focused on the single ambiguity, not a dump of everything"
