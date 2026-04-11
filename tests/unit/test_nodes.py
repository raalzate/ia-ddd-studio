"""Unit tests for node execution with mock InferencePort and TranscriptionPort.

Asserts no real API calls, valid typed output.

[TS-004, TS-005]
"""

import pytest

pytestmark = pytest.mark.offline

from models.domain_analysis import (
    BigPicture,
    DomainAnalysis,
    NodoGrafo,
)


def _make_mock_analysis() -> DomainAnalysis:
    return DomainAnalysis(
        nombre_proyecto="Test",
        fecha_analisis="2026-03-18",
        big_picture=BigPicture(
            descripcion="Test domain",
            nodos=[
                NodoGrafo(
                    id="a1",
                    tipo_elemento="Actor",
                    nombre="User",
                    descripcion="Test actor",
                    nivel="big_picture",
                )
            ],
            aristas=[],
        ),
        agregados=[],
    )


class TestAnalyzeSemanticsNode:
    """[TS-004] Semantic analysis node uses injected InferencePort."""

    def test_returns_domain_analysis(self, mock_inference):
        from application.nodes.analyze_semantics import analyze_semantics

        mock_analysis = _make_mock_analysis()
        mock_inference.configure_response(mock_analysis)

        state = {"transcript": "A customer places an order", "context": ""}
        result = analyze_semantics(state, inference=mock_inference)

        assert result["analysis"] is mock_analysis
        assert isinstance(result["analysis"], DomainAnalysis)
        assert len(mock_inference.invoke_calls) == 1

    def test_sets_has_refine_when_context_present(self, mock_inference):
        from application.nodes.analyze_semantics import analyze_semantics

        mock_inference.configure_response(_make_mock_analysis())

        state = {"transcript": "test", "context": "some context doc"}
        result = analyze_semantics(state, inference=mock_inference)

        assert result["has_refine"] is True

    def test_sets_has_refine_false_when_no_context(self, mock_inference):
        from application.nodes.analyze_semantics import analyze_semantics

        mock_inference.configure_response(_make_mock_analysis())

        state = {"transcript": "test", "context": ""}
        result = analyze_semantics(state, inference=mock_inference)

        assert result["has_refine"] is False


class TestTranscribeNode:
    """[TS-005] Transcription node uses injected TranscriptionPort."""

    def test_returns_transcript_string(self, mock_transcription, tmp_path):
        from application.nodes.transcribe import transcribe

        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio bytes")
        mock_transcription.configure_response("transcribed text output")

        state = {"audio_path": str(audio_file)}
        result = transcribe(state, transcription=mock_transcription)

        assert result["transcript"] == "transcribed text output"
        assert len(mock_transcription.transcribe_calls) == 1
        assert mock_transcription.transcribe_calls[0]["audio_bytes"] == b"fake audio bytes"


class TestCacheCheckNode:
    """Cache check node uses injected CachePort."""

    def test_cache_miss(self, mock_cache):
        from application.nodes.cache_check import cache_check

        state = {"audio_path": "/tmp/test.wav", "audio_name": "test.wav"}
        result = cache_check(state, cache=mock_cache)

        assert result["cache_exists"] is False
        assert result["cache_path"] is not None

    def test_cache_hit(self, mock_cache):
        # Pre-populate cache
        import hashlib

        from application.nodes.cache_check import cache_check

        key = hashlib.sha256(b"test.wav:/tmp/test.wav").hexdigest()
        mock_cache.set(key, "cached transcript")

        state = {"audio_path": "/tmp/test.wav", "audio_name": "test.wav"}
        result = cache_check(state, cache=mock_cache)

        assert result["cache_exists"] is True
        assert result["transcript"] == "cached transcript"


class TestRefineAnalysisNode:
    """Refine analysis node uses injected InferencePort."""

    def test_returns_refined_analysis(self, mock_inference):
        from application.nodes.refine_analysis import refine_analysis

        original = _make_mock_analysis()
        refined = _make_mock_analysis()
        refined.nombre_proyecto = "Refined"
        mock_inference.configure_response(refined)

        state = {"analysis": original, "context": "Business rules doc"}
        result = refine_analysis(state, inference=mock_inference)

        assert result["analysis"] is refined
        assert result["analysis"].nombre_proyecto == "Refined"


class TestGenerateSpecsNode:
    """Generate specs node uses injected InferencePort."""

    def test_returns_specs_dict(self, mock_inference):
        from application.nodes.generate_specs import generate_specs

        mock_inference.configure_text_response("Feature: Test")

        state = {"analysis": _make_mock_analysis()}
        result = generate_specs(state, inference=mock_inference)

        assert "specs" in result
        assert "gherkin" in result["specs"]
        assert "domain_models" in result["specs"]
        assert len(mock_inference.invoke_text_calls) == 2


# --- Phase 7 / US5: Independent Service Testability ---


@pytest.mark.offline
class TestSemanticAnalysisIndependent:
    """[TS-013] Semantic analysis processes transcript using only the substituted client."""

    def test_returns_typed_domain_analysis(self, mock_inference):
        """Result must be a DomainAnalysis instance from the injected port, not a dict."""
        from application.nodes.analyze_semantics import analyze_semantics

        mock_analysis = _make_mock_analysis()
        mock_inference.configure_response(mock_analysis)

        state = {"transcript": "Un cliente realiza un pedido", "context": ""}
        result = analyze_semantics(state, inference=mock_inference)

        assert isinstance(result["analysis"], DomainAnalysis)
        assert result["analysis"].nombre_proyecto == "Test"

    def test_zero_real_api_calls(self, mock_inference):
        """Only the injected inference port should be called — no internal client creation."""
        from application.nodes.analyze_semantics import analyze_semantics

        mock_inference.configure_response(_make_mock_analysis())

        state = {"transcript": "workshop text", "context": ""}
        analyze_semantics(state, inference=mock_inference)

        # Exactly one call to the injected port, nothing else
        assert len(mock_inference.invoke_calls) == 1
        assert mock_inference.invoke_calls[0]["output_schema"] is DomainAnalysis

    def test_no_import_of_concrete_adapter(self):
        """The node module must not import any concrete adapter class."""
        import ast
        import inspect

        from application.nodes import analyze_semantics as mod

        source = inspect.getsource(mod)
        tree = ast.parse(source)
        imported_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "infra" in node.module:
                    imported_names.append(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if "infra" in alias.name:
                        imported_names.append(alias.name)
        assert imported_names == [], f"Node imports infra modules: {imported_names}"


@pytest.mark.offline
class TestTranscriptionIndependent:
    """[TS-014] Transcription converts audio bytes using only the substituted client."""

    def test_bytes_to_str_conversion(self, mock_transcription, tmp_path):
        """Transcription port receives bytes, node returns str transcript."""
        from application.nodes.transcribe import transcribe

        audio_file = tmp_path / "meeting.wav"
        audio_file.write_bytes(b"\x00\x01\x02\x03audio-data")
        mock_transcription.configure_response("texto transcrito")

        state = {"audio_path": str(audio_file)}
        result = transcribe(state, transcription=mock_transcription)

        assert isinstance(result["transcript"], str)
        assert result["transcript"] == "texto transcrito"

    def test_zero_real_network_calls(self, mock_transcription, tmp_path):
        """Only the injected transcription port should be called."""
        from application.nodes.transcribe import transcribe

        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"audio content")
        mock_transcription.configure_response("result")

        state = {"audio_path": str(audio_file)}
        transcribe(state, transcription=mock_transcription)

        assert len(mock_transcription.transcribe_calls) == 1
        assert isinstance(mock_transcription.transcribe_calls[0]["audio_bytes"], bytes)

    def test_no_import_of_concrete_adapter(self):
        """The node module must not import any concrete adapter class."""
        import ast
        import inspect

        from application.nodes import transcribe as mod

        source = inspect.getsource(mod)
        tree = ast.parse(source)
        imported_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "infra" in node.module:
                    imported_names.append(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if "infra" in alias.name:
                        imported_names.append(alias.name)
        assert imported_names == [], f"Node imports infra modules: {imported_names}"
