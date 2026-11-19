# Tareas — Spec 015

> Una tarea cada vez: `/sdd-implementar Tn`. Tests primero. Marca `[x]` al terminar.

- [x] T1. Añadir pruebas unitarias del cliente HTTP: URL por defecto/configurada, health público, query `api_key` en rutas protegidas, JSON de `/ask` y `/approve`, historial y conversión de errores HTTP/red. (RF-1, RF-2, RF-3, RF-4, RF-5, RF-7, RF-8, RF-9, RF-12, RF-13)
      Hecho cuando: `python -m pytest tests/test_api_http.py` queda verde usando `urlopen` simulado y no abre conexiones de red.

- [x] T2. Crear `src/clientes/api_http.py` con el cliente `urllib` probado en T1 y documentar `API_BASE_URL`/`API_KEY` en `.env.example`, sin credenciales reales. (RF-1, RF-2, RF-3, RF-4, RF-5, RF-7, RF-8, RF-9, RF-12, RF-13)
      Hecho cuando: `python -m pytest tests/test_api_http.py` queda verde y `.env.example` contiene solo valores de ejemplo para ambas variables.

- [x] T3. Añadir pruebas AppTest para el estado de sesión y el chat: sin imports del grafo/backend, envío de `pregunta` y `auto_aprobar`, omisión de `thread_id` al iniciar, adopción del id devuelto y creación de conversación nueva. (RF-1, RF-5, RF-10, RF-11)
      Hecho cuando: `python -m pytest tests/test_front_streamlit_api.py` queda verde con el cliente HTTP sustituido por un doble.

- [x] T4. Sustituir en `front.py` los imports y llamadas directos al agente/sesión por el cliente HTTP y estado de chat en `st.session_state`; implementar envío, indicador de espera y nueva conversación. (RF-1, RF-5, RF-10, RF-11)
      Hecho cuando: `python -m pytest tests/test_front_streamlit_api.py` queda verde y `rg "src\.(agent|graph|tools|clientes\.(cargar|sesion))" front.py` no encuentra imports del backend.

- [x] T5. Añadir pruebas AppTest de la barra lateral: health solo por pulsación y sin clave, conservación del último estado, carga de hilo, orden por `orden`, roles conocidos/desconocidos y conservación del chat ante 404/501/red. (RF-4, RF-8, RF-9, RF-11, RF-12)
      Hecho cuando: `python -m pytest tests/test_front_streamlit_api.py` queda verde con respuestas del cliente simuladas.

- [x] T6. Implementar en `front.py` el botón de health, el campo de carga de hilo y su comportamiento transaccional: solo cambiar hilo e historial cuando la respuesta sea válida; mostrar mensaje específico para 501. (RF-4, RF-8, RF-9, RF-11, RF-12)
      Hecho cuando: `python -m pytest tests/test_front_streamlit_api.py` queda verde; una carga fallida conserva el hilo y mensajes anteriores.

- [x] T7. Añadir pruebas AppTest de planes y decisiones: controles solo con `pendiente_hitl`, selección de plan cuando hay varios, body de aprobación/rechazo, render de `AskOut` y recarga de historial con éxito o fallo. (RF-6, RF-7, RF-9, RF-12, RF-13)
      Hecho cuando: `python -m pytest tests/test_front_streamlit_api.py` queda verde con `/approve` e historial simulados.

- [x] T8. Implementar el interruptor «Aprobar automáticamente un único plan», presentación de planes y botones Aprobar/Rechazar; mostrar respuesta de `/approve` y reemplazar el chat solo si recargar el historial funciona. (RF-6, RF-7, RF-9, RF-13)
      Hecho cuando: `python -m pytest tests/test_front_streamlit_api.py` queda verde y un fallo de recarga mantiene visible el resultado de decisión junto al chat previo.

- [x] T9. Añadir pruebas de errores y configuración: `API_KEY` ausente sin petición protegida, 401, fallo del primer `/ask` sin reintento y conservación del texto/conversación. (RF-3, RF-10, RF-12)
      Hecho cuando: `python -m pytest tests/test_front_streamlit_api.py` queda verde y los dobles confirman que no se hace una petición protegida sin clave.

- [x] T10. Implementar los mensajes de configuración/autenticación y el manejo de fallos del primer `/ask`, conservando el texto y sin reintentos automáticos. (RF-3, RF-10, RF-12)
      Hecho cuando: `python -m pytest tests/test_front_streamlit_api.py` queda verde para clave ausente, 401 y fallo de red.

- [x] T11. Validación final RF por RF (`/sdd-validar`), ejecutar la suite y revisar manualmente la UI contra API local donde el contrato esté disponible. (Todos los RF)
      Hecho cuando: `python -m pytest` queda verde; `validacion.md` registra veredicto para RF-1 a RF-13 y deja constancia explícita del 501 actual de historial y del estado real de autenticación de la API.
