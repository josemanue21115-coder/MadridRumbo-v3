"""Lógica de la API (spec 013): traduce lo que llega por HTTP a llamadas al agente y viceversa.

Las rutas de app.py son finas a propósito: la lógica vive aquí para poder probarla aparte.
"""
import uuid
from typing import Any

import config
from src.api.esquemas import AskIn, AskOut
from src.clientes.cargar import cargar_agente
from src.clientes.contrato import estado_vacio
from src.clientes.planes import ids_de_planes

# El agente se carga una sola vez y se reutiliza: guarda las conversaciones en memoria,
# así que crear uno nuevo en cada petición le haría olvidar los planes pendientes.
_agente: Any = None


def obtener_agente() -> Any:
    """Devuelve el agente (real o simulado, según el entorno), cargándolo la primera vez."""
    global _agente
    if _agente is None:
        agente, _aviso = cargar_agente()
        _agente = agente
    return _agente


def _deducir_error(resultado: dict) -> str | None:
    """Devuelve el aviso si el agente rechazó la consulta por una regla de control; si no, None."""
    for entrada in resultado.get("log") or []:
        if entrada.get("tipo") == "control" and entrada.get("resultado") == "rechazado":
            return resultado.get("respuesta") or config.API_AVISO_RECHAZO_GENERICO
    return None


def _a_respuesta(resultado: dict, thread_id: str) -> AskOut:
    """Empaqueta el resultado del agente con el formato de salida de la API."""
    return AskOut(
        respuesta=resultado["respuesta"],
        thread_id=thread_id,
        done=resultado["done"],
        pendiente_hitl=resultado["hitl_pendiente"],
        plan=resultado["plan"],
        error=_deducir_error(resultado),
    )


def preguntar(datos: AskIn) -> AskOut:
    """Pasa la pregunta al agente y, si procede, aprueba solo el plan pendiente."""
    # Si la persona no envía identificador, se crea uno nuevo para esta conversación.
    thread_id = datos.thread_id or str(uuid.uuid4())
    agente = obtener_agente()
    resultado = agente.procesar_turno(estado_vacio(), datos.pregunta, thread_id)

    # Aprobación automática: solo si se pide, hay un plan esperando y es uno único.
    # Con varios planes la API no elige por la persona (RF-9).
    if (
        datos.auto_aprobar
        and resultado["hitl_pendiente"]
        and len(ids_de_planes(resultado["plan"])) == 1
    ):
        # El agente real recupera el plan de su memoria; el simulado lo lee de este estado.
        estado = {**estado_vacio(), "plan": resultado["plan"]}
        resultado = agente.aprobar_plan(estado, thread_id, True)

    return _a_respuesta(resultado, thread_id)