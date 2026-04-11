import json

import streamlit as st

from models.domain_analysis import DomainAnalysis
from prompts import registry


# --- 1. PREPROCESADOR DE DATOS ---
@st.cache_data(show_spinner=False)
def get_optimized_domain_context(domain_dict: dict, options: dict = None, specs: dict = None) -> str:
    if options is None:
        options = {"bp": True, "aggs": True, "rms": True, "policies": True}
    if specs is None:
        specs = {}
    output = []

    def clean(s):
        return str(s).replace("|", "/").replace("\n", " ").strip()

    def fmt_tags(node):
        tags = node.get("tags_tecnologia", [])
        state = node.get("estado_comparativo", "")
        parts = []
        if tags:
            parts.append(f"[{', '.join(tags)}]")
        if state:
            parts.append(f"({state})")
        return " ".join(parts) if parts else "-"

    def should_include_node(n):
        if not options["policies"] and n.get("tipo_elemento") == "Política":
            return False
        return True

    id_map = {}
    if domain_dict.get("big_picture"):
        for n in domain_dict["big_picture"].get("nodos", []):
            id_map[n.get("id")] = n.get("nombre")
    for agg in domain_dict.get("agregados", []):
        for n in agg.get("nodos", []):
            id_map[n.get("id")] = n.get("nombre")
    output.append("ROOT:")
    bp = domain_dict.get("big_picture", {})
    if bp and options["bp"]:
        output.append("  big_picture:")
        output.append("    nodes: [Type | Name | Description | Metadata]")
        for n in bp.get("nodos", []):
            if should_include_node(n):
                output.append(
                    f"    | {clean(n.get('tipo_elemento'))} | {clean(n.get('nombre'))} | {clean(n.get('descripcion'))} | {fmt_tags(n)}"
                )
        if bp.get("aristas"):
            output.append("    flows: [Description | Source -> Target]")
            for e in bp.get("aristas", []):
                src = id_map.get(e.get("fuente"), "Unknown")
                dst = id_map.get(e.get("destino"), "Unknown")
                output.append(f"    | {clean(e.get('descripcion'))} | {src} -> {dst}")
    aggs = domain_dict.get("agregados", [])
    if aggs and options["aggs"]:
        output.append("  aggregates:")
        for agg in aggs:
            name = clean(agg.get("nombre_agregado"))
            root = clean(agg.get("entidad_raiz"))
            output.append(f"    - name: {name} (Root: {root})")
            nodes = agg.get("nodos", [])
            if nodes:
                output.append("      nodes: [Type | Name | Description | Metadata]")
                for n in nodes:
                    if should_include_node(n):
                        output.append(
                            f"      | {clean(n.get('tipo_elemento'))} | {clean(n.get('nombre'))} | {clean(n.get('descripcion'))} | {fmt_tags(n)}"
                        )
            edges = agg.get("aristas", [])
            if edges:
                output.append("      flows: [Description | Source -> Target]")
                for e in edges:
                    src = id_map.get(e.get("fuente"), "Unknown")
                    dst = id_map.get(e.get("destino"), "Unknown")
                    output.append(f"      | {clean(e.get('descripcion'))} | {src} -> {dst}")
    rms = domain_dict.get("read_models", [])
    if rms and options["rms"]:
        output.append("  read_models:")
        output.append("    models: [Name | Description | Projections]")
        for rm in rms:
            proyecta_names = [id_map.get(pid, pid) for pid in rm.get("proyecta", [])]
            output.append(
                f"    | {clean(rm.get('nombre'))} | {clean(rm.get('descripcion'))} | Proyects: {', '.join(proyecta_names)}"
            )
    pols = domain_dict.get("politicas_inter_agregados", [])
    if pols and options["policies"]:
        output.append("  global_policies:")
        output.append("    flows: [Description | Source -> Target]")
        for e in pols:
            src = id_map.get(e.get("fuente"), "Unknown")
            dst = id_map.get(e.get("destino"), "Unknown")
            output.append(f"    | {clean(e.get('descripcion'))} | {src} -> {dst}")
    # --- Especificaciones generadas ---
    if options.get("domain_models") and specs.get("domain_models"):
        output.append("\n--- ESPECIFICACIONES: Modelo de Dominio (DDD) ---")
        output.append(specs["domain_models"])
    if options.get("context_map") and specs.get("context_map"):
        output.append("\n--- ESPECIFICACIONES: Context Map ---")
        output.append(specs["context_map"])
    # --- Transcripción Original ---
    if options.get("transcript") and specs.get("transcript"):
        output.append("\n--- TRANSCRIPCIÓN ORIGINAL DE LA SESIÓN ---")
        output.append(specs["transcript"])
    return "\n".join(output)


def _trigger_summary_and_critique(analysis_obj) -> None:
    """Run post-generation project summary and critique, and inject into chat_messages."""
    inference = st.session_state.get("_inference_port")
    if not inference:
        return

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    try:
        # Check if the summary was already generated to avoid re-generating
        if any(msg.get("is_summary") for msg in st.session_state.chat_messages):
            return

        domain_json = analysis_obj.model_dump_json()
        system_instruction = (
            registry.get("project_summary_and_critique").render(domain_analysis=domain_json).to_string()
        )

        # We call the model with just the system prompt to get the critique
        with st.spinner("Generando Resumen y Crítica del Proyecto..."):
            response = inference.invoke_text(system_instruction)

        content = "## Análisis y Crítica Inicial\n\n" + response

        st.session_state.chat_messages.append({"role": "assistant", "content": content, "is_summary": True})

    except Exception as e:
        # Fallback si falla
        st.session_state.chat_messages.append(
            {
                "role": "assistant",
                "content": f"No se pudo generar la crítica automática: {e}",
                "is_summary": True,
            }
        )


def _render_tool_executions(tool_executions):
    """Render tool execution summary as a collapsible section."""
    if not tool_executions:
        return

    write_tools = {
        "add_node",
        "add_edge",
        "delete_node",
        "delete_edge",
        "rename_element",
        "undo_last_change",
    }
    writes = [e for e in tool_executions if e.tool_name in write_tools]
    reads = [e for e in tool_executions if e.tool_name not in write_tools]

    label_parts = []
    if writes:
        label_parts.append(f"{len(writes)} escritura(s)")
    if reads:
        label_parts.append(f"{len(reads)} consulta(s)")
    label = f"🔧 Herramientas ejecutadas: {', '.join(label_parts)}"

    with st.expander(label, expanded=False):
        for exec in tool_executions:
            icon = "✅" if exec.success else "❌"
            st.markdown(f"**{icon} {exec.tool_name}**")
            st.json(exec.arguments)
            try:
                result_data = json.loads(exec.result)
                if isinstance(result_data, dict) and "message" in result_data:
                    st.caption(result_data["message"])
            except (json.JSONDecodeError, TypeError):
                pass


# --- 2. RENDERIZADO PRINCIPAL ---
def render_chat_tab(analysis_obj: DomainAnalysis):
    # Get the chat agent port from session state (preferred), fallback to inference port
    chat_agent = st.session_state.get("_chat_agent_port")
    inference = st.session_state.get("_inference_port")

    if chat_agent is None and inference is None:
        st.warning("Motor de inferencia no disponible. Reinicia la aplicación.")
        return

    # 1. Inicializar Estado
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # Auto-trigger the summary when post-generation flag is set
    if st.session_state.get("refinement_pending"):
        st.session_state.refinement_pending = False
        _trigger_summary_and_critique(analysis_obj)
        st.rerun()

    # 2. ENCABEZADO Y PERSONA
    st.subheader("Arquitecto Senior AI")
    if chat_agent:
        st.caption(
            "Agente libre. Puedes preguntarle cualquier cosa, o usar sus herramientas para editar el mapa de dominio."
        )
    else:
        st.caption("Asistente experto en DDD, listo para conversar libremente sobre el diseño.")

    # 3. CONFIGURACIÓN DE CONTEXTO
    with st.expander("⚙️ Configuración de Contexto y Memoria", expanded=False):
        st.markdown("##### 🧠 ¿Qué información debe considerar el AI?")

        c1, c2, c3, c4 = st.columns(4)
        context_opts = {}

        context_opts["bp"] = c1.toggle("Big Picture", value=True, help="Visión macro del sistema")
        context_opts["aggs"] = c2.toggle("Agregados", value=True, help="Detalle interno de módulos")
        context_opts["rms"] = c3.toggle("Read Models", value=True, help="Vistas y Proyecciones")
        context_opts["policies"] = c4.toggle("Políticas", value=True, help="Reglas de negocio globales")

        st.markdown("##### 📄 Elementos Adicionales")
        c5, c6, c7 = st.columns(3)
        context_opts["domain_models"] = c5.toggle("Modelo Táctico", value=False, help="Diagrama de Clases")
        context_opts["context_map"] = c6.toggle("Context Map", value=False, help="Mapa Estratégico PlantUML")
        context_opts["transcript"] = c7.toggle("Transcripción Original", value=False, help="Audio/Texto base")

        st.divider()

        col_tools_1, col_tools_2 = st.columns([3, 1])
        with col_tools_1:
            show_debug = st.checkbox("👁️ Ver prompt generado (Debug)", value=False)
        with col_tools_2:
            if st.button("🧹 Limpiar Chat", width="stretch"):
                st.session_state.chat_messages = []
                st.rerun()

    # Validación
    if not any(context_opts.values()):
        st.warning("⚠️ Debes activar al menos una capa de contexto.")
        return

    # 4. Preparar Contexto
    domain_dict = analysis_obj.model_dump()
    ddd_specs = analysis_obj.ddd_specs or {}
    specs_for_ctx = {
        "domain_models": ddd_specs.get("domain_models") if context_opts.get("domain_models") else None,
        "context_map": ddd_specs.get("context_map") if context_opts.get("context_map") else None,
        "transcript": st.session_state.analysis_result.get("transcript") if context_opts.get("transcript") else None,
    }
    csv_context = get_optimized_domain_context(domain_dict, context_opts, specs_for_ctx)

    if show_debug:
        st.caption("Payload enviado al LLM:")
        st.code(csv_context, language="yaml")

    # 6. RENDERIZADO DEL HISTORIAL
    chat_container = st.container()
    with chat_container:
        if not st.session_state.chat_messages:
            st.info(
                "👋 El contexto está cargado. Pregúntame sobre **Riesgos**, **Inconsistencias** o **Flujos críticos**."
            )

        for msg in st.session_state.chat_messages:
            avatar_icon = "👤" if msg["role"] == "user" else "👷‍♂️"
            with st.chat_message(msg["role"], avatar=avatar_icon):
                st.markdown(msg["content"])
                if msg.get("tool_executions"):
                    _render_tool_executions(msg["tool_executions"])

    # 7. INPUT Y LÓGICA (Conversación libre)
    if prompt := st.chat_input("Consulta o instrucción sobre el modelo de dominio..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})

        with chat_container:
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)

            with st.chat_message("assistant", avatar="👷‍♂️"):
                message_placeholder = st.empty()
                system_instruction = registry.get("architectural_chat").render(csv_context=csv_context).to_string()

                if chat_agent:
                    from services.model_accessor import ModelAccessor

                    accessor = ModelAccessor(st.session_state)

                    try:
                        with st.spinner("Pensando..."):
                            # Exclude the last message (just-appended user prompt) to avoid
                            # duplicating it — the agent appends user_message itself.
                            recent_history = [
                                {"role": m["role"], "content": m["content"]}
                                for m in st.session_state.chat_messages[:-1][-6:]
                            ]

                            agent_response = chat_agent.run(
                                user_message=prompt,
                                history=recent_history,
                                system_prompt=system_instruction,
                                model_accessor=accessor,
                            )

                        # --- Sintetizar contenido si el LLM lo devolvió vacío tras tool calls ---
                        response_content = agent_response.content or ""
                        tool_execs = agent_response.tool_executions

                        if not response_content.strip() and tool_execs:
                            import json as _json

                            summary_lines = []
                            for te in tool_execs:
                                try:
                                    parsed = _json.loads(te.result)
                                    msg = parsed.get("message", "ejecutado")
                                    icon = "✅" if te.success else "❌"
                                    summary_lines.append(f"{icon} **{te.tool_name}**: {msg}")
                                except Exception:
                                    summary_lines.append(f"🔧 **{te.tool_name}**: ejecutado")
                            response_content = "### Operaciones realizadas\n\n" + "\n".join(summary_lines)

                        message_placeholder.markdown(response_content)

                        if tool_execs:
                            _render_tool_executions(tool_execs)

                        msg_data = {"role": "assistant", "content": response_content}
                        if tool_execs:
                            msg_data["tool_executions"] = tool_execs
                        st.session_state.chat_messages.append(msg_data)

                        write_tools = {
                            "add_node",
                            "add_edge",
                            "delete_node",
                            "delete_edge",
                            "rename_element",
                            "undo_last_change",
                        }
                        has_writes = any(e.tool_name in write_tools for e in tool_execs)
                        if has_writes:
                            from models.domain_analysis import DomainAnalysis as _DA
                            from ui.utils.storage import save_static_json

                            _current = st.session_state.analysis_result["analysis"]
                            st.session_state.analysis_result["analysis"] = _DA.model_validate(_current.model_dump())

                            # 1) Guardar los cambios persistentes en JSON preservando el transcript
                            to_save = _current.model_dump()
                            to_save["transcript"] = st.session_state.analysis_result.get("transcript", "")
                            save_static_json(to_save)

                            # 2) Limpiar el state de los data_editors para forzar el repintado
                            for key in [
                                "edit_nodes_bp",
                                "edit_edges_bp",
                                "edit_nodes_agg",
                                "edit_edges_agg",
                                "edit_policies",
                                "edit_rms",
                            ]:
                                if key in st.session_state:
                                    del st.session_state[key]

                            st.rerun()

                    except Exception as e:
                        st.error(f"Error en el agente: {e}")
                else:
                    # Fallback (legacy mode)
                    recent_history = st.session_state.chat_messages[-6:]
                    conversation_parts = [system_instruction]
                    for msg in recent_history:
                        role_label = "Usuario" if msg["role"] == "user" else "Asistente"
                        conversation_parts.append(f"{role_label}: {msg['content']}")

                    full_prompt = "\n\n".join(conversation_parts)

                    try:
                        with st.spinner("Elaborando respuesta..."):
                            full_response = inference.invoke_text(full_prompt)

                        message_placeholder.markdown(full_response)
                        st.session_state.chat_messages.append({"role": "assistant", "content": full_response})
                    except Exception as e:
                        st.error(f"Error en el motor de inferencia: {e}")
