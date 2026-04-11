"""Unit tests for RefinementOrchestrator service.

Tests session lifecycle, plan creation from user response, and plan approval/rejection
as required by T012.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


def _make_simple_model():
    """Build a minimal DomainAnalysis model for testing."""
    from models.domain_analysis import AristaGrafo, BigPicture, DomainAnalysis, NodoGrafo

    return DomainAnalysis(
        nombre_proyecto="OrchestratorTest",
        version="1.0.0",
        fecha_analisis="2026-03-19",
        big_picture=BigPicture(
            descripcion="Simple test model",
            nodos=[
                NodoGrafo(
                    id="cmd_crear",
                    tipo_elemento="Comando",
                    nombre="CrearPedido",
                    descripcion="Create pedido",
                    nivel="big_picture",
                ),
                NodoGrafo(
                    id="evt_creado",
                    tipo_elemento="Evento",
                    nombre="PedidoCreado",
                    descripcion="Pedido created",
                    nivel="big_picture",
                ),
            ],
            aristas=[
                AristaGrafo(fuente="cmd_crear", destino="evt_creado", descripcion="produces"),
            ],
        ),
        agregados=[],
        read_models=[],
        politicas_inter_agregados=[],
    )


def _make_session_state(model=None):
    model = model or _make_simple_model()
    return {"analysis_result": {"analysis": model}}


def _make_ambiguity(amb_id="amb_001", priority=2):
    from domain.models.tool_schemas import Ambiguity

    return Ambiguity(
        id=amb_id,
        type="lexical",
        priority=priority,
        description=f"Test ambiguity {amb_id}",
        affected_elements=["cmd_crear"],
        suggested_resolutions=["Option A", "Option B"],
    )


class TestRefinementOrchestratorInit:
    """Tests for RefinementOrchestrator initialization."""

    def test_initializes_with_all_dependencies(self):
        from services.ambiguity_detector import AmbiguityDetector
        from services.completeness_analyzer import CompletenessAnalyzer
        from services.model_accessor import ModelAccessor
        from services.refinement_orchestrator import RefinementOrchestrator

        inference = MagicMock()
        orchestrator = RefinementOrchestrator(
            ambiguity_detector=AmbiguityDetector(inference),
            completeness_analyzer=CompletenessAnalyzer(),
            model_accessor=ModelAccessor(_make_session_state()),
        )
        assert orchestrator is not None


class TestRefinementOrchestratorStartSession:
    """Tests for RefinementOrchestrator.start_session()."""

    def test_returns_refinement_session_with_presenting_status(self):
        from domain.models.tool_schemas import RefinementSession
        from services.ambiguity_detector import AmbiguityDetector
        from services.completeness_analyzer import CompletenessAnalyzer
        from services.model_accessor import ModelAccessor
        from services.refinement_orchestrator import RefinementOrchestrator

        inference = MagicMock()
        inference.invoke.return_value = []

        orchestrator = RefinementOrchestrator(
            ambiguity_detector=AmbiguityDetector(inference),
            completeness_analyzer=CompletenessAnalyzer(),
            model_accessor=ModelAccessor(_make_session_state()),
        )

        session = orchestrator.start_session()

        assert isinstance(session, RefinementSession)
        assert session.status == "presenting"

    def test_session_has_non_empty_model_hash(self):
        from services.ambiguity_detector import AmbiguityDetector
        from services.completeness_analyzer import CompletenessAnalyzer
        from services.model_accessor import ModelAccessor
        from services.refinement_orchestrator import RefinementOrchestrator

        inference = MagicMock()
        inference.invoke.return_value = []

        orchestrator = RefinementOrchestrator(
            ambiguity_detector=AmbiguityDetector(inference),
            completeness_analyzer=CompletenessAnalyzer(),
            model_accessor=ModelAccessor(_make_session_state()),
        )

        session = orchestrator.start_session()
        assert session.model_hash != ""
        assert len(session.model_hash) == 64  # SHA-256

    def test_session_merges_lexical_and_structural_ambiguities(self):
        from domain.models.tool_schemas import Ambiguity
        from models.domain_analysis import (
            AristaGrafo,
            BigPicture,
            DomainAnalysis,
            GrafoPorAgregado,
            NodoGrafo,
        )
        from services.ambiguity_detector import AmbiguityDetector
        from services.completeness_analyzer import CompletenessAnalyzer
        from services.model_accessor import ModelAccessor
        from services.refinement_orchestrator import RefinementOrchestrator

        # Model with no events (will generate structural gap)
        model = DomainAnalysis(
            nombre_proyecto="MergeTest",
            version="1.0.0",
            fecha_analisis="2026-03-19",
            big_picture=BigPicture(
                descripcion="merge test",
                nodos=[
                    NodoGrafo(
                        id="cmd_1",
                        tipo_elemento="Comando",
                        nombre="CrearPedido",
                        descripcion="create",
                        nivel="big_picture",
                    ),
                    NodoGrafo(
                        id="evt_1",
                        tipo_elemento="Evento",
                        nombre="PedidoCreado",
                        descripcion="created",
                        nivel="big_picture",
                    ),
                ],
                aristas=[AristaGrafo(fuente="cmd_1", destino="evt_1", descripcion="produces")],
            ),
            agregados=[
                GrafoPorAgregado(
                    nombre_agregado="Pedidos",
                    entidad_raiz="Pedido",
                    nodos=[
                        NodoGrafo(
                            id="cmd_agg",
                            tipo_elemento="Comando",
                            nombre="CrearPedido",
                            descripcion="create",
                            nivel="process_level",
                        ),
                        NodoGrafo(
                            id="ent_agg",
                            tipo_elemento="Entidad Raíz",
                            nombre="Pedido",
                            descripcion="root",
                            nivel="process_level",
                        ),
                        # No event -> triggers aggregate_has_events rule
                    ],
                    aristas=[AristaGrafo(fuente="cmd_agg", destino="ent_agg", descripcion="creates")],
                )
            ],
            read_models=[],
            politicas_inter_agregados=[],
        )

        inference = MagicMock()
        inference.invoke.return_value = [
            Ambiguity(
                id="amb_001",
                type="lexical",
                priority=2,
                description="Lexical ambiguity",
                affected_elements=["cmd_1"],
                suggested_resolutions=["fix"],
            )
        ]

        orchestrator = RefinementOrchestrator(
            ambiguity_detector=AmbiguityDetector(inference),
            completeness_analyzer=CompletenessAnalyzer(),
            model_accessor=ModelAccessor({"analysis_result": {"analysis": model}}),
        )

        session = orchestrator.start_session()
        # Should have both lexical (from detector) and structural (from completeness)
        types = {a.type for a in session.ambiguities}
        assert "lexical" in types
        assert "structural" in types

    def test_ambiguities_sorted_by_priority(self):
        from domain.models.tool_schemas import Ambiguity
        from services.ambiguity_detector import AmbiguityDetector
        from services.completeness_analyzer import CompletenessAnalyzer
        from services.model_accessor import ModelAccessor
        from services.refinement_orchestrator import RefinementOrchestrator

        inference = MagicMock()
        inference.invoke.return_value = [
            Ambiguity(
                id="amb_p3",
                type="lexical",
                priority=3,
                description="low",
                affected_elements=["x"],
                suggested_resolutions=["fix"],
            ),
            Ambiguity(
                id="amb_p2",
                type="lexical",
                priority=2,
                description="mid",
                affected_elements=["y"],
                suggested_resolutions=["fix"],
            ),
        ]

        orchestrator = RefinementOrchestrator(
            ambiguity_detector=AmbiguityDetector(inference),
            completeness_analyzer=CompletenessAnalyzer(),
            model_accessor=ModelAccessor(_make_session_state()),
        )

        session = orchestrator.start_session()
        priorities = [a.priority for a in session.ambiguities]
        assert priorities == sorted(priorities)


class TestRefinementOrchestratorFormatFindings:
    """Tests for RefinementOrchestrator.format_findings()."""

    def test_returns_markdown_string(self):
        from domain.models.tool_schemas import RefinementSession
        from services.ambiguity_detector import AmbiguityDetector
        from services.completeness_analyzer import CompletenessAnalyzer
        from services.model_accessor import ModelAccessor
        from services.refinement_orchestrator import RefinementOrchestrator

        inference = MagicMock()
        orchestrator = RefinementOrchestrator(
            ambiguity_detector=AmbiguityDetector(inference),
            completeness_analyzer=CompletenessAnalyzer(),
            model_accessor=ModelAccessor(_make_session_state()),
        )

        session = RefinementSession(
            model_hash="abc",
            ambiguities=[_make_ambiguity()],
            status="presenting",
        )

        msg = orchestrator.format_findings(session)
        assert isinstance(msg, str)
        assert len(msg) > 0

    def test_empty_session_returns_no_ambiguity_message(self):
        from domain.models.tool_schemas import RefinementSession
        from services.ambiguity_detector import AmbiguityDetector
        from services.completeness_analyzer import CompletenessAnalyzer
        from services.model_accessor import ModelAccessor
        from services.refinement_orchestrator import RefinementOrchestrator

        inference = MagicMock()
        orchestrator = RefinementOrchestrator(
            ambiguity_detector=AmbiguityDetector(inference),
            completeness_analyzer=CompletenessAnalyzer(),
            model_accessor=ModelAccessor(_make_session_state()),
        )

        session = RefinementSession(model_hash="abc", ambiguities=[], status="presenting")
        msg = orchestrator.format_findings(session)
        # Should indicate no ambiguities
        assert "No" in msg or "no" in msg or "✅" in msg


class TestRefinementOrchestratorCreatePlan:
    """Tests for RefinementOrchestrator.create_plan()."""

    def test_returns_pending_plan(self):
        from domain.models.tool_schemas import RefinementSession
        from services.ambiguity_detector import AmbiguityDetector
        from services.completeness_analyzer import CompletenessAnalyzer
        from services.model_accessor import ModelAccessor
        from services.refinement_orchestrator import RefinementOrchestrator

        inference = MagicMock()
        orchestrator = RefinementOrchestrator(
            ambiguity_detector=AmbiguityDetector(inference),
            completeness_analyzer=CompletenessAnalyzer(),
            model_accessor=ModelAccessor(_make_session_state()),
        )

        session = RefinementSession(
            model_hash="abc",
            ambiguities=[_make_ambiguity()],
            status="presenting",
        )

        plan = orchestrator.create_plan(
            session=session,
            ambiguity_ids=["amb_001"],
            resolution_description="Rename X to Y",
        )

        assert plan.status == "pending"
        assert plan.source_ambiguity_ids == ["amb_001"]

    def test_plan_has_non_empty_description(self):
        from domain.models.tool_schemas import RefinementSession
        from services.ambiguity_detector import AmbiguityDetector
        from services.completeness_analyzer import CompletenessAnalyzer
        from services.model_accessor import ModelAccessor
        from services.refinement_orchestrator import RefinementOrchestrator

        inference = MagicMock()
        orchestrator = RefinementOrchestrator(
            ambiguity_detector=AmbiguityDetector(inference),
            completeness_analyzer=CompletenessAnalyzer(),
            model_accessor=ModelAccessor(_make_session_state()),
        )

        session = RefinementSession(model_hash="abc", ambiguities=[_make_ambiguity()])

        plan = orchestrator.create_plan(
            session=session,
            ambiguity_ids=["amb_001"],
            resolution_description="Fix the issue",
        )

        assert plan.description != ""

    def test_rejection_plan_has_no_operations(self):
        from domain.models.tool_schemas import RefinementSession
        from services.ambiguity_detector import AmbiguityDetector
        from services.completeness_analyzer import CompletenessAnalyzer
        from services.model_accessor import ModelAccessor
        from services.refinement_orchestrator import RefinementOrchestrator

        inference = MagicMock()
        orchestrator = RefinementOrchestrator(
            ambiguity_detector=AmbiguityDetector(inference),
            completeness_analyzer=CompletenessAnalyzer(),
            model_accessor=ModelAccessor(_make_session_state()),
        )

        session = RefinementSession(model_hash="abc", ambiguities=[_make_ambiguity()])

        plan = orchestrator.create_plan(
            session=session,
            ambiguity_ids=["amb_001"],
            resolution_description="Mantener ambos como conceptos distintos",
        )

        # Rejection/keep-separate decisions should not produce rename/delete ops
        merge_ops = [op for op in plan.proposed_operations if op.get("tool") in ("rename_element", "delete_node")]
        assert len(merge_ops) == 0


class TestRefinementOrchestratorCheckFreshness:
    """Tests for check_model_freshness."""

    def test_fresh_model_returns_true(self):
        from domain.models.tool_schemas import RefinementSession
        from services.ambiguity_detector import AmbiguityDetector
        from services.completeness_analyzer import CompletenessAnalyzer
        from services.model_accessor import ModelAccessor
        from services.refinement_orchestrator import RefinementOrchestrator

        model = _make_simple_model()
        session_state = _make_session_state(model)

        inference = MagicMock()
        orchestrator = RefinementOrchestrator(
            ambiguity_detector=AmbiguityDetector(inference),
            completeness_analyzer=CompletenessAnalyzer(),
            model_accessor=ModelAccessor(session_state),
        )

        model_hash = RefinementSession.compute_model_hash(model.model_dump_json())
        session = RefinementSession(model_hash=model_hash)

        assert orchestrator.check_model_freshness(session) is True

    def test_stale_model_returns_false(self):
        from domain.models.tool_schemas import RefinementSession
        from services.ambiguity_detector import AmbiguityDetector
        from services.completeness_analyzer import CompletenessAnalyzer
        from services.model_accessor import ModelAccessor
        from services.refinement_orchestrator import RefinementOrchestrator

        model = _make_simple_model()
        session_state = _make_session_state(model)

        inference = MagicMock()
        orchestrator = RefinementOrchestrator(
            ambiguity_detector=AmbiguityDetector(inference),
            completeness_analyzer=CompletenessAnalyzer(),
            model_accessor=ModelAccessor(session_state),
        )

        # Session has an old hash
        session = RefinementSession(model_hash="old_hash_that_does_not_match")

        assert orchestrator.check_model_freshness(session) is False

    def test_execute_plan_raises_stale_on_changed_model(self):
        """FR-009: execute_plan raises StaleModelError when model hash changed."""
        from domain.models.tool_schemas import RefinementPlan, RefinementSession
        from services.ambiguity_detector import AmbiguityDetector
        from services.completeness_analyzer import CompletenessAnalyzer
        from services.model_accessor import ModelAccessor
        from services.refinement_orchestrator import RefinementOrchestrator, StaleModelError

        model = _make_simple_model()
        session_state = _make_session_state(model)
        inference = MagicMock()
        orchestrator = RefinementOrchestrator(
            ambiguity_detector=AmbiguityDetector(inference),
            completeness_analyzer=CompletenessAnalyzer(),
            model_accessor=ModelAccessor(session_state),
        )

        # Session created with old hash (model changed since)
        session = RefinementSession(model_hash="stale_hash_does_not_match")
        plan = RefinementPlan(
            source_ambiguity_ids=["amb_001"],
            description="test stale",
            proposed_operations=[],
            status="approved",
        )

        with pytest.raises(StaleModelError):
            orchestrator.execute_plan(session, plan)

    def test_format_findings_shows_at_most_5_per_priority_group(self):
        """FR-007: format_findings caps each priority group at 5 items."""
        from domain.models.tool_schemas import Ambiguity, RefinementSession
        from services.ambiguity_detector import AmbiguityDetector
        from services.completeness_analyzer import CompletenessAnalyzer
        from services.model_accessor import ModelAccessor
        from services.refinement_orchestrator import RefinementOrchestrator

        model = _make_simple_model()
        session_state = _make_session_state(model)
        inference = MagicMock()
        orchestrator = RefinementOrchestrator(
            ambiguity_detector=AmbiguityDetector(inference),
            completeness_analyzer=CompletenessAnalyzer(),
            model_accessor=ModelAccessor(session_state),
        )

        # Create session with 8 p2 ambiguities (exceeds cap of 5)
        ambiguities = [
            Ambiguity(
                id=f"amb_p2_{i}",
                type="lexical",
                priority=2,
                description=f"Synonym {i}",
                affected_elements=[f"cmd_{i}"],
                suggested_resolutions=[f"Option {i}"],
            )
            for i in range(8)
        ]
        session = RefinementSession(
            model_hash="test_hash",
            ambiguities=ambiguities,
            status="presenting",
        )

        findings = orchestrator.format_findings(session)

        # Count how many amb_p2_ entries appear in findings
        shown_count = sum(1 for i in range(8) if f"amb_p2_{i}" in findings)
        assert shown_count <= 5
        # And excess items are mentioned
        assert "adicionales" in findings
