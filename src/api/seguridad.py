"""Autenticación de las rutas protegidas de la API."""
from collections import deque
import hmac
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Query

import config

_VENTANA_SEGUNDOS = 60
_intentos_por_clave: dict[str | None, deque[float]] = {}
_orden_intentos: deque[tuple[float, str | None]] = deque()
_lock_intentos = Lock()


def _aplicar_limite(api_key: str | None) -> None:
    """Cuenta el intento en una ventana móvil compartida entre rutas protegidas."""
    with _lock_intentos:
        ahora = monotonic()
        # Expira intentos globalmente para liberar también claves que no se reutilizan.
        while _orden_intentos and ahora - _orden_intentos[0][0] >= _VENTANA_SEGUNDOS:
            _instante, identidad = _orden_intentos.popleft()
            intentos = _intentos_por_clave.get(identidad)
            if intentos:
                intentos.popleft()
                if not intentos:
                    del _intentos_por_clave[identidad]

        intentos = _intentos_por_clave.get(api_key)
        if intentos and len(intentos) >= config.RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=429,
                detail="Has superado el límite de peticiones. Inténtalo de nuevo más tarde.",
            )

        if intentos is None:
            intentos = deque()
            _intentos_por_clave[api_key] = intentos
        intentos.append(ahora)
        _orden_intentos.append((ahora, api_key))


def validar_api_key(api_key: str | None = Query(default=None)) -> None:
    """Valida la clave recibida en query sin revelarla en el error."""
    clave_configurada = config.API_KEY
    if not clave_configurada:
        raise HTTPException(
            status_code=503,
            detail="El servicio no está configurado para aceptar peticiones protegidas.",
        )

    _aplicar_limite(api_key)

    if api_key is None or not hmac.compare_digest(
        api_key.encode("utf-8"), clave_configurada.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Clave API ausente o no válida.")
