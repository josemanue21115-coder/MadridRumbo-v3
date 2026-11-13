# Tareas — Spec 013

> Una tarea cada vez: `/sdd-implementar Tn`. Tests primero. Marca `[x]` al terminar.

- [x] T1. Preparar el terreno: añadir `fastapi`, `uvicorn` y `httpx` a `requirements.txt`, instalarlos y crear el paquete vacío `src/api/`. (Stack, sin RF)
      Hecho cuando: `pip install -r requirements.txt` termina sin errores y `python -c "import src.api, fastapi"` no falla.

- [x] T2. Añadir primero pruebas de los formatos de datos; después, crear `src/api/esquemas.py` con pregunta, respuesta, aprobación y mensaje. (RF-4, RF-5, RF-10, RF-11)
      Hecho cuando: `python -m pytest tests/test_api_esquemas.py` queda verde e incluye pregunta vacía rechazada, `thread_id` opcional, `auto_aprobar` verdadero por defecto y `plan_id` opcional.

- [x] T3. Añadir primero pruebas de las rutas básicas; después, crear `app.py` en la raíz con GET /health y la documentación en /docs (RF-1, RF-2, RF-3, RF-16)
      Hecho cuando: `python -m pytest tests/test_api_rutas.py` queda verde e incluye /health indicando el modo simulado y /docs accesible sin clave.

- [x] T4. Añadir primero pruebas de POST /ask sin aprobación automática; después, crear `src/api/servicio.py` y la ruta: pasa la pregunta al agente, crea `thread_id` si falta, devuelve 422 si es inválida y deduce el campo de error. (RF-4, RF-5, RF-6, RF-13)
      Hecho cuando: `python -m pytest tests/test_api_rutas.py` queda verde con una pregunta válida, una vacía y una sin `thread_id`.

- [x] T5. Añadir primero pruebas de la aprobación automática con `GrafoFalso`; después, implementar `auto_aprobar` para uno y para varios planes. (RF-7, RF-8, RF-9, RF-15)
      Hecho cuando: `python -m pytest tests/test_api_aprobacion.py` queda verde e incluye un plan con aprobación automática, un plan sin ella y varios planes sin aprobar ninguno.

- [x] T6. Añadir primero pruebas de POST /approve; después, crear la ruta: aprobar, rechazar, elegir plan y aprobar sin plan pendiente. (RF-10, RF-11, RF-12, RF-13)
      Hecho cuando: `python -m pytest tests/test_api_aprobacion.py` queda verde con aprobar, rechazar, `plan_id` y un aviso sin plan pendiente.

- [ ] T7. Añadir primero pruebas del fallo del agente y de la ruta del historial; después, devolver 500 genérico ante un fallo inesperado y 501 en GET /threads/{thread_id}/messages. (RF-1, RF-14)
      Hecho cuando: `python -m pytest tests/test_api_rutas.py` queda verde con un agente que falla (500 sin detalles internos) y la ruta del historial respondiendo 501.

- [ ] T8. Validación final RF por RF (`/sdd-validar`). (Todos los RF)
      Hecho cuando: `python -m pytest` queda verde y `validacion.md` contiene un veredicto «Sí» para RF-1 a RF-16, más la demo manual en /docs con el modo simulado.