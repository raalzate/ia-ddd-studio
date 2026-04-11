import pandas as pd

from models.domain_analysis import DomainAnalysis


def analyze_domain_data(analysis_obj: DomainAnalysis) -> dict[str, pd.DataFrame]:
    """
    Extrae DataFrames separados para edición:
    Big Picture (BP) y Agregados (AGG), Políticas y Read Models.
    """
    data = analysis_obj.model_dump()
    nodes, edges, policies, read_models = [], [], [], []
    technologies = set()

    # --- 1. Extracción de Nodos y Aristas (Maestros) ---

    # 1.1 Big Picture
    bp = data["big_picture"]
    for node in bp["nodos"]:
        nodes.append(
            {
                "aggregate": "Big Picture",
                "id": node["id"],
                "tipo_elemento": node["tipo_elemento"],
                "nombre": node["nombre"],
                "estado_comparativo": node["estado_comparativo"],
                "tags_tecnologia": ", ".join(node["tags_tecnologia"] or []),
            }
        )
        technologies.update(node["tags_tecnologia"] or [])
    for edge in bp["aristas"]:
        edges.append(
            {
                "aggregate": "Big Picture",
                "fuente": edge["fuente"],
                "destino": edge["destino"],
                "descripcion": edge["descripcion"],
                "estado_comparativo": edge["estado_comparativo"],
            }
        )

    # 1.2 Agregados (Proceso)
    for agg in data["agregados"]:
        agg_name = agg["nombre_agregado"]
        for node in agg["nodos"]:
            node_data = {k: v for k, v in node.items() if k != "nivel"}
            node_data["nivel"] = node.get("nivel", None)

            nodes.append(
                {
                    "aggregate": agg_name,
                    **node_data,
                    "tags_tecnologia": ", ".join(node["tags_tecnologia"] or []),
                }
            )
            technologies.update(node["tags_tecnologia"] or [])
        for edge in agg["aristas"]:
            edges.append({"aggregate": agg_name, **edge})

    # 1.3 Políticas Inter-Agregados
    for p in data["politicas_inter_agregados"]:
        policies.append(p)

    # 1.4 Read Models
    for rm in data["read_models"]:
        read_models.append(
            {
                "nombre": rm["nombre"],
                "descripcion": rm.get("descripcion", "") or "",
                "proyecta": ", ".join(rm["proyecta"]),
                "ui_policies": "; ".join(rm["ui_policies"] or []),
                "tecnologias": ", ".join(rm["tecnologias"] or []),
            }
        )

    # --- 2. Creación de DataFrames Maestros ---
    nodes_df = pd.DataFrame(nodes)
    edges_df = pd.DataFrame(edges)

    # 3. Separar DataFrames por ámbito para Edición
    # Nodos y Aristas de Big Picture (Sin columna 'aggregate' para limpieza visual)
    if "aggregate" in nodes_df.columns:
        nodes_bp_df = nodes_df[nodes_df["aggregate"] == "Big Picture"].drop(columns=["aggregate"], errors="ignore")
        nodes_agg_df = nodes_df[nodes_df["aggregate"] != "Big Picture"]
    else:
        nodes_bp_df = pd.DataFrame()
        nodes_agg_df = pd.DataFrame()

    if "aggregate" in edges_df.columns:
        edges_bp_df = edges_df[edges_df["aggregate"] == "Big Picture"].drop(columns=["aggregate"], errors="ignore")
        edges_agg_df = edges_df[edges_df["aggregate"] != "Big Picture"]
    else:
        edges_bp_df = pd.DataFrame()
        edges_agg_df = pd.DataFrame()

    # Políticas e Read Models (Manejo de DF vacíos para data_editor)
    policies_df = pd.DataFrame(
        policies or [{"fuente": "", "destino": "", "descripcion": "", "estado_comparativo": "nuevo"}]
    )
    read_models_df = pd.DataFrame(
        read_models or [{"nombre": "", "descripcion": "", "proyecta": "", "ui_policies": "", "tecnologias": ""}]
    )

    # --- 4. Devolver DataFrames ---
    return {
        "nodes_bp_df": nodes_bp_df.fillna(""),
        "edges_bp_df": edges_bp_df.fillna(""),
        "nodes_agg_df": nodes_agg_df.fillna(""),
        "edges_agg_df": edges_agg_df.fillna(""),
        "policies_df": policies_df.fillna(""),
        "read_models_df": read_models_df.fillna(""),
        # DataFrames para estadísticas y compatibilidad (usando los maestros)
        "node_types_df": nodes_df["tipo_elemento"].value_counts().reset_index()
        if "tipo_elemento" in nodes_df.columns
        else pd.DataFrame(columns=["tipo_elemento", "count"]),
        "node_states_df": nodes_df["estado_comparativo"].value_counts().reset_index()
        if "estado_comparativo" in nodes_df.columns
        else pd.DataFrame(columns=["estado_comparativo", "count"]),
        "edge_types_df": edges_df["descripcion"].value_counts().reset_index()
        if "descripcion" in edges_df.columns
        else pd.DataFrame(columns=["descripcion", "count"]),
        "technologies_df": pd.DataFrame(sorted(technologies), columns=["technology"])
        if technologies
        else pd.DataFrame(columns=["technology"]),
    }
