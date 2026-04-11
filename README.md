# DDD Studio - Herramienta de Análisis de Dominio y Event Storming

**DDD Studio** es un entorno de trabajo interactivo diseñado para cerrar la brecha entre los talleres de **descubrimiento de flujos de negocio** y la implementación formal de **Diseño Guiado por el Dominio (DDD)**. 

Resuelve el problema de la "documentación estática" convirtiendo transcripciones de talleres y documentos técnicos en **modelos de dominio dinámicos**, visualizados como grafos interactivos y analizados por Inteligencia Artificial agéntica.

---

## 🚀 Características Principales

*   **Event Storming Aumentado por IA**: Generación automática de grafos que distinguen Comandos, Eventos, Agregados y Políticas a partir de texto o audio.
*   **"Arquitecto Senior" de IA**: Asistente especializado en DDD que analiza la arquitectura de tu dominio y sugiere mejoras. (Ver [ARCHITECTURE.md](docs/ARCHITECTURE.md))
*   **Audio y Transcripción**: Sube grabaciones de tus sesiones/talleres. Utiliza **Whisper** para transcribir y extraer elementos automáticamente.
*   **Contexto Optimizado (TOON)**: Utiliza el formato [TOON](docs/TOON_FORMAT.md) para alimentar grandes modelos eficientemente.
*   **Anclaje Lingüístico (spaCy)**: Utiliza motores NLP determísticos para asegurar que la IA respete el Lenguaje Ubicuo y no alucine términos.
*   **Análisis Estructural**: Estadísticas automáticas sobre la complejidad, acoplamiento y cohesión del modelo.

---

## 📦 Instalación y Configuración

### Requisitos Previos
*   Python **3.10.9+**
*   API Key de **Google Gemini** para todo el procesamiento de IA (Análisis y Chat).

### 1. Configuración del Entorno
Crea un archivo `.env` en la raíz del proyecto:
```env
# API Key de Gemini
GOOGLE_API_KEY="tu-api-key"
```

### 2. Instalación con `uv`
Utilizamos `uv` para una gestión de dependencias extremadamente rápida y reproducible:
```bash
# Sincronizar entorno y dependencias
uv sync
```

### 3. Ejecución
```bash
# Iniciar la aplicación Streamlit
uv run streamlit run src/main.py
```

---

## 🧠 Flujo de Trabajo (Knowledge Pipeline)

DDD Studio implementa un ciclo de vida completo **"Del Caos a la Estructura"**:

1.  **Ingesta y Descubrimiento**:
    *   Subida de grabaciones de audio o especificaciones funcionales en PDF.
    *   **Transcripción/OCR**: Whisper convierte el audio en texto con diarización de interlocutores.
2.  **Análisis Semántico (GraphChain)**:
    *   Utilizamos **LangGraph** para orquestar un pipeline agéntico con **Gemini 1.5 Pro**.
    *   Se extraen entidades (Actores, Comandos, Eventos) mapeándolas a modelos estrictos de Pydantic.
3.  **Modelado y Refinamiento**:
    *   **Proyección**: Visualización interactiva del grafo.
    *   **Crítica de la IA**: El asistente analiza el modelo en busca de errores estructurales utilizando el formato **TOON**.
4.  **Validación y Exportación**:
    *   Auditoría de integridad y exportación a esquemas SQL para su uso en analítica de negocio.

---

## 🛠️ Arquitectura Técnica

El proyecto sigue una arquitectura de **Corte Vertical (Vertical Slice)**, separando claramente la lógica de infraestructura, dominio y presentación.

### Estructura de Archivos
```text
studio/
├── src/
│   ├── main.py                 # Punto de entrada
│   ├── application/            # Orquestación de casos de uso y Grafos (LangGraph)
│   ├── domain/                 # Modelos de negocio (Pydantic), Excepciones y Eventos
│   ├── infra/                  # Adaptadores (Gemini, Whisper, Local LLM, Cache)
│   ├── services/               # Lógica de soporte (NLP, Analizadores de completitud)
│   └── ui/                     # Componentes Streamlit y Visualización
├── tests/                      # Suite de pruebas unitarias e integración
└── pyproject.toml              # Configuración de uv y herramientas de calidad
```

### Estrategia de IA
*   **Análisis Pesado**: Google Gemini 1.5/2.5 Pro para manejar ventanas de contexto masivas y salida JSON estructurada con razonamiento DDD profundo.
*   **Interacción de Chat**: El asistente de chat también utiliza Gemini, aprovechando la misma base de conocimiento y capacidades de razonamiento para una asistencia técnica superior.
*   **Orquestación**: LangGraph para ciclos de razonamiento agéntico que permiten refinar el análisis cruzando múltiples fuentes de datos.

---

## 🧪 Calidad y Desarrollo

Mantenemos un estándar riguroso de desarrollo mediante integración continua:

*   **Linting/Formato**: `uv run ruff check .` y `uv run ruff format .`
*   **Pruebas Unitarias**: `uv run pytest tests/unit/`

El pipeline de CI en GitHub Actions garantiza que el código cumpla con estos estándares antes de cualquier despliegue.

---
_Construido para el Programa de Maestría - Arquitectura de Desarrollo._