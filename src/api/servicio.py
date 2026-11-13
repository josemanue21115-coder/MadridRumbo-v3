"""Lógica de la API (spec 013): traduce lo que llega por HTTP a llamadas al agente y viceversa.

Las rutas de app.py son finas a propósito: la lógica vive aquí para poder probarla aparte.
"""
import uuid
from typing import Any

import config
from src.api.esquemas import AskIn, AskOut
from src.clientes.cargar import cargar_agente
from src.clientes.contrato import estado_vacio

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


def preguntar(datos: AskIn) -> AskOut:
    """Pasa la pregunta al agente y empaqueta su resultado con el formato de la API."""
    # Si la persona no envía identificador, se crea uno nuevo para esta conversación.
    thread_id = datos.thread_id or str(uuid.uuid4())
    resultado = obtener_agente().procesar_turno(estado_vacio(), datos.pregunta, thread_id)
    return AskOut(
        respuesta=resultado["respuesta"],
        thread_id=thread_id,
        done=resultado["done"],
        pendiente_hitl=resultado["hitl_pendiente"],
        plan=resultado["plan"],
        error=_deducir_error(resultado),
    )