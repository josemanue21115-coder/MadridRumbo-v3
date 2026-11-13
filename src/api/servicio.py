"""Lógica de la API (spec 013): traduce lo que llega por HTTP a llamadas al agente y viceversa.

Las rutas de app.py son finas a propósito: la lógica vive aquí para poder probarla aparte.
"""
import uuid
from typing import Any

import config
from src.api.esquemas import ApproveIn, AskIn, AskOut
from src.clientes.cargar import cargar_agente
from src.clientes.contrato import estado_vacio
from src.clientes.planes import ids_de_planes

# El agente se carga una sola vez y se reutiliza: guarda las conversaciones en memoria,
# así que crear uno nuevo en cada petición le haría olvidar los planes pendientes.
_agente: Any = None

# Plan pendiente de cada conversación, por thread_id. El agente simulado necesita recibirlo
# para poder aprobar; el real lo recupera él solo de su memoria y lo ignora.
_planes_pendientes: dict[str, list] = {}


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


def _recordar_plan(thread_id: str, resultado: dict) -> None:
    """Apunta el plan pendiente de la conversación, o lo borra cuando ya no hay ninguno."""
    # Un rechazo de control (por ejemplo, "indica qué plan") no cambia lo que está pendiente.
    if _deducir_error(resultado) is not None:
        return
    if resultado["hitl_pendiente"] and resultado["plan"]:
        _planes_pendientes[thread_id] = resultado["plan"]
    else:
        _planes_pendientes.pop(thread_id, None)


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
    _recordar_plan(thread_id, resultado)

    # Aprobación automática: solo si se pide, hay un plan esperando y es uno único.
    # Con varios planes la API no elige por la persona (RF-9).
    if (
        datos.auto_aprobar
        and resultado["hitl_pendiente"]
        and len(ids_de_planes(resultado["plan"])) == 1
    ):
        estado = {**estado_vacio(), "plan": resultado["plan"]}
        resultado = agente.aprobar_plan(estado, thread_id, True)
        _recordar_plan(thread_id, resultado)

    return _a_respuesta(resultado, thread_id)


def aprobar(datos: ApproveIn) -> AskOut:
    """Aprueba o rechaza el plan pendiente de una conversación (RF-10 a RF-13)."""
    estado = {**estado_vacio(), "plan": _planes_pendientes.get(datos.thread_id, [])}
    # Solo hace falta indicar el plan cuando hay varios pendientes.
    if datos.plan_id:
        estado["plan_id_seleccionado"] = datos.plan_id
    resultado = obtener_agente().aprobar_plan(estado, datos.thread_id, datos.aprobado)
    _recordar_plan(datos.thread_id, resultado)
    return _a_respuesta(resultado, datos.thread_id)