# Plan técnico — Spec 013

> Basado en `spec.md` (estado: Aprobada). No añade comportamiento que no esté en la spec.

## Archivos afectados
| Archivo | Crear / Modificar | Qué cambia | RF |
|---|---|---|---|
| `src/api/__init__.py` | Crear | Paquete de la API. | — |
| `src/api/esquemas.py` | Crear | Formatos de datos: pregunta, respuesta, aprobación y mensaje del historial. | RF-4, RF-5, RF-10, RF-11 |
| `src/api/servicio.py` | Crear | Traduce cada petición a una llamada al agente: auto_aprobar, identificador nuevo y deducción del campo de error. | RF-4, RF-6 a RF-13, RF-15 |
| `src/api/app.py` | Crear | Aplicación FastAPI: rutas, documentación y manejo del fallo inesperado. | RF-1 a RF-3, RF-14, RF-16 |
| `config.py` | Modificar | Textos fijos de la API (errores y avisos) en un solo punto. | RF-13, RF-14 |
| `requirements.txt` | Modificar | Añadir `fastapi`, `uvicorn` y `httpx` (este último solo para los tests). | — |
| `tests/test_api_rutas.py` | Crear | Tests de las rutas con el agente simulado. | RF-1 a RF-6, RF-14, RF-16 |
| `tests/test_api_aprobacion.py` | Crear | Tests de auto_aprobar, aprobar y rechazar. | RF-7 a RF-13, RF-15 |

## Contrato
Entrada de POST /ask:
`{"pregunta": "¿Hasta qué hora hay metro?", "thread_id": "abc-1", "auto_aprobar": true}`
Salida de POST /ask y de POST /approve:
`{"respuesta": "...", "thread_id": "abc-1", "done": false, "pendiente_hitl": true, "plan": [...], "error": null}`
Entrada de POST /approve:
`{"thread_id": "abc-1", "aprobado": true, "plan_id": "ruta-1"}` (`plan_id` solo si hay varios planes).
GET /threads/{thread_id}/messages: declarada aquí; devuelve 501 hasta que la spec de Persona 2 aporte el historial.

## Lógica clave
```text
ask(entrada):
    thread_id = entrada.thread_id o uuid nuevo
    resultado = agente.procesar_turno(estado_vacio(), pregunta, thread_id)
    si auto_aprobar y resultado.hitl_pendiente y hay exactamente 1 plan:
        resultado = agente.aprobar_plan({}, thread_id, True)
    devolver respuesta con error deducido del registro

approve(entrada):
    estado = {"plan_id_seleccionado": plan_id} si viene plan_id, si no {}
    resultado = agente.aprobar_plan(estado, thread_id, aprobado)
    devolver respuesta con error deducido del registro

error deducido: si el registro tiene una entrada de tipo "control" con resultado "rechazado",
    error = respuesta; si no, error = null
```

## Decisiones técnicas
| Decisión | Alternativa descartada | Por qué |
|---|---|---|
| La API vive en `src/api/` y arranca con `src.api.app:app` | Usar `app.py` de la raíz | Hoy es la Streamlit; así no se pisa con el trabajo de Persona 3. |
| Cargar el agente con `cargar_agente()` | Importar `src.agent` directamente | Reutiliza el cambio real/simulado (RF-16) que ya usan la CLI y Streamlit. |
| Pasar `estado_vacio()` en cada pregunta | Guardar el estado en la API | El agente guarda el estado por conversación; es la fuente de verdad. |
| Rutas síncronas (`def`) | Rutas asíncronas (`async def`) | El agente bloquea mientras trabaja; FastAPI ejecuta las rutas síncronas en hilos aparte. |
| Deducir `error` del registro de rechazos | Pedir un campo nuevo al agente | La spec prohíbe cambiar el agente. |

## Estrategia de tests
Todos con el cliente de pruebas de FastAPI y el agente simulado (activado con la variable de entorno del modo simulado). No hay llamadas a LLM, embeddings ni ChromaDB. Los planes múltiples (RF-9, RF-11) se prueban con los pedidos del simulado que devuelven varios planes. A mano: abrir /docs con el modo simulado y probar pregunta con aprobación automática, pregunta con aprobación manual y rechazo.

## Riesgos
- La deducción del campo de error depende del formato del registro del agente; si cambia, hay que ajustarla.
- El estado de las conversaciones vive en la memoria de un solo proceso: la API debe ejecutarse con un único worker.
- FastAPI amplía el stack cerrado de la constitución (art. 12): hay que acordar su actualización con el equipo.
- La ruta del historial devuelve 501 hasta que exista la spec de Persona 2.

## Trazabilidad
| RF | Parte del plan | Test |
|---|---|---|
| RF-1, RF-2 | `app.py` | `tests/test_api_rutas.py::test_rutas_y_docs_existen` |
| RF-3, RF-16 | `app.py` | `tests/test_api_rutas.py::test_health_indica_modo` |
| RF-4, RF-5 | `esquemas.py`, `servicio.py` | `tests/test_api_rutas.py::test_ask_valido_y_422` |
| RF-6 | `servicio.py` | `tests/test_api_rutas.py::test_ask_sin_thread_id` |
| RF-7, RF-8, RF-9 | `servicio.py` | `tests/test_api_aprobacion.py::test_auto_aprobar` |
| RF-10, RF-11, RF-12 | `servicio.py` | `tests/test_api_aprobacion.py::test_aprobar_y_rechazar` |
| RF-13 | `servicio.py` | `tests/test_api_aprobacion.py::test_aprobar_sin_plan` |
| RF-14 | `app.py` | `tests/test_api_rutas.py::test_fallo_inesperado_500` |
| RF-15 | `servicio.py` | `tests/test_api_aprobacion.py::test_done_lo_decide_el_agente` |