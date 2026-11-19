# Validación — Spec 019

> Fecha: 2026-11-18 · Resultado de `python -m pytest`: 1404 passed / 0 failed / 27 skipped

| RF | Cómo se comprueba | Test o comprobación manual | Resultado |
|---|---|---|---|
| RF-1 | Automático: un único evento JSON contiene método, ruta concreta, `thread_id`, duración y estado final. | `tests/test_api_logs.py::test_ask_registra_campos_y_thread_id_generado`, `test_approve_registra_campos_y_thread_id`, `test_historial_registra_campos_y_thread_id_concreto` | ✅ |
| RF-2 | Automático: el identificador se registra como `null` cuando no está disponible; si se crea en `/ask`, se registra el valor devuelto. | `tests/test_api_logs.py::test_ask_registra_campos_y_thread_id_generado`, `test_error_401_registra_estado_y_thread_id_null` | ✅ |
| RF-3 | Automático: fallo temprano y fallo de validación generan registro con `thread_id: null`. | `tests/test_api_logs.py::test_fallo_antes_de_obtener_thread_id_registra_null`, `test_validacion_422_registra_peticion_y_thread_id_null` | ✅ |
| RF-4 | Automático: se conserva la ruta concreta sin query; el access log sanea queries y suprime duplicados protegidos. | `tests/test_api_logs.py::test_ask_registra_campos_y_thread_id_generado`, `tests/test_api_seguridad.py::test_access_log_sanea_query_y_no_duplica_rutas_protegidas` | ✅ |
| RF-5 | Automático: se inspeccionan logs de aplicación, servicio y servidor con marcadores de `API_KEY`, claves OpenAI/Gemini y `DATABASE_URL`. | `tests/test_api_logs.py::test_logs_de_exito_no_contienen_secretos_ni_texto_conversacional`, `test_log_de_excepcion_no_contiene_detalle_sensible`, `tests/test_api_seguridad.py::test_access_log_sanea_query_y_no_duplica_rutas_protegidas` | ✅ |
| RF-6 | Automático: se comprueba que los logs no contienen los marcadores de pregunta y respuesta. | `tests/test_api_logs.py::test_logs_de_exito_no_contienen_secretos_ni_texto_conversacional`, `test_log_de_excepcion_no_contiene_detalle_sensible` | ✅ |
| RF-7 | Automático: el estado registrado coincide con respuestas 401, 429, 503, 504 y 500. | `tests/test_api_logs.py::test_error_401_registra_estado_y_thread_id_null`, `test_error_429_registra_estado`, `test_error_503_registra_estado`, `test_error_504_registra_estado`, `test_error_500_registra_estado_y_mensaje_generico` | ✅ |
| RF-8 | Automático: el error inesperado mantiene el mensaje genérico y sus detalles no aparecen en logs ni respuesta. | `tests/test_api_logs.py::test_error_500_registra_estado_y_mensaje_generico`, `test_log_de_excepcion_no_contiene_detalle_sensible`, `tests/test_api_errores.py::test_fallo_del_agente_en_ask_da_500_generico` | ✅ |
| RF-9 | Automático: se cubren rutas protegidas, la respuesta 422 por validación y un fallo antes del envío de respuesta. | `tests/test_api_logs.py::test_ask_registra_campos_y_thread_id_generado`, `test_approve_registra_campos_y_thread_id`, `test_historial_registra_campos_y_thread_id_concreto`, `test_validacion_422_registra_peticion_y_thread_id_null`, `test_fallo_antes_de_enviar_respuesta_registra_estado_null` | ✅ |
| RF-10 | Automático: se inspeccionan los logs de éxito y error y el access log, incluyendo secretos, texto conversacional y detalles de excepción. | `tests/test_api_logs.py::test_logs_de_exito_no_contienen_secretos_ni_texto_conversacional`, `test_log_de_excepcion_no_contiene_detalle_sensible`, `tests/test_api_seguridad.py::test_access_log_sanea_query_y_no_duplica_rutas_protegidas` | ✅ |

## Criterios de finalización

- [x] Los campos del registro se verifican en peticiones correctas y errores representativos; el estado queda en `null` si no se envió respuesta.
- [x] Se verifica `thread_id` presente, ausente y no disponible por fallo temprano.
- [x] Se verifican 401, 429, 503, 504 y 500; el 500 mantiene el mensaje genérico al cliente.
- [x] Las pruebas inspeccionan logs de aplicación, servicio y servidor para descartar `api_key`, secretos, texto conversacional y detalles sensibles.
- [x] `python -m pytest` termina con código 0: 1404 pasaron, 27 omitidas.

## Fuera de spec

Nada observable fuera de los comportamientos especificados. No se requiere verificación manual.

## Veredicto

**Sí** — RF-1 a RF-10 y los criterios de finalización están cubiertos por pruebas locales; la suite completa termina sin fallos.
