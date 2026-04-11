"""Unit tests for PromptTemplate and RenderedPrompt.

TDD: These tests are written FIRST and must FAIL before production code exists.
Test IDs: TS-003, TS-004, TS-005, TS-006, TS-007, TS-008, TS-009, TS-010, TS-011, TS-012, TS-013
"""

from __future__ import annotations

import pytest

from prompts.errors import MissingVariableError
from prompts.template import PromptTemplate, RenderedPrompt

# ---------------------------------------------------------------------------
# TS-003: Template renderizado con parámetros produce cadena final correcta
# ---------------------------------------------------------------------------


def test_ts003_render_substitutes_variable():
    tmpl = PromptTemplate(
        name="semantic_analysis",
        description="Semantic analysis prompt",
        system="Analyze: $transcript",
    )
    rendered = tmpl.render(transcript="El usuario crea una orden de compra")
    assert "El usuario crea una orden de compra" in rendered.system
    assert "$transcript" not in rendered.system


# ---------------------------------------------------------------------------
# TS-004: Template con múltiples variables renderiza correctamente
# ---------------------------------------------------------------------------


def test_ts004_render_multiple_variables():
    tmpl = PromptTemplate(
        name="refinement",
        description="Refinement prompt",
        system="Contexto: $context",
        user="Borrador: $draft_json",
    )
    rendered = tmpl.render(context="documentación de dominio", draft_json='{"agregados": []}')
    assert "documentación de dominio" in rendered.system
    assert '{"agregados": []}' in rendered.user
    assert "$context" not in rendered.system
    assert "$draft_json" not in rendered.user


# ---------------------------------------------------------------------------
# TS-005: Renderizado sin variable requerida señala la variable faltante
# ---------------------------------------------------------------------------


def test_ts005_render_missing_variable_raises():
    tmpl = PromptTemplate(
        name="semantic_analysis",
        description="Semantic analysis prompt",
        system="Analyze: $transcript",
    )
    with pytest.raises(MissingVariableError) as exc_info:
        tmpl.render()
    assert "transcript" in str(exc_info.value)


# ---------------------------------------------------------------------------
# TS-006: Consultar metadata devuelve nombre, propósito y variables
# ---------------------------------------------------------------------------


def test_ts006_metadata_name_description_variables():
    tmpl = PromptTemplate(
        name="semantic_analysis",
        description="Semantic analysis prompt",
        system="Analyze: $transcript",
    )
    assert tmpl.name == "semantic_analysis"
    assert tmpl.description != ""
    assert "transcript" in tmpl.variables


# ---------------------------------------------------------------------------
# TS-007: render() devuelve un RenderedPrompt con campos system y user
# ---------------------------------------------------------------------------


def test_ts007_render_returns_rendered_prompt():
    tmpl = PromptTemplate(
        name="test_tmpl",
        description="Test template",
        system="Eres un experto en $domain",
        user="Analiza: $input",
    )
    rendered = tmpl.render(domain="DDD", input="transcripción de evento")
    assert isinstance(rendered, RenderedPrompt)
    assert "DDD" in rendered.system
    assert "transcripción de evento" in rendered.user


# ---------------------------------------------------------------------------
# TS-008: RenderedPrompt.to_string() combina system y user con doble salto de línea
# ---------------------------------------------------------------------------


def test_ts008_to_string_combines_system_and_user():
    rendered = RenderedPrompt(system="Sistema", user="Usuario")
    result = rendered.to_string()
    assert "Sistema" in result
    assert "Usuario" in result
    assert "LANGUAGE CONSTRAINT" in result
    assert result.index("Sistema") < result.index("Usuario")


# ---------------------------------------------------------------------------
# TS-009: Template sin parte user renderiza correctamente devolviendo solo system
# ---------------------------------------------------------------------------


def test_ts009_template_without_user_renders_system_only():
    tmpl = PromptTemplate(
        name="narrative_simulation",
        description="Narrative simulation prompt",
        system="Eres un facilitador experto.",
    )
    rendered = tmpl.render()
    assert rendered.user is None
    result = rendered.to_string()
    assert rendered.system in result
    assert "LANGUAGE CONSTRAINT" in result


# ---------------------------------------------------------------------------
# TS-010: Llaves JSON literales no son interpretadas como variables
# ---------------------------------------------------------------------------


def test_ts010_json_braces_not_interpreted_as_variables():
    tmpl = PromptTemplate(
        name="json_test",
        description="Template with JSON braces",
        system='Responde en JSON: {"events": [{"name": "string"}]}',
    )
    rendered = tmpl.render()
    assert '{"events": [{"name": "string"}]}' in rendered.system


# ---------------------------------------------------------------------------
# TS-011: Nombre de template con caracteres inválidos es rechazado
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "invalid_name",
    [
        "",
        "Semantic Analysis",
        "semantic-analysis",
        "1_invalid",
    ],
)
def test_ts011_invalid_name_raises_value_error(invalid_name):
    with pytest.raises(ValueError):
        PromptTemplate(
            name=invalid_name,
            description="Test",
            system="System prompt",
        )


# ---------------------------------------------------------------------------
# TS-012: Sistema vacío es rechazado en la creación del template
# ---------------------------------------------------------------------------


def test_ts012_empty_system_raises_value_error():
    with pytest.raises(ValueError):
        PromptTemplate(
            name="test_tmpl",
            description="Test",
            system="",
        )


# ---------------------------------------------------------------------------
# TS-013: Variables se extraen automáticamente de los campos system y user
# ---------------------------------------------------------------------------


def test_ts013_variables_extracted_from_system_and_user():
    tmpl = PromptTemplate(
        name="multi_var",
        description="Multi variable template",
        system="Eres experto en $domain",
        user="Transcripción: $transcript",
    )
    assert "domain" in tmpl.variables
    assert "transcript" in tmpl.variables
    assert len(tmpl.variables) == 2
