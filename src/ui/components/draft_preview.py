"""DraftPreview — read-only preview of a draft's domain model snapshot.

Renders the snapshot fields in a non-editable format using Streamlit expanders.
"""

from __future__ import annotations

import streamlit as st

from domain.models.draft import Draft


def render_draft_preview(draft: Draft) -> None:
    """Render a read-only preview of a draft's domain model output."""
    snapshot = draft.snapshot
    if not snapshot:
        st.warning("Draft snapshot is empty.")
        return

    st.subheader(f"📋 Draft Preview — {draft.summary.label}")
    st.caption(
        f"Created: {draft.created_at.strftime('%Y-%m-%d %H:%M UTC')} | "
        f"Updated: {draft.updated_at.strftime('%Y-%m-%d %H:%M UTC')}"
    )

    # Project info
    st.markdown(f"**Project:** {snapshot.get('nombre_proyecto', 'N/A')}")
    st.markdown(f"**Version:** {snapshot.get('version', 'N/A')}")

    # Big Picture
    bp = snapshot.get("big_picture", {})
    with st.expander("🌐 Big Picture", expanded=False):
        st.markdown(f"**Description:** {bp.get('descripcion', 'N/A')}")
        nodes = bp.get("nodos", [])
        if nodes:
            st.markdown(f"**Nodes ({len(nodes)}):**")
            for node in nodes:
                st.markdown(
                    f"- `{node.get('tipo_elemento')}` — **{node.get('nombre')}**: {node.get('descripcion', '')}"
                )

    # Aggregates
    aggregates = snapshot.get("agregados", [])
    with st.expander(f"📦 Aggregates ({len(aggregates)})", expanded=False):
        for agg in aggregates:
            st.markdown(f"### {agg.get('nombre_agregado', 'Unknown')}")
            st.markdown(f"Root Entity: `{agg.get('entidad_raiz', 'N/A')}`")
            agg_nodes = agg.get("nodos", [])
            for node in agg_nodes:
                st.markdown(
                    f"- `{node.get('tipo_elemento')}` — **{node.get('nombre')}**: {node.get('descripcion', '')}"
                )

    # Read Models
    read_models = snapshot.get("read_models", [])
    if read_models:
        with st.expander(f"📊 Read Models ({len(read_models)})", expanded=False):
            for rm in read_models:
                st.markdown(f"- **{rm.get('nombre')}**: {rm.get('descripcion', '')}")
