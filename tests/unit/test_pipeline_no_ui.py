"""Acceptance test: pipeline runs without Streamlit active.

Verifies the agent pipeline can be invoked programmatically
without any UI framework being imported or active.

[TS-001]
"""

import sys

import pytest

pytestmark = pytest.mark.offline

import pytest


class TestPipelineWithoutUI:
    """Agent pipeline must run without any UI framework active."""

    def test_pipeline_import_does_not_require_streamlit(self):
        """Importing pipeline module must not transitively import streamlit."""
        # Ensure streamlit is not in sys.modules before import
        streamlit_before = "streamlit" in sys.modules

        from application.pipeline import run_analysis  # noqa: F401

        # If streamlit was not loaded before, it should not be loaded now
        if not streamlit_before:
            assert "streamlit" not in sys.modules, "Importing pipeline loaded streamlit as a side effect"

    def test_run_analysis_with_mock_adapters(self, mock_inference, mock_transcription, mock_cache):
        """Pipeline invocation must work with injected mock adapters."""
        from application.pipeline import AnalysisRequest, run_analysis

        # Configure mock inference to return a minimal DomainAnalysis
        from models.domain_analysis import (
            BigPicture,
            DomainAnalysis,
            NodoGrafo,
        )

        mock_analysis = DomainAnalysis(
            nombre_proyecto="Test",
            fecha_analisis="2026-03-18",
            big_picture=BigPicture(
                descripcion="Test domain",
                nodos=[
                    NodoGrafo(
                        id="a1",
                        tipo_elemento="Actor",
                        nombre="User",
                        descripcion="Test",
                        nivel="big_picture",
                    )
                ],
                aristas=[],
            ),
            agregados=[],
        )
        mock_inference.configure_response(mock_analysis)

        request = AnalysisRequest(transcript="A customer places an order")
        result = run_analysis(
            request=request,
            inference=mock_inference,
            cache=mock_cache,
        )

        assert result.analysis is not None
        assert result.transcript == "A customer places an order"
