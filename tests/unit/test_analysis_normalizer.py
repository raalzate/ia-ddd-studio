"""Tests for the deterministic post-processor (services/analysis_normalizer.py).

These tests pin the contract that the normalizer collapses small variations
across LLM runs into a single canonical form.
"""

from __future__ import annotations

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from models.domain_analysis import (
    AristaGrafo,
    BigPicture,
    DomainAnalysis,
    GrafoPorAgregado,
    NodoGrafo,
    ReadModel,
)
from services.analysis_normalizer import (
    canonical_id,
    normalize_analysis,
    repair_project_name,
)


# --- canonical_id ---------------------------------------------------------


class TestCanonicalId:
    def test_strips_accents_and_punctuation(self):
        assert canonical_id("big_picture", "Actor", "Supervisor de Logística") == "BP-ACT-SupervisorDeLogistica"

    def test_pascal_case_for_systems(self):
        assert canonical_id("big_picture", "Sistema Externo", "Azure AD (Microsoft)") == "BP-SYS-AzureAdMicrosoft"

    def test_command_naming(self):
        assert canonical_id("big_picture", "Comando", "asignar paquete") == "BP-CMD-AsignarPaquete"

    def test_event_naming(self):
        assert canonical_id("big_picture", "Evento", "Paquete asignado") == "BP-EVT-PaqueteAsignado"

    def test_aggregate_naming(self):
        assert canonical_id("big_picture", "Agregado", "Entrega") == "BP-AGG-Entrega"

    def test_hotspot_naming(self):
        assert canonical_id("big_picture", "Hotspot", "Asignación manual") == "BP-HOT-AsignacionManual"

    def test_unknown_type_falls_back(self):
        # Unknown types still produce a stable ID with fallback code.
        rid = canonical_id("big_picture", "Actor", "x")
        assert rid.startswith("BP-")

    def test_empty_name_does_not_crash(self):
        rid = canonical_id("big_picture", "Actor", "")
        assert rid == "BP-ACT-X"


# --- repair_project_name --------------------------------------------------


class TestRepairProjectName:
    def test_keeps_well_formed_natural_text(self):
        assert repair_project_name("Digitalización última milla bancaria", "transcript") == \
            "Digitalización última milla bancaria"

    def test_repairs_pascal_case_leak(self):
        transcript = (
            "hablemos de la digitalización última milla bancaria. "
            "Es un proceso complejo."
        )
        result = repair_project_name("DigitalizarUltimaMillaBanco", transcript)
        assert "Digitaliza" in result
        assert "Banco" not in result.split()[0:1]  # not the malformed PascalCase

    def test_repairs_screaming_snake(self):
        transcript = "el sistema de gestión de pagos B2B procesa miles de transacciones."
        result = repair_project_name("ULTIMA_MILLA_BANCO", transcript)
        # Should extract a phrase from the transcript.
        assert any(token in result.lower() for token in ("sistema de", "gestión de"))

    def test_empty_falls_back_to_default(self):
        result = repair_project_name("", "")
        assert result == "Proyecto sin nombre"


# --- normalize_analysis ---------------------------------------------------


def _make_node(node_id: str, tipo: str, nombre: str, nivel: str = "big_picture") -> NodoGrafo:
    return NodoGrafo(
        id=node_id,
        tipo_elemento=tipo,  # type: ignore[arg-type]
        nombre=nombre,
        descripcion="x",
        estado_comparativo="existente",
        tags_tecnologia=None,
        nivel=nivel,  # type: ignore[arg-type]
    )


def _make_analysis(nodes: list[NodoGrafo], edges: list[AristaGrafo]) -> DomainAnalysis:
    # Add self-loop edges so strip_orphan_nodes validator keeps every node.
    referenced = set()
    for e in edges:
        referenced.add(e.fuente)
        referenced.add(e.destino)
    all_edges = list(edges)
    for n in nodes:
        if n.id not in referenced:
            all_edges.append(
                AristaGrafo(fuente=n.id, destino=n.id, descripcion="anchor", estado_comparativo="existente")
            )
    return DomainAnalysis(
        nombre_proyecto="DigitalizarUltimaMillaBanco",
        fecha_analisis="2026-04-10",
        big_picture=BigPicture(descripcion="x", nodos=nodes, aristas=all_edges),
        agregados=[
            GrafoPorAgregado(
                nombre_agregado="Entrega",
                entidad_raiz="Entrega",
                descripcion="x",
                nodos=[],
                aristas=[],
            )
        ],
    )


TRANSCRIPT = (
    "El supervisor de logística asigna paquetes en Salesforce. "
    "Luego el oficial de entregas escanea el código de barras. "
    "Hablamos de la digitalización última milla bancaria."
)


class TestNormalizeAnalysis:
    def test_canonicalizes_ids(self):
        nodes = [
            _make_node("ugly-1", "Actor", "Supervisor de Logística"),
            _make_node("ugly-2", "Sistema Externo", "Salesforce"),
        ]
        edges = [AristaGrafo(fuente="ugly-1", destino="ugly-2", descripcion="usa", estado_comparativo="existente")]
        analysis = _make_analysis(nodes, edges)

        normalize_analysis(analysis, TRANSCRIPT)

        ids = {n.id for n in analysis.big_picture.nodos}
        assert "BP-ACT-SupervisorDeLogistica" in ids
        assert "BP-SYS-Salesforce" in ids
        # Edges rewritten too
        assert analysis.big_picture.aristas[0].fuente == "BP-ACT-SupervisorDeLogistica"
        assert analysis.big_picture.aristas[0].destino == "BP-SYS-Salesforce"

    def test_dedupes_by_accent_insensitive_name(self):
        nodes = [
            _make_node("a", "Actor", "Oficial de Entregas"),
            _make_node("b", "Actor", "oficial de entregas"),  # duplicate
            _make_node("c", "Actor", "OFICIAL DE ENTREGAS"),  # duplicate
        ]
        analysis = _make_analysis(nodes, [])

        normalize_analysis(analysis, TRANSCRIPT)

        names = [n.nombre.lower() for n in analysis.big_picture.nodos]
        assert names.count("oficial de entregas") == 1

    def test_orders_by_transcript_appearance(self):
        # Salesforce appears before "oficial de entregas" in TRANSCRIPT.
        nodes = [
            _make_node("z", "Actor", "Oficial de Entregas"),
            _make_node("y", "Sistema Externo", "Salesforce"),
            _make_node("x", "Actor", "Supervisor de Logística"),
        ]
        analysis = _make_analysis(nodes, [])

        normalize_analysis(analysis, TRANSCRIPT)

        order = [n.nombre for n in analysis.big_picture.nodos]
        assert order.index("Supervisor de Logística") < order.index("Salesforce")
        assert order.index("Salesforce") < order.index("Oficial de Entregas")

    def test_repairs_project_name(self):
        nodes = [_make_node("a", "Actor", "Cliente")]
        analysis = _make_analysis(nodes, [])

        normalize_analysis(analysis, TRANSCRIPT)

        # The leaked PascalCase should be replaced by something natural.
        assert analysis.nombre_proyecto != "DigitalizarUltimaMillaBanco"
        assert " " in analysis.nombre_proyecto or analysis.nombre_proyecto == "Proyecto sin nombre"

    def test_idempotent(self):
        nodes = [
            _make_node("a", "Actor", "Supervisor de Logística"),
            _make_node("b", "Sistema Externo", "Salesforce"),
        ]
        edges = [AristaGrafo(fuente="a", destino="b", descripcion="usa", estado_comparativo="existente")]
        analysis = _make_analysis(nodes, edges)

        normalize_analysis(analysis, TRANSCRIPT)
        snapshot = analysis.model_dump(mode="json")

        normalize_analysis(analysis, TRANSCRIPT)
        again = analysis.model_dump(mode="json")

        assert snapshot == again

    def test_read_model_event_ids_are_rewired(self):
        nodes = [
            _make_node("evt-old", "Evento", "Paquete asignado"),
        ]
        analysis = _make_analysis(nodes, [])
        analysis.read_models = [
            ReadModel(
                nombre="Lista de entregas",
                descripcion="x",
                proyecta=["evt-old"],
                ui_policies=None,
                tecnologias=None,
            )
        ]

        normalize_analysis(analysis, TRANSCRIPT)

        assert analysis.read_models[0].proyecta == ["BP-EVT-PaqueteAsignado"]
