# Tareas — Spec 019

> Una tarea cada vez: `/sdd-implementar Tn`. Tests primero. Marca `[x]` al terminar.

- [x] T1. Añadir en `tests/test_api_logs.py` pruebas de contrato para una petición protegida correcta: exactamente un evento JSON con método, ruta concreta sin query, `thread_id`, duración no negativa y estado HTTP; cubrir `/ask`, `/approve`, historial y el caso sin identificador disponible. (RF-1, RF-2, RF-4, RF-9)
      Hecho cuando: `python -m pytest tests/test_api_logs.py` falla solo porque aún no existe el registro de petición; las pruebas usan `TestClient` y servicios simulados, sin leer `.env` ni llamar a servicios externos.

- [x] T2. Implementar `src/api/logs_peticion.py` y conectarlo desde `app.py`: envolver FastAPI para capturar la respuesta final, medir duración, emitir un evento JSON por ruta protegida y proporcionar al logger el `thread_id` disponible en la ruta del historial o en datos ya validados de `/ask` y `/approve`. No leer cuerpos; registrar `null` cuando el identificador aún no esté disponible. (RF-1, RF-2, RF-3, RF-4, RF-9)
      Hecho cuando: `python -m pytest tests/test_api_logs.py` queda verde para los escenarios de T1 y cada evento contiene los campos acordados sin parámetros de query.

- [x] T3. Ampliar primero `tests/test_api_logs.py` con casos de errores HTTP 401, 429, 503, 504 y 500; validación fallida 422; excepción inesperada con mensaje genérico al cliente; e interrupción antes de enviar respuesta HTTP con `status_code: null`. (RF-3, RF-7, RF-8, RF-9)
      Hecho cuando: `python -m pytest tests/test_api_logs.py` falla únicamente en los casos nuevos aún no cubiertos por la integración del middleware; los dobles no llaman al LLM.

- [x] T4. Completar el middleware y los puntos de integración para registrar exactamente una vez el estado final de errores y validación, conservar `null` cuando no haya respuesta o `thread_id`, y mantener el 500 genérico. Asegurar que el registro de timeout 504 satisface también el requisito de evento de timeout de la spec 017. (RF-1, RF-3, RF-7, RF-8, RF-9)
      Hecho cuando: `python -m pytest tests/test_api_logs.py` queda verde para éxito, validación, 401, 429, 503, 504, 500 y fallo sin respuesta; las respuestas HTTP conservan sus códigos y mensajes existentes.

- [x] T5. Añadir primero pruebas de privacidad en `tests/test_api_logs.py` y adaptar las pruebas de `tests/test_api_seguridad.py`: incluir marcadores de `api_key`, secreto de proveedor/LLM, `DATABASE_URL`, pregunta, respuesta y excepción; comprobar la ruta concreta sin query, la ausencia total de texto conversacional y que el access log no duplica rutas protegidas. (RF-4, RF-5, RF-6, RF-10)
      Hecho cuando: `python -m pytest tests/test_api_logs.py tests/test_api_seguridad.py` detecta las exposiciones o duplicados que todavía existan, sin depender de un servidor Uvicorn desplegado.

- [x] T6. Corregir la exposición de datos en todos los logs del servicio: mantener el saneamiento de query y suprimir el access log duplicado de rutas protegidas en `app.py`; retirar el registro de excepción con traceback en `src/api/servicio.py`; y eliminar el log separado del timeout, que queda cubierto por el evento 504. (RF-4, RF-5, RF-6, RF-8, RF-10)
      Hecho cuando: `python -m pytest tests/test_api_logs.py tests/test_api_seguridad.py tests/test_api_errores.py tests/test_api_timeout.py` queda verde y ningún marcador secreto, texto conversacional ni detalle de excepción aparece en los logs capturados.

- [x] T7. Validación final RF por RF (`/sdd-validar`): verificar campos y duración, disponibilidad del `thread_id`, errores, sanitización, ausencia de duplicados y compatibilidad de respuestas; ejecutar la suite completa sin servicios externos y documentar el veredicto en `specs/019-logs-peticiones/validacion.md`. (RF-1 a RF-10)
      Hecho cuando: `python -m pytest` termina con código 0 y `validacion.md` registra evidencia y veredicto para cada RF.
