import json

import streamlit as st

from models.domain_analysis import DomainAnalysis
from ui.analyze import analyze_domain_data
from ui.components.chat import render_chat_tab
from ui.components.specs import render_specs_tab
from ui.reconstruct_utils import reconstruct_domain_analysis
from ui.utils.storage import save_static_json
from ui.visualization.graph import render_graph_tab
from ui.visualization.stats import render_stats_tab


def _render_summary_metrics(analysis_obj: DomainAnalysis):
    """UX: Muestra métricas clave antes de las tablas detalladas."""
    bp = analysis_obj.big_picture
    # Módulos = cantidad de subdominos GrafoPorAgregado (≠ nodos de tipo "Agregado")
    total_modules = len(analysis_obj.agregados)
    total_rms = len(analysis_obj.read_models)
    # Políticas = aristas inter-agregado (politicas_inter_agregados), no nodos
    total_policies = len(analysis_obj.politicas_inter_agregados)

    st.markdown("### 📊 3. Resumen del Modelo")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Módulos de Dominio", total_modules, help="Subdominos modelados a nivel de proceso (GrafoPorAgregado)")
    c2.metric("Read Models", total_rms, help="Vistas o reportes identificados")
    c3.metric("Nodos Big Picture", len(bp.nodos), help="Total de elementos en la vista global")
    c4.metric("Políticas Inter-Agregado", total_policies, help="Flujos de política que conectan distintos módulos")
    st.divider()


def _render_data_tab(analysis_obj: DomainAnalysis, data: dict):
    """Tab de Edición con mejor jerarquía visual."""
    dfs = analyze_domain_data(analysis_obj)

    st.info(
        "💡 **Tip:** Puedes editar las celdas directamente. Los cambios se guardarán al presionar el botón al final."
    )

    with st.expander("1. Big Picture (Contexto Global)", expanded=True):
        c1, c2 = st.columns(2)
        c1.markdown("#### 🔵 Nodos")
        edited_nodes_bp = c1.data_editor(dfs["nodes_bp_df"], key="edit_nodes_bp", num_rows="dynamic", width="stretch")
        c2.markdown("#### 🔗 Aristas")
        edited_edges_bp = c2.data_editor(dfs["edges_bp_df"], key="edit_edges_bp", num_rows="dynamic", width="stretch")

    with st.expander("2. Detalle por Agregados", expanded=False):
        c1, c2 = st.columns(2)
        c1.markdown("#### 📦 Nodos Internos")
        edited_nodes_agg = c1.data_editor(
            dfs["nodes_agg_df"], key="edit_nodes_agg", num_rows="dynamic", width="stretch"
        )
        c2.markdown("#### 🔗 Flujos Internos")
        edited_edges_agg = c2.data_editor(
            dfs["edges_agg_df"], key="edit_edges_agg", num_rows="dynamic", width="stretch"
        )

    with st.expander("3. Políticas y Read Models", expanded=False):
        st.markdown("#### 📜 Políticas de Negocio")
        edited_policies = st.data_editor(dfs["policies_df"], key="edit_policies", num_rows="dynamic", width="stretch")
        st.markdown("#### 👁️ Read Models (Vistas)")
        edited_rms = st.data_editor(dfs["read_models_df"], key="edit_rms", num_rows="dynamic", width="stretch")

    st.write("")
    if st.button("💾 Guardar y Aplicar Cambios", type="primary", use_container_width=True):
        try:
            modified = reconstruct_domain_analysis(
                data,
                edited_nodes_bp,
                edited_edges_bp,
                edited_nodes_agg,
                edited_edges_agg,
                edited_policies,
                edited_rms,
            )
            validated = DomainAnalysis.model_validate(modified)
            st.session_state.analysis_result["analysis"] = validated

            # Persist the validated version (includes transcript)
            to_save = validated.model_dump()
            to_save["transcript"] = st.session_state.analysis_result.get("transcript", "")
            save_static_json(to_save)

            st.session_state.modified_json = json.dumps(to_save, indent=2, ensure_ascii=False)

            # Clear data_editor cached keys so they re-init from updated model
            for key in [
                "edit_nodes_bp",
                "edit_edges_bp",
                "edit_nodes_agg",
                "edit_edges_agg",
                "edit_policies",
                "edit_rms",
            ]:
                st.session_state.pop(key, None)

            st.toast("✅ Modelo actualizado correctamente", icon="💾")
            st.rerun()
        except Exception as e:
            st.error(f"Error al reconstruir datos: {e}")


def render_results_tabs(result: dict):
    """Muestra resultados con métricas iniciales y tabs ordenados."""
    if not isinstance(result, dict) or result.get("error") or "analysis" not in result:
        st.error(result.get("error", "Error interno."))
        return

    analysis_obj: DomainAnalysis = result["analysis"]
    data = analysis_obj.model_dump()
    data["transcript"] = result.get("transcript", "")

    st.divider()
    _render_summary_metrics(analysis_obj)

    t_chat, t_graph, t_data, t_stats, t_specs, t_raw = st.tabs(
        [
            "Chat IA",
            "🕸️ Visualización",
            "✏️ Datos y Edición",
            "📊 Estadísticas",
            "🚀 DDD",
            " Raw & Logs",
        ]
    )

    with t_chat:
        render_chat_tab(analysis_obj)
    with t_graph:
        render_graph_tab(analysis_obj)
    with t_data:
        _render_data_tab(analysis_obj, data)
    with t_stats:
        render_stats_tab(analysis_obj)
    with t_specs:
        render_specs_tab(analysis_obj, result.get("specs"))
    with t_raw:
        c1, c2 = st.columns(2)
        with c1:
            st.write("JSON Generado")
            st.download_button("⬇️ Descargar JSON", json.dumps(data, indent=2), "domain.json", width="stretch")
            st.json(data, expanded=False)
        with c2:
            st.write("Logs del Proceso")
            st.code(st.session_state.logs, language="log")
