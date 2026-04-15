import uuid

import streamlit as st
from config.settings import LLM_MODEL
from prompts import registry
from ui.components.context import render_context_fields


def _get_draft_service():
    """Build or retrieve the DraftService singleton from session state."""
    if "_draft_service" not in st.session_state:
        from infra.adapters.file_draft_repository import FileDraftRepository
        from services.draft_service import DraftService

        repo = FileDraftRepository()
        st.session_state["_draft_service"] = DraftService(repository=repo)
    return st.session_state["_draft_service"]


def _pdf_to_markdown(uploaded_pdf, inference=None):
    """Extract PDF content and convert to structured Markdown (AI-powered when available)."""
    from ui.utils.pdf import pdf_to_markdown

    return pdf_to_markdown(uploaded_pdf, inference=inference)


def process_input(source_type, source_data, source_name, ctx_pdf, ctx_text):
    """Process input using the new refactored pipeline with injected adapters."""
    from application.pipeline import AnalysisRequest, run_analysis
    from domain.events import ErrorEvent, ProgressEvent

    inference = st.session_state.get("_inference_port")
    transcription = st.session_state.get("_transcription_port")
    cache = st.session_state.get("_cache_port")

    if inference is None:
        st.error("Motor de inferencia no disponible. Reinicia la aplicación.")
        return

    with st.status(f"🤖 Procesando {source_name}...", expanded=True) as status:
        try:
            # Prepare context
            final_context = ctx_text or ""
            if ctx_pdf:
                ctx_pdf_name = getattr(ctx_pdf, "name", "PDF")
                status.write(f"📄 Procesando documento «{ctx_pdf_name}» (etapa: Contexto Adicional)...")
                pdf_md = _pdf_to_markdown(ctx_pdf, inference=inference)
                final_context = f"{final_context}\n\n--- DOCUMENTACIÓN PDF ---\n{pdf_md}"

            # Build event handler for real-time UI updates.
            # LangGraph runs parallel branches in worker threads that lack a
            # Streamlit ScriptRunContext; swallow those writes instead of
            # crashing the pipeline. Events are still captured by the
            # collector in pipeline.run_analysis.
            from streamlit.errors import NoSessionContext

            def on_event(event):
                try:
                    if isinstance(event, ProgressEvent):
                        status.write(f"⚙️ [{event.node_name}] {event.message}")
                    elif isinstance(event, ErrorEvent):
                        status.write(f"⚠️ [{event.node_name}] {event.message}")
                except NoSessionContext:
                    pass

            # Build request
            if source_type == "audio":
                status.write(f"🎧 Transcribiendo audio «{source_name}» (etapa: Fuente de Información)...")
                audio_bytes = source_data.getvalue() if hasattr(source_data, "getvalue") else source_data
                request = AnalysisRequest(
                    audio_bytes=audio_bytes,
                    audio_name=source_name,
                    context=final_context if final_context.strip() else None,
                    language="es",
                )
            else:
                status.write(f"🧠 Analizando documento «{source_name}» (etapa: Fuente de Información)...")
                request = AnalysisRequest(
                    transcript=source_data,
                    context=final_context if final_context.strip() else None,
                    language="es",
                )

            # Run the pipeline
            result = run_analysis(
                request=request,
                inference=inference,
                transcription=transcription,
                cache=cache,
                emitter=on_event,
            )

            # Store result in session state
            st.session_state.analysis_result = {
                "analysis": result.analysis,
                "transcript": result.transcript,
                "context": final_context if final_context.strip() else None,
                "logs": f"Events: {len(result.events)}, Errors: {len(result.errors)}",
            }

            # Persist the full analysis (including ddd_specs) to disk
            from ui.utils.storage import save_static_json as _save_json

            to_save = result.analysis.model_dump()
            to_save["transcript"] = result.transcript
            _save_json(to_save)

            if result.errors:
                for err in result.errors:
                    st.warning(f"⚠️ [{err.node_name}] {err.message}")

            # Create draft snapshot of the successful generation
            generation_id = str(uuid.uuid4())
            st.session_state.current_generation_id = generation_id
            try:
                draft_service = _get_draft_service()
                draft_service.create_draft(result.analysis, generation_id)
            except Exception:
                pass  # Draft creation failure must not block the pipeline

            # Signal the refinement agent to auto-trigger post-generation analysis.
            st.session_state.refinement_pending = True

            status.update(label="✅ ¡Análisis Completado!", state="complete", expanded=False)
            st.rerun()

        except Exception as e:
            status.update(label="❌ Error Crítico", state="error")
            st.error(f"Ocurrió un error inesperado: {e}")


def render_input_tabs():
    """Renderiza las fases de entrada como acordeones colapsables."""

    has_result = bool(st.session_state.get("analysis_result"))

    # ── Phase 1: Fuente de Información ──────────────────────────
    audio_source = None
    audio_name = None
    final_transcript_to_process = ""

    with st.expander("📥 1. Fuente de Información", expanded=not has_result):
        tab_audio, tab_text = st.tabs(["🎙️ Audio / Grabación", "📝 Transcripción / Texto"])

        # === AUDIO ===
        with tab_audio:
            input_mode = st.radio(
                "Selecciona fuente de audio:",
                ["🎙️ Grabar Voz", "📂 Subir Archivo"],
                horizontal=True,
                label_visibility="collapsed",
            )

            if input_mode == "🎙️ Grabar Voz":
                audio_bytes = st.audio_input("Haz click para grabar")
                if audio_bytes:
                    audio_source = audio_bytes
                    audio_name = "audio_grabado.wav"
            else:
                uploaded_file = st.file_uploader(
                    "Sube tu archivo (mp3, wav, m4a, opus)", type=["mp3", "wav", "m4a", "opus"]
                )
                if uploaded_file:
                    audio_source = uploaded_file
                    audio_name = uploaded_file.name

        # === TEXTO / DOCUMENTO ===
        with tab_text:
            st.info("Sube un documento o pega texto para analizar.")

            doc_file = st.file_uploader("📂 Cargar Documento Base (PDF, TXT, MD)", type=["pdf", "txt", "md"])

            initial_text = ""
            if doc_file:
                cached_key = f"_doc_cache_{doc_file.name}_{doc_file.size}"
                if cached_key not in st.session_state:
                    inference = st.session_state.get("_inference_port")
                    with st.spinner(f"📄 Procesando documento «{doc_file.name}» (etapa: Fuente de Información)..."):
                        if doc_file.type == "application/pdf":
                            st.session_state[cached_key] = _pdf_to_markdown(doc_file, inference=inference)
                        else:
                            try:
                                st.session_state[cached_key] = doc_file.getvalue().decode("utf-8")
                            except Exception:
                                st.session_state[cached_key] = str(doc_file.getvalue())
                initial_text = st.session_state[cached_key]

            transcript = st.text_area("Contenido / Transcripción", value=initial_text, height=300)

            # Simulation options
            st.markdown("**Modo de simulación:**")
            sim_mode = st.radio(
                "Modo de simulación:",
                [
                    "Sin simulación",
                    "✨ Narrativa (un agente reescribe)",
                    "🤖 Taller Multi-Agente (dos agentes conversan)",
                ],
                horizontal=True,
                label_visibility="collapsed",
            )
            final_transcript_to_process = transcript

            # ── Opción 1: Narrativa (un agente) ──────────────────────
            if sim_mode == "✨ Narrativa (un agente reescribe)" and transcript.strip():
                if st.button("🎭 Generar Simulación Narrativa", type="secondary"):
                    inference = st.session_state.get("_inference_port")
                    if inference:
                        with st.spinner(f"🤖 Generando simulación de taller ({LLM_MODEL})..."):
                            prompt = registry.get("narrative_transform_ui").render(transcript=transcript).to_string()
                            simulated_text = inference.invoke_text(prompt)
                            st.session_state["simulated_narrative"] = simulated_text
                            st.session_state.pop("multi_agent_simulation", None)
                            st.success("¡Narrativa generada!")

                if "simulated_narrative" in st.session_state:
                    with st.expander("Ver Narrativa Simulada", expanded=True):
                        st.markdown(st.session_state["simulated_narrative"])
                        if st.checkbox("Usar esta narrativa para el análisis", value=True):
                            final_transcript_to_process = st.session_state["simulated_narrative"]

            # ── Opción 2: Taller Multi-Agente ────────────────────────
            elif sim_mode == "🤖 Taller Multi-Agente (dos agentes conversan)":
                st.info(
                    "Dos agentes conversan entre sí: un **Facilitador** de Event Storming "
                    "y un **Experto de Dominio**. La conversación genera un transcript listo para análisis.\n\n"
                    "Usa el texto del área de arriba como descripción del dominio (fuente de conocimiento del experto). "
                    "El Contexto Adicional (fase 2) también será considerado."
                )
                num_turns = st.slider("Número de turnos de conversación", min_value=4, max_value=16, value=8, step=2)

                domain_description = transcript.strip()
                if not domain_description:
                    st.warning(
                        "Escribe una descripción del dominio en el área de texto para que el Experto tenga conocimiento base."
                    )
                else:
                    if st.button("🎭 Iniciar Taller Multi-Agente", type="secondary"):
                        inference = st.session_state.get("_inference_port")
                        if inference:
                            from services.workshop_simulation import WorkshopSimulator

                            st.session_state.pop("multi_agent_simulation", None)
                            st.session_state.pop("simulated_narrative", None)
                            simulation_turns_display = []
                            sim_container = st.container()

                            def on_turn(turn):
                                simulation_turns_display.append(turn)
                                with sim_container:
                                    with st.chat_message("assistant", avatar="🧑‍💼"):
                                        st.markdown(f"**Facilitador (turno {turn.turn_number}):** {turn.facilitator}")
                                    with st.chat_message("user", avatar="👤"):
                                        st.markdown(f"**Experto (turno {turn.turn_number}):** {turn.expert}")

                            with st.spinner(f"🤖 Simulando taller ({num_turns} turnos)..."):
                                simulator = WorkshopSimulator(inference)
                                simulation = simulator.simulate(
                                    context=domain_description,
                                    num_turns=num_turns,
                                    on_turn=on_turn,
                                )
                            st.session_state["multi_agent_simulation"] = simulation
                            st.success(f"✅ Taller completado — {len(simulation.turns)} turnos generados.")

                if "multi_agent_simulation" in st.session_state:
                    sim = st.session_state["multi_agent_simulation"]
                    with st.expander("📜 Ver Transcript Completo del Taller", expanded=False):
                        st.text_area("Transcript generado", value=sim.transcript, height=300, disabled=True)
                    if st.checkbox(
                        "Usar esta conversación para el análisis",
                        value=True,
                        key="use_multi_agent_sim",
                    ):
                        final_transcript_to_process = sim.transcript

    # ── Phase 2: Contexto Adicional ─────────────────────────────
    with st.expander("📚 2. Contexto Adicional (Reglas, Diccionario, PDFs)", expanded=not has_result):
        context_pdf, context_text = render_context_fields()

    # ── Actions: Botones de análisis ────────────────────────────
    if audio_source:
        st.success(f"🎧 Audio listo: **{audio_name}**")
        if st.button("🚀 Analizar Audio", type="primary", width="stretch"):
            process_input(
                source_type="audio",
                source_data=audio_source,
                source_name=audio_name,
                ctx_pdf=context_pdf,
                ctx_text=context_text,
            )

    if final_transcript_to_process.strip():
        if st.button("🚀 Analizar Contenido", type="primary", width="stretch"):
            process_input(
                source_type="text",
                source_data=final_transcript_to_process,
                source_name="Texto/Narrativa",
                ctx_pdf=context_pdf,
                ctx_text=context_text,
            )
