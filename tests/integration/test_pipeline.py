"""End-to-end integration test using real GeminiInferenceAdapter.

Requires GOOGLE_API_KEY environment variable. Run with:
    pytest tests/integration/ -m integration
"""

import os

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not os.environ.get("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY not set — skipping integration tests",
)
class TestPipelineIntegration:
    """Integration test invoking the full pipeline with real Gemini adapter."""

    def test_text_pipeline_end_to_end(self):
        from application.pipeline import AnalysisRequest, AnalysisResult, run_analysis
        from infra.adapters.gemini_inference import GeminiInferenceAdapter

        adapter = GeminiInferenceAdapter()

        request = AnalysisRequest(
            transcript="Un cliente llama al call center para solicitar la cancelación de su póliza de seguro. "
            "El agente verifica la identidad, consulta el estado de la póliza y procesa la cancelación.",
            language="es",
        )

        result = run_analysis(request=request, inference=adapter)

        assert isinstance(result, AnalysisResult)
        assert result.analysis is not None
        assert result.transcript is not None
        assert len(result.transcript) > 0
