# Validación — Spec 017

> Fecha: 2026-11-18 · Resultado de `python -m pytest`: 1354 passed / 9 skipped / 0 failed (56.82 s)

| RF | Cómo se comprueba | Test o comprobación manual | Resultado |
|---|---|---|---|
| RF-1 | Automático | `tests/test_api_seguridad.py::test_clave_valida_permite_acceder_a_rutas_protegidas`; `test_openapi_declara_api_key_como_parametro_de_query` | ✅ |
| RF-2 | Automático y manual | `tests/test_api_seguridad.py::test_rutas_publicas_responden_sin_clave`; `tests/test_api_rutas.py::test_docs_son_publicas`. Uvicorn local: `/health` y `/docs` respondieron 200 sin clave. | ✅ |
| RF-3 | Automático | `tests/test_api_seguridad.py::test_clave_ausente_o_incorrecta_devuelve_401` | ✅ |
| RF-4 | Automático | `tests/test_api_seguridad.py::test_clave_del_servicio_no_configurada_devuelve_503` | ✅ |
| RF-5 | Automático | `tests/test_api_seguridad.py::test_configuracion_usa_valores_del_entorno` | ✅ |
| RF-6 | Automático | `tests/test_api_seguridad.py::test_configuracion_usa_valores_predeterminados_si_faltan`, `test_limite_compartido_se_aplica_entre_rutas` y `test_limite_usa_ventana_movil_de_60_segundos` | ✅ |
| RF-7 | Automático y manual | `tests/test_api_seguridad.py::test_limite_compartido_se_aplica_entre_rutas`, `test_limite_usa_ventana_movil_de_60_segundos`. Con cuota local 2, historial respondió 501, 501 y después 429. | ✅ |
| RF-8 | Automático | `tests/test_api_timeout.py::test_timeout_predeterminado_si_la_variable_no_esta_configurada`, `test_timeout_invalido_usa_300_segundos` | ✅ |
| RF-9 | Automático y manual | `tests/test_api_timeout.py::test_ask_lento_devuelve_504_con_mensaje_y_sin_secreto`. Con timeout de 0.01 s y turno simulado de 0.05 s, respondió 504 con el mensaje acordado. | ✅ |
| RF-10 | Automático | `tests/test_api_timeout.py::test_approve_no_aplica_el_timeout_de_ask`, `test_historial_no_aplica_el_timeout_de_ask` | ✅ |
| RF-11 | Automático | `tests/test_api_errores.py::test_fallo_del_agente_en_ask_da_500_generico`, `test_fallo_del_agente_en_approve_da_500_generico`, `test_agente_no_disponible_da_500_generico` | ✅ |
| RF-12 | Automático y manual | `tests/test_api_timeout.py::test_ask_lento_devuelve_504_con_mensaje_y_sin_secreto`; en la ejecución local el log registró el timeout sin clave. El access log de Uvicorn mostró las rutas sin query string. | ✅ |
| RF-13 | Automático | `tests/test_api_seguridad.py::test_env_example_documenta_configuracion_sin_secretos` | ✅ |
| RF-14 | Automático y manual | `tests/test_api_seguridad.py::test_clave_ausente_o_incorrecta_devuelve_401`. `POST /ask` local con cuerpo válido y sin `api_key`: 401. | ✅ |
| RF-15 | Automático y manual | `tests/test_api_seguridad.py::test_limite_compartido_se_aplica_entre_rutas`. Se usó `GET /threads/hilo-prueba/messages`, que no inicia llamadas a LLM: 501, 501 y 429 al superar la cuota. | ✅ |
| RF-16 | Automático y manual | `tests/test_api_timeout.py::test_ask_lento_devuelve_504_con_mensaje_y_sin_secreto`. Comprobación manual con `TestClient`, clave ficticia, timeout 0.01 s y `servicio.preguntar` sustituido por una función que duerme 0.05 s; no se llamó a un LLM real. | ✅ |
| RF-17 | Automático | `tests/test_api_seguridad.py::test_configuracion_usa_valores_predeterminados_si_limites_son_invalidos` | ✅ |
| RF-18 | Automático | `tests/test_api_seguridad.py::test_intentos_sin_clave_comparten_el_mismo_limite` | ✅ |
| RF-19 | Automático | `tests/test_api_seguridad.py::test_limite_intentos_con_clave_invalida_consumen_cuota_de_esa_clave` | ✅ |

## Comprobaciones manuales locales

- Uvicorn se ejecutó en `127.0.0.1:8766` con `API_KEY` ficticia, `RATE_LIMIT_PER_MINUTE=2` y `ASK_TIMEOUT_SECONDS=1`.
- `GET /health` → 200; `GET /docs` → 200; `POST /ask` con cuerpo válido y sin `api_key` → 401.
- Tres peticiones autenticadas a la ruta de historial → 501, 501 y 429. El historial está reservado y no invoca al agente.
- El access log de Uvicorn omitió `api_key` y el resto de la query. Para RF-16 se hizo una comprobación aislada con `TestClient`, timeout reducido y turno simulado; devolvió 504 con el texto exacto y el log solo registró el evento de timeout.

## Criterios de finalización

- [x] Los RF-1 a RF-19 tienen comprobaciones; se cubren valores de configuración ausentes o inválidos, cuota compartida y ventana móvil de 60 segundos.
- [x] Se verificaron localmente 401, 429 y 504 según RF-14, RF-15 y RF-16, sin llamadas a un LLM real.
- [x] `.env.example` documenta los valores acordados sin una clave real; las pruebas y comprobaciones de respuesta y logs no encontraron claves, excepciones ni detalles internos expuestos.

## Fuera de spec

`GET /openapi.json` también queda accesible sin clave para que `/docs` pueda cargar el esquema interactivo. Es un endpoint auxiliar de documentación.

## Veredicto

**Sí.** La suite completa pasó y se verificaron los códigos y registros requeridos en local; RF-1 a RF-19 están cubiertos.
