"""Unit tests for Dynamic LLM Configuration."""

from __future__ import annotations

import os
from unittest.mock import patch

from infra.inference_provider import InferenceProvider


def test_inference_provider_default_config():
    """Verify provider loads defaults from environment variables."""
    with (
        patch.dict(os.environ, {"GEMINI_MODEL": "env-model", "GOOGLE_API_KEY": "env-key"}),
        patch("streamlit.session_state", {}) as mock_state,
        patch("ui.utils.storage.load_llm_config", return_value=None),
    ):
        config = InferenceProvider.get_config()

        assert config["model_name"] == "env-model"
        assert config["api_key"] == "env-key"
        assert "llm_config" in mock_state


def test_inference_provider_override():
    """Verify session state overrides environment variables."""
    mock_state = {
        "llm_config": {
            "model_name": "override-model",
            "api_key": "override-key",
        }
    }

    with (
        patch.dict(os.environ, {"GEMINI_MODEL": "env-model", "GOOGLE_API_KEY": "env-key"}),
        patch("streamlit.session_state", mock_state),
    ):
        config = InferenceProvider.get_config()

        assert config["model_name"] == "override-model"
        assert config["api_key"] == "override-key"
        assert "temperature" not in config


def test_inference_provider_strips_legacy_temperature():
    """Legacy persisted configs with `temperature` must be ignored silently."""
    mock_state = {
        "llm_config": {
            "model_name": "legacy-model",
            "api_key": "legacy-key",
            "temperature": 0.7,
        }
    }

    with patch("streamlit.session_state", mock_state):
        config = InferenceProvider.get_config()
        assert "temperature" not in config


@patch("infra.inference_provider.GeminiInferenceAdapter")
def test_get_inference_port_uses_config(mock_adapter):
    """Verify that get_inference_port initializes the adapter with correct settings."""
    mock_state = {
        "llm_config": {
            "model_name": "test-model",
            "api_key": "test-key",
        }
    }

    with patch("streamlit.session_state", mock_state):
        InferenceProvider.get_inference_port()

        mock_adapter.assert_called_once_with(model="test-model", api_key="test-key")


@patch("infra.inference_provider.GeminiChatAgentAdapter")
def test_get_chat_agent_port_uses_config(mock_agent):
    """Verify that get_chat_agent_port initializes the agent with correct configuration."""
    mock_state = {
        "llm_config": {
            "model_name": "agent-model",
            "api_key": "agent-key",
        }
    }

    with patch("streamlit.session_state", mock_state):
        InferenceProvider.get_chat_agent_port()

        mock_agent.assert_called_once_with(model="agent-model", api_key="agent-key")
