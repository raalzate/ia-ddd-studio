import streamlit as st

from models.domain_analysis import DomainAnalysis
from ui.analyze import analyze_domain_data


def render_stats_tab(analysis_obj: DomainAnalysis):
    """Renderiza estadísticas detalladas en una pestaña."""
    import pandas as pd

    dfs = analyze_domain_data(analysis_obj)

    st.subheader("📊 Detalles Estadísticos")
    col1, col2 = st.columns(2)
    with col1:
        if "node_types_df" in dfs and not dfs["node_types_df"].empty:
            node_types_df = dfs["node_types_df"].copy()

            # "Agregado" nodes appear at big_picture level AND inside each
            # process-level graph. Only the big_picture instances represent
            # real domain modules; the internal ones are sub-elements.
            # Override the count with the number of GrafoPorAgregado objects
            # so the table matches the actual module count.
            n_modules = len(analysis_obj.agregados)
            mask = node_types_df["tipo_elemento"] == "Agregado"
            if mask.any():
                node_types_df.loc[mask, "count"] = n_modules
            else:
                agg_row = pd.DataFrame([{"tipo_elemento": "Agregado", "count": n_modules}])
                node_types_df = pd.concat([node_types_df, agg_row], ignore_index=True)

            # Append inter-aggregate policies (edges, not nodes) as a row.
            n_policies = len(analysis_obj.politicas_inter_agregados)
            if n_policies > 0:
                policy_row = pd.DataFrame([{"tipo_elemento": "Política Inter-Agregado", "count": n_policies}])
                node_types_df = pd.concat([node_types_df, policy_row], ignore_index=True)

            # Re-sort descending by count for readability
            node_types_df = node_types_df.sort_values("count", ascending=False).reset_index(drop=True)

            st.markdown("**Distribución de Elementos**")
            st.dataframe(node_types_df, hide_index=True, use_container_width=True)
    with col2:
        if "technologies_df" in dfs and not dfs["technologies_df"].empty:
            st.markdown("**Tecnologías Identificadas**")
            st.dataframe(dfs["technologies_df"], hide_index=True, use_container_width=True)
