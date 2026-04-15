# DDD Studio — Análisis de Dominio y Event Storming asistido por IA

**DDD Studio** es un entorno interactivo que cierra la brecha entre **talleres de descubrimiento de flujos de negocio** y la implementación formal de **Diseño Guiado por el Dominio (DDD)**.

Convierte transcripciones de talleres (audio o texto) y documentación técnica en **modelos de dominio** estructurados, visualizados como grafos interactivos y refinables mediante un asistente conversacional con herramientas (tool calling).

---

## Características principales

*   **Pipeline single-shot determinístico**: `cache_check` → `transcribe` → `analyze_semantics` → `refine_analysis` (LangGraph). Un único LLM call produce el `DomainAnalysis` completo (nodos + aristas).
*   **Validación estructural post-extracción**: `integrity_validator` verifica invariantes del grafo (comandos sin ejecutor, eventos sin productor, agregados vacíos) y emite warnings via el event emitter.
*   **Canonicalización semántica**: `analysis_normalizer` normaliza IDs, deduplica nodos y reordena por aparición en transcript.
*   **Caché de análisis por hash**: clave `(transcript, model_name)`; mismo input = mismo output garantizado en re-ejecución.
*   **Caché de transcripciones de audio**: evita re-transcribir MP4/MP3 ya procesados.
*   **Dos backends de transcripción**: `FasterWhisperTranscriptionAdapter` (local, CTranslate2) o `GoogleTranscriptionAdapter` (remoto). Configurable via `WHISPER_MODEL`.
*   **Agente conversacional DDD**: ReAct loop sobre Gemini con herramientas para modificar el grafo (añadir/eliminar nodos, refinar agregados) desde chat.
*   **Simulación inter-agente de talleres**: `WorkshopSimulator` orquesta dos agentes (facilitador + experto) para producir transcripciones sintéticas listas para el pipeline.
*   **Drafts de generaciones**: historial persistente de modelos generados con `DraftService` + `FileDraftRepository`.
*   **Exportación de artefactos**: Mermaid, PlantUML, PDF y especificaciones via `spec_generator`.
*   **Decoding greedy hardcoded**: estabilidad como propiedad del sistema, no ajuste de usuario.

---

## Instalación y configuración

```
uv tool install git+https://github.com/raalzate/ia-ddd-studio.git
ddd-studio
```

### Requisitos
*   Python **3.10.9+**
*   API Key de **Google Gemini** (AI Studio).

### 1. Variables de entorno (`.env`)
```env
# Obligatorio
GOOGLE_API_KEY="tu-api-key"

# Opcional — nombre del modelo (default: gemini-2.5-flash)
GEMINI_MODEL="gemini-2.5-flash"

# Opcional — modelo local Whisper para transcripción offline (ej: "small", "medium")
# Si no se define, usa GoogleTranscriptionAdapter (remoto)
WHISPER_MODEL="small"

# Opcional — idioma de respuesta (default: es)
RESPONSE_LANGUAGE="es"
```

### 2. Dependencias con `uv`
```bash
uv sync
```

### 3. Ejecución
```bash
# Via Streamlit directo
uv run streamlit run src/ddd_studio/app.py

# O usando el CLI instalado (equivalente)
uv run ddd-studio
```

---

## Pipeline de análisis

### Flujo (LangGraph)

```
cache_check → [cache hit] → analyze_semantics → [has context] → refine_analysis → END
             → [miss]     → transcribe         ↗
```

1. **cache_check**: verifica si ya existe un análisis cacheado para el transcript/audio.
2. **transcribe** (solo audio): `FasterWhisperAdapter` o `GoogleTranscriptionAdapter` según configuración.
3. **analyze_semantics**:
   - Un único LLM call sobre el transcript produce `DomainAnalysis` completo (nodos + aristas).
   - `analysis_normalizer` canonicaliza IDs y deduplica.
   - `integrity_validator` reporta warnings estructurales via emitter.
   - Resultado se persiste en caché por hash.
4. **refine_analysis**: si se provee contexto adicional, un segundo LLM call ajusta el modelo.

---

## Determinismo y estabilidad semántica

DDD Studio **no promete determinismo byte-a-byte** — los LLMs bajo infra compartida tienen varianza residual. Promete **estabilidad semántica**: mismo transcript → mismo conjunto de conceptos con mismos nombres canónicos. Se logra mediante:

1. **Greedy decoding hardcoded** en `gemini_inference.py` y `gemini_chat_agent.py`.
2. **Canonicalización post-extracción** (`analysis_normalizer.py`).
3. **Caché por hash** `(transcript, model_name)` — re-ejecución = resultado idéntico.

---

## Arquitectura técnica

Arquitectura **Vertical Slice**. Todo el código vive dentro del paquete `src/ddd_studio/`:

*   `src/ddd_studio/app.py` — entry point de Streamlit.
*   `src/ddd_studio/cli.py` — CLI `ddd-studio` que lanza Streamlit con CWD al paquete instalado.
*   `src/ddd_studio/application/` — orquestación LangGraph:
    *   `graph_builder.py` — construye `build_audio_graph` y `build_text_graph`.
    *   `pipeline.py` — ejecuta el grafo y expone la API de alto nivel.
    *   `nodes/` — `cache_check`, `transcribe`, `analyze_semantics`, `refine_analysis`, `generate_specs`.
*   `src/ddd_studio/domain/` — modelos Pydantic, eventos de progreso, excepciones, `ports.py` (InferencePort, TranscriptionPort, CachePort, DraftRepositoryPort):
    *   `models/agent_state.py` — `NodeContract`, `AgentState`.
    *   `models/draft.py` — `Draft`, `DraftSummary`, `DraftManifest`.
    *   `models/tool_schemas.py` — schemas de herramientas del agente.
*   `src/ddd_studio/models/` — modelos de dominio DDD:
    *   `domain_analysis.py` — `DomainAnalysis`, `BigPicture`, `Nodo`, `Arista`.
    *   `event_storming_state.py` — estado de sesión de Event Storming.
*   `src/ddd_studio/infra/adapters/` — adaptadores externos:
    *   `gemini_inference.py` — `GeminiInferenceAdapter` (InferencePort).
    *   `gemini_chat_agent.py` — `GeminiChatAgentAdapter` (ChatAgentPort).
    *   `file_cache.py` — `FileCacheAdapter` (CachePort).
    *   `faster_whisper_transcription.py` — transcripción local (CTranslate2).
    *   `google_transcription.py` — transcripción remota vía Google.
    *   `file_draft_repository.py` — persistencia de drafts en JSON.
*   `src/ddd_studio/infra/inference_provider.py` — fábrica que inyecta la config activa.
*   `src/ddd_studio/infra/streaming.py` — streaming de eventos al UI.
*   `src/ddd_studio/prompts/` — `catalog.py`, `registry.py`, `template.py` y plantillas en `templates/` (`analysis.py`, `generation.py`, `ui.py`).
*   `src/ddd_studio/services/` — lógica de soporte:
    *   `analysis_normalizer.py` — canonicalización de IDs y deduplicación.
    *   `analysis_cache.py` — compute/load/store de caché por hash.
    *   `integrity_validator.py` — validación estructural del grafo DDD.
    *   `draft_service.py` — gestión del historial de generaciones.
    *   `spec_generator.py` — generación de especificaciones desde el modelo.
    *   `agent_tools.py` — herramientas del agente conversacional.
    *   `transcription_service.py` — fachada de transcripción.
    *   `cache_service.py` — fachada de caché de transcripciones.
    *   `workshop_simulation.py` — simulación inter-agente de talleres DDD.
    *   `model_accessor.py` — acceso tipado al modelo activo.
*   `src/ddd_studio/ui/` — componentes Streamlit:
    *   `components/` — `sidebar`, `input`, `results`, `chat`, `context`, `draft_preview`, `specs`.
    *   `visualization/` — `graph.py` (Graphviz/Mermaid), `stats.py`.
    *   `utils/` — `mermaid.py`, `puml.py`, `pdf.py`, `storage.py`.
*   `src/ddd_studio/config/settings.py` — configuración desde env vars.
*   `specs/` — features gestionadas con `tessl-labs/intent-integrity-kit`.
*   `tests/` — suite completa de tests (ver sección Calidad).

---

## Calidad

### Tests unitarios
```bash
uv run pytest tests/unit/
uv run pytest tests/unit/ --cov=src --cov-report=term-missing --cov-fail-under=80
```

### Tests de contrato (arquitectura por capas)
```bash
uv run pytest tests/contract/
```
Verifica: violaciones de capas, contratos de nodos, interface de puertos de transcripción.

### Tests BDD (Gherkin / behave)
```bash
uv run pytest tests/features/
```
Ejecuta los `.feature` files generados por `/iikit-04-testify`.

### Tests de integración (sin mocks)
```bash
uv run pytest tests/integration/
```

### Tests de integración con Gemini (coste real)
Requieren `GOOGLE_API_KEY`:
```bash
uv run pytest tests/ai/
```

### Lint y formato (ruff)
```bash
uv run ruff check .
uv run ruff format --check .
```

---

## Workflow de features

El proyecto usa `tessl-labs/intent-integrity-kit` para disciplinar el ciclo de entrega:

```
/iikit-01-specify   →  spec.md
/iikit-02-plan      →  plan.md
/iikit-04-testify   →  .feature files + test-specs.md (TDD obligatorio por constitución)
/iikit-05-tasks     →  tasks.md dependency-ordered
/iikit-07-implement →  código
```

`CONSTITUTION.md` define los principios no-negociables (Specification-First, Domain Integrity, Test-First, AI Auditability, Iterative Refinement).

---

_Construido para el Programa de Maestría — Arquitectura de Desarrollo._
