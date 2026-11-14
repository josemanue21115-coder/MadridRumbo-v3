"""Interfaz Streamlit cliente de la API HTTP de MadridRumbo."""

from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
import streamlit as st

from src.clientes.api_http import APIConnectionError, APIHttpClient, APIHttpError


load_dotenv(Path(__file__).resolve().parent / ".env")
st.set_page_config(page_title="MadridRumbo", page_icon="assets/icono.png")


def inicializar_estado() -> None:
    """Prepara una conversación vacía una sola vez por sesión de Streamlit."""
    valores_iniciales = {
        "api_client": APIHttpClient(),
        "thread_id": None,
        "messages": [],
        "auto_aprobar": False,
        "ask_error": None,
        "pending_question": None,
        "ask_result": None,
        "decision_result": None,
        "decision_error": None,
        "pending_hitl": False,
        "pending_plans": [],
        "selected_plan_id": None,
        "health_status": None,
        "history_error": None,
        "thread_id_to_load": "",
    }
    for clave, valor in valores_iniciales.items():
        if clave not in st.session_state:
            st.session_state[clave] = valor


def mostrar_error_api(error: Exception) -> str:
    """Convierte errores HTTP y de red en mensajes comprensibles para el chat."""
    if isinstance(error, APIHttpError) and error.status_code == 401:
        return "Error de autenticación con la API. Comprueba la configuración de API_KEY."
    if isinstance(error, APIConnectionError):
        return "No se pudo conectar con el servicio. Comprueba que la API esté disponible."
    if isinstance(error, APIHttpError):
        return f"La API devolvió un error: {error}"
    return "No se pudo completar la consulta. Inténtalo de nuevo."


def nueva_conversacion() -> None:
    """Desvincula la sesión del hilo actual y limpia los datos de presentación."""
    st.session_state.thread_id = None
    st.session_state.messages = []
    st.session_state.ask_error = None
    st.session_state.pending_question = None
    st.session_state.ask_result = None
    st.session_state.decision_result = None
    st.session_state.decision_error = None
    st.session_state.pending_hitl = False
    st.session_state.pending_plans = []
    st.session_state.selected_plan_id = None


def comprobar_estado() -> None:
    """Consulta health solo por acción explícita y conserva el último resultado."""
    try:
        resultado = st.session_state.api_client.health()
        st.session_state.health_status = resultado.get("estado") == "ok"
    except (APIHttpError, APIConnectionError):
        st.session_state.health_status = False


def cargar_historial(thread_id: str) -> None:
    """Carga y valida el historial antes de sustituir el hilo y los mensajes visibles."""
    thread_id = thread_id.strip()
    st.session_state.history_error = None
    if not thread_id:
        st.session_state.history_error = "Escribe el identificador de la conversación que quieres cargar."
        return

    try:
        resultado = st.session_state.api_client.messages(thread_id)
    except APIHttpError as error:
        if error.status_code == 501:
            st.session_state.history_error = "El historial todavía no está implementado en la API."
        else:
            st.session_state.history_error = f"No se pudo cargar la conversación: {error}"
        return
    except APIConnectionError:
        st.session_state.history_error = "No se pudo cargar la conversación porque el servicio no está disponible."
        return

    if isinstance(resultado, list):
        registros = resultado
    else:
        registros = resultado.get("mensajes") if isinstance(resultado, dict) else None
    if not isinstance(registros, list):
        st.session_state.history_error = "La API devolvió un historial con formato no válido."
        return

    normalizados = []
    for registro in registros:
        if (
            not isinstance(registro, dict)
            or not isinstance(registro.get("role"), str)
            or not isinstance(registro.get("content"), str)
            or not isinstance(registro.get("orden"), (int, float))
        ):
            st.session_state.history_error = "La API devolvió un historial con formato no válido."
            return
        rol_original = registro["role"]
        normalizados.append(
            {
                "role": rol_original if rol_original in ("user", "assistant") else "other",
                "original_role": rol_original,
                "content": registro["content"],
                "orden": registro["orden"],
            }
        )

    normalizados.sort(key=lambda mensaje: mensaje["orden"])
    st.session_state.thread_id = thread_id
    st.session_state.messages = normalizados


def enviar_pregunta(pregunta: str) -> None:
    """Envía una pregunta al hilo activo y guarda solo los datos devueltos por la API."""
    st.session_state.ask_error = None
    st.session_state.decision_result = None
    st.session_state.decision_error = None
    clave_api = getattr(st.session_state.api_client, "api_key", None)
    if clave_api is None:
        clave_api = os.getenv("API_KEY", "")
    if not isinstance(clave_api, str) or not clave_api.strip():
        st.session_state.ask_error = "Falta configurar API_KEY. Añádela a tu archivo .env local y reinicia Streamlit."
        st.session_state.pending_question = pregunta
        return
    try:
        resultado = st.session_state.api_client.ask(
            pregunta=pregunta,
            thread_id=st.session_state.thread_id,
            auto_aprobar=st.session_state.auto_aprobar,
        )
    except (APIHttpError, APIConnectionError) as error:
        st.session_state.ask_error = mostrar_error_api(error)
        st.session_state.pending_question = pregunta
        return

    st.session_state.pending_question = None
    thread_id = resultado.get("thread_id")
    if isinstance(thread_id, str) and thread_id.strip():
        st.session_state.thread_id = thread_id
    st.session_state.ask_result = resultado
    st.session_state.pending_hitl = resultado.get("pendiente_hitl") is True
    planes = resultado.get("plan")
    st.session_state.pending_plans = planes if st.session_state.pending_hitl and isinstance(planes, list) else []
    st.session_state.selected_plan_id = None
    st.session_state.messages.extend(
        [
            {"role": "user", "content": pregunta},
            {"role": "assistant", "content": resultado.get("respuesta", "")},
        ]
    )


def decidir_plan(aprobado: bool) -> None:
    """Envía la decisión y recarga el historial sin perder el chat si falla."""
    thread_id = st.session_state.thread_id
    planes = st.session_state.pending_plans
    if not st.session_state.pending_hitl or not thread_id:
        return

    plan_id = st.session_state.selected_plan_id if len(planes) > 1 else None
    st.session_state.decision_error = None
    try:
        resultado = st.session_state.api_client.approve(
            thread_id=thread_id,
            aprobado=aprobado,
            plan_id=plan_id,
        )
    except (APIHttpError, APIConnectionError) as error:
        st.session_state.decision_error = mostrar_error_api(error)
        return

    st.session_state.decision_result = resultado
    st.session_state.pending_hitl = resultado.get("pendiente_hitl") is True
    planes_resultado = resultado.get("plan")
    st.session_state.pending_plans = (
        planes_resultado if st.session_state.pending_hitl and isinstance(planes_resultado, list) else []
    )
    st.session_state.selected_plan_id = None
    # cargar_historial solo reemplaza el estado visible después de validar toda la respuesta.
    cargar_historial(thread_id)


inicializar_estado()

with st.sidebar:
    st.image("assets/icono.png", width=80)
    st.subheader("Conversación")
    st.checkbox(
        "Aprobar automáticamente un único plan",
        value=False,
        key="auto_aprobar",
    )
    columna_health, columna_estado = st.columns([1, 2])
    if columna_health.button("Comprobar estado"):
        comprobar_estado()
    if st.session_state.health_status is True:
        columna_estado.success("🟢 Backend disponible")
    elif st.session_state.health_status is False:
        columna_estado.error("🔴 Backend no disponible")

    if st.session_state.thread_id:
        st.caption(f"Hilo activo: {st.session_state.thread_id}")

    if st.session_state.pending_hitl:
        st.subheader("Planes pendientes")
        for indice, plan in enumerate(st.session_state.pending_plans, start=1):
            st.markdown(f"**Plan {indice}**")
            st.json(plan)
        ids_planes = [
            plan.get("id") for plan in st.session_state.pending_plans
            if isinstance(plan, dict) and isinstance(plan.get("id"), str)
        ]
        if len(ids_planes) > 1:
            st.session_state.selected_plan_id = st.radio(
                "Plan a decidir", ids_planes, key="plan_selector"
            )
        columna_aprobar, columna_rechazar = st.columns(2)
        if columna_aprobar.button("Aprobar", type="primary"):
            decidir_plan(aprobado=True)
            st.rerun()
        if columna_rechazar.button("Rechazar"):
            decidir_plan(aprobado=False)
            st.rerun()

    st.text_input("ID de conversación", key="thread_id_to_load")
    if st.button("Cargar conversación"):
        cargar_historial(st.session_state.thread_id_to_load)
        st.rerun()
    if st.session_state.history_error:
        st.error(st.session_state.history_error)
    if st.button("Nueva conversación"):
        nueva_conversacion()
        st.rerun()

st.title("MadridRumbo — Asistente de transporte de Madrid")

for mensaje in st.session_state.messages:
    rol = mensaje["role"]
    if rol == "other":
        with st.chat_message("assistant", avatar="❔"):
            st.caption(f"Mensaje de rol {mensaje['original_role']}")
            st.write(mensaje["content"])
        continue
    with st.chat_message("user" if rol == "user" else "assistant"):
        st.write(mensaje["content"])

if st.session_state.ask_error:
    st.error(st.session_state.ask_error)
if st.session_state.ask_result and st.session_state.ask_result.get("error"):
    st.warning(st.session_state.ask_result["error"])
if st.session_state.decision_result:
    respuesta_decision = st.session_state.decision_result.get("respuesta")
    if respuesta_decision:
        st.info(respuesta_decision)
    if st.session_state.decision_result.get("error"):
        st.warning(st.session_state.decision_result["error"])
if st.session_state.decision_error:
    st.error(st.session_state.decision_error)
if st.session_state.history_error:
    st.error(st.session_state.history_error)
if st.session_state.pending_question:
    st.info(f"Pregunta conservada para que puedas volver a enviarla: {st.session_state.pending_question}")

pregunta = st.chat_input("Escribe tu pregunta sobre transporte en Madrid...")
if pregunta:
    with st.chat_message("user"):
        st.write(pregunta)
    with st.chat_message("assistant"), st.spinner("Consultando al asistente..."):
        enviar_pregunta(pregunta)
    if st.session_state.ask_error:
        st.error(st.session_state.ask_error)
        if st.session_state.pending_question:
            st.info(f"Pregunta conservada para que puedas volver a enviarla: {st.session_state.pending_question}")
    else:
        st.rerun()
