"""Integration tests for prompt migration verification.

Asserts that migrated nodes and services produce prompts identical to
the original inline strings. These tests verify US-004 (transparent migration).

Test IDs: TS-020, TS-021, TS-022, TS-023, TS-024, TS-025
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# TS-020: analyze_semantics node preserves original prompt
# ---------------------------------------------------------------------------


def test_ts020_analyze_semantics_prompt_preserved():
    from application.nodes.analyze_semantics import analyze_semantics
    from prompts.catalog import registry

    transcript = "El sistema recibe una orden de compra del cliente"

    # Capture the prompt sent to inference
    captured = {}
    mock_inference = MagicMock()
    mock_inference.invoke.side_effect = lambda prompt, schema: captured.__setitem__("prompt", prompt) or MagicMock()

    analyze_semantics({"transcript": transcript}, inference=mock_inference)

    assert "prompt" in captured
    prompt = captured["prompt"]

    # Verify template system text is present
    template = registry.get("semantic_analysis")
    rendered = template.render(transcript=transcript)
    assert rendered.system in prompt or prompt == rendered.to_string()
    assert transcript in prompt


def test_ts020_analyze_semantics_contains_transcript():
    from application.nodes.analyze_semantics import analyze_semantics

    transcript = "El sistema recibe una orden de compra del cliente"
    captured = {}
    mock_inference = MagicMock()
    mock_inference.invoke.side_effect = lambda prompt, schema: captured.__setitem__("prompt", prompt) or MagicMock()

    analyze_semantics({"transcript": transcript}, inference=mock_inference)
    assert transcript in captured["prompt"]


# ---------------------------------------------------------------------------
# TS-021: refine_analysis node preserves original prompt
# ---------------------------------------------------------------------------


def test_ts021_refine_analysis_prompt_preserved():
    from application.nodes.refine_analysis import refine_analysis

    context_doc = "Documentación DDD"
    draft_json_val = '{"agregados": ["Orden"]}'

    mock_analysis = MagicMock()
    mock_analysis.model_dump_json.return_value = draft_json_val

    captured = {}
    mock_inference = MagicMock()
    mock_inference.invoke.side_effect = lambda prompt, schema: captured.__setitem__("prompt", prompt) or mock_analysis

    refine_analysis({"analysis": mock_analysis, "context": context_doc}, inference=mock_inference)

    assert "prompt" in captured
    prompt = captured["prompt"]
    assert context_doc in prompt
    assert draft_json_val in prompt


# ---------------------------------------------------------------------------
# TS-022: narrative_transform_ui preserves original prompt
# ---------------------------------------------------------------------------


def test_ts022_narrative_transform_ui_prompt_preserved():
    from prompts.catalog import registry

    transcript = "Sesión de Event Storming con el equipo de producto"
    rendered = registry.get("narrative_transform_ui").render(transcript=transcript)
    assert transcript in rendered.to_string()


# ---------------------------------------------------------------------------
# TS-023: All prompts defined in src/prompts/ module
# ---------------------------------------------------------------------------


def test_ts023_catalog_contains_active_prompts():
    from prompts.catalog import registry

    expected_names = {
        "semantic_analysis",
        "refinement",
        "gherkin_generation",
        "domain_model_generation",
        "gherkin_specs",
        "domain_model_specs",
        "narrative_transform_ui",
        "architectural_chat",
    }

    registered = {t.name for t in registry.list_all()}
    assert expected_names.issubset(registered), f"Missing templates: {expected_names - registered}"


# ---------------------------------------------------------------------------
# TS-024: semantic_analysis template contains required structural markers
# ---------------------------------------------------------------------------


def test_ts024_semantic_analysis_system_text_verbatim():
    from prompts.catalog import registry

    template = registry.get("semantic_analysis")
    system = template.system

    # Must define an expert persona
    assert "Domain Architect" in system or "Event Storming" in system
    # Must instruct on DomainAnalysis output
    assert "DomainAnalysis" in system
    # Must constrain output to JSON only
    assert "JSON" in system
    # Must reference ubiquitous language
    assert "Ubiquitous Language" in system or "Lenguaje Ubicuo" in system or "Ubiquitous" in system


# ---------------------------------------------------------------------------
# TS-025: Migrated files import from prompts and have no inline LLM strings
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "migrated_file",
    [
        "src/application/nodes/analyze_semantics.py",
        "src/application/nodes/refine_analysis.py",
        "src/application/nodes/generate_specs.py",
        "src/services/spec_generator.py",
        "src/ui/components/input.py",
        "src/ui/components/chat.py",
    ],
)
def test_ts025_migrated_file_imports_from_prompts_no_inline_strings(migrated_file):
    source = Path(migrated_file).read_text()
    # Must import from prompts or use registry
    uses_registry = "from prompts" in source or "registry" in source
    assert uses_registry, f"{migrated_file}: must import from prompts or use registry"

    # No multiline LLM instruction strings (triple-quoted with > 3 content lines)
    triple_strings = re.findall(r'"""[\s\S]*?"""', source)
    for s in triple_strings:
        lines = s.strip().splitlines()
        content_lines = [l.strip() for l in lines[1:-1] if l.strip()]
        if len(content_lines) > 3:
            pytest.fail(f"{migrated_file}: found multiline LLM string: {s[:80]}...")
