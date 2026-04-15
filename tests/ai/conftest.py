"""Shared fixtures and markers for AI prompt functional tests."""

from __future__ import annotations

import os

import pytest
from infra.adapters.gemini_inference import GeminiInferenceAdapter

AI_SKIP = pytest.mark.skipif(
    not os.environ.get("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY not set — skipping AI prompt tests",
)


@pytest.fixture(scope="module")
def llm_adapter() -> GeminiInferenceAdapter:
    """Real Gemini adapter with hardcoded greedy decoding."""
    return GeminiInferenceAdapter()


@pytest.fixture(scope="module")
def sample_transcript() -> str:
    """Realistic Event Storming transcript in Spanish about car insurance policy cancellation."""
    return """
    === SESIÓN DE EVENT STORMING — CANCELACIÓN DE PÓLIZA DE SEGURO DE AUTOMÓVIL ===

    Participantes: Ana (Cliente), Carlos (Agente de Seguros), equipo técnico

    --- BIG PICTURE ---

    El Cliente (Actor) inicia el proceso enviando una solicitud formal de cancelación.
    Comando: SolicitarCancelacion — el cliente llena el formulario de baja en el portal web.

    El Agente (Actor) recibe la solicitud y ejecuta el Comando: VerificarIdentidad,
    comprobando documentos del titular contra el CRM (Sistema Externo).

    Una vez verificada la identidad, el sistema evalúa el estado de la Póliza (Agregado).
    Si la póliza no tiene siniestros abiertos, se emite el Evento: PolizaCancelada.

    ⚠️ HOTSPOT: ¿Qué sucede si la póliza tiene un siniestro en proceso?
    El equipo no llegó a un acuerdo. Opciones: bloquear la cancelación o permitirla con advertencia.

    Tras la cancelación, el Agregado Reembolso calcula el monto proporcional al tiempo restante.
    Comando: ProcesarReembolso — se envía solicitud al SistemaPagos (Sistema Externo).
    Evento: ReembolsoProcesado — confirmación recibida desde SistemaPagos.

    El CRM (Sistema Externo) se actualiza con el nuevo estado del cliente.
    Evento: NotificacionEnviada — se envía email y SMS de confirmación al Cliente.

    Read Model: EstadoPolizaView — muestra el estado actual de la póliza, fechas de vigencia,
    número de siniestros y monto del reembolso pendiente. Usado por el Agente y el Cliente.

    --- RESUMEN DE ELEMENTOS ---

    Actores: Cliente, Agente
    Comandos: SolicitarCancelacion, VerificarIdentidad, ProcesarReembolso
    Eventos: PolizaCancelada, ReembolsoProcesado, NotificacionEnviada
    Agregados: Poliza, Reembolso
    Sistemas Externos: SistemaPagos, CRM
    Read Models: EstadoPolizaView
    Hotspot: Póliza con siniestro abierto al momento de la cancelación
    """


@pytest.fixture(scope="module")
def sample_domain_analysis_json() -> str:
    """Minimal but complete DomainAnalysis JSON for the car insurance cancellation domain."""
    return """{
  "nombre_proyecto": "Cancelacion de Poliza de Seguro de Automovil",
  "version": "1.0.0",
  "fecha_analisis": "2026-03-20",
  "big_picture": {
    "descripcion": "Flujo de cancelacion de poliza de seguro de automovil iniciado por el cliente.",
    "nodos": [
      {
        "id": "actor_cliente",
        "tipo_elemento": "Actor",
        "nombre": "Cliente",
        "descripcion": "Titular de la poliza que solicita la cancelacion.",
        "estado_comparativo": "existente",
        "nivel": "big_picture"
      },
      {
        "id": "cmd_solicitar_cancelacion",
        "tipo_elemento": "Comando",
        "nombre": "SolicitarCancelacion",
        "descripcion": "Comando que inicia el proceso de baja de la poliza.",
        "estado_comparativo": "existente",
        "nivel": "big_picture"
      },
      {
        "id": "agg_poliza",
        "tipo_elemento": "Agregado",
        "nombre": "Poliza",
        "descripcion": "Agregado que representa la poliza de seguro del automovil.",
        "estado_comparativo": "existente",
        "nivel": "big_picture"
      },
      {
        "id": "evt_poliza_cancelada",
        "tipo_elemento": "Evento",
        "nombre": "PolizaCancelada",
        "descripcion": "Evento que indica que la poliza ha sido dada de baja exitosamente.",
        "estado_comparativo": "existente",
        "nivel": "big_picture"
      },
      {
        "id": "sis_crm",
        "tipo_elemento": "Sistema Externo",
        "nombre": "CRM",
        "descripcion": "Sistema externo de gestion de relaciones con clientes.",
        "estado_comparativo": "existente",
        "nivel": "big_picture"
      }
    ],
    "aristas": [
      {
        "fuente": "actor_cliente",
        "destino": "cmd_solicitar_cancelacion",
        "descripcion": "El cliente emite el comando de cancelacion.",
        "estado_comparativo": "existente"
      },
      {
        "fuente": "cmd_solicitar_cancelacion",
        "destino": "agg_poliza",
        "descripcion": "El comando actua sobre el agregado Poliza.",
        "estado_comparativo": "existente"
      },
      {
        "fuente": "agg_poliza",
        "destino": "evt_poliza_cancelada",
        "descripcion": "El agregado produce el evento de cancelacion.",
        "estado_comparativo": "existente"
      },
      {
        "fuente": "evt_poliza_cancelada",
        "destino": "sis_crm",
        "descripcion": "El evento notifica al CRM para actualizar el estado del cliente.",
        "estado_comparativo": "existente"
      }
    ]
  },
  "agregados": [
    {
      "nombre_agregado": "Poliza",
      "entidad_raiz": "Poliza",
      "descripcion": "Agregado que gestiona el ciclo de vida de la poliza de seguro.",
      "nodos": [
        {
          "id": "cmd_verificar_identidad",
          "tipo_elemento": "Comando",
          "nombre": "VerificarIdentidad",
          "descripcion": "Valida la identidad del titular antes de procesar la cancelacion.",
          "estado_comparativo": "existente",
          "nivel": "process_level"
        },
        {
          "id": "evt_identidad_verificada",
          "tipo_elemento": "Evento",
          "nombre": "IdentidadVerificada",
          "descripcion": "Confirmacion de que la identidad del cliente ha sido validada.",
          "estado_comparativo": "existente",
          "nivel": "process_level"
        }
      ],
      "aristas": [
        {
          "fuente": "cmd_verificar_identidad",
          "destino": "evt_identidad_verificada",
          "descripcion": "El comando de verificacion produce el evento de confirmacion.",
          "estado_comparativo": "existente"
        }
      ]
    }
  ],
  "read_models": [
    {
      "nombre": "EstadoPolizaView",
      "descripcion": "Vista que muestra el estado actual de la poliza, incluyendo siniestros y reembolsos pendientes.",
      "proyecta": ["evt_poliza_cancelada"],
      "ui_policies": null,
      "tecnologias": null
    }
  ],
  "politicas_inter_agregados": [],
  "responsables": ["Cliente", "Agente de Seguros"],
  "notas": "Hotspot pendiente: comportamiento cuando existe un siniestro abierto al momento de la cancelacion."
}"""


@pytest.fixture(scope="module")
def sample_csv_context() -> str:
    """Plain text representation of the domain model (nodes + edges tables) for agent prompts."""
    return """=== NODOS DEL MODELO ===
id,tipo_elemento,nombre,nivel,descripcion
actor_cliente,Actor,Cliente,big_picture,Titular de la poliza que solicita la cancelacion
cmd_solicitar_cancelacion,Comando,SolicitarCancelacion,big_picture,Comando que inicia el proceso de baja de la poliza
agg_poliza,Agregado,Poliza,big_picture,Agregado que representa la poliza de seguro del automovil
evt_poliza_cancelada,Evento,PolizaCancelada,big_picture,Evento que indica que la poliza ha sido dada de baja
sis_crm,Sistema Externo,CRM,big_picture,Sistema externo de gestion de relaciones con clientes
cmd_verificar_identidad,Comando,VerificarIdentidad,process_level,Valida la identidad del titular antes de cancelar
evt_identidad_verificada,Evento,IdentidadVerificada,process_level,Confirmacion de identidad validada

=== ARISTAS DEL MODELO ===
fuente,destino,descripcion
actor_cliente,cmd_solicitar_cancelacion,El cliente emite el comando de cancelacion
cmd_solicitar_cancelacion,agg_poliza,El comando actua sobre el agregado Poliza
agg_poliza,evt_poliza_cancelada,El agregado produce el evento de cancelacion
evt_poliza_cancelada,sis_crm,El evento notifica al CRM para actualizar el estado
cmd_verificar_identidad,evt_identidad_verificada,El comando de verificacion produce el evento de confirmacion

=== READ MODELS ===
nombre,descripcion,proyecta
EstadoPolizaView,Vista del estado actual de la poliza con siniestros y reembolsos,evt_poliza_cancelada

=== NOTAS ===
Hotspot: comportamiento cuando existe un siniestro abierto al momento de la cancelacion.
"""
