import warnings

import streamlit as st

from config.settings import load_api_key
from models.domain_analysis import DomainAnalysis
from ui.components.input import render_input_tabs
from ui.components.results import render_results_tabs
from ui.components.sidebar import render_sidebar
from ui.utils.storage import STATIC_JSON_PATH, load_static_json

# --- Configuración ---
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")


@st.cache_resource
def _get_inference_port(config_hash: int):
    """Retrieve the inference port, cached by configuration hash."""
    from infra.inference_provider import InferenceProvider

    return InferenceProvider.get_inference_port()


@st.cache_resource
def _build_transcription_adapter():
    """Construct the transcription adapter once.

    Uses FasterWhisperTranscriptionAdapter when WHISPER_MODEL is set,
    otherwise falls back to GoogleTranscriptionAdapter.
    """
    from config.settings import WHISPER_MODEL

    if WHISPER_MODEL:
        from config.settings import TRANSCRIPTION_MAX_BYTES
        from infra.adapters.faster_whisper_transcription import (
            FasterWhisperTranscriptionAdapter,
        )

        return FasterWhisperTranscriptionAdapter(model_name=WHISPER_MODEL, max_bytes=TRANSCRIPTION_MAX_BYTES)

    from infra.adapters.google_transcription import GoogleTranscriptionAdapter

    return GoogleTranscriptionAdapter()


@st.cache_resource
def _build_cache_adapter():
    """Construct the FileCacheAdapter once."""
    from infra.adapters.file_cache import FileCacheAdapter

    return FileCacheAdapter()


@st.cache_resource
def _get_chat_agent_port(config_hash: int):
    """Retrieve the chat agent port, cached by configuration hash."""
    from infra.inference_provider import InferenceProvider

    return InferenceProvider.get_chat_agent_port()


def setup_app():
    """Configura la página y carga el estado inicial."""
    load_api_key()
    st.set_page_config(
        layout="wide",
        page_title="Domain Modeler AI",
        page_icon="🧠",
        initial_sidebar_state="expanded",
    )

    # Construct and store infrastructure adapters in session state
    from infra.inference_provider import InferenceProvider

    config = InferenceProvider.get_config()
    config_hash = hash(frozenset(config.items()))

    # Always get the port (it will be cached based on settings)
    st.session_state["_inference_port"] = _get_inference_port(config_hash)
    st.session_state["_chat_agent_port"] = _get_chat_agent_port(config_hash)

    if "_transcription_port" not in st.session_state:
        st.session_state["_transcription_port"] = _build_transcription_adapter()
        st.session_state["_cache_port"] = _build_cache_adapter()

    # Carga de estado
    if "analysis_result" not in st.session_state:
        loaded = load_static_json()
        if loaded:
            try:
                analysis_obj = DomainAnalysis.model_validate(loaded)
                st.session_state.analysis_result = {
                    "analysis": analysis_obj,
                    "transcript": loaded.get("transcript", ""),
                    "logs": f"Cargado desde {STATIC_JSON_PATH}",
                }
                st.info("📂 Análisis previo cargado automáticamente.")
            except Exception as e:
                st.session_state.analysis_result = {"error": f"Error cargando JSON: {e}"}
        else:
            st.session_state.analysis_result = None
        st.session_state.logs = ""


def run_streamlit_app():
    setup_app()
    render_sidebar()

    # Header Principal
    st.title("Análisis de Dominio Aumentado")

    render_input_tabs()

    if st.session_state.analysis_result:
        render_results_tabs(st.session_state.analysis_result)


if __name__ == "__main__":
    run_streamlit_app()
