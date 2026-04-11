# Arquitectura y Diseño Técnico

## Descripción General

**DDD Studio** es una plataforma modular construida con **Streamlit** y **LangGraph**, diseñada para transformar sesiones de Event Storming en modelos de dominio estructurados. La arquitectura sigue principios de **Corte Vertical (Vertical Slice)** para asegurar la cohesión de las funcionalidades desde la UI hasta la infraestructura.

## Estructura del Proyecto

El código fuente se organiza bajo el directorio `src/` para separar la lógica de negocio de la configuración del entorno.

```text
studio/
├── src/
│   ├── main.py                     # Punto de entrada de la aplicación
│   ├── application/                # Orquestación de Grafos de Estado y Nodos (LangGraph)
│   │   ├── nodes/                  # Nodos individuales del pipeline (transcribe, analyze, etc.)
│   │   └── graph_builder.py        # Constructor del StateGraph
│   ├── domain/                     # Corazón del negocio
│   │   ├── models/                 # Definiciones Pydantic (DomainAnalysis, Nodes, Edges)
│   │   ├── ports/                  # Interfaces (InferencePort, TranscriptionPort)
│   │   └── exceptions.py           # Excepciones de dominio a medida
│   ├── infra/                      # Implementaciones técnicas (Adaptadores)
│   │   └── adapters/               # Gemini, Whisper, Cache, FileStorage
│   ├── services/                   # Lógica de soporte y algoritmos complejos (NLP)
│   └── ui/                         # Capa de presentación Streamlit
│       ├── components/             # Fragmentos de UI (Chat, Results, Input)
│       └── visualization/          # Renderizado de grafos con Graphviz
└── tests/                          # Suite de pruebas automatizadas
```

## Componentes Clave

### 1. Sistema de Inferencia Híbrido
El sistema utiliza ahora un enfoque centrado en la nube para maximizar la calidad del análisis:

*   **Motor de Inferencia (Remote)**: Se utiliza **Google Gemini 1.5/2.5 Pro** via API. Su ventana de contexto masiva permite procesar transcripciones completas sin pérdida de información.
*   **Agente de Chat**: También integrado con Gemini, lo que permite al "Arquitecto Senior" tener una visión completa y coherente del modelo generado.

### 2. Motor de Anclaje Determinístico (spaCy)
Antes de enviar cualquier transcripción al LLM, el sistema utiliza **spaCy** (modelo `es_core_news_md`) para una extracción lingüística de bajo nivel.
*   **Propósito**: Identificar sustantivos y verbos reales en el texto original.
*   **Anclaje**: Estos términos se inyectan en el prompt del LLM como "anclas", forzando a la IA a utilizarlos para definir actores, comandos y agregados.
*   **Beneficio**: Elimina alucinaciones terminológicas y garantiza que se respete el **Lenguaje Ubicuo** definido por los expertos de dominio en la sesión.

### 3. Orquestación con LangGraph (`application/`)
El flujo de procesamiento no es lineal. Utilizamos un Grafo de Estados (`StateGraph`) para manejar la lógica de:
*   **Caché**: Si ya existe una transcripción para un audio, se salta el paso de Whisper.
*   **Refinamiento**: Si se proporciona documentación extra (PDF), se activa un nodo de refinamiento que cruza datos.

### 3. Modelo de Datos Pydantic (`domain/models/`)
El objeto `DomainAnalysis` es la "Única Fuente de Verdad". Garantiza que cualquier cambio en la UI o sugerencia de la IA cumpla con el esquema estructural antes de ser persistido.

---

## Flujo de Datos (Pipeline)

1.  **Ingesta**: Sube audio o PDF.
2.  **Procesamiento Crudo**: Whisper (Faster-Whisper) genera el texto base.
3.  **Extracción Semántica**: Gemini analiza el texto y devuelve un JSON estructurado según el modelo DDD.
4.  **Proyección Visual**: La UI renderiza el JSON en un grafo interactivo.
5.  **Refinamiento Interactivo**: El usuario conversa con el asistente para ajustar detalles, lo cual actualiza el objeto `DomainAnalysis` en tiempo real.

---
_Para detalles sobre el formato de intercambio con la IA, ver [TOON_FORMAT.md](./TOON_FORMAT.md)._