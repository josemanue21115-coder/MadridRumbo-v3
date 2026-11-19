"""Cliente HTTP de la API de MadridRumbo para clientes ligeros como Streamlit."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


URL_BASE_PREDETERMINADA = "http://127.0.0.1:8000"
TIMEOUT_SEGUNDOS = 90


class APIHttpError(Exception):
    """Error HTTP o de formato de respuesta devuelto por la API."""

    def __init__(self, mensaje: str, status_code: int | None = None):
        super().__init__(mensaje)
        self.status_code = status_code


class APIConnectionError(Exception):
    """Error al establecer comunicación con la API."""


class APIHttpClient:
    """Envía peticiones HTTP a la API usando solo la biblioteca estándar."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        url_configurada = base_url if base_url is not None else os.getenv("API_BASE_URL", "")
        self.base_url = (url_configurada.strip() or URL_BASE_PREDETERMINADA).rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("API_KEY", "")

    def health(self) -> dict:
        """Consulta el estado público del servicio, sin enviar clave."""
        return self._request("GET", "/health", protegido=False)

    def ask(self, pregunta: str, thread_id: str | None = None, auto_aprobar: bool = False) -> dict:
        """Envía una pregunta y, si existe, el hilo en curso."""
        datos = {"pregunta": pregunta, "auto_aprobar": auto_aprobar}
        if thread_id is not None:
            datos["thread_id"] = thread_id
        return self._request("POST", "/ask", datos, protegido=True)

    def approve(self, thread_id: str, aprobado: bool, plan_id: str | None = None) -> dict:
        """Aprueba o rechaza un plan pendiente en un hilo."""
        datos = {"thread_id": thread_id, "aprobado": aprobado}
        if plan_id is not None:
            datos["plan_id"] = plan_id
        return self._request("POST", "/approve", datos, protegido=True)

    def messages(self, thread_id: str) -> dict | list:
        """Obtiene los mensajes disponibles para un hilo."""
        ruta = f"/threads/{quote(thread_id, safe='')}/messages"
        return self._request("GET", ruta, protegido=True, permitir_lista=True)

    def _request(
        self,
        metodo: str,
        ruta: str,
        datos: dict | None = None,
        protegido: bool = False,
        permitir_lista: bool = False,
    ) -> dict | list:
        partes = urlsplit(self.base_url)
        ruta_url = f"{partes.path.rstrip('/')}{ruta}"
        query = partes.query
        if protegido and self.api_key:
            clave_query = urlencode({"api_key": self.api_key})
            query = f"{query}&{clave_query}" if query else clave_query
        url = urlunsplit((partes.scheme, partes.netloc, ruta_url, query, ""))

        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8") if datos is not None else None
        headers = {"Accept": "application/json"}
        if cuerpo is not None:
            headers["Content-Type"] = "application/json"
        request = Request(url, data=cuerpo, headers=headers, method=metodo)

        try:
            with urlopen(request, timeout=TIMEOUT_SEGUNDOS) as respuesta:
                contenido = respuesta.read()
        except HTTPError as error:
            detalle = self._detalle_http(error)
            if self.api_key:
                detalle = detalle.replace(self.api_key, "[oculta]")
            raise APIHttpError(detalle, status_code=error.code) from None
        except (URLError, OSError, TimeoutError) as error:
            detalle = str(getattr(error, "reason", error))
            if self.api_key:
                detalle = detalle.replace(self.api_key, "[oculta]")
            raise APIConnectionError(f"No se pudo conectar con la API: {detalle}") from None

        try:
            resultado = json.loads(contenido.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise APIHttpError("La API devolvió una respuesta JSON no válida.") from None
        if not isinstance(resultado, dict) and not (permitir_lista and isinstance(resultado, list)):
            raise APIHttpError("La API devolvió una respuesta JSON inesperada.")
        return resultado

    @staticmethod
    def _detalle_http(error: HTTPError) -> str:
        """Extrae un mensaje legible sin mostrar la URL de la petición."""
        try:
            cuerpo = json.loads(error.read().decode("utf-8"))
            detalle = cuerpo.get("detail", cuerpo.get("mensaje")) if isinstance(cuerpo, dict) else None
            if isinstance(detalle, str) and detalle.strip():
                return detalle.strip()
        except (UnicodeDecodeError, json.JSONDecodeError, OSError):
            pass
        return f"La API respondió con error HTTP {error.code}."
