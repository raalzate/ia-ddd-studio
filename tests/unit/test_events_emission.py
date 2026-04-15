"""Unit tests for ProgressEvent and ErrorEvent emission at checkpoints.

[TS-010, TS-011, TS-012, TS-017, TS-018]
"""

import pytest

pytestmark = pytest.mark.offline

from domain.events import ErrorEvent, ProgressEvent
from models.domain_analysis import BigPicture, DomainAnalysis, NodoGrafo


def _make_mock_analysis() -> DomainAnalysis:
    return DomainAnalysis(
        nombre_proyecto="Test",
        fecha_analisis="2026-03-18",
        big_picture=BigPicture(
            descripcion="T",
            nodos=[NodoGrafo(id="a", tipo_elemento="Actor", nombre="U", descripcion="T", nivel="big_picture")],
            aristas=[],
        ),
        agregados=[],
    )


class TestProgressEventEmission:
    """[TS-010, TS-012] ProgressEvent emitted at defined checkpoints."""

    def test_analyze_semantics_emits_events(self, mock_inference, mock_emitter):
        from application.nodes.analyze_semantics import analyze_semantics

        mock_inference.configure_step_extraction_responses()
        state = {"transcript": "test", "context": ""}
        analyze_semantics(state, inference=mock_inference, emitter=mock_emitter)

        checkpoints = [e.checkpoint for e in mock_emitter.events if isinstance(e, ProgressEvent)]
        assert "analysis_start" in checkpoints
        assert "analysis_complete" in checkpoints

    def test_generate_specs_emits_events(self, mock_inference, mock_emitter):
        from application.nodes.generate_specs import generate_specs

        mock_inference.configure_text_response("specs output")
        state = {"analysis": _make_mock_analysis()}
        generate_specs(state, inference=mock_inference, emitter=mock_emitter)

        checkpoints = [e.checkpoint for e in mock_emitter.events if isinstance(e, ProgressEvent)]
        assert "spec_generation_start" in checkpoints
        assert "spec_generation_complete" in checkpoints

    def test_pipeline_produces_event_trace(self, mock_inference, mock_cache, mock_emitter):
        """[TS-012] Complete run produces auditable event trace."""
        from application.pipeline import AnalysisRequest, run_analysis

        mock_inference.configure_step_extraction_responses()
        mock_inference.configure_text_response("specs")

        request = AnalysisRequest(transcript="test")
        result = run_analysis(
            request=request,
            inference=mock_inference,
            cache=mock_cache,
            emitter=mock_emitter,
        )

        # Events list should be populated after full run
        assert len(result.events) > 0 or len(mock_emitter.events) > 0


class TestErrorEventEmission:
    """[TS-011, TS-017, TS-018] Error paths emit structured ErrorEvent."""

    def test_service_unavailable_emits_error_event(self, mock_emitter):
        from application.nodes.analyze_semantics import analyze_semantics

        from tests.conftest import MockInferencePort

        class FailingInference(MockInferencePort):
            def invoke(self, prompt, output_schema):
                from domain.exceptions import ServiceUnavailableError

                raise ServiceUnavailableError("API down")

        failing = FailingInference()
        state = {"transcript": "test", "context": ""}

        # Node should catch error and emit ErrorEvent
        result = analyze_semantics(state, inference=failing, emitter=mock_emitter)

        errors = [e for e in mock_emitter.events if isinstance(e, ErrorEvent)]
        assert len(errors) >= 1
        assert errors[0].node_name == "analyze_semantics"
        assert errors[0].error_type == "service"
        assert "error" in result

    def test_file_too_large_emits_error_event(self, mock_emitter):
        from application.nodes.transcribe import transcribe
        from domain.exceptions import FileTooLargeError

        from tests.conftest import MockTranscriptionPort

        class FailingTranscription(MockTranscriptionPort):
            def transcribe(self, audio_bytes, language="es"):
                raise FileTooLargeError("Too large")

        failing = FailingTranscription()

        import os
        import tempfile

        fd, path = tempfile.mkstemp()
        os.write(fd, b"fake")
        os.close(fd)

        state = {"audio_path": path}
        result = transcribe(state, transcription=failing, emitter=mock_emitter)

        os.unlink(path)

        errors = [e for e in mock_emitter.events if isinstance(e, ErrorEvent)]
        assert len(errors) >= 1
        assert "error" in result
