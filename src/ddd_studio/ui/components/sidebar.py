import streamlit as st
from infra.inference_provider import InferenceProvider
from models.domain_analysis import DomainAnalysis
from ui.utils.storage import clear_all_data


def _get_draft_service():
    """Build or retrieve the DraftService singleton from session state."""
    if "_draft_service" not in st.session_state:
        from infra.adapters.file_draft_repository import FileDraftRepository
        from services.draft_service import DraftService

        repo = FileDraftRepository()
        st.session_state["_draft_service"] = DraftService(repository=repo)
    return st.session_state["_draft_service"]


def render_sidebar():
    """Renderiza la barra lateral con instrucciones y controles de sesión."""
    with st.sidebar:
        st.header("🧠 Domain Modeler AI")
        _maybe_show_clear_result()
        _render_ai_config()
        _render_history_section()
        st.markdown("""
        Esta herramienta utiliza **GenAI** para convertir Transcripciónes de talleres (Event Storming) en modelos de dominio DDD.

        **Pasos:**
        1. 🎤 Sube un audio o pega texto.
        2. 📝 (Opcional) Sube un PDF con reglas de negocio.
        3. 🚀 Genera el modelo.
        4. ✏️ Edita y valida los resultados.
        """)

        st.divider()
        if st.button("🗑️ Limpiar Todo", width="stretch"):
            st.session_state["_confirm_clear_all"] = True

        if st.session_state.get("_confirm_clear_all"):
            _render_clear_all_confirmation()

        st.caption("v2.1 - Powered by Raul A.")


def _maybe_show_clear_result():
    """Show a one-shot success toast after a full clear."""
    counts = st.session_state.pop("_clear_result", None)
    if not counts:
        return
    parts = [
        f"static: {counts.get('static', 0)}",
        f"cache: {counts.get('cache', 0)}",
        f"drafts: {counts.get('drafts', 0)}",
    ]
    if counts.get("llm_config"):
        parts.append("llm_config: 1")
    st.success("🧹 Limpieza completada — " + ", ".join(parts))


@st.dialog("Confirmar Limpieza Total")
def _render_clear_all_confirmation():
    """Confirm full wipe: session, cache, drafts, static JSON, optionally API key."""
    st.warning(
        "Esto borrará: resultado actual, caché (`.cache/`), historial de drafts "
        "(`drafts/`) y el JSON estático. La acción **no se puede deshacer**."
    )
    wipe_config = st.checkbox(
        "También borrar configuración LLM (API Key y modelo)",
        value=False,
        help="Si lo marcas, tendrás que reingresar tu Google API Key.",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Sí, limpiar todo", type="primary", width="stretch"):
            counts = clear_all_data(include_llm_config=wipe_config)
            st.session_state.clear()
            st.session_state["_clear_result"] = counts
            st.rerun()
    with col2:
        if st.button("Cancelar", width="stretch"):
            st.session_state.pop("_confirm_clear_all", None)
            st.rerun()


def _render_history_section():
    """Render the Generation History expander in the sidebar."""
    draft_service = _get_draft_service()

    drafts = draft_service.list_drafts()

    with st.expander("📜 Generation History", expanded=bool(drafts)):
        if not drafts:
            st.info("No generations saved yet. Run a generation to see your history here.")
            return

        for entry in drafts:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(
                    f"**{entry.project_name}**\n\n{entry.created_at[:16].replace('T', ' ')} — {entry.summary.label}"
                )
                if st.button("👁️ Preview", key=f"preview_{entry.id}", width="stretch"):
                    _load_draft_into_session(draft_service, entry.id, entry.generation_id)

            with col2:
                if st.button("🗑️", key=f"delete_{entry.id}"):
                    st.session_state["_confirm_delete_draft_id"] = entry.id

    # Handle delete confirmation dialog
    confirm_id = st.session_state.get("_confirm_delete_draft_id")
    if confirm_id:
        _render_delete_confirmation(draft_service, confirm_id)


def _load_draft_into_session(draft_service, draft_id: str, generation_id: str):
    """Load a draft snapshot into session state as the active model."""
    draft = draft_service.get_draft(draft_id)
    if not draft:
        st.error("Draft not found.")
        return

    try:
        analysis_obj = DomainAnalysis.model_validate(draft.snapshot)
    except Exception as e:
        st.error(f"Failed to load draft: {e}")
        return

    st.session_state.analysis_result = {
        "analysis": analysis_obj,
        "transcript": draft.snapshot.get("transcript", ""),
        "logs": f"Loaded from draft {draft_id[:8]}…",
    }
    st.session_state.current_generation_id = generation_id
    st.session_state.pop("_preview_draft_id", None)
    st.rerun()


@st.dialog("Confirm Deletion")
def _render_delete_confirmation(draft_service, draft_id):
    """Show a confirmation dialog before deleting a draft."""
    st.warning("Are you sure you want to permanently delete this draft?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, delete", type="primary", width="stretch"):
            draft_service.delete_draft(draft_id)
            # Clear preview if the deleted draft was being previewed
            if st.session_state.get("_preview_draft_id") == draft_id:
                st.session_state.pop("_preview_draft_id", None)
            st.session_state.pop("_confirm_delete_draft_id", None)
            st.rerun()
    with col2:
        if st.button("Cancel", width="stretch"):
            st.session_state.pop("_confirm_delete_draft_id", None)
            st.rerun()


def _render_ai_config():
    """Render the AI engine configuration in the sidebar."""
    config = InferenceProvider.get_config()

    with st.expander("⚙️ Configuración IA", expanded=False):
        st.info("Configura el motor de IA para esta sesión.")

        available_models = [
            "gemini-3-flash-preview",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ]
        current_model = config.get("model_name", "gemini-2.5-pro")
        default_index = available_models.index(current_model) if current_model in available_models else 0
        model_name = st.selectbox(
            "Gemini Model",
            options=available_models,
            index=default_index,
        )

        api_key = st.text_input(
            "Google API Key",
            value=config.get("api_key", ""),
            type="password",
            help="Tu clave de API de Google AI Studio",
        )

        st.caption("🪓 Decoding: greedy fijo (temperature=0.0, top_k=1). ")

        if st.button("💾 Guardar Configuración", width="stretch"):
            cfg = {
                "model_name": model_name,
                "api_key": api_key,
            }
            st.session_state.llm_config = cfg
            from ui.utils.storage import save_llm_config

            save_llm_config(cfg)
            st.success("Configuración guardada y persistida.")

        if st.button("🔌 Probar Conexión", width="stretch"):
            if not api_key:
                st.error("Por favor, ingresa una API Key.")
            else:
                try:
                    with st.spinner("Validando..."):
                        inference = InferenceProvider.get_inference_port()
                        result = inference.invoke_text("Dí 'Conexión Exitosa' en 2 palabras.")
                        st.success(f"¡Listo! {result}")
                except Exception as e:
                    st.error(f"Error de conexión: {str(e)}")
