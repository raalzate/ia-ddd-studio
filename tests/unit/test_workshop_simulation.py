"""Unit tests for the Workshop Simulation service.

Validates phase management, turn distribution, and agent orchestration.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from services.workshop_simulation import _PHASE_PLAN, WorkshopSimulator, _get_phase_for_turn


class TestPhaseManagement:
    """Tests for phase logic and turn distribution."""

    def test_get_phase_for_turn_distribution(self):
        """Verify the proportional distribution algorithm (turn-1/total_turns)."""
        total_turns = 10
        num_phases = len(_PHASE_PLAN)  # 9 phases

        # Turn 1 should always be the first phase
        phase_1 = _get_phase_for_turn(1, total_turns)
        assert phase_1["phase"] == _PHASE_PLAN[0]["phase"]

        # Final turn should be the last phase
        phase_last = _get_phase_for_turn(10, total_turns)
        assert phase_last["phase"] == _PHASE_PLAN[-1]["phase"]

        # Mid turn (e.g., 5) should be roughly in the middle
        phase_mid = _get_phase_for_turn(5, total_turns)
        expected_idx = int((4 / 10) * num_phases)
        assert phase_mid["phase"] == _PHASE_PLAN[expected_idx]["phase"]

    def test_all_phases_are_reachable(self):
        """Ensure that with enough turns, every phase in the plan is hit."""
        total_turns = 50
        hit_phases = set()
        for i in range(1, total_turns + 1):
            p = _get_phase_for_turn(i, total_turns)
            hit_phases.add(p["phase"])

        expected_phases = {p["phase"] for p in _PHASE_PLAN}
        assert hit_phases == expected_phases


class TestWorkshopSimulator:
    """Tests for the WorkshopSimulator orchestration."""

    @pytest.fixture
    def mock_inference(self):
        mock = MagicMock()
        # Mock Facilitator question and Expert answer multiple times
        mock.invoke_text.side_effect = [
            "Facilitator question 1?",
            "Expert answer 1 [Actor: User].",
            "Facilitator question 2?",
            "Expert answer 2 [Comando: Action].",
            "Facilitator question 3?",
            "Expert answer 3 [Evento: Success].",
            "Facilitator question 4?",
            "Expert answer 4 [Agregado: Root].",
        ]
        return mock

    def test_simulator_orchestration(self, mock_inference):
        """Verify that facilitators and experts are called sequentially.
        Note: num_turns has a minimum of 2 in the implementation.
        """
        simulator = WorkshopSimulator(inference=mock_inference)

        context = "Text about a system where users place orders."
        # Even with num_turns=1, the implementation forces 2
        result = simulator.simulate(context=context, num_turns=1)

        assert len(result.turns) == 2
        assert result.turns[0].turn_number == 1
        assert result.turns[1].turn_number == 2

        # Should have 4 invoke_text calls (2 facilitator, 2 expert)
        assert mock_inference.invoke_text.call_count == 4

    def test_on_turn_callback(self, mock_inference):
        """Verify the progress callback is triggered."""
        callback = MagicMock()
        simulator = WorkshopSimulator(inference=mock_inference)

        # Implementation forces 2 turns
        simulator.simulate(context="test", num_turns=1, on_turn=callback)

        assert callback.called
        # It should have been called twice. Let's check the first call.
        assert callback.call_args_list[0][0][0].turn_number == 1
        assert callback.call_args_list[1][0][0].turn_number == 2

    def test_simulator_runs_without_nlp_anchors(self, mock_inference):
        """Simulator must run end-to-end after nlp_extractor removal."""
        simulator = WorkshopSimulator(inference=mock_inference)

        result = simulator.simulate(context="Small text", num_turns=1)
        assert result.transcript != ""
