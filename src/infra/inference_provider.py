"""Provider for dynamic LLM inference injection.

Checks streamlit session state for overrides, falls back to env vars.
"""

from __future__ import annotations

import os
from typing import Any

import streamlit as st

from domain.ports import ChatAgentPort, InferencePort
from infra.adapters.gemini_chat_agent import GeminiChatAgentAdapter
from infra.adapters.gemini_inference import GeminiInferenceAdapter


class InferenceProvider:
    """Manages the lifecycle and configuration of LLM clients."""

    @staticmethod
    def get_config() -> dict[str, Any]:
        """Get current active configuration from session state, persisted file, or env."""
        if "llm_config" not in st.session_state:
            from ui.utils.storage import load_llm_config

            saved = load_llm_config()
            st.session_state["llm_config"] = saved or {
                "model_name": os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
                "api_key": os.getenv("GOOGLE_API_KEY", ""),
                "temperature": 0.1,
            }
        return st.session_state["llm_config"]

    @staticmethod
    def get_inference_port() -> InferencePort:
        """Create an InferencePort with current config."""
        config = InferenceProvider.get_config()
        return GeminiInferenceAdapter(
            model=config["model_name"],
            api_key=config["api_key"],
            temperature=config["temperature"],
        )

    @staticmethod
    def get_chat_agent_port() -> ChatAgentPort:
        """Create a ChatAgentPort with current config."""
        config = InferenceProvider.get_config()
        return GeminiChatAgentAdapter(
            model=config["model_name"],
            api_key=config["api_key"],
            temperature=config["temperature"],
        )


def get_inference_client() -> InferencePort:
    """Helper for functional injection."""
    return InferenceProvider.get_inference_port()


def get_chat_agent() -> ChatAgentPort:
    """Helper for functional injection."""
    return InferenceProvider.get_chat_agent_port()
