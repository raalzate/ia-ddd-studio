"""Unit tests for AgentState Pydantic validation rules.

Tests:
- Field types match data-model.md specification
- has_refine=True requires context not None validator
- State merge semantics (partial updates preserve existing fields)
- NodeContract dataclass fields
"""

import pytest

pytestmark = pytest.mark.offline
from pydantic import ValidationError


class TestAgentStateFieldTypes:
    """Verify AgentState fields match data-model.md specification."""

    def test_default_state_has_all_fields(self):
        from domain.models.agent_state import AgentState

        state = AgentState()
        assert state.audio_path is None
        assert state.audio_name is None
        assert state.transcript is None
        assert state.context is None
        assert state.analysis is None
        assert state.specs is None
        assert state.has_refine is False
        assert state.cache_path is None
        assert state.cache_exists is False
        assert state.error is None

    def test_audio_path_accepts_string(self):
        from domain.models.agent_state import AgentState

        state = AgentState(audio_path="/tmp/audio.wav")
        assert state.audio_path == "/tmp/audio.wav"

    def test_analysis_must_be_domain_analysis_instance(self):
        from domain.models.agent_state import AgentState

        with pytest.raises(ValidationError):
            AgentState(analysis={"not": "a DomainAnalysis"})

    def test_specs_accepts_dict(self):
        from domain.models.agent_state import AgentState

        state = AgentState(specs={"gherkin": "Feature: ..."})
        assert state.specs == {"gherkin": "Feature: ..."}


class TestAgentStateHasRefineValidator:
    """Verify has_refine=True requires context not None."""

    def test_has_refine_true_with_context_passes(self):
        from domain.models.agent_state import AgentState

        state = AgentState(has_refine=True, context="some context")
        assert state.has_refine is True
        assert state.context == "some context"

    def test_has_refine_true_without_context_raises(self):
        from domain.models.agent_state import AgentState

        with pytest.raises(ValidationError, match="context"):
            AgentState(has_refine=True, context=None)

    def test_has_refine_false_without_context_passes(self):
        from domain.models.agent_state import AgentState

        state = AgentState(has_refine=False, context=None)
        assert state.has_refine is False


class TestAgentStateMergeSemantics:
    """Verify partial state updates preserve existing fields (LangGraph merge)."""

    def test_partial_update_preserves_existing_fields(self):
        from domain.models.agent_state import AgentState

        original = AgentState(audio_path="/tmp/audio.wav", audio_name="test.wav")
        update = {"transcript": "hello world"}
        merged = original.model_copy(update=update)
        assert merged.audio_path == "/tmp/audio.wav"
        assert merged.audio_name == "test.wav"
        assert merged.transcript == "hello world"

    def test_partial_update_can_overwrite_field(self):
        from domain.models.agent_state import AgentState

        original = AgentState(transcript="draft")
        merged = original.model_copy(update={"transcript": "final"})
        assert merged.transcript == "final"


class TestNodeContract:
    """Verify NodeContract dataclass structure."""

    def test_node_contract_has_required_fields(self):
        from domain.models.agent_state import NodeContract

        contract = NodeContract(
            node_name="cache_check",
            required_inputs=["audio_path", "audio_name"],
            produced_outputs=["cache_path", "cache_exists"],
            emits_events=["cache_check"],
        )
        assert contract.node_name == "cache_check"
        assert contract.required_inputs == ["audio_path", "audio_name"]
        assert contract.produced_outputs == ["cache_path", "cache_exists"]
        assert contract.emits_events == ["cache_check"]

    def test_node_contract_is_dataclass(self):
        import dataclasses

        from domain.models.agent_state import NodeContract

        assert dataclasses.is_dataclass(NodeContract)
