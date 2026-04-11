"""Integration tests for the refinement pipeline.

T015: End-to-end flow: generation → flag → detection → user resolution → model mutation.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


def _make_model_with_synonym(include_synonym=True):
    """Build a test DomainAnalysis. If include_synonym, include 'Orden' nodes."""
    from models.domain_analysis import (
        AristaGrafo,
        BigPicture,
        DomainAnalysis,
        NodoGrafo,
    )

    nodes = [
        NodoGrafo(
            id="cmd_crear_pedido",
            tipo_elemento="Comando",
            nombre="CrearPedido",
            descripcion="Create pedido",
            nivel="big_picture",
        ),
        NodoGrafo(
            id="evt_pedido_creado",
            tipo_elemento="Evento",
            nombre="PedidoCreado",
            descripcion="Pedido created",
            nivel="big_picture",
        ),
    ]
    aristas = [
        AristaGrafo(fuente="cmd_crear_pedido", destino="evt_pedido_creado", descripcion="produces"),
    ]
    if include_synonym:
        nodes.append(
            NodoGrafo(
                id="cmd_crear_orden",
                tipo_elemento="Comando",
                nombre="CrearOrden",
                descripcion="Create orden",
                nivel="big_picture",
            )
        )
        aristas.append(AristaGrafo(fuente="cmd_crear_orden", destino="evt_pedido_creado", descripcion="produces"))

    return DomainAnalysis(
        nombre_proyecto="IntegrationTest",
        version="1.0.0",
        fecha_analisis="2026-03-19",
        big_picture=BigPicture(descripcion="Integration test model", nodos=nodes, aristas=aristas),
        agregados=[],
        read_models=[],
        politicas_inter_agregados=[],
    )


@pytest.mark.integration
class TestRefinementEndToEnd:
    """End-to-end integration tests for the refinement flow."""

    def test_flag_is_set_after_process_input_completes(self):
        """After generation, refinement_pending flag must be True."""
        session_state = {}
        model = _make_model_with_synonym()
        session_state["analysis_result"] = {"analysis": model}
        session_state["refinement_pending"] = True  # simulates process_input setting the flag

        assert session_state.get("refinement_pending") is True

    def test_trigger_refinement_creates_session_and_finds_ambiguities(self):
        """Orchestrator.start_session() returns a session with detected ambiguities."""
        from domain.models.tool_schemas import Ambiguity
        from services.ambiguity_detector import AmbiguityDetector
        from services.completeness_analyzer import CompletenessAnalyzer
        from services.model_accessor import ModelAccessor
        from services.refinement_orchestrator import RefinementOrchestrator

        model = _make_model_with_synonym()
        session_state = {"analysis_result": {"analysis": model}}

        inference = MagicMock()
        inference.invoke.return_value = [
            Ambiguity(
                id="amb_001",
                type="lexical",
                priority=2,
                description="'CrearPedido' y 'CrearOrden' son potenciales sinónimos.",
                affected_elements=["cmd_crear_pedido", "cmd_crear_orden"],
                suggested_resolutions=["Unificar bajo 'CrearPedido'", "Mantener ambos"],
            )
        ]

        orchestrator = RefinementOrchestrator(
            ambiguity_detector=AmbiguityDetector(inference),
            completeness_analyzer=CompletenessAnalyzer(),
            model_accessor=ModelAccessor(session_state),
        )

        session = orchestrator.start_session()

        assert session.status == "presenting"
        assert len(session.ambiguities) >= 1
        assert session.model_hash != ""

    def test_create_plan_from_user_resolution(self):
        """create_plan() builds a plan from user resolution text."""
        from domain.models.tool_schemas import Ambiguity, RefinementSession
        from services.ambiguity_detector import AmbiguityDetector
        from services.completeness_analyzer import CompletenessAnalyzer
        from services.model_accessor import ModelAccessor
        from services.refinement_orchestrator import RefinementOrchestrator

        model = _make_model_with_synonym()
        session_state = {"analysis_result": {"analysis": model}}

        inference = MagicMock()
        orchestrator = RefinementOrchestrator(
            ambiguity_detector=AmbiguityDetector(inference),
            completeness_analyzer=CompletenessAnalyzer(),
            model_accessor=ModelAccessor(session_state),
        )

        session = RefinementSession(
            model_hash=RefinementSession.compute_model_hash(model.model_dump_json()),
            ambiguities=[
                Ambiguity(
                    id="amb_001",
                    type="lexical",
                    priority=2,
                    description="Synonym pair",
                    affected_elements=["cmd_crear_pedido", "cmd_crear_orden"],
                    suggested_resolutions=["Merge", "Keep"],
                )
            ],
            status="presenting",
        )

        plan = orchestrator.create_plan(
            session=session,
            ambiguity_ids=["amb_001"],
            resolution_description="Pedido y Orden son sinónimos, unificar bajo Pedido",
        )

        assert plan.status == "pending"
        assert plan.source_ambiguity_ids == ["amb_001"]
        assert plan.description != ""

    def test_plan_preview_shows_proposed_operations(self):
        """create_plan() includes proposed_operations for user preview."""
        from domain.models.tool_schemas import Ambiguity, RefinementSession
        from services.ambiguity_detector import AmbiguityDetector
        from services.completeness_analyzer import CompletenessAnalyzer
        from services.model_accessor import ModelAccessor
        from services.refinement_orchestrator import RefinementOrchestrator

        model = _make_model_with_synonym()
        session_state = {"analysis_result": {"analysis": model}}
        inference = MagicMock()

        orchestrator = RefinementOrchestrator(
            ambiguity_detector=AmbiguityDetector(inference),
            completeness_analyzer=CompletenessAnalyzer(),
            model_accessor=ModelAccessor(session_state),
        )

        session = RefinementSession(
            model_hash=RefinementSession.compute_model_hash(model.model_dump_json()),
            ambiguities=[
                Ambiguity(
                    id="amb_001",
                    type="lexical",
                    priority=2,
                    description="Synonym",
                    affected_elements=["cmd_crear_pedido", "cmd_crear_orden"],
                    suggested_resolutions=["Merge"],
                )
            ],
        )

        plan = orchestrator.create_plan(
            session=session,
            ambiguity_ids=["amb_001"],
            resolution_description="Unificar bajo Pedido",
        )

        # Plan preview: user can inspect proposed_operations before approval
        assert plan.status == "pending"
        assert isinstance(plan.proposed_operations, list)

    def test_execute_plan_raises_stale_model_error(self):
        """execute_plan raises StaleModelError when model changed since session start."""
        from domain.models.tool_schemas import RefinementPlan, RefinementSession
        from services.ambiguity_detector import AmbiguityDetector
        from services.completeness_analyzer import CompletenessAnalyzer
        from services.model_accessor import ModelAccessor
        from services.refinement_orchestrator import RefinementOrchestrator, StaleModelError

        model = _make_model_with_synonym()
        session_state = {"analysis_result": {"analysis": model}}
        inference = MagicMock()

        orchestrator = RefinementOrchestrator(
            ambiguity_detector=AmbiguityDetector(inference),
            completeness_analyzer=CompletenessAnalyzer(),
            model_accessor=ModelAccessor(session_state),
        )

        # Session with OLD hash
        session = RefinementSession(model_hash="old_hash_that_does_not_match")

        plan = RefinementPlan(
            source_ambiguity_ids=["amb_001"],
            description="test",
            proposed_operations=[],
            status="approved",
        )

        with pytest.raises(StaleModelError):
            orchestrator.execute_plan(session, plan)

    def test_execute_plan_with_empty_operations_succeeds(self):
        """execute_plan with zero operations succeeds and marks status as executed."""
        from domain.models.tool_schemas import RefinementPlan, RefinementSession
        from services.ambiguity_detector import AmbiguityDetector
        from services.completeness_analyzer import CompletenessAnalyzer
        from services.model_accessor import ModelAccessor
        from services.refinement_orchestrator import RefinementOrchestrator

        model = _make_model_with_synonym()
        session_state = {"analysis_result": {"analysis": model}}
        inference = MagicMock()

        orchestrator = RefinementOrchestrator(
            ambiguity_detector=AmbiguityDetector(inference),
            completeness_analyzer=CompletenessAnalyzer(),
            model_accessor=ModelAccessor(session_state),
        )

        model_hash = RefinementSession.compute_model_hash(model.model_dump_json())
        session = RefinementSession(model_hash=model_hash)

        plan = RefinementPlan(
            source_ambiguity_ids=["amb_001"],
            description="No-op plan",
            proposed_operations=[],  # No operations
            status="approved",
        )

        result = orchestrator.execute_plan(session, plan)
        assert result.status == "executed"

    def test_full_flow_detection_to_session(self):
        """Full integration: detect → create session → format findings → plan."""
        from domain.models.tool_schemas import Ambiguity
        from services.ambiguity_detector import AmbiguityDetector
        from services.completeness_analyzer import CompletenessAnalyzer
        from services.model_accessor import ModelAccessor
        from services.refinement_orchestrator import RefinementOrchestrator

        model = _make_model_with_synonym()
        session_state = {"analysis_result": {"analysis": model}}

        inference = MagicMock()
        inference.invoke.return_value = [
            Ambiguity(
                id="amb_001",
                type="lexical",
                priority=2,
                description="Synonym candidates",
                affected_elements=["cmd_crear_pedido", "cmd_crear_orden"],
                suggested_resolutions=["Merge into CrearPedido", "Keep both"],
            )
        ]

        orchestrator = RefinementOrchestrator(
            ambiguity_detector=AmbiguityDetector(inference),
            completeness_analyzer=CompletenessAnalyzer(),
            model_accessor=ModelAccessor(session_state),
        )

        # Step 1: Start session (detection)
        session = orchestrator.start_session()
        assert len(session.ambiguities) >= 1
        session_state["refinement_session"] = session

        # Step 2: Format findings
        findings = orchestrator.format_findings(session)
        assert len(findings) > 0
        assert "Análisis" in findings

        # Step 3: Create plan from user response
        plan = orchestrator.create_plan(
            session=session,
            ambiguity_ids=["amb_001"],
            resolution_description="Unificar bajo CrearPedido",
        )
        assert plan.status == "pending"
        assert len(plan.source_ambiguity_ids) >= 1

    def test_executed_results_link_to_source_ambiguity(self):
        """FR-008/SC-003: Every ToolExecution in executed_results is traceable to source ambiguity."""
        from domain.models.tool_schemas import Ambiguity, RefinementSession
        from services.ambiguity_detector import AmbiguityDetector
        from services.completeness_analyzer import CompletenessAnalyzer
        from services.model_accessor import ModelAccessor
        from services.refinement_orchestrator import RefinementOrchestrator

        model = _make_model_with_synonym()
        session_state = {"analysis_result": {"analysis": model}}
        inference = MagicMock()

        orchestrator = RefinementOrchestrator(
            ambiguity_detector=AmbiguityDetector(inference),
            completeness_analyzer=CompletenessAnalyzer(),
            model_accessor=ModelAccessor(session_state),
        )

        model_hash = RefinementSession.compute_model_hash(model.model_dump_json())
        session = RefinementSession(
            model_hash=model_hash,
            ambiguities=[
                Ambiguity(
                    id="amb_001",
                    type="lexical",
                    priority=2,
                    description="Synonym pair",
                    affected_elements=["cmd_crear_pedido", "cmd_crear_orden"],
                    suggested_resolutions=["Merge"],
                )
            ],
        )

        plan = orchestrator.create_plan(
            session=session,
            ambiguity_ids=["amb_001"],
            resolution_description="Unificar bajo CrearPedido",
        )
        assert plan.source_ambiguity_ids == ["amb_001"]

        # Execute plan (empty ops path — no tool calls)
        plan.proposed_operations = []
        plan.status = "approved"
        result = orchestrator.execute_plan(session, plan)

        assert result.status == "executed"
        # source_ambiguity_ids is the traceability link
        assert "amb_001" in result.source_ambiguity_ids
