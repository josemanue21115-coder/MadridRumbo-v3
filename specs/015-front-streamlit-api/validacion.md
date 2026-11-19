# Validación — Spec 015

> Fecha: 2026-11-14 · Resultado de `python -m pytest`: **1322 passed, 9 skipped, 0 failed** · 1 warning deprecado de Starlette/httpx.

| RF | Comprobación | Test o evidencia | Resultado |
|---|---|---|---|
| RF-1 | Frontend aislado del agente y cliente HTTP para las rutas de la API. | `tests/test_front_streamlit_api.py::test_front_no_importa_grafo_ni_modulos_de_sesion_backend`; pruebas de rutas en `tests/test_api_http.py`. | ✅ |
| RF-2 | URL predeterminada cuando la variable falta o está vacía, y URL configurada desde el entorno. | `tests/test_api_http.py::test_url_base_por_defecto_y_configurada`. | ✅ |
| RF-3 | `API_KEY` viaja como query en rutas protegidas; health no lleva clave; sin clave el front no pregunta e indica cómo configurar `.env`. `.env.example` contiene ejemplos. | `tests/test_api_http.py::test_rutas_protegidas_incluyen_api_key_en_query`; `tests/test_api_http.py::test_health_es_publico_y_devuelve_json`; `tests/test_front_streamlit_api.py::test_api_key_ausente_no_envia_pregunta_protegida`. | ⚠️ Front cumple. La API actual **no valida ni exige `api_key`** en sus endpoints. |
| RF-4 | Health solo al pulsar, estado disponible/no disponible y conservación del último estado. | `tests/test_front_streamlit_api.py::test_health_solo_se_consulta_al_pulsar_y_no_envia_clave`; `test_health_fallido_muestra_backend_no_disponible`; `test_estado_health_se_conserva_entre_reruns`; comprobación local real abajo. | ✅ |
| RF-5 | Envío de pregunta, valor inicial `auto_aprobar=false`, hilo opcional y adopción del hilo devuelto. | `tests/test_front_streamlit_api.py::test_primera_pregunta_envia_auto_aprobar_false_y_omite_thread_id`; `test_interruptor_auto_aprobar_se_envia_en_la_pregunta`; `test_pregunta_siguiente_reutiliza_el_hilo_devuelto`. | ✅ |
| RF-6 | Controles solo con HITL pendiente; la API simula autoaprobación única y no aprueba varios planes automáticamente. | `tests/test_front_streamlit_api.py::test_controles_de_decision_solo_aparecen_con_plan_pendiente`; `tests/test_api_autoaprobar.py`. | ✅ |
| RF-7 | Aprobar/rechazar envía hilo, decisión y `plan_id` cuando hay varios; resultado visible; historial sustituye el chat solo al cargar bien. | `tests/test_front_streamlit_api.py::test_decision_envia_plan_seleccionado_y_muestra_respuesta_de_api`; `test_decision_de_un_solo_plan_omite_plan_id`; `test_aprobar_recarga_historial_y_sustituye_chat_si_funciona`; `test_fallo_de_recarga_conserva_chat_y_resultado_de_decision`. | ✅ |
| RF-8 | Historial ordenado por `orden`, roles canónicos y desconocidos, respuesta de lista del contrato OpenAPI. | `tests/test_front_streamlit_api.py::test_carga_historial_ordena_mensajes_y_conserva_roles`; `test_carga_historial_acepta_lista_del_contrato_de_api`; `tests/test_api_http.py::test_historial_consulta_thread_y_devuelve_json`. | ✅ Cliente/front preparados; la API no proporciona historial todavía. |
| RF-9 | Errores 404, 501 y red conservan hilo y mensajes; 501 tiene aviso propio. | `tests/test_front_streamlit_api.py::test_fallo_historial_conserva_chat_y_hilo`; `test_fallo_de_recarga_conserva_chat_y_resultado_de_decision`. | ✅ Para los errores cubiertos. El backend actual responde 501. |
| RF-10 | Nueva conversación limpia el estado; primer envío omite el hilo; fallo inicial no reintenta y conserva pregunta. | `tests/test_front_streamlit_api.py::test_nueva_conversacion_limpia_mensajes_y_omite_hilo_en_siguiente_envio`; `test_fallo_de_red_en_primer_ask_conserva_texto_y_no_reintenta`. | ✅ |
| RF-11 | Hilo activo se muestra y mensajes de hilos distintos se sustituyen solo al cargar correctamente. | `tests/test_front_streamlit_api.py::test_pregunta_siguiente_reutiliza_el_hilo_devuelto`; `test_carga_historial_ordena_mensajes_y_conserva_roles`; `test_fallo_historial_conserva_chat_y_hilo`. | ✅ |
| RF-12 | Clave ausente, 401, HTTP y red muestran errores comprensibles y conservan el chat. | `tests/test_front_streamlit_api.py::test_api_key_ausente_no_envia_pregunta_protegida`; `test_401_muestra_error_de_autenticacion_y_conserva_chat`; `test_fallo_de_red_en_primer_ask_conserva_texto_y_no_reintenta`; casos de error de historial. | ✅ Front. La API no tiene autenticación activa. |
| RF-13 | Front muestra campos de `/ask` y `/approve` devueltos por API, sin decidir por su cuenta el resultado. | `tests/test_front_streamlit_api.py::test_askout_muestra_respuesta_y_conserva_campos_devuelto_por_api`; `test_decision_envia_plan_seleccionado_y_muestra_respuesta_de_api`. | ✅ |

## Comprobación manual local

Se inició Uvicorn en `127.0.0.1:8765` con `MADRIDRUMBO_GRAFO=falso` y se abrió el frontend mediante `AppTest` usando el cliente HTTP real, sin dobles. `/health` devolvió 200 y se mostró «Backend disponible»; `/ask` devolvió 200 con un plan pendiente; `/approve` devolvió 200. La posterior carga de historial devolvió 501; el front mostró el aviso de historial no implementado y conservó el chat y el resultado de la decisión. No se invocaron servicios externos.

## Estado real de la API

- **Historial:** `GET /threads/{thread_id}/messages` está declarado con `response_model=list[MessageOut]`, pero la implementación actual responde **501**. El cliente y el front aceptan ya la lista especificada cuando el endpoint esté implementado.
- **Autenticación:** la API actualmente **no exige ni valida `api_key`**. `app.py` no declara dependencia de autenticación ni parámetro de clave en `/ask`, `/approve` o historial. El cliente front envía la clave en el query si está configurada, y evita peticiones protegidas si falta; esto no protege por sí solo el servidor.
- **Pruebas omitidas:** nueve pruebas de `tests/test_app_streamlit.py` pertenecen al frontend anterior basado en grafo y depuración; se dejaron omitidas porque ese comportamiento fue reemplazado por la spec 015 y su cobertura AppTest está en `tests/test_front_streamlit_api.py`.

## Veredicto

**Parcial en el despliegue integrado:** la UI y el cliente cumplen los RF comprobables, la suite pasa y la integración local simulada funciona. El historial sigue en 501 y la API no valida autenticación; ambos estados quedan registrados explícitamente para el trabajo del backend.
