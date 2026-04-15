"""Unit tests for services.integrity_validator."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from models.domain_analysis import (
    AristaGrafo,
    BigPicture,
    DomainAnalysis,
    GrafoPorAgregado,
    NodoGrafo,
    ReadModel,
)
from services.integrity_validator import summarize, validate


def _node(nid: str, tipo: str, nombre: str | None = None) -> NodoGrafo:
    return NodoGrafo(
        id=nid,
        tipo_elemento=tipo,
        nombre=nombre or nid,
        descripcion="x",
        nivel="big_picture",
    )


def _edge(src: str, dst: str) -> AristaGrafo:
    return AristaGrafo(fuente=src, destino=dst, descripcion="x")


def _build(
    *,
    nodes: list[NodoGrafo],
    edges: list[AristaGrafo],
    aggregates: list[GrafoPorAgregado] | None = None,
    read_models: list[ReadModel] | None = None,
) -> DomainAnalysis:
    return DomainAnalysis(
        nombre_proyecto="t",
        fecha_analisis="2026-04-14",
        big_picture=BigPicture(descripcion="x", nodos=nodes, aristas=edges),
        agregados=aggregates or [],
        read_models=read_models or [],
    )


class TestOrphanCommand:
    def test_command_without_actor_edge_flagged(self):
        # Command has outgoing edge to event but no actor->command edge.
        analysis = _build(
            nodes=[
                _node("BP-CMD-X", "Comando", "X"),
                _node("BP-EVT-X", "Evento", "Y"),
            ],
            edges=[_edge("BP-CMD-X", "BP-EVT-X")],
        )
        codes = {i.code for i in validate(analysis)}
        assert "orphan_command" in codes


class TestOrphanEvent:
    def test_event_without_producer_flagged(self):
        # Event is source (Event→AggregateNode) but never destination.
        analysis = _build(
            nodes=[
                _node("BP-EVT-A", "Evento", "A"),
                _node("BP-AGG-Z", "Agregado", "Z"),
            ],
            edges=[_edge("BP-EVT-A", "BP-AGG-Z")],
        )
        codes = {i.code for i in validate(analysis)}
        assert "orphan_event" in codes


class TestReadModels:
    def test_empty_proyecta_flagged(self):
        analysis = _build(
            nodes=[
                _node("BP-CMD-X", "Comando"),
                _node("BP-EVT-X", "Evento"),
            ],
            edges=[_edge("BP-CMD-X", "BP-EVT-X")],
            read_models=[ReadModel(nombre="Vacio", descripcion="x", proyecta=[])],
        )
        codes = {i.code for i in validate(analysis)}
        assert "empty_read_model" in codes

    def test_dangling_projection_flagged(self):
        analysis = _build(
            nodes=[
                _node("BP-CMD-X", "Comando"),
                _node("BP-EVT-X", "Evento"),
            ],
            edges=[_edge("BP-CMD-X", "BP-EVT-X")],
            read_models=[ReadModel(nombre="V", descripcion="x", proyecta=["BP-EVT-NOTEXIST"])],
        )
        issues = validate(analysis)
        assert any(i.code == "dangling_read_model_projection" for i in issues)


class TestHealthy:
    def test_well_formed_has_no_warnings(self):
        analysis = _build(
            nodes=[
                _node("BP-ACT-Op", "Actor", "Op"),
                _node("BP-CMD-Do", "Comando", "Do"),
                _node("BP-EVT-Done", "Evento", "Done"),
            ],
            edges=[
                _edge("BP-ACT-Op", "BP-CMD-Do"),
                _edge("BP-CMD-Do", "BP-EVT-Done"),
            ],
            read_models=[ReadModel(nombre="V", descripcion="x", proyecta=["BP-EVT-Done"])],
        )
        warnings = [i for i in validate(analysis) if i.severity == "warning"]
        assert warnings == []


class TestSummarize:
    def test_counts_by_severity(self):
        analysis = _build(
            nodes=[
                _node("BP-CMD-X", "Comando"),
                _node("BP-EVT-X", "Evento"),
            ],
            edges=[_edge("BP-CMD-X", "BP-EVT-X")],
            read_models=[ReadModel(nombre="V", descripcion="x", proyecta=[])],
        )
        counts = summarize(validate(analysis))
        assert counts["warning"] >= 1
        assert set(counts.keys()) == {"error", "warning", "info"}
