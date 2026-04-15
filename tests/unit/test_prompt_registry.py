"""Unit tests for PromptRegistry.

TDD: These tests are written FIRST and must FAIL before production code exists.
Test IDs: TS-014, TS-015, TS-016, TS-017
"""

from __future__ import annotations

import pytest
from prompts.errors import DuplicateTemplateError, TemplateNotFoundError
from prompts.registry import PromptRegistry
from prompts.template import PromptTemplate


def _make_template(name: str, description: str = "A test template") -> PromptTemplate:
    return PromptTemplate(name=name, description=description, system=f"System for {name}")


# ---------------------------------------------------------------------------
# TS-014: Listar todos los templates devuelve nombre y descripción de cada uno
# ---------------------------------------------------------------------------


def test_ts014_list_all_returns_sorted_templates_with_metadata():
    registry = PromptRegistry()
    registry.register(_make_template("semantic_analysis", "Semantic analysis"))
    registry.register(_make_template("refinement", "Refinement prompt"))
    registry.register(_make_template("gherkin_generation", "Gherkin generation"))

    templates = registry.list_all()

    assert len(templates) == 3
    for tmpl in templates:
        assert tmpl.name != ""
        assert tmpl.description != ""
    # Sorted alphabetically
    names = [t.name for t in templates]
    assert names == sorted(names)


# ---------------------------------------------------------------------------
# TS-015: Obtener template por nombre devuelve la plantilla correspondiente
# ---------------------------------------------------------------------------


def test_ts015_get_returns_matching_template():
    registry = PromptRegistry()
    registry.register(_make_template("semantic_analysis"))

    result = registry.get("semantic_analysis")

    assert result.name == "semantic_analysis"


# ---------------------------------------------------------------------------
# TS-016: Solicitar template con nombre inexistente lanza error claro
# ---------------------------------------------------------------------------


def test_ts016_get_nonexistent_raises_template_not_found():
    registry = PromptRegistry()

    with pytest.raises(TemplateNotFoundError) as exc_info:
        registry.get("nonexistent_template")

    assert "nonexistent_template" in str(exc_info.value)


# ---------------------------------------------------------------------------
# TS-017: Registrar dos templates con el mismo nombre lanza error de duplicado
# ---------------------------------------------------------------------------


def test_ts017_register_duplicate_raises_duplicate_template_error():
    registry = PromptRegistry()
    registry.register(_make_template("semantic_analysis"))

    with pytest.raises(DuplicateTemplateError) as exc_info:
        registry.register(_make_template("semantic_analysis"))

    assert "semantic_analysis" in str(exc_info.value)
