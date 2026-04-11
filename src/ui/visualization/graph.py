"""Domain graph visualization — professional Event Storming diagrams.

Renders DomainAnalysis models as Event Storming flow diagrams with
canonical sticky-note colours, HTML-rich labels, semantic edge styling,
and interactive pan/zoom SVG embedding.
"""

import html as _html

import graphviz
import streamlit as st
import streamlit.components.v1 as components

from models.domain_analysis import DomainAnalysis

# ── Event Storming canonical palette ─────────────────────────────────────
# Faithful to the original ES colour coding by Alberto Brandolini.
# Each entry: (fill, font_color, shape, graphviz_style, border_color)

_STYLE = {
    "Actor": ("#FFF9C4", "#5D4037", "box", "filled,rounded,bold", "#F9A825"),
    "Sistema Externo": ("#ECEFF1", "#37474F", "component", "filled", "#78909C"),
    "Comando": ("#BBDEFB", "#0D47A1", "box", "filled,rounded", "#42A5F5"),
    "Agregado": ("#FFF3E0", "#E65100", "box3d", "filled,bold", "#FB8C00"),
    "Entidad Raíz": ("#FFF3E0", "#E65100", "box", "filled", "#FB8C00"),
    "Evento": ("#FFE0B2", "#BF360C", "box", "filled,rounded,bold", "#FF8C00"),
    "Política": ("#E8EAF6", "#283593", "box", "filled,rounded", "#7C4DFF"),
    "Regla de Negocio": ("#EDE7F6", "#4A148C", "box", "filled,rounded", "#9C27B0"),
    "Read Model": ("#E8F5E9", "#1B5E20", "box", "filled,rounded", "#43A047"),
    "Vista": ("#E8F5E9", "#1B5E20", "box", "filled,rounded", "#43A047"),
    "Proyección": ("#E8F5E9", "#1B5E20", "box", "filled,rounded", "#43A047"),
    "Política de UI": ("#F3E5F5", "#6A1B9A", "box", "filled,rounded", "#AB47BC"),
    "Hotspot": ("#FFEBEE", "#B71C1C", "octagon", "filled,bold", "#EF5350"),
}

_STATE_BADGE = {
    "nuevo": " [NEW]",
    "modificado": " [MOD]",
    "eliminado": " [DEL]",
    "existente": "",
}

_ICONS = {
    "Actor": "&#x1F464;",  # 👤
    "Sistema Externo": "&#9881;",  # ⚙
    "Comando": "&#9654;",  # ▶
    "Agregado": "&#x1F4E6;",  # 📦
    "Entidad Raíz": "&#x1F4E6;",  # 📦
    "Evento": "&#9889;",  # ⚡
    "Política": "&#x1F6E1;",  # 🛡
    "Regla de Negocio": "&#x1F6E1;",  # 🛡
    "Read Model": "&#x1F441;",  # 👁
    "Vista": "&#x1F441;",  # 👁
    "Proyección": "&#x1F441;",  # 👁
    "Política de UI": "&#x1F5A5;",  # 🖥
    "Hotspot": "&#x1F525;",  # 🔥
}

# ── Edge semantic colours ────────────────────────────────────────────────

_EDGE_KEYWORDS = {
    # keyword substring  → (colour, style, penwidth)
    "dispara": ("#42A5F5", "solid", "1.4"),  # command trigger
    "ejecuta": ("#42A5F5", "solid", "1.4"),
    "produce": ("#FF8C00", "solid", "1.4"),  # event emission
    "resulta": ("#FF8C00", "solid", "1.4"),
    "emite": ("#FF8C00", "dashed", "1.4"),
    "proyecta": ("#43A047", "dashed", "1.2"),  # read-model projection
    "almacena": ("#43A047", "dashed", "1.2"),
    "expone": ("#43A047", "dotted", "1.0"),
    "presenta": ("#78909C", "solid", "1.0"),  # UI / actor
    "depende": ("#EF5350", "dotted", "1.2"),  # hotspot / risk
    "afectado": ("#EF5350", "dotted", "1.2"),
    "registra": ("#78909C", "dashed", "1.0"),  # external writes
    "consulta": ("#78909C", "dashed", "1.0"),
    "gestiona": ("#78909C", "solid", "1.2"),
    "genera": ("#78909C", "solid", "1.2"),
    "activa": ("#7C4DFF", "bold", "2.0"),  # policy trigger
    "proporciona": ("#78909C", "dashed", "1.0"),
    "entrega": ("#78909C", "solid", "1.0"),
    "envía": ("#78909C", "dashed", "1.0"),
    "inicia": ("#42A5F5", "solid", "1.4"),
    "orquesta": ("#42A5F5", "solid", "1.4"),
}

_DEFAULT_EDGE = ("#90A4AE", "solid", "1.0")


def _edge_style(description: str):
    """Pick colour & style based on edge description keywords."""
    desc_lower = description.lower()
    for kw, style in _EDGE_KEYWORDS.items():
        if kw in desc_lower:
            return style
    return _DEFAULT_EDGE


# ── Node rendering ───────────────────────────────────────────────────────


def _html_label(tipo: str, nombre: str, badge: str = "") -> str:
    """Build a rich HTML-like Graphviz label with type header + name."""
    icon = _ICONS.get(tipo, "")
    safe_name = _html.escape(nombre)
    safe_tipo = _html.escape(tipo)
    safe_badge = _html.escape(badge) if badge else ""

    return (
        f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2" CELLPADDING="3">'
        f'<TR><TD><FONT POINT-SIZE="8" COLOR="#888888">{icon} {safe_tipo}{safe_badge}</FONT></TD></TR>'
        f'<TR><TD><B><FONT POINT-SIZE="11">{safe_name}</FONT></B></TD></TR>'
        f"</TABLE>>"
    )


def _add_node(g, node, *, show_state=True, compact=False):
    """Add a NodoGrafo to a graphviz graph/subgraph."""
    fill, font_c, shape, style, border = _STYLE.get(node.tipo_elemento, ("#F5F5F5", "#333", "box", "filled", "#BDBDBD"))
    badge = _STATE_BADGE.get(node.estado_comparativo, "") if show_state else ""

    if compact:
        safe = _html.escape(f"{node.nombre}")
        label = f'<<B><FONT POINT-SIZE="10">{safe}</FONT></B>>'
    else:
        label = _html_label(node.tipo_elemento, node.nombre, badge)

    tooltip = f"{node.nombre} ({node.tipo_elemento})\n{node.descripcion}"

    g.node(
        node.id,
        label=label,
        shape=shape,
        style=style,
        fillcolor=fill,
        fontcolor=font_c,
        fontname="Helvetica Neue, Helvetica, Arial, sans-serif",
        color=border,
        penwidth="1.5",
        tooltip=tooltip,
        margin="0.20,0.12",
    )


def _add_edge(g, edge, *, color=None, style=None, penwidth=None, is_policy=False):
    """Add an AristaGrafo with semantic colouring."""
    auto_c, auto_s, auto_pw = _edge_style(edge.descripcion)
    c = color or auto_c
    s = style or auto_s
    pw = penwidth or auto_pw

    if is_policy:
        c, s, pw = "#7C4DFF", "bold", "2.2"

    desc = edge.descripcion
    label = desc if len(desc) < 40 else desc[:37] + "..."
    font_c = "#555555" if not is_policy else "#5E35B1"

    g.edge(
        edge.fuente,
        edge.destino,
        label=f"  {label}  ",
        color=c,
        fontcolor=font_c,
        fontname="Helvetica Neue, Helvetica, Arial, sans-serif",
        fontsize="8",
        style=s,
        penwidth=pw,
        arrowsize="0.8",
    )


# ── Graph factories ──────────────────────────────────────────────────────


def _flow_graph(*, rankdir="LR", title="", fontsize="16"):
    """Digraph optimised for sequential Event Storming flow (dot engine)."""
    g = graphviz.Digraph(engine="dot", format="svg")
    g.attr(
        rankdir=rankdir,
        bgcolor="transparent",
        label=f"<<B><FONT POINT-SIZE='{fontsize}'>{_html.escape(title)}</FONT></B>>",
        labelloc="t",
        labeljust="l",
        fontname="Helvetica Neue, Helvetica, Arial, sans-serif",
        pad="0.6",
        nodesep="0.7",
        ranksep="1.0",
        splines="ortho",
        concentrate="false",
    )
    g.attr("node", fontname="Helvetica Neue, Helvetica, Arial, sans-serif", fontsize="10")
    g.attr("edge", fontname="Helvetica Neue, Helvetica, Arial, sans-serif", fontsize="8")
    return g


# ── Flow rank enforcement ────────────────────────────────────────────────

_RANK_ORDER = {
    "Actor": 0,
    "Sistema Externo": 1,
    "Comando": 2,
    "Agregado": 3,
    "Entidad Raíz": 3,
    "Evento": 4,
    "Política": 5,
    "Regla de Negocio": 5,
    "Read Model": 6,
    "Vista": 6,
    "Proyección": 6,
    "Política de UI": 6,
    "Hotspot": 4,
}


def _enforce_ranks(g, nodes):
    """Group nodes by rank to enforce Event Storming flow order."""
    by_rank: dict[int, list[str]] = {}
    for n in nodes:
        rank = _RANK_ORDER.get(n.tipo_elemento, 4)
        by_rank.setdefault(rank, []).append(n.id)

    for rank in sorted(by_rank):
        with g.subgraph() as s:
            s.attr(rank="same")
            for nid in by_rank[rank]:
                s.node(nid)


# ── View builders ────────────────────────────────────────────────────────


def _build_big_picture(analysis_obj: DomainAnalysis):
    """Big Picture — vista macro del problema de dominio."""
    g = _flow_graph(title="Big Picture — Vista Macro del Dominio")
    g.attr(splines="true")

    for n in analysis_obj.big_picture.nodos:
        _add_node(g, n)

    _enforce_ranks(g, analysis_obj.big_picture.nodos)

    for e in analysis_obj.big_picture.aristas:
        _add_edge(g, e)

    # Show read models connected to their source events (if projections map to BP nodes)
    bp_ids = {n.id for n in analysis_obj.big_picture.nodos}
    for rm in analysis_obj.read_models:
        rm_id = f"bp_rm_{rm.nombre}"
        g.node(
            rm_id,
            label=_html_label("Read Model", rm.nombre),
            shape="box",
            style="filled,rounded",
            fillcolor="#E8F5E9",
            fontcolor="#1B5E20",
            color="#43A047",
            penwidth="1.5",
            fontname="Helvetica Neue, Helvetica, Arial, sans-serif",
            tooltip=rm.descripcion or rm.nombre,
            margin="0.20,0.12",
        )
        for ev_id in rm.proyecta:
            if ev_id in bp_ids:
                g.edge(
                    ev_id,
                    rm_id,
                    label="  proyecta  ",
                    style="dashed",
                    color="#43A047",
                    fontcolor="#2E7D32",
                    fontsize="8",
                    arrowsize="0.7",
                )

    return g


def _build_aggregate(agg, analysis_obj: DomainAnalysis | None = None):
    """Single aggregate — detailed process-level Event Storming."""
    g = _flow_graph(title=f"Process Level — {agg.nombre_agregado}  (raiz: {agg.entidad_raiz})")

    for n in agg.nodos:
        _add_node(g, n)

    _enforce_ranks(g, agg.nodos)

    for e in agg.aristas:
        _add_edge(g, e)

    # Include read models that project events from this aggregate
    if analysis_obj:
        agg_node_ids = {n.id for n in agg.nodos}
        for rm in analysis_obj.read_models:
            connected_evs = [ev for ev in rm.proyecta if ev in agg_node_ids]
            if connected_evs:
                rm_id = f"agg_rm_{rm.nombre}"
                g.node(
                    rm_id,
                    label=_html_label("Read Model", rm.nombre),
                    shape="box",
                    style="filled,rounded",
                    fillcolor="#E8F5E9",
                    fontcolor="#1B5E20",
                    color="#43A047",
                    penwidth="1.5",
                    fontname="Helvetica Neue, Helvetica, Arial, sans-serif",
                    tooltip=rm.descripcion or rm.nombre,
                    margin="0.20,0.12",
                )
                for ev_id in connected_evs:
                    g.edge(
                        ev_id,
                        rm_id,
                        label="  proyecta  ",
                        style="dashed",
                        color="#43A047",
                        fontcolor="#2E7D32",
                        fontsize="8",
                        arrowsize="0.7",
                    )

    return g


def _build_all_aggregates(analysis_obj: DomainAnalysis):
    """Todos los agregados con sus flujos internos, modelos de lectura y politicas."""
    g = _flow_graph(title="Process Level — Todos los Agregados")

    for agg in analysis_obj.agregados:
        with g.subgraph(name=f"cluster_{agg.nombre_agregado}") as sub:
            sub.attr(
                label=f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">'
                f'<TR><TD><B><FONT POINT-SIZE="13" COLOR="#E65100">'
                f"&#x1F4E6; {_html.escape(agg.nombre_agregado)}</FONT></B></TD></TR>"
                f'<TR><TD><FONT POINT-SIZE="9" COLOR="#999999">'
                f"Raiz: {_html.escape(agg.entidad_raiz)}</FONT></TD></TR></TABLE>>",
                style="dashed,rounded",
                color="#FB8C00",
                bgcolor="#FFFAF3",
                fontname="Helvetica Neue, Helvetica, Arial, sans-serif",
                penwidth="2.5",
                margin="24",
            )
            for n in agg.nodos:
                _add_node(sub, n)

        # Edges go to the parent graph so inter-cluster edges render
        for e in agg.aristas:
            _add_edge(g, e)

    # Read models as a cluster
    if analysis_obj.read_models:
        all_agg_ids = set()
        for agg in analysis_obj.agregados:
            all_agg_ids.update(n.id for n in agg.nodos)

        with g.subgraph(name="cluster_read_models") as rm_sub:
            rm_sub.attr(
                label='<<B><FONT POINT-SIZE="12" COLOR="#1B5E20">&#x1F441; Modelos de Lectura</FONT></B>>',
                style="dashed,rounded",
                color="#43A047",
                bgcolor="#F1F8E9",
                fontname="Helvetica Neue, Helvetica, Arial, sans-serif",
                penwidth="2",
                margin="20",
            )
            for rm in analysis_obj.read_models:
                rm_id = f"rm_{rm.nombre}"
                rm_sub.node(
                    rm_id,
                    label=_html_label("Read Model", rm.nombre),
                    shape="box",
                    style="filled,rounded",
                    fillcolor="#E8F5E9",
                    fontcolor="#1B5E20",
                    color="#43A047",
                    penwidth="1.5",
                    fontname="Helvetica Neue, Helvetica, Arial, sans-serif",
                    tooltip=f"{rm.nombre}\n{rm.descripcion or ''}",
                    margin="0.20,0.12",
                )

            for rm in analysis_obj.read_models:
                rm_id = f"rm_{rm.nombre}"
                for ev_id in rm.proyecta:
                    if ev_id in all_agg_ids:
                        g.edge(
                            ev_id,
                            rm_id,
                            label="  proyecta  ",
                            style="dashed",
                            color="#43A047",
                            fontcolor="#2E7D32",
                            fontsize="8",
                            arrowsize="0.7",
                        )

    # Inter-aggregate policies
    for p in analysis_obj.politicas_inter_agregados:
        _add_edge(g, p, is_policy=True)

    return g


def _build_read_models(analysis_obj: DomainAnalysis):
    """Vista de Modelos de Lectura — que informacion necesitan los actores."""
    g = _flow_graph(title="Modelos de Lectura — Vistas de Informacion")
    g.attr(splines="true", ranksep="1.5")

    added = set()
    for rm in analysis_obj.read_models:
        rm_id = f"rm_{rm.nombre}"
        techs = ", ".join(rm.tecnologias or [])
        desc_safe = _html.escape(rm.descripcion or "")
        tech_row = (
            f'<TR><TD><FONT POINT-SIZE="7" COLOR="#999999">{_html.escape(techs)}</FONT></TD></TR>' if techs else ""
        )

        g.node(
            rm_id,
            label=f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2" CELLPADDING="3">'
            f'<TR><TD><FONT POINT-SIZE="8" COLOR="#888888">&#x1F441; Read Model</FONT></TD></TR>'
            f'<TR><TD><B><FONT POINT-SIZE="11">{_html.escape(rm.nombre)}</FONT></B></TD></TR>'
            f'<TR><TD><FONT POINT-SIZE="8" COLOR="#666666">{desc_safe}</FONT></TD></TR>'
            f"{tech_row}</TABLE>>",
            shape="box",
            style="filled,rounded",
            fillcolor="#E8F5E9",
            fontcolor="#1B5E20",
            color="#43A047",
            penwidth="2",
            fontname="Helvetica Neue, Helvetica, Arial, sans-serif",
            tooltip=rm.descripcion or rm.nombre,
            margin="0.20,0.12",
        )

        for ev_id in rm.proyecta:
            if ev_id not in added:
                # Find the event node in the model to get its description
                ev_desc = ev_id
                for agg in analysis_obj.agregados:
                    for n in agg.nodos:
                        if n.id == ev_id:
                            ev_desc = n.nombre
                            break

                g.node(
                    ev_id,
                    label=_html_label("Evento", ev_desc),
                    shape="box",
                    style="filled,rounded,bold",
                    fillcolor="#FFE0B2",
                    fontcolor="#BF360C",
                    color="#FF8C00",
                    penwidth="1.5",
                    fontname="Helvetica Neue, Helvetica, Arial, sans-serif",
                    margin="0.20,0.12",
                )
                added.add(ev_id)

            g.edge(
                ev_id,
                rm_id,
                label="  proyecta  ",
                style="dashed",
                color="#43A047",
                fontcolor="#2E7D32",
                fontname="Helvetica Neue, Helvetica, Arial, sans-serif",
                fontsize="9",
                arrowsize="0.8",
                penwidth="1.5",
            )

    return g


def _build_user_journey(analysis_obj: DomainAnalysis):
    """Event Storming completo — mapa del problema de dominio."""
    g = _flow_graph(title="Event Storming — Mapa del Problema de Dominio")
    g.attr(ranksep="1.2", nodesep="0.6", splines="true")

    added_ids = set()

    # ── Big Picture nodes (outside clusters) ──
    for n in analysis_obj.big_picture.nodos:
        # Skip Agregado nodes in BP — they'll be represented by clusters
        if n.tipo_elemento == "Agregado":
            continue
        _add_node(g, n)
        added_ids.add(n.id)

    # ── Agregados como clusters ──
    for agg in analysis_obj.agregados:
        with g.subgraph(name=f"cluster_{agg.nombre_agregado}") as sub:
            sub.attr(
                label=f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">'
                f'<TR><TD><B><FONT POINT-SIZE="13" COLOR="#E65100">'
                f"&#x1F4E6; {_html.escape(agg.nombre_agregado)}</FONT></B></TD></TR>"
                f'<TR><TD><FONT POINT-SIZE="9" COLOR="#999999">'
                f"Raiz: {_html.escape(agg.entidad_raiz)}</FONT></TD></TR></TABLE>>",
                style="dashed,rounded",
                color="#FB8C00",
                bgcolor="#FFFAF3",
                fontname="Helvetica Neue, Helvetica, Arial, sans-serif",
                penwidth="2.5",
                margin="24",
            )
            for n in agg.nodos:
                if n.id not in added_ids:
                    _add_node(sub, n)
                    added_ids.add(n.id)

        for e in agg.aristas:
            _add_edge(g, e)

    # ── Big Picture edges — re-route Agregado references to cluster nodes ──
    agg_bp_ids = {n.id for n in analysis_obj.big_picture.nodos if n.tipo_elemento == "Agregado"}
    # Map BP aggregate ID → set of entry-point node IDs inside the cluster
    agg_entry_map: dict[str, str | None] = {}
    for bp_node in analysis_obj.big_picture.nodos:
        if bp_node.tipo_elemento != "Agregado":
            continue
        # Find the matching GrafoPorAgregado
        for agg in analysis_obj.agregados:
            if (
                bp_node.nombre in (agg.nombre_agregado, agg.entidad_raiz)
                or bp_node.id.replace("BP_", "") in agg.nombre_agregado
            ):
                # Pick the first command or first node as entry
                entry = None
                for n in agg.nodos:
                    if n.tipo_elemento == "Comando":
                        entry = n.id
                        break
                if not entry and agg.nodos:
                    entry = agg.nodos[0].id
                agg_entry_map[bp_node.id] = entry
                break

    for e in analysis_obj.big_picture.aristas:
        src = e.fuente
        dst = e.destino
        # Skip edges between two BP aggregates (clusters handle that)
        if src in agg_bp_ids and dst in agg_bp_ids:
            continue
        # Re-route to cluster entry points
        if src in agg_bp_ids:
            src = agg_entry_map.get(src, src)
        if dst in agg_bp_ids:
            dst = agg_entry_map.get(dst, dst)
        if src and dst and src in added_ids and dst in added_ids:
            desc = e.descripcion
            ec, es, ep = _edge_style(desc)
            label = desc if len(desc) < 40 else desc[:37] + "..."
            g.edge(
                src,
                dst,
                label=f"  {label}  ",
                color=ec,
                style=es,
                penwidth=ep,
                fontcolor="#555555",
                fontsize="8",
                arrowsize="0.8",
            )

    # ── Read Models cluster ──
    if analysis_obj.read_models:
        with g.subgraph(name="cluster_read_models") as rm_sub:
            rm_sub.attr(
                label='<<B><FONT POINT-SIZE="12" COLOR="#1B5E20">&#x1F441; Modelos de Lectura</FONT></B>>',
                style="dashed,rounded",
                color="#43A047",
                bgcolor="#F1F8E9",
                fontname="Helvetica Neue, Helvetica, Arial, sans-serif",
                penwidth="2",
                margin="20",
            )
            for rm in analysis_obj.read_models:
                rm_id = f"rm_{rm.nombre}"
                rm_sub.node(
                    rm_id,
                    label=_html_label("Read Model", rm.nombre),
                    shape="box",
                    style="filled,rounded",
                    fillcolor="#E8F5E9",
                    fontcolor="#1B5E20",
                    color="#43A047",
                    penwidth="1.5",
                    fontname="Helvetica Neue, Helvetica, Arial, sans-serif",
                    tooltip=f"{rm.nombre}\n{rm.descripcion or ''}",
                    margin="0.20,0.12",
                )
                added_ids.add(rm_id)

        for rm in analysis_obj.read_models:
            rm_id = f"rm_{rm.nombre}"
            for ev_id in rm.proyecta:
                if ev_id in added_ids:
                    g.edge(
                        ev_id,
                        rm_id,
                        label="  proyecta  ",
                        style="dashed",
                        color="#43A047",
                        fontcolor="#2E7D32",
                        fontsize="8",
                        arrowsize="0.7",
                    )

    # ── Inter-aggregate policies ──
    for p in analysis_obj.politicas_inter_agregados:
        if p.fuente in added_ids and p.destino in added_ids:
            _add_edge(g, p, is_policy=True)

    return g


# ── Legend ────────────────────────────────────────────────────────────────


def _render_legend():
    """Render a professional Event Storming legend."""
    st.markdown("---")
    st.markdown("#### Leyenda ES")

    st.markdown(
        """
        <style>
        .es-legend { display: flex; flex-direction: column; gap: 6px; }
        .es-item {
            display: flex; align-items: center; gap: 10px;
            font-size: 0.82rem; line-height: 1.2;
        }
        .es-swatch {
            min-width: 22px; height: 18px; border-radius: 4px;
            border: 1.5px solid rgba(0,0,0,0.15);
        }
        .es-label { color: #666; }
        .es-flow {
            font-size: 0.75rem; color: #888; margin-top: 8px;
            line-height: 1.5; border-left: 2px solid #ddd; padding-left: 8px;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    items = [
        ("Actor", "#FFF9C4", "#F9A825"),
        ("Comando", "#BBDEFB", "#42A5F5"),
        ("Agregado", "#FFF3E0", "#FB8C00"),
        ("Evento", "#FFE0B2", "#FF8C00"),
        ("Politica", "#E8EAF6", "#7C4DFF"),
        ("Modelo Lectura", "#E8F5E9", "#43A047"),
        ("Hotspot", "#FFEBEE", "#EF5350"),
        ("Sistema Ext.", "#ECEFF1", "#78909C"),
    ]

    html_items = []
    for label, bg, border in items:
        html_items.append(
            f'<div class="es-item">'
            f'<div class="es-swatch" style="background:{bg};border-color:{border};"></div>'
            f'<div class="es-label">{label}</div>'
            f"</div>"
        )

    st.markdown(f'<div class="es-legend">{"".join(html_items)}</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="es-flow">'
        "<b>Flujo ES:</b><br>"
        "Actor &rarr; Comando &rarr; Agregado &rarr; Evento &rarr; Politica &rarr; Modelo de Lectura"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown(
        '<div style="font-size:0.75rem;color:#999;">'
        "<b>Aristas:</b><br>"
        '<span style="color:#42A5F5;">&#9644;</span> dispara/ejecuta &nbsp; '
        '<span style="color:#FF8C00;">&#9644;</span> produce &nbsp; '
        '<span style="color:#43A047;">- - -</span> proyecta<br>'
        '<span style="color:#7C4DFF;">&#9644;&#9644;</span> politica &nbsp; '
        '<span style="color:#EF5350;">&#183;&#183;&#183;</span> depende/riesgo'
        "</div>",
        unsafe_allow_html=True,
    )


# ── Main entry point ─────────────────────────────────────────────────────


def render_graph_tab(analysis_obj: DomainAnalysis):
    """Render domain graph as an Event Storming diagram."""

    c1, c2 = st.columns([5, 1])

    with c2:
        st.markdown("### Config")
        view = st.selectbox(
            "Vista",
            [
                "Event Storming (Full)",
                "Big Picture",
                "Process Level (todos)",
                "Process Level (detalle)",
                "Modelos de Lectura",
            ],
        )

        use_tb = st.toggle("Layout vertical (TB)", value=True)
        _render_legend()

    with c1:
        g = None

        if view == "Big Picture":
            g = _build_big_picture(analysis_obj)
        elif view == "Process Level (todos)":
            g = _build_all_aggregates(analysis_obj)
        elif view == "Process Level (detalle)":
            agg_names = [a.nombre_agregado for a in analysis_obj.agregados]
            if not agg_names:
                st.warning("No hay agregados en este analisis.")
            else:
                agg_name = st.selectbox("Agregado:", agg_names, key="sel_agg_gv")
                agg = next(a for a in analysis_obj.agregados if a.nombre_agregado == agg_name)
                g = _build_aggregate(agg, analysis_obj)
        elif view == "Modelos de Lectura":
            g = _build_read_models(analysis_obj)
        elif view == "Event Storming (Full)":
            g = _build_user_journey(analysis_obj)

        if g is not None:
            if use_tb:
                g.attr(rankdir="TB")

            if st.button("Ver MODO MAXIMIZADO", use_container_width=False):
                _show_fullscreen_dialog(g)

            _render_zoomable_graph(g)
        else:
            st.info("No hay datos para visualizar.")


@st.dialog("Visor Ampliado", width="large")
def _show_fullscreen_dialog(g):
    _render_zoomable_graph(g, height=750)


def _render_zoomable_graph(g, height=850):
    """Render a Graphviz graph as an interactive SVG with pan & zoom."""
    svg_bytes = g.pipe(format="svg")
    svg_str = svg_bytes.decode("utf-8")
    if svg_str.startswith("<?xml"):
        svg_str = svg_str[svg_str.index("?>") + 2 :].strip()

    viewer_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ overflow: hidden; background: #fafafa; font-family: sans-serif; }}
        #container {{
            width: 100%; height: {height}px;
            overflow: hidden; cursor: grab;
            position: relative; border: 1px solid #e0e0e0;
            border-radius: 12px; background: #fafafa;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
        }}
        #container:active {{ cursor: grabbing; }}
        #graph {{
            transform-origin: 0 0;
            position: absolute; top: 0; left: 0;
            will-change: transform;
        }}
        #graph svg {{ display: block; width: auto; height: auto; }}
        #controls {{
            position: absolute; bottom: 16px; right: 16px;
            display: flex; gap: 8px; z-index: 10;
        }}
        #controls button {{
            width: 40px; height: 40px; border-radius: 8px;
            border: 1px solid #ddd; background: white;
            font-size: 20px; cursor: pointer; color: #555;
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            transition: all 0.2s;
        }}
        #controls button:hover {{ background: #f8f8f8; color: #000; border-color: #bbb; }}
        #zoom-level {{
            font-size: 12px; color: #666; line-height: 40px;
            padding: 0 12px; background: white; border-radius: 8px;
            border: 1px solid #ddd; font-weight: bold;
        }}
    </style>
    </head>
    <body>
    <div id="container">
        <div id="graph">{svg_str}</div>
        <div id="controls">
            <span id="zoom-level">80%</span>
            <button onclick="toggleFS()" title="Pantalla Completa">&#x26F6;</button>
            <button onclick="zoomIn()" title="Zoom in">+</button>
            <button onclick="zoomOut()" title="Zoom out">&minus;</button>
            <button onclick="resetView()" title="Fit to view">&#x27F2;</button>
        </div>
    </div>
    <script>
        const container = document.getElementById('container');
        const graph     = document.getElementById('graph');
        const zoomLabel = document.getElementById('zoom-level');

        const MIN_SCALE   = 0.2;
        const MAX_SCALE   = 2.0;
        const DEFAULT_MAX = 0.8;

        let scale = DEFAULT_MAX, panX = 0, panY = 0;
        let dragging = false, startX = 0, startY = 0;

        function toggleFS() {{
            if (!document.fullscreenElement) {{
                container.requestFullscreen().catch(() => {{}});
            }} else {{
                document.exitFullscreen();
            }}
        }}

        function applyTransform() {{
            graph.style.transform = `translate(${{panX}}px, ${{panY}}px) scale(${{scale}})`;
            zoomLabel.textContent = Math.round(scale * 100) + '%';
        }}

        function resetView() {{
            const svg = graph.querySelector('svg');
            if (!svg) return;
            graph.style.transform = 'translate(0px,0px) scale(1)';
            requestAnimationFrame(() => {{
                const sw = svg.scrollWidth  || svg.clientWidth  || svg.getBoundingClientRect().width;
                const sh = svg.scrollHeight || svg.clientHeight || svg.getBoundingClientRect().height;
                if (!sw || !sh) return;
                const cw = container.clientWidth  || 800;
                const ch = container.clientHeight || 600;
                scale = Math.min((cw - 40) / sw, (ch - 40) / sh, DEFAULT_MAX);
                scale = Math.max(scale, MIN_SCALE);
                panX  = (cw - sw * scale) / 2;
                panY  = Math.max((ch - sh * scale) / 2, 20);
                applyTransform();
            }});
        }}

        function zoomIn()  {{ scale = Math.min(scale * 1.25, MAX_SCALE); applyTransform(); }}
        function zoomOut() {{ scale = Math.max(scale / 1.25, MIN_SCALE); applyTransform(); }}

        container.addEventListener('wheel', (e) => {{
            e.preventDefault();
            const rect = container.getBoundingClientRect();
            const mx = e.clientX - rect.left;
            const my = e.clientY - rect.top;
            const oldScale = scale;
            const delta = e.deltaY < 0 ? 1.15 : 1/1.15;
            scale = Math.min(Math.max(scale * delta, MIN_SCALE), MAX_SCALE);
            panX = mx - (mx - panX) * (scale / oldScale);
            panY = my - (my - panY) * (scale / oldScale);
            applyTransform();
        }}, {{ passive: false }});

        container.addEventListener('mousedown', (e) => {{
            if (e.button !== 0) return;
            dragging = true;
            startX = e.clientX - panX;
            startY = e.clientY - panY;
            container.style.cursor = 'grabbing';
        }});
        window.addEventListener('mousemove', (e) => {{
            if (!dragging) return;
            panX = e.clientX - startX;
            panY = e.clientY - startY;
            applyTransform();
        }});
        window.addEventListener('mouseup', () => {{
            dragging = false;
            container.style.cursor = 'grab';
        }});

        function scheduleReset() {{ setTimeout(resetView, 150); }}
        if (document.readyState === 'complete') {{ scheduleReset(); }}
        else {{ window.addEventListener('load', scheduleReset); }}
        setTimeout(resetView, 500);
        document.addEventListener('fullscreenchange', () => setTimeout(resetView, 150));
    </script>
    </body>
    </html>
    """
    components.html(viewer_html, height=height + 20, scrolling=False)
