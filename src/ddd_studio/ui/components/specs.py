import streamlit as st
from models.domain_analysis import DomainAnalysis
from services.spec_generator import SpecGenerator
from ui.utils.puml import render_plantuml
from ui.utils.storage import save_static_json


def _clean_puml(raw: str) -> str:
    """Strip markdown fences so only PlantUML syntax remains."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    # If LLM added prose before @startuml, skip to it
    if not text.startswith("@startuml") and "@startuml" in text:
        text = text[text.index("@startuml") :]
    return text.strip()


def render_specs_tab(analysis_obj: DomainAnalysis, specs: dict | None = None):
    """
    Renders the Domain-Driven Design tab with strategic and tactical models.
    """
    st.markdown("### 🛠️ Domain-Driven Design (DDD)")
    st.info("Genera mapas estratégicos (Context Map) y modelos tácticos (Diagramas de Clases) basados en tu análisis.")

    # Aseguramos que el objeto tenga el diccionario listo
    if analysis_obj.ddd_specs is None:
        analysis_obj.ddd_specs = {}

    # Use the dynamic inference port from session state
    inference = st.session_state.get("_inference_port")
    generator = SpecGenerator(analysis_obj, inference)

    tab1, tab2 = st.tabs(["🗺️ Context Map", "🏗️ Modelo de Dominio (Táctico)"])

    # === CONTEXT MAP ===
    with tab1:
        st.markdown("#### Strategic Design — Mapa Estratégico")
        st.caption("Subdominios (Core / Supporting / Generic), Bounded Contexts y sus relaciones de mapa de contexto.")

        context_map_code = analysis_obj.ddd_specs.get("context_map")

        if context_map_code:
            puml_code = _clean_puml(context_map_code)
            render_plantuml(puml_code, height=650)

            with st.expander("Ver / editar código PlantUML", expanded=False):
                edited = st.text_area(
                    "Código PlantUML (puedes corregir errores de sintaxis aquí)",
                    value=puml_code,
                    height=300,
                    key="puml_editor_cmap",
                )
                if edited.strip() != puml_code.strip():
                    if st.button("Guardar y Re-renderizar diagrama", key="btn_rerender_cmap"):
                        analysis_obj.ddd_specs["context_map"] = edited
                        save_static_json(analysis_obj.model_dump())
                        st.rerun()

            st.download_button(
                "Descargar diagrama (.puml)",
                puml_code,
                "context_map.puml",
                mime="text/plain",
            )
        else:
            st.markdown("*No se ha generado el Context Map aún.*")

        if st.button("Generar Context Map", key="btn_gen_cmap"):
            with st.spinner("Generando diagrama de diseño estratégico con IA..."):
                result = generator.generate_context_map()
                analysis_obj.ddd_specs["context_map"] = result
                save_static_json(analysis_obj.model_dump())
                st.rerun()

    # === DDD DOMAIN MODELS (Tactical) ===
    with tab2:
        st.markdown("#### Tactical Design — Diagrama de Clases")
        st.caption("Entidades, Value Objects, Aggregates y su comportamiento interno.")

        domain_model_code = analysis_obj.ddd_specs.get("domain_models")

        if domain_model_code:
            puml_code = _clean_puml(domain_model_code)
            render_plantuml(puml_code, height=650)

            with st.expander("Ver / editar código PlantUML", expanded=False):
                edited = st.text_area(
                    "Código PlantUML (puedes corregir errores de sintaxis aquí)",
                    value=puml_code,
                    height=300,
                    key="puml_editor_dmodel",
                )
                if edited.strip() != puml_code.strip():
                    if st.button("Guardar y Re-renderizar diagrama", key="btn_rerender_dmodel"):
                        analysis_obj.ddd_specs["domain_models"] = edited
                        save_static_json(analysis_obj.model_dump())
                        st.rerun()

            st.download_button(
                "Descargar diagrama (.puml)",
                puml_code,
                "tactical_domain_model.puml",
                mime="text/plain",
            )
        else:
            st.markdown("*No se ha generado el modelo de dominio tácico aún.*")

        if st.button("Generar Modelo de Dominio (Táctico)", key="btn_gen_ddd"):
            with st.spinner("Generando diagrama de dominio táctico con IA..."):
                result = generator.generate_domain_models()
                analysis_obj.ddd_specs["domain_models"] = result
                save_static_json(analysis_obj.model_dump())
                st.rerun()
