"""Unit tests for the Pipeline logic.

Validates the run_analysis flow, event collection, and graph selection.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from application.pipeline import AnalysisRequest, AnalysisResult, run_analysis
from domain.events import ProgressEvent
from models.domain_analysis import BigPicture, DomainAnalysis


def _make_mock_analysis() -> DomainAnalysis:
    return DomainAnalysis(
        nombre_proyecto="Test",
        fecha_analisis="2026-04-07",
        big_picture=BigPicture(descripcion="Test", nodos=[], aristas=[]),
        agregados=[],
    )


class TestAnalysisRequest:
    """Tests for the AnalysisRequest model validation."""

    def test_requires_input(self):
        with pytest.raises(ValidationError):
            AnalysisRequest(transcript=None, audio_bytes=None)

    def test_accepts_transcript(self):
        req = AnalysisRequest(transcript="test")
        assert req.transcript == "test"

    def test_accepts_audio(self):
        req = AnalysisRequest(audio_bytes=b"fake", audio_name="test.wav")
        assert req.audio_bytes == b"fake"


class TestPipelineFlow:
    """Tests for the run_analysis orchestration."""

    @pytest.fixture
    def mock_inference(self):
        mock = MagicMock()
        mock.invoke.return_value = _make_mock_analysis()
        mock.invoke_text.return_value = "Mocked Spec Content"
        return mock

    @pytest.fixture
    def mock_transcription(self):
        mock = MagicMock()
        mock.transcribe.return_value = "transcribed text"
        return mock

    @pytest.fixture
    def mock_cache(self):
        mock = MagicMock()
        mock.get.return_value = None
        return mock

    def test_text_pipeline_flow(self, mock_inference):
        """Verify that a text-based request follows the correct graph path."""
        req = AnalysisRequest(transcript="Process this text")

        result = run_analysis(request=req, inference=mock_inference)

        assert isinstance(result, AnalysisResult)
        assert result.transcript == "Process this text"
        assert isinstance(result.analysis, DomainAnalysis)
        assert result.analysis.nombre_proyecto == "Test"

    def test_event_collection(self, mock_inference):
        """Verify that progress events are collected during execution."""
        req = AnalysisRequest(transcript="test")
        result = run_analysis(request=req, inference=mock_inference)

        assert len(result.events) > 0
        assert any(isinstance(e, ProgressEvent) for e in result.events)

    def test_audio_pipeline_flow(self, mock_inference, mock_transcription, mock_cache, tmp_path):
        """Verify that an audio-based request uses the transcription port."""
        req = AnalysisRequest(audio_bytes=b"fake audio", audio_name="test.wav")

        result = run_analysis(
            request=req,
            inference=mock_inference,
            transcription=mock_transcription,
            cache=mock_cache,
        )

        assert isinstance(result.analysis, DomainAnalysis)
        assert result.transcript == "transcribed text"
        # Since it's audio, the transcript should come from the transcription port
        # Note: In our current build_audio_graph, the transcript is returned by the node.
        # This depends on mock_transcription being correctly called.
