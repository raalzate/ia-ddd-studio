"""Unit tests for the NLP Extractor service.

Validates determinism, extraction quality, prompt injection, and fallback.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from services.nlp_extractor import extract_anchors, inject_anchors_to_prompt, is_available

SAMPLE_TRANSCRIPT = (
    "El cliente solicita una cotización al asesor. "
    "El asesor verifica la disponibilidad del producto en el sistema. "
    "Seguro de Pichincha aprueba la póliza y notifica al cliente."
)


class TestExtractAnchors:
    """TS-001: Deterministic extraction of entities."""

    def test_extracts_domain_terms(self):
        anchors = extract_anchors(SAMPLE_TRANSCRIPT)
        assert len(anchors["domain_terms"]) > 0, "Should extract at least one domain term"

    def test_extracts_action_verbs(self):
        anchors = extract_anchors(SAMPLE_TRANSCRIPT)
        assert len(anchors["action_verbs"]) > 0, "Should extract at least one action verb"

    def test_extracts_potential_commands(self):
        anchors = extract_anchors(SAMPLE_TRANSCRIPT)
        assert len(anchors["potential_commands"]) > 0, "Should extract at least one command"

    def test_extracts_actors(self):
        anchors = extract_anchors(SAMPLE_TRANSCRIPT)
        assert len(anchors["actors"]) > 0, "Should extract at least one actor"

    def test_extracts_named_entities(self):
        """TS-001.1: Verify named entities like Seguros de Pichincha."""
        anchors = extract_anchors(SAMPLE_TRANSCRIPT)
        entity_texts = {e["text"].lower() for e in anchors["entities"]}
        assert any("pichincha" in t for t in entity_texts), (
            "Should detect 'Seguro de Pichincha' as an entity"
        )

    def test_filters_generic_nouns(self):
        anchors = extract_anchors("El sistema tiene información del proceso.")
        terms = anchors["domain_terms"]
        for generic in ("sistema", "información", "proceso"):
            assert generic not in terms, f"Generic noun '{generic}' should be filtered"

    def test_filters_generic_verbs(self):
        anchors = extract_anchors("El cliente debe poder hacer la solicitud.")
        verbs = anchors["action_verbs"]
        for generic in ("deber", "poder", "hacer"):
            assert generic not in verbs, f"Generic verb '{generic}' should be filtered"

    def test_deterministic_output(self):
        """Same input MUST yield identical output every time."""
        result_1 = extract_anchors(SAMPLE_TRANSCRIPT)
        result_2 = extract_anchors(SAMPLE_TRANSCRIPT)
        result_3 = extract_anchors(SAMPLE_TRANSCRIPT)

        assert result_1 == result_2, "Run 1 and 2 must be identical"
        assert result_2 == result_3, "Run 2 and 3 must be identical"

    def test_json_serializable(self):
        anchors = extract_anchors(SAMPLE_TRANSCRIPT)
        serialized = json.dumps(anchors, ensure_ascii=False)
        deserialized = json.loads(serialized)
        assert deserialized == anchors

    def test_empty_input_returns_empty_anchors(self):
        anchors = extract_anchors("")
        assert anchors["domain_terms"] == []
        assert anchors["action_verbs"] == []
        assert anchors["actors"] == []
        assert anchors["potential_commands"] == []
        assert anchors["entities"] == []


class TestPerformance:
    """TS-002: NLP extraction performance overhead."""

    def test_extraction_under_one_second(self):
        long_text = SAMPLE_TRANSCRIPT * 50
        start = time.time()
        extract_anchors(long_text)
        elapsed = time.time() - start
        assert elapsed < 1.0, f"Extraction took {elapsed:.2f}s, must be < 1s"


class TestPromptInjection:
    """TS-003: Constraint injection into LLM context."""

    def test_injects_anchors_block(self):
        anchors = extract_anchors(SAMPLE_TRANSCRIPT)
        base = "Analyze this transcript."
        result = inject_anchors_to_prompt(anchors, base)

        assert "<anchors>" in result
        assert "</anchors>" in result
        assert "Analyze this transcript." in result

    def test_injects_ddd_taxonomy_labels(self):
        """TS-003.1: Verify anchors reference DDD element types."""
        anchors = {
            "actors": ["Cliente"],
            "domain_terms": ["pago", "factura"],
            "potential_commands": ["Validar pago"],
            "action_verbs": ["validar"],
            "entities": [{"text": "SDP", "label": "ORG"}],
        }
        result = inject_anchors_to_prompt(anchors, "Base")
        assert "POTENTIAL ACTORS" in result
        assert "CORE DOMAIN TERMS" in result
        assert "POTENTIAL COMMANDS" in result
        assert "ACTION VERBS" in result
        assert "NAMED ENTITIES" in result
        assert "- Cliente" in result
        assert "- Validar pago" in result
        assert "- SDP (ORG)" in result
        # Verify DDD taxonomy mapping hints
        assert "Agregado" in result
        assert "Comando" in result
        assert "Evento" in result

    def test_injects_no_hallucination_instruction(self):
        """TS-003.2: Verify strict no-hallucination instruction is present."""
        anchors = {"actors": ["Test"], "domain_terms": ["test"], "potential_commands": [], "action_verbs": [], "entities": []}
        result = inject_anchors_to_prompt(anchors, "Base")
        assert "You MUST map these terms" in result
        assert "Do NOT invent new root aggregates" in result

    def test_empty_anchors_returns_base_prompt(self):
        result = inject_anchors_to_prompt(
            {"actors": [], "domain_terms": [], "potential_commands": [], "action_verbs": [], "entities": []},
            "Hello",
        )
        assert result == "Hello"


class TestFallback:
    """TS-004: Graceful degradation when spaCy is missing."""

    def test_is_available_returns_bool(self):
        result = is_available()
        assert isinstance(result, bool)

    def test_missing_model_returns_empty_anchors(self, mocker):
        mocker.patch("spacy.cli.download")
        anchors = extract_anchors("some text", model_name="nonexistent_model_xyz")
        assert anchors == {
            "actors": [],
            "domain_terms": [],
            "potential_commands": [],
            "action_verbs": [],
            "entities": [],
        }
