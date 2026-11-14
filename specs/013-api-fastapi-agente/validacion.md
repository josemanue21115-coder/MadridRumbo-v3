# Validación — Spec 013

> Fecha: 2026-11-13 · Resultado de `python -m pytest`: **1295 passed**

| RF | Cómo se comprueba | Test o comprobación | Resultado |
| --- | --- | --- | --- |
| RF-1 | El esquema de la API incluye las cuatro rutas. | `tests/test_api_rutas.py::test_esquema_incluye_health`; `tests/test_api_ask.py::test_esquema_incluye_ask`; `tests/test_api_aprobacion.py::test_esquema_incluye_approve`; `tests/test_api_errores.py::test_esquema_incluye_la_ruta_de_mensajes` | Sí |
| RF-2 | `/docs` abre sin clave de acceso. | `tests/test_api_rutas.py::test_docs_son_publicas` | Sí |
| RF-3 | `/health` responde 200 con estado `ok`. | `tests/test_api_rutas.py::test_health_responde_ok` | Sí |
| RF-4 | `/ask` devuelve respuesta, thread_id, done, pendiente_hitl, plan y error. | `tests/test_api_ask.py::test_pregunta_sin_plan_devuelve_respuesta_y_cierra`; `tests/test_api_ask.py::test_pregunta_de_ruta_deja_el_plan_pendiente`; `tests/test_api_ask.py::test_rechazo_del_agente_se_convierte_en_error`; `tests/test_api_esquemas.py` | Sí |
| RF-5 | Una pregunta vacía, con solo espacios o ausente da 422. | `tests/test_api_ask.py::test_pregunta_vacia_da_422`; `tests/test_api_ask.py::test_sin_pregunta_da_422` | Sí |
| RF-6 | Sin thread_id se crea uno nuevo; si llega, se respeta. | `tests/test_api_ask.py::test_sin_thread_id_se_crea_uno_nuevo_cada_vez`; `tests/test_api_ask.py::test_thread_id_recibido_se_respeta_y_llega_al_agente` | Sí |
| RF-7 | Con auto_aprobar y un solo plan, la API aprueba. | `tests/test_api_autoaprobar.py::test_con_un_solo_plan_se_aprueba_solo_por_defecto` | Sí |
| RF-8 | Con auto_aprobar falso, el plan queda pendiente. | `tests/test_api_autoaprobar.py::test_con_auto_aprobar_falso_el_plan_queda_pendiente` | Sí |
| RF-9 | Con varios planes no se aprueba ninguno. | `tests/test_api_autoaprobar.py::test_con_varios_planes_no_se_aprueba_ninguno` | Sí |
| RF-10 | `/approve` devuelve el mismo formato que `/ask`. | `tests/test_api_aprobacion.py::test_aprobar_el_plan_pendiente` | Sí |
| RF-11 | Con varios planes, `/approve` exige plan_id y avisa si falta. | `tests/test_api_aprobacion.py::test_con_varios_planes_hace_falta_elegir_uno` | Sí |
| RF-12 | Rechazar el plan no es un error y la conversación continúa. | `tests/test_api_aprobacion.py::test_rechazar_el_plan_deja_continuar_la_conversacion` | Sí |
| RF-13 | Sin plan pendiente, el aviso en español llega en `error`. | `tests/test_api_aprobacion.py::test_sin_plan_pendiente_avisa_en_error` | Sí |
| RF-14 | Un fallo inesperado del agente da 500 con mensaje genérico, sin detalles internos. | `tests/test_api_errores.py::test_fallo_del_agente_en_ask_da_500_generico`; `tests/test_api_errores.py::test_fallo_del_agente_en_approve_da_500_generico`; `tests/test_api_errores.py::test_agente_no_disponible_da_500_generico` | Sí |
| RF-15 | `done` lo decide el agente: la API no lo modifica. | `tests/test_api_ask.py::test_pregunta_sin_plan_devuelve_respuesta_y_cierra`; `tests/test_api_ask.py::test_pregunta_de_ruta_deja_el_plan_pendiente` | Sí |
| RF-16 | `/health` indica si el agente es simulado o real. | `tests/test_api_rutas.py::test_health_indica_modo_simulado`; `tests/test_api_rutas.py::test_health_indica_modo_real` | Sí |

## Criterios de finalización

- [x] Todos los RF tienen pruebas automatizadas en verde, sin API, usando el agente simulado.
- [x] Prueba manual en `/docs` con el agente simulado: `/health` indica modo simulado; `/ask` con un plan se aprueba solo; `/ask` con dos planes los deja pendientes y `/approve` pide plan_id y luego aprueba el elegido; la ruta de mensajes responde 501.
- [x] La suite completa pasa: `1295 passed`.

## Fuera de spec

- La API recuerda en memoria el plan pendiente de cada conversación (`_planes_pendientes` en `src/api/servicio.py`), porque el agente simulado necesita recibirlo para aprobar. El agente real lo recupera de su propia memoria e ignora ese dato.
- La ruta `GET /threads/{thread_id}/messages` queda declarada y responde 501 hasta que la Persona 2 conecte el historial en base de datos.
- Pendiente de equipo: incluir FastAPI y uvicorn en el stack cerrado de `docs/constitution.md` (art. 12).

## Veredicto

Cumple. Los 16 RF quedan verificados con pruebas automatizadas y con la prueba manual en `/docs`.