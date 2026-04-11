import copy

import pandas as pd


def _process_nodes_list(nodes_list: list, default_nivel: str) -> list:
    """Procesa una lista de nodos para limpiar tags y asegurar el campo nivel."""
    for node in nodes_list:
        # Asegurar que nivel existe
        if "nivel" not in node or node["nivel"] == "":
            node["nivel"] = default_nivel

        tags = node.get("tags_tecnologia", "")
        if isinstance(tags, str):
            if tags.strip().lower() in ["none", "", "nan"]:
                node["tags_tecnologia"] = []
            else:
                node["tags_tecnologia"] = [t.strip() for t in tags.split(",") if t.strip()]
        # Si ya es lista pero vacía, dejarla como lista
        elif not isinstance(tags, list):
            node["tags_tecnologia"] = []
    return nodes_list


## BLOQUE 1: BIG PICTURE
def _reconstruct_big_picture(modified: dict, nodes_df: pd.DataFrame, edges_df: pd.DataFrame):
    """Reconstruye la sección Big Picture usando DataFrames ya filtrados (sin columna 'aggregate')."""
    # Se espera que nodes_df y edges_df ya contengan solo elementos de Big Picture.

    nodes_list = nodes_df.to_dict("records") if not nodes_df.empty else []
    modified["big_picture"]["nodos"] = _process_nodes_list(nodes_list, default_nivel="big_picture")
    modified["big_picture"]["aristas"] = edges_df.to_dict("records") if not edges_df.empty else []


## BLOQUE 2: AGREGADOS
def _reconstruct_aggregates(modified: dict, nodes_agg_df: pd.DataFrame, edges_agg_df: pd.DataFrame):
    """Reconstruye la sección de Agregados a partir de DataFrames que contienen la columna 'aggregate'."""

    # Asegurar que los DataFrames no estén vacíos antes de iterar
    if nodes_agg_df.empty:
        nodes_agg_df = pd.DataFrame(columns=nodes_agg_df.columns)
    if edges_agg_df.empty:
        edges_agg_df = pd.DataFrame(columns=edges_agg_df.columns)

    # Mantenemos solo los agregados que existían originalmente para evitar crear nuevos vacíos
    {agg["nombre_agregado"] for agg in modified["agregados"]}

    for agg in modified["agregados"]:
        agg_name = agg["nombre_agregado"]

        # Filtramos los nodos y aristas que corresponden a este agregado
        agg_nodes = nodes_agg_df[nodes_agg_df["aggregate"] == agg_name].drop(columns=["aggregate"], errors="ignore")
        agg_edges = edges_agg_df[edges_agg_df["aggregate"] == agg_name].drop(columns=["aggregate"], errors="ignore")

        nodes_list = agg_nodes.to_dict("records") if not agg_nodes.empty else []
        agg["nodos"] = _process_nodes_list(nodes_list, default_nivel="process_level")

        agg["aristas"] = agg_edges.to_dict("records") if not agg_edges.empty else []

    # Mejorar: Se podrían considerar los nuevos agregados (si se añadieron filas con nuevos nombres de 'aggregate'),
    # pero para simplificar la reconstrucción, nos limitamos a modificar los agregados existentes.


## BLOQUE 3: READ MODELS
def _reconstruct_read_models(modified: dict, read_models_df: pd.DataFrame):
    """Reconstruye la sección de Read Models."""
    modified["read_models"] = []
    for _, row in read_models_df.iterrows():
        rm = {
            "nombre": str(row["nombre"]).strip(),
            "descripcion": str(row.get("descripcion", "") or "").strip(),
            # Usar .split(',') para proyecta (eventos)
            "proyecta": [p.strip() for p in str(row.get("proyecta", "")).split(",") if p.strip()],
            # Usar .split(';') para ui_policies
            "ui_policies": [p.strip() for p in str(row.get("ui_policies", "")).split(";") if p.strip()],
            # Usar .split(',') para tecnologias
            "tecnologias": [t.strip() for t in str(row.get("tecnologias", "")).split(",") if t.strip()],
        }
        # Asegura que el nombre no sea None, NaN o cadena vacía
        if rm["nombre"] and rm["nombre"].lower() != "nan":
            modified["read_models"].append(rm)


## BLOQUE 4: POLÍTICAS INTER-AGREGADOS
def _reconstruct_inter_aggregate_policies(modified: dict, policies_df: pd.DataFrame):
    """Reconstruye la sección de Políticas Inter-Agregados."""
    modified["politicas_inter_agregados"] = policies_df.to_dict("records") if not policies_df.empty else []


def reconstruct_domain_analysis(
    original: dict,
    nodes_bp_df: pd.DataFrame,
    edges_bp_df: pd.DataFrame,
    nodes_agg_df: pd.DataFrame,
    edges_agg_df: pd.DataFrame,
    policies_df: pd.DataFrame,
    read_models_df: pd.DataFrame,
) -> dict:
    """Reconstruye el DomainAnalysis desde DataFrames editados ya separados."""
    modified = copy.deepcopy(original)

    # Limpieza general de NaN
    nodes_bp_df = nodes_bp_df.fillna("")
    edges_bp_df = edges_bp_df.fillna("")
    nodes_agg_df = nodes_agg_df.fillna("")
    edges_agg_df = edges_agg_df.fillna("")
    policies_df = policies_df.fillna("")
    read_models_df = read_models_df.fillna("")

    _reconstruct_inter_aggregate_policies(modified, policies_df)

    # Notar que aquí pasamos los DF separados, y los reconstructores ya no filtran
    _reconstruct_aggregates(modified, nodes_agg_df, edges_agg_df)
    _reconstruct_big_picture(modified, nodes_bp_df, edges_bp_df)

    _reconstruct_read_models(modified, read_models_df)

    return modified
