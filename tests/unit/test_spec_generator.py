"""Unit tests for SpecGenerator service."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from models.domain_analysis import BigPicture, DomainAnalysis
from services.spec_generator import SpecGenerator


@pytest.fixture
def mock_analysis():
    """Create a minimal valid DomainAnalysis for testing."""
    return DomainAnalysis(
        nombre_proyecto="TestProject",
        version="1.0.0",
        fecha_analisis="2026-03-24",
        big_picture=BigPicture(descripcion="Test", nodos=[], aristas=[]),
        agregados=[],
        read_models=[],
        politicas_inter_agregados=[],
    )


@pytest.fixture
def mock_inference():
    """Create a mock InferencePort."""
    return MagicMock()


def test_spec_generator_initialization(mock_analysis, mock_inference):
    """Verify SpecGenerator initializes with the correct dependencies."""
    generator = SpecGenerator(mock_analysis, mock_inference)
    assert generator is not None
    assert generator.inference == mock_inference


def test_generate_context_map(mock_analysis, mock_inference):
    """Verify context map generation calls inference with correct prompts."""
    mock_inference.invoke_text.return_value = "@startuml\n[Test]\n@enduml"
    generator = SpecGenerator(mock_analysis, mock_inference)

    result = generator.generate_context_map()

    assert "@startuml" in result
    assert mock_inference.invoke_text.called
    # Check that it combined prompts and data
    call_args = mock_inference.invoke_text.call_args[0][0]
    assert "Strategic Domain-Driven Design" in call_args
    assert "TestProject" in call_args


def test_generate_domain_models(mock_analysis, mock_inference):
    """Verify domain model generation calls inference with correct prompts."""
    mock_inference.invoke_text.return_value = "@startuml\nclass Test\n@enduml"
    generator = SpecGenerator(mock_analysis, mock_inference)

    result = generator.generate_domain_models()

    assert "class Test" in result
    assert mock_inference.invoke_text.called
    call_args = mock_inference.invoke_text.call_args[0][0]
    assert "Tactical Domain-Driven Design" in call_args


def test_generate_specs_all(mock_analysis, mock_inference):
    """Verify generate_specs_all returns both artifacts."""
    mock_inference.invoke_text.return_value = "mocked content"
    generator = SpecGenerator(mock_analysis, mock_inference)

    results = generator.generate_specs_all()

    assert "context_map" in results
    assert "domain_models" in results
    assert results["context_map"] == "mocked content"
    assert results["domain_models"] == "mocked content"
    assert mock_inference.invoke_text.call_count == 2
