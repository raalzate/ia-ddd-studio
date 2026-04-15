from typing import Literal

from pydantic import BaseModel, Field, model_validator

# === TIPOS DE ELEMENTOS POR NIVEL DE EVENT STORMING ===
ElementType = Literal[
    "Actor",
    "Sistema Externo",
    "Hotspot",
    "Comando",
    "Evento",
    "Política",
    "Entidad Raíz",
    "Agregado",
    "Read Model",
    "Vista",
    "Proyección",
    "Regla de Negocio",
    "Política de UI",
]

ComparativeState = Literal["nuevo", "modificado", "existente", "eliminado"]


# === 1. NODO DEL GRAFO ===
class NodoGrafo(BaseModel):
    """
    Define un nodo genérico dentro del grafo de dominio.
    Representa cualquier elemento modelado (ej. Evento, Comando, Actor)
    en los distintos niveles de análisis.
    """

    id: str = Field(..., description="Identificador único del nodo, preferiblemente semántico.")
    tipo_elemento: ElementType = Field(..., description="Clasificación del nodo según la taxonomía de Event Storming.")
    nombre: str = Field(
        ...,
        description="Nombre del elemento expresado en el Lenguaje Ubicuo del dominio, agrega en paréntesis una referencia si existe.",
    )
    descripcion: str = Field(
        ...,
        description="Descripción detallada del propósito o responsabilidad del nodo dentro del dominio.",
    )
    estado_comparativo: ComparativeState = Field(
        "existente",
        description="Estado del nodo de una comparación que se menciona de su existencia o modificación del mismo (nuevo, modificado, existente, eliminado).",
    )
    tags_tecnologia: list[str] | None = Field(
        None,
        description="Lista de etiquetas que identifican tecnologías o plataformas asociadas al nodo.",
    )
    nivel: Literal["big_picture", "process_level", "read_model"] = Field(
        ...,
        description="Nivel de abstracción del análisis (Big Picture, Process Level, Read Model) al que pertenece el nodo.",
    )


# === 2. ARISTA DEL GRAFO ===
class AristaGrafo(BaseModel):
    """
    Define una relación direccional (arista) entre dos nodos del grafo de dominio.
    """

    fuente: str = Field(..., description="Identificador (ID) del nodo de origen de la relación.")
    destino: str = Field(..., description="Identificador (ID) del nodo de destino de la relación.")
    descripcion: str = Field(
        ...,
        description="Descripción semántica de la relación (ej. 'dispara', 'produce', 'proyecta').",
    )
    estado_comparativo: ComparativeState = Field(
        "existente",
        description="Estado de la arista resultante de una comparación entre versiones del modelo.",
    )


# === 3. GRAFO POR AGREGADO (Process Level) ===
class GrafoPorAgregado(BaseModel):
    """
    Modelo detallado (Process Level) que encapsula el comportamiento
    y los elementos de un Agregado (Aggregate).
    """

    nombre_agregado: str = Field(..., description="Nombre del Agregado según el Lenguaje Ubicuo.")
    entidad_raiz: str = Field(
        ...,
        description="Nombre de la Entidad Raíz (Root Entity) que define la identidad del Agregado.",
    )
    descripcion: str | None = Field(
        None, description="Descripción del propósito y la responsabilidad de negocio del Agregado."
    )
    nodos: list[NodoGrafo] = Field(..., description="Lista de nodos que componen el modelo interno del Agregado.")
    aristas: list[AristaGrafo] = Field(
        ..., description="Lista de aristas que definen las relaciones internas del Agregado."
    )

    @model_validator(mode="after")
    def strip_orphan_edges(self) -> "GrafoPorAgregado":
        node_ids = {n.id for n in self.nodos}
        self.aristas = [e for e in self.aristas if e.fuente in node_ids and e.destino in node_ids]
        return self


# === 4. READ MODEL ===
class ReadModel(BaseModel):
    """
    Define un modelo de lectura (proyección) optimizado para consultas,
    UI o reportes (lado 'Query' de CQRS).
    """

    nombre: str = Field(..., description="Nombre identificativo del modelo de lectura o proyección.")
    descripcion: str | None = Field(None, description="Descripción del propósito de la vista o los datos que expone.")
    proyecta: list[str] = Field(
        ...,
        description="Lista de identificadores (IDs) de los Eventos de Dominio que actualizan este modelo.",
    )
    ui_policies: list[str] | None = Field(
        None,
        description="Lista de reglas o políticas específicas de la interfaz de usuario asociadas a esta vista.",
    )
    tecnologias: list[str] | None = Field(
        None,
        description="Tecnologías específicas de implementación (ej. Frontend, Base de datos de lectura).",
    )


# === 5. BIG PICTURE (nivel de alto nivel) ===
class BigPicture(BaseModel):
    """
    Representa la visión de alto nivel del dominio (Nivel 'Big Picture').
    """

    descripcion: str = Field(..., description="Descripción narrativa de alto nivel del flujo de negocio principal.")
    nodos: list[NodoGrafo] = Field(..., description="Lista de nodos principales que componen la visión 'Big Picture'.")
    aristas: list[AristaGrafo] = Field(
        ..., description="Lista de aristas que definen el flujo principal de alto nivel."
    )

    @model_validator(mode="after")
    def strip_orphan_edges(self) -> "BigPicture":
        node_ids = {n.id for n in self.nodos}
        self.aristas = [e for e in self.aristas if e.fuente in node_ids and e.destino in node_ids]
        return self


# === 6. MODELO COMPLETO DE ANÁLISIS DE DOMINIO ===
class DomainAnalysis(BaseModel):
    """
    Modelo raíz que consolida el análisis de dominio completo
    basado en Event Storming.
    """

    nombre_proyecto: str = Field(..., description="Nombre identificativo del proyecto o iniciativa de software.")
    version: str = Field("1.0.0", description="Control de versiones semántico del modelo de dominio.")
    fecha_analisis: str = Field(
        ..., description="Fecha de realización o actualización del análisis (formato ISO 8601)."
    )

    big_picture: BigPicture = Field(..., description="El modelo 'Big Picture' que describe el contexto general.")
    agregados: list[GrafoPorAgregado] = Field(
        ..., description="Colección de los modelos de proceso (Process Level) para cada Agregado."
    )
    read_models: list[ReadModel] = Field(
        default_factory=list,
        description="Colección de los modelos de lectura (proyecciones) definidos.",
    )
    politicas_inter_agregados: list[AristaGrafo] = Field(
        default_factory=list,
        description="Lista de aristas que representan políticas o flujos (eventos) que conectan diferentes Agregados.",
    )
    responsables: list[str] | None = Field(
        None, description="Lista de los participantes o responsables clave del análisis de dominio."
    )
    notas: str | None = Field(
        None, description="Notas, comentarios u observaciones generales sobre el modelo de dominio."
    )
    ddd_specs: dict[str, str | None] | None = Field(
        default_factory=dict,
        description="Modelos y especificaciones generadas en formato texto o PlantUML (ej. context_map, domain_model).",
    )

    @model_validator(mode="after")
    def strip_orphan_inter_aggregate_edges(self) -> "DomainAnalysis":
        all_node_ids = {n.id for n in self.big_picture.nodos}
        for agg in self.agregados:
            all_node_ids.update(n.id for n in agg.nodos)
        self.politicas_inter_agregados = [
            e for e in self.politicas_inter_agregados if e.fuente in all_node_ids and e.destino in all_node_ids
        ]
        return self

    @model_validator(mode="after")
    def strip_orphan_nodes(self) -> "DomainAnalysis":
        """Remove nodes that have zero connections across ALL edge sources."""
        # Collect every referenced node ID from all edge lists
        connected_ids: set[str] = set()
        for e in self.big_picture.aristas:
            connected_ids.add(e.fuente)
            connected_ids.add(e.destino)
        for agg in self.agregados:
            for e in agg.aristas:
                connected_ids.add(e.fuente)
                connected_ids.add(e.destino)
        for e in self.politicas_inter_agregados:
            connected_ids.add(e.fuente)
            connected_ids.add(e.destino)

        # Strip orphan nodes from big_picture and each aggregate
        self.big_picture.nodos = [n for n in self.big_picture.nodos if n.id in connected_ids]
        for agg in self.agregados:
            agg.nodos = [n for n in agg.nodos if n.id in connected_ids]
        return self
