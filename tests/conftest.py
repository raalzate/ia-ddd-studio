"""Shared test fixtures providing mock adapter implementations for all port protocols."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import TypeVar

import pytest

# Base directory for feature 004 BDD feature files.
# Step definition files in tests/unit/ use:
#   scenarios("../../specs/004-reactive-refinement-agent/tests/features/<file>.feature")
FEATURE_004_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "specs",
        "004-reactive-refinement-agent",
        "tests",
        "features",
    )
)

# Base directory for feature 005 BDD feature files.
FEATURE_005_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "specs",
        "005-history-sidebar-draft",
        "tests",
        "features",
    )
)

# Base directory for feature 006 BDD feature files.
FEATURE_006_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "specs",
        "006-faster-whisper-audio",
        "tests",
        "features",
    )
)

T = TypeVar("T")


class MockInferencePort:
    """Mock implementation of InferencePort for unit tests."""

    def __init__(self) -> None:
        self.invoke_calls: list[dict] = []
        self.invoke_text_calls: list[str] = []
        self._invoke_response: object = None
        self._invoke_text_response: str = ""
        self._schema_responses: dict[type, object] = {}

    def configure_response(self, response: object) -> None:
        self._invoke_response = response

    def configure_response_for_schema(self, schema: type, response: object) -> None:
        """Register a canned response for a specific output_schema type."""
        self._schema_responses[schema] = response

    def configure_text_response(self, response: str) -> None:
        self._invoke_text_response = response

    def configure_step_extraction_responses(self) -> None:
        """Helper to configure a valid DomainAnalysis response for single-shot extraction."""
        from models.domain_analysis import (
            AristaGrafo,
            BigPicture,
            DomainAnalysis,
            NodoGrafo,
        )

        analysis = DomainAnalysis(
            nombre_proyecto="Test",
            fecha_analisis="2026-04-15",
            big_picture=BigPicture(
                descripcion="Mocked analysis",
                nodos=[
                    NodoGrafo(
                        id="BP-ACT-User",
                        tipo_elemento="Actor",
                        nombre="User",
                        descripcion="Test actor",
                        nivel="big_picture",
                    ),
                    NodoGrafo(
                        id="BP-CMD-PlaceOrder",
                        tipo_elemento="Comando",
                        nombre="PlaceOrder",
                        descripcion="places an order",
                        nivel="big_picture",
                    ),
                    NodoGrafo(
                        id="BP-EVT-OrderPlaced",
                        tipo_elemento="Evento",
                        nombre="OrderPlaced",
                        descripcion="order placed",
                        nivel="big_picture",
                    ),
                ],
                aristas=[
                    AristaGrafo(fuente="BP-ACT-User", destino="BP-CMD-PlaceOrder", descripcion="ejecuta"),
                    AristaGrafo(fuente="BP-CMD-PlaceOrder", destino="BP-EVT-OrderPlaced", descripcion="produce"),
                ],
            ),
            agregados=[],
        )
        self.configure_response_for_schema(DomainAnalysis, analysis)

    def invoke(self, prompt: str, output_schema: type[T]) -> T:
        self.invoke_calls.append({"prompt": prompt, "output_schema": output_schema})
        # Schema-specific response takes priority over catch-all
        if output_schema in self._schema_responses:
            return self._schema_responses[output_schema]  # type: ignore[return-value]
        return self._invoke_response  # type: ignore[return-value]

    def invoke_text(self, prompt: str) -> str:
        self.invoke_text_calls.append(prompt)
        return self._invoke_text_response


class MockTranscriptionPort:
    """Mock implementation of TranscriptionPort for unit tests."""

    def __init__(self) -> None:
        self.transcribe_calls: list[dict] = []
        self._response: str = "transcribed text"

    def configure_response(self, response: str) -> None:
        self._response = response

    def transcribe(self, audio_bytes: bytes, language: str = "es") -> str:
        self.transcribe_calls.append({"audio_bytes": audio_bytes, "language": language})
        return self._response


class MockCachePort:
    """Mock implementation of CachePort for unit tests."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def set(self, key: str, value: str) -> None:
        self._store[key] = value


class MockEventEmitter:
    """Mock implementation of EventEmitter for unit tests."""

    def __init__(self) -> None:
        self.events: list[object] = []

    def __call__(self, event: object) -> None:
        self.events.append(event)


@pytest.fixture
def mock_inference() -> MockInferencePort:
    return MockInferencePort()


@pytest.fixture
def mock_transcription() -> MockTranscriptionPort:
    return MockTranscriptionPort()


@pytest.fixture
def mock_cache() -> MockCachePort:
    return MockCachePort()


@pytest.fixture
def mock_emitter() -> MockEventEmitter:
    return MockEventEmitter()


@pytest.fixture(autouse=True)
def _block_socket_in_offline_tests(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Block all socket connections during tests marked @pytest.mark.offline.

    Ensures unit tests never make real network calls.
    """
    marker = request.node.get_closest_marker("offline")
    if marker is None:
        return

    import socket

    def _guarded_connect(self: socket.socket, *args: object, **kwargs: object) -> None:
        raise RuntimeError(f"Network access blocked in @offline test: attempted connect to {args}")

    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _guarded_connect)


# ── Feature 005: Draft fixtures ──────────────────────────────────────────


def _make_sample_domain_analysis(
    project_name: str = "TestProject",
    num_aggregates: int = 2,
    num_events: int = 4,
    num_commands: int = 3,
) -> DomainAnalysis:
    """Build a minimal but valid DomainAnalysis for testing."""
    from models.domain_analysis import (
        AristaGrafo,
        BigPicture,
        DomainAnalysis,
        GrafoPorAgregado,
        NodoGrafo,
    )

    bp_nodes = []
    bp_edges = []
    for i in range(num_events):
        bp_nodes.append(
            NodoGrafo(
                id=f"evt-{i}",
                tipo_elemento="Evento",
                nombre=f"Event{i}",
                descripcion=f"Event {i}",
                nivel="big_picture",
            )
        )
    for i in range(num_commands):
        bp_nodes.append(
            NodoGrafo(
                id=f"cmd-{i}",
                tipo_elemento="Comando",
                nombre=f"Command{i}",
                descripcion=f"Command {i}",
                nivel="big_picture",
            )
        )
    # Create edges so nodes aren't orphaned by strip_orphan_nodes validator.
    # Chain all nodes together: cmd-0 → evt-0 → cmd-1 → evt-1 → ...
    all_bp_ids = [n.id for n in bp_nodes]
    for i in range(len(all_bp_ids) - 1):
        bp_edges.append(AristaGrafo(fuente=all_bp_ids[i], destino=all_bp_ids[i + 1], descripcion="triggers"))

    aggregates = []
    for i in range(num_aggregates):
        agg_node = NodoGrafo(
            id=f"agg-{i}",
            tipo_elemento="Agregado",
            nombre=f"Aggregate{i}",
            descripcion=f"Aggregate {i}",
            nivel="process_level",
        )
        root_node = NodoGrafo(
            id=f"root-{i}",
            tipo_elemento="Entidad Raíz",
            nombre=f"Root{i}",
            descripcion=f"Root entity {i}",
            nivel="process_level",
        )
        agg_edge = AristaGrafo(fuente=f"agg-{i}", destino=f"root-{i}", descripcion="contains")
        aggregates.append(
            GrafoPorAgregado(
                nombre_agregado=f"Aggregate{i}",
                entidad_raiz=f"Root{i}",
                nodos=[agg_node, root_node],
                aristas=[agg_edge],
            )
        )

    return DomainAnalysis(
        nombre_proyecto=project_name,
        version="1.0.0",
        fecha_analisis=datetime.now(timezone.utc).isoformat(),
        big_picture=BigPicture(
            descripcion="Test big picture",
            nodos=bp_nodes,
            aristas=bp_edges,
        ),
        agregados=aggregates,
    )


@pytest.fixture
def sample_domain_analysis():
    """A minimal valid DomainAnalysis instance for draft testing."""
    return _make_sample_domain_analysis()


@pytest.fixture
def make_domain_analysis():
    """Factory fixture: make_domain_analysis(project_name, num_aggregates, num_events, num_commands)."""
    return _make_sample_domain_analysis


@pytest.fixture
def tmp_drafts_dir(tmp_path):
    """A temporary directory for draft file storage."""
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    return str(drafts)
