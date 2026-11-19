"""Pruebas AppTest del chat HTTP de Streamlit, con cliente simulado."""

from pathlib import Path
import re

import pytest
from streamlit.testing.v1 import AppTest

import src.clientes.api_http as api_http
from src.clientes.api_http import APIConnectionError, APIHttpError
import src.clientes.cargar as cargar
from src.clientes.contrato import estado_vacio


FRONT = Path(__file__).resolve().parents[1] / "front.py"


class ClienteFalso:
    """Doble del cliente HTTP que registra las preguntas y devuelve un hilo nuevo."""

    instancias = []

    def __init__(self, *args, **kwargs):
        self.preguntas = []
        self.ask_error = None
        self.ask_result = None
        self.aprobaciones = []
        self.approve_result = {
            "respuesta": "Decisión registrada",
            "thread_id": "hilo-generado-1",
            "done": False,
            "pendiente_hitl": False,
            "plan": [],
            "error": None,
        }
        self.health_calls = 0
        self.health_error = None
        self.historial_llamadas = []
        self.historial_resultado = {"mensajes": []}
        self.historial_error = None
        self.__class__.instancias.append(self)

    def ask(self, pregunta, thread_id=None, auto_aprobar=False):
        self.preguntas.append(
            {"pregunta": pregunta, "thread_id": thread_id, "auto_aprobar": auto_aprobar}
        )
        if self.ask_error:
            raise self.ask_error
        return self.ask_result or {
            "respuesta": f"Respuesta a: {pregunta}",
            "thread_id": thread_id or "hilo-generado-1",
            "done": False,
            "pendiente_hitl": False,
            "plan": [],
            "error": None,
        }

    def approve(self, thread_id, aprobado, plan_id=None):
        llamada = {"thread_id": thread_id, "aprobado": aprobado}
        if plan_id is not None:
            llamada["plan_id"] = plan_id
        self.aprobaciones.append(llamada)
        return self.approve_result

    def health(self):
        self.health_calls += 1
        if self.health_error:
            raise self.health_error
        return {"estado": "ok"}

    def messages(self, thread_id):
        self.historial_llamadas.append(thread_id)
        if self.historial_error:
            raise self.historial_error
        return self.historial_resultado


class GrafoFalsoSeguro:
    """Evita que AppTest invoque cualquier modelo durante la transición T3/T4."""

    def procesar_turno(self, estado, mensaje, thread_id):
        resultado = estado_vacio()
        resultado["respuesta"] = f"Respuesta a: {mensaje}"
        return resultado

    def aprobar_plan(self, estado, thread_id, aprobado):
        return estado_vacio()


def iniciar_front(monkeypatch, api_key="clave-de-test"):
    ClienteFalso.instancias.clear()
    monkeypatch.setattr(api_http, "APIHttpClient", ClienteFalso)
    monkeypatch.setenv("API_KEY", api_key)
    monkeypatch.delenv("API_BASE_URL", raising=False)
    monkeypatch.setattr(cargar, "cargar_agente", lambda: (GrafoFalsoSeguro(), None))
    return AppTest.from_file(str(FRONT), default_timeout=10).run()


def enviar(app, texto):
    app.chat_input[0].set_value(texto).run()
    assert not app.exception
    return app


def cargar_hilo(app, thread_id):
    app.text_input[0].set_value(thread_id).run()
    next(elemento for elemento in app.button if elemento.label == "Cargar conversación").click().run()
    assert not app.exception
    return app


def test_front_no_importa_grafo_ni_modulos_de_sesion_backend():
    codigo = FRONT.read_text(encoding="utf-8")
    imports_backend = re.compile(
        r"(?:from|import)\s+src\.(?:agent|graph|tools|clientes\.(?:cargar|sesion))\b"
    )

    assert imports_backend.search(codigo) is None


def test_primera_pregunta_envia_auto_aprobar_false_y_omite_thread_id(monkeypatch):
    app = iniciar_front(monkeypatch)

    enviar(app, "¿A qué hora cierra el metro?")

    assert ClienteFalso.instancias[0].preguntas == [
        {
            "pregunta": "¿A qué hora cierra el metro?",
            "thread_id": None,
            "auto_aprobar": False,
        }
    ]
    assert app.session_state["thread_id"] == "hilo-generado-1"
    assert app.session_state["messages"][-1] == {
        "role": "assistant",
        "content": "Respuesta a: ¿A qué hora cierra el metro?",
    }


def test_pregunta_siguiente_reutiliza_el_hilo_devuelto(monkeypatch):
    app = iniciar_front(monkeypatch)
    enviar(app, "Primera pregunta")
    enviar(app, "Pregunta de seguimiento")

    assert ClienteFalso.instancias[0].preguntas[1] == {
        "pregunta": "Pregunta de seguimiento",
        "thread_id": "hilo-generado-1",
        "auto_aprobar": False,
    }
    assert app.session_state["thread_id"] == "hilo-generado-1"
    assert any("Hilo activo: hilo-generado-1" in elemento.value for elemento in app.caption)


def test_interruptor_auto_aprobar_se_envia_en_la_pregunta(monkeypatch):
    app = iniciar_front(monkeypatch)
    control = next(elemento for elemento in app.checkbox if elemento.label == "Aprobar automáticamente un único plan")
    control.check().run()

    enviar(app, "Planifica un viaje")

    assert ClienteFalso.instancias[0].preguntas[-1] == {
        "pregunta": "Planifica un viaje",
        "thread_id": None,
        "auto_aprobar": True,
    }


def test_nueva_conversacion_limpia_mensajes_y_omite_hilo_en_siguiente_envio(monkeypatch):
    app = iniciar_front(monkeypatch)
    enviar(app, "Pregunta del hilo anterior")
    next(elemento for elemento in app.button if elemento.label == "Nueva conversación").click().run()

    assert not app.exception
    assert app.session_state["thread_id"] is None
    assert app.session_state["messages"] == []

    enviar(app, "Pregunta del hilo nuevo")

    assert ClienteFalso.instancias[0].preguntas[-1]["thread_id"] is None
    assert app.session_state["thread_id"] == "hilo-generado-1"


def test_health_solo_se_consulta_al_pulsar_y_no_envia_clave(monkeypatch):
    app = iniciar_front(monkeypatch)
    cliente = ClienteFalso.instancias[0]

    assert cliente.health_calls == 0
    next(elemento for elemento in app.button if elemento.label == "Comprobar estado").click().run()

    assert not app.exception
    assert cliente.health_calls == 1
    assert any("Backend disponible" in elemento.value for elemento in app.success)


def test_estado_health_se_conserva_entre_reruns(monkeypatch):
    app = iniciar_front(monkeypatch)
    next(elemento for elemento in app.button if elemento.label == "Comprobar estado").click().run()
    next(elemento for elemento in app.button if elemento.label == "Nueva conversación").click().run()

    assert any("Backend disponible" in elemento.value for elemento in app.success)
    assert ClienteFalso.instancias[0].health_calls == 1


def test_health_fallido_muestra_backend_no_disponible(monkeypatch):
    app = iniciar_front(monkeypatch)
    ClienteFalso.instancias[0].health_error = APIConnectionError("sin conexión")

    next(elemento for elemento in app.button if elemento.label == "Comprobar estado").click().run()

    assert any("Backend no disponible" in elemento.value for elemento in app.error)


def test_carga_historial_ordena_mensajes_y_conserva_roles(monkeypatch):
    app = iniciar_front(monkeypatch)
    cliente = ClienteFalso.instancias[0]
    cliente.historial_resultado = {
        "mensajes": [
            {"role": "assistant", "content": "Respuesta", "orden": 2},
            {"role": "system", "content": "Aviso", "orden": 3},
            {"role": "user", "content": "Pregunta", "orden": 1},
        ]
    }

    cargar_hilo(app, "hilo-cargado")

    assert cliente.historial_llamadas == ["hilo-cargado"]
    assert app.session_state["thread_id"] == "hilo-cargado"
    assert [mensaje["content"] for mensaje in app.session_state["messages"]] == [
        "Pregunta",
        "Respuesta",
        "Aviso",
    ]
    assert [mensaje["role"] for mensaje in app.session_state["messages"][:2]] == ["user", "assistant"]
    assert any("Mensaje de rol system" in elemento.value for elemento in app.caption)


def test_carga_historial_acepta_lista_del_contrato_de_api(monkeypatch):
    app = iniciar_front(monkeypatch)
    cliente = ClienteFalso.instancias[0]
    cliente.historial_resultado = [
        {"role": "assistant", "content": "Respuesta", "orden": 2},
        {"role": "user", "content": "Pregunta", "orden": 1},
    ]

    cargar_hilo(app, "hilo-lista")

    assert app.session_state["thread_id"] == "hilo-lista"
    assert [mensaje["content"] for mensaje in app.session_state["messages"]] == ["Pregunta", "Respuesta"]


@pytest.mark.parametrize(
    ("error", "mensaje_visible"),
    [
        (APIHttpError("No encontrado", status_code=404), "No se pudo cargar"),
        (APIHttpError("No implementado", status_code=501), "todavía no está implementado"),
        (APIConnectionError("conexión rechazada"), "No se pudo cargar"),
    ],
)
def test_fallo_historial_conserva_chat_y_hilo(monkeypatch, error, mensaje_visible):
    app = iniciar_front(monkeypatch)
    cliente = ClienteFalso.instancias[0]
    app.session_state["thread_id"] = "hilo-activo"
    app.session_state["messages"] = [
        {"role": "user", "content": "Mensaje existente"},
        {"role": "assistant", "content": "Respuesta existente"},
    ]
    anterior = list(app.session_state["messages"])
    cliente.historial_error = error

    cargar_hilo(app, "hilo-ajeno")

    assert app.session_state["thread_id"] == "hilo-activo"
    assert app.session_state["messages"] == anterior
    assert any(mensaje_visible in elemento.value for elemento in app.error)


def respuesta_pendiente(planes):
    return {
        "respuesta": "He preparado una propuesta.",
        "thread_id": "hilo-pendiente",
        "done": False,
        "pendiente_hitl": True,
        "plan": planes,
        "error": None,
    }


def test_controles_de_decision_solo_aparecen_con_plan_pendiente(monkeypatch):
    app = iniciar_front(monkeypatch)
    assert not any(elemento.label in {"Aprobar", "Rechazar"} for elemento in app.button)

    ClienteFalso.instancias[0].ask_result = respuesta_pendiente(
        [{"id": "ruta-1", "resultado": {"resumen": "Ruta propuesta"}}]
    )
    enviar(app, "Propón una ruta")

    assert any(elemento.label == "Aprobar" for elemento in app.button)
    assert any(elemento.label == "Rechazar" for elemento in app.button)


@pytest.mark.parametrize(
    ("decision", "aprobado"), [("Aprobar", True), ("Rechazar", False)]
)
def test_decision_envia_plan_seleccionado_y_muestra_respuesta_de_api(monkeypatch, decision, aprobado):
    app = iniciar_front(monkeypatch)
    cliente = ClienteFalso.instancias[0]
    cliente.ask_result = respuesta_pendiente(
        [
            {"id": "ruta-1", "resultado": {"resumen": "Ruta norte"}},
            {"id": "ruta-2", "resultado": {"resumen": "Ruta sur"}},
        ]
    )
    cliente.approve_result = {
        "respuesta": "Resultado confirmado por la API",
        "thread_id": "hilo-pendiente",
        "done": True,
        "pendiente_hitl": False,
        "plan": [],
        "error": None,
    }
    enviar(app, "Propón una ruta")

    selector = next(elemento for elemento in app.radio if elemento.label == "Plan a decidir")
    selector.set_value("ruta-2").run()
    next(elemento for elemento in app.button if elemento.label == decision).click().run()

    assert not app.exception
    assert cliente.aprobaciones == [
        {"thread_id": "hilo-pendiente", "aprobado": aprobado, "plan_id": "ruta-2"}
    ]
    assert app.session_state["decision_result"]["respuesta"] == "Resultado confirmado por la API"


def test_decision_de_un_solo_plan_omite_plan_id(monkeypatch):
    app = iniciar_front(monkeypatch)
    cliente = ClienteFalso.instancias[0]
    cliente.ask_result = respuesta_pendiente(
        [{"id": "ruta-unica", "resultado": {"resumen": "Ruta única"}}]
    )
    enviar(app, "Propón una ruta")
    next(elemento for elemento in app.button if elemento.label == "Aprobar").click().run()

    assert cliente.aprobaciones == [{"thread_id": "hilo-pendiente", "aprobado": True}]


def test_askout_muestra_respuesta_y_conserva_campos_devuelto_por_api(monkeypatch):
    app = iniciar_front(monkeypatch)
    resultado = {
        "respuesta": "Propuesta de viaje lista.",
        "thread_id": "hilo-pendiente",
        "done": False,
        "pendiente_hitl": True,
        "plan": [{"id": "ruta-1", "resultado": {"resumen": "Ruta norte"}}],
        "error": "Aviso devuelto por el servicio",
    }
    ClienteFalso.instancias[0].ask_result = resultado

    enviar(app, "Planifica el viaje")

    assert app.session_state["ask_result"] == resultado
    assert app.session_state["messages"][-1] == {
        "role": "assistant",
        "content": "Propuesta de viaje lista.",
    }


def test_aprobar_recarga_historial_y_sustituye_chat_si_funciona(monkeypatch):
    app = iniciar_front(monkeypatch)
    cliente = ClienteFalso.instancias[0]
    cliente.ask_result = respuesta_pendiente(
        [{"id": "ruta-1", "resultado": {"resumen": "Ruta norte"}}]
    )
    cliente.historial_resultado = {
        "mensajes": [
            {"role": "assistant", "content": "Turno cerrado", "orden": 2},
            {"role": "user", "content": "Planifica", "orden": 1},
        ]
    }
    enviar(app, "Planifica")
    next(elemento for elemento in app.button if elemento.label == "Aprobar").click().run()

    assert cliente.historial_llamadas == ["hilo-pendiente"]
    assert [mensaje["content"] for mensaje in app.session_state["messages"]] == [
        "Planifica",
        "Turno cerrado",
    ]


def test_fallo_de_recarga_conserva_chat_y_resultado_de_decision(monkeypatch):
    app = iniciar_front(monkeypatch)
    cliente = ClienteFalso.instancias[0]
    cliente.ask_result = respuesta_pendiente(
        [{"id": "ruta-1", "resultado": {"resumen": "Ruta norte"}}]
    )
    cliente.approve_result = {
        "respuesta": "El plan se ha rechazado.",
        "thread_id": "hilo-pendiente",
        "done": False,
        "pendiente_hitl": False,
        "plan": [],
        "error": None,
    }
    cliente.historial_error = APIHttpError("No implementado", status_code=501)
    enviar(app, "Mi pregunta")
    anterior = list(app.session_state["messages"])
    next(elemento for elemento in app.button if elemento.label == "Rechazar").click().run()

    assert app.session_state["messages"] == anterior
    assert app.session_state["decision_result"]["respuesta"] == "El plan se ha rechazado."
    assert any("todavía no está implementado" in elemento.value for elemento in app.error)


def test_api_key_ausente_no_envia_pregunta_protegida(monkeypatch):
    app = iniciar_front(monkeypatch, api_key="")
    enviar(app, "¿Cuándo pasa el próximo autobús?")

    assert ClienteFalso.instancias[0].preguntas == []
    assert app.session_state["thread_id"] is None
    assert app.session_state["messages"] == []
    assert any("API_KEY" in elemento.value and ".env" in elemento.value for elemento in app.error)


def test_401_muestra_error_de_autenticacion_y_conserva_chat(monkeypatch):
    app = iniciar_front(monkeypatch)
    cliente = ClienteFalso.instancias[0]
    app.session_state["thread_id"] = "hilo-existente"
    app.session_state["messages"] = [
        {"role": "user", "content": "Pregunta previa"},
        {"role": "assistant", "content": "Respuesta previa"},
    ]
    mensajes_anteriores = list(app.session_state["messages"])
    cliente.ask_error = APIHttpError("No autorizado", status_code=401)

    enviar(app, "Pregunta que requiere autenticación")

    assert len(cliente.preguntas) == 1
    assert cliente.preguntas[0]["thread_id"] == "hilo-existente"
    assert app.session_state["thread_id"] == "hilo-existente"
    assert app.session_state["messages"] == mensajes_anteriores
    assert any("autenticación" in elemento.value.lower() for elemento in app.error)


def test_fallo_de_red_en_primer_ask_conserva_texto_y_no_reintenta(monkeypatch):
    app = iniciar_front(monkeypatch)
    cliente = ClienteFalso.instancias[0]
    cliente.ask_error = APIConnectionError("conexión rechazada")

    enviar(app, "¿Hay incidencias en la línea 1?")

    assert len(cliente.preguntas) == 1
    assert cliente.preguntas[0]["thread_id"] is None
    assert app.session_state["thread_id"] is None
    assert app.session_state["messages"] == []
    assert app.session_state["pending_question"] == "¿Hay incidencias en la línea 1?"
