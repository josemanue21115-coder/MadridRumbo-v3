# Plan técnico — Spec 015

> Basado en `spec.md` (estado: Aprobada). No añade comportamiento fuera de la spec.

## Archivos afectados

| Archivo | Crear / Modificar | Qué cambia | RF |
|---|---|---|---|
| `front.py` | Modificar | Reemplazar carga directa del agente, sesión y grafo por una UI Streamlit cliente HTTP; guardar hilo, mensajes, planes y estados de petición en `st.session_state`. | RF-1 a RF-13 |
| `src/clientes/api_http.py` | Crear | Cliente HTTP pequeño para health, ask, approve e historial; autenticación por parámetro `api_key`, errores legibles y validación básica de respuestas. Usará `urllib` de la biblioteca estándar. | RF-1 a RF-9, RF-12, RF-13 |
| `.env.example` | Modificar | Documentar `API_BASE_URL=http://127.0.0.1:8000` y `API_KEY=` con valores de ejemplo no secretos. | RF-2, RF-3 |
| `tests/test_api_http.py` | Crear | Probar la construcción de peticiones y el manejo de respuestas/errores del cliente HTTP sin red. | RF-1 a RF-9, RF-12, RF-13 |
| `tests/test_front_streamlit_api.py` | Crear | Probar la interfaz con Streamlit `AppTest` y un cliente HTTP simulado; comprobar que el frontend no importa módulos del grafo. | RF-1 a RF-13 |

No se modifica `app.py`, el agente ni la lógica interna del backend. La UI consume el contrato especificado: la autenticación de las rutas protegidas y la futura implementación del historial son responsabilidad de la API.

## Contrato

No cambian los contratos HTTP de la API ni los comandos de ejecución. `front.py` deja de llamar a funciones Python del grafo y llama a las rutas HTTP. El cliente local recibe `base_url`, clave (si aplica), ruta y datos; devuelve JSON validado o lanza un error de cliente que la UI presenta sin borrar el estado visible.

Ejemplos de peticiones:

```http
GET /health
POST /ask?api_key=<clave>
Content-Type: application/json

{"pregunta":"¿Hasta qué hora hay metro?","auto_aprobar":false}

POST /approve?api_key=<clave>
Content-Type: application/json

{"thread_id":"abc-1","aprobado":true}

GET /threads/abc-1/messages?api_key=<clave>
```

`POST /ask` devuelve el contrato de la spec 013, por ejemplo:

```json
{"respuesta":"Hay un plan pendiente.","thread_id":"abc-1","done":false,"pendiente_hitl":true,"plan":[{"id":"ruta-1","resultado":{}}],"error":null}
```

El historial devuelve mensajes `{role, content, orden}`. El frontend ordena por `orden`; `user` y `assistant` tienen presentación diferenciada y cualquier rol desconocido conserva el contenido con una presentación genérica.

## Lógica clave

```text
inicializar:
    cargar .env sin importar config ni módulos del backend
    base_url = API_BASE_URL no vacía o http://127.0.0.1:8000
    inicializar estado de chat e hilo en session_state

health:
    GET /health sin api_key
    mostrar estado ok de la spec 013 o error

enviar(pregunta):
    si falta API_KEY: mostrar instrucción y conservar conversación
    body = pregunta + auto_aprobar
    si hay hilo activo: añadir thread_id
    POST /ask?api_key=...
    en éxito: guardar thread_id devuelto, añadir pregunta/respuesta y planes
    en fallo: conservar texto y conversación; no reintentar automáticamente

decidir(aprobado, plan_id):
    POST /approve?api_key=... con hilo activo y decisión
    mostrar respuesta del endpoint
    GET /threads/{thread_id}/messages?api_key=...
    si funciona: ordenar y reemplazar historial visible
    si falla: conservar chat y respuesta; para 501 indicar que historial aún no está implementado

cargar_hilo(id):
    mantener snapshot visible
    GET historial; solo en éxito reemplazar chat y activar id
    en error: restaurar/conservar snapshot e informar

nueva_conversacion:
    vaciar mensajes, planes e hilo; siguiente ask omite thread_id
```

## Decisiones técnicas

| Decisión | Alternativa descartada | Por qué |
|---|---|---|
| Crear `src/clientes/api_http.py` como adaptador HTTP pequeño. | Hacer las peticiones directamente en los bloques de UI de `front.py`. | Centraliza URL, autenticación, decodificación JSON y errores, y permite probar el contrato aislado. |
| Usar `urllib.request` de la biblioteca estándar. | Añadir `requests` o usar HTTPX en ejecución. | Evita añadir dependencias y HTTPX está permitido por la constitución para pruebas de API, no como dependencia de ejecución del cliente. |
| Cargar el `.env` desde el frontend con `python-dotenv` y leer solo `API_BASE_URL`/`API_KEY`. | Importar `config.py` para cargar variables. | `config.py` importa configuración del backend y carga claves de otros proveedores; el frontend debe permanecer desacoplado y no inspeccionar ni mostrar secretos ajenos a la API. |
| Mantener el historial visible en `st.session_state` y reemplazarlo solo tras una carga de historial exitosa. | Vaciar el chat antes de una petición o tratar la respuesta de error como un hilo nuevo. | Cumple la conservación del chat ante fallos y evita mezclar hilos. |
| Validar HTTP 501 como estado esperado temporal del historial. | Tratarlo como historial vacío o como error genérico. | La ruta actual responde 501; el mensaje específico permite que el front funcione antes de que la API de historial esté disponible. |
| Enviar la clave en el query param `api_key` y omitir la petición si falta localmente. | Incluir la clave en JSON, encabezados no contemplados por el contrato o dejar que falle una petición sin credenciales. | Sigue el contrato indicado y permite mostrar una instrucción de configuración; la API conserva la responsabilidad de autorizar. |

## Estrategia de tests

Los tests unitarios del cliente HTTP sustituirán `urllib.request.urlopen` por dobles que registren URL, método, query, cabeceras y cuerpo, y devuelvan respuestas JSON o errores HTTP sin abrir sockets. Las pruebas de UI usarán `AppTest` con métodos del cliente HTTP parcheados. No se invocarán el agente, herramientas, LLM, PostgreSQL ni una API real. La comprobación manual se limita a iniciar la API local con `uvicorn app:app` y abrir Streamlit; no se requiere para validar automáticamente el contrato.

| RF | Comprobación propuesta |
|---|---|
| RF-1 | Test estático de imports de `front.py` y test UI con cliente HTTP simulado; confirmar que no se carga el grafo. |
| RF-2 | Tests del fallback para variable ausente/vacía y del uso de una URL configurada. |
| RF-3 | Test de query `api_key`, ausencia de clave en logs/UI y variables documentadas en `.env.example`. |
| RF-4 | Test UI: health se solicita sin clave; respuesta `estado=ok` y fallo de conexión muestran el estado correspondiente y no se refresca sin pulsar. |
| RF-5 | Test UI y cliente: envío por chat construye pregunta, `auto_aprobar` y solo añade `thread_id` cuando existe. |
| RF-6 | Tests de respuesta sin pendiente, un plan autoaprobado y varios pendientes; con pendientes se presentan controles de decisión. |
| RF-7 | Tests de aprobar/rechazar, `plan_id` cuando hay varios planes, resultado visible, recarga exitosa que reemplaza historial y recarga fallida que conserva chat/resultado. |
| RF-8 | Test de carga que ordena por `orden`, representa roles conocidos/desconocidos y activa el hilo cargado. |
| RF-9 | Tests de 404, error de red y 501; conservar snapshot del hilo y mostrar mensajes comprensibles. |
| RF-10 | Test de nueva conversación: limpiar estado, omitir hilo en la siguiente pregunta y adoptar el identificador devuelto por la API. |
| RF-11 | Test UI del identificador activo y de que cargar/cambiar hilo sustituye mensajes sin mezclarlos. |
| RF-12 | Tests de API apagada, HTTP no exitoso, 401 y clave ausente; los errores conservan los mensajes visibles. |
| RF-13 | Tests de `/ask` y `/approve`: mostrar `respuesta`, manejar `done`, `pendiente_hitl`, `plan` y `error` como datos de API sin derivar decisiones propias. |

La navegación visual de Streamlit y la conexión de extremo a extremo se pueden comprobar a mano con la API local; no se automatiza la llamada a servicios externos.

## Riesgos

- La API actual de `app.py` no implementa autenticación, aunque este frontend enviará `api_key`; hasta que la protección de spec 013/Persona 3 esté activa, la clave no será validada localmente.
- `GET /threads/{thread_id}/messages` devuelve 501 en la implementación actual. La UI debe manejarlo explícitamente; cargar conversaciones previas funcionará cuando la API implemente el historial.
- Un timeout durante el primer `/ask` puede ocurrir después de que el servidor procese la pregunta pero antes de devolver el `thread_id`; por decisión de spec no se reintenta automáticamente y un siguiente envío inicia otro hilo.
- `urllib` requiere convertir y presentar errores HTTP/red de forma consistente; los cuerpos de error pueden variar entre errores FastAPI y fallos de conexión.
- Streamlit vuelve a ejecutar el script tras las interacciones; limpiar o actualizar el estado en el orden incorrecto puede mezclar hilos o perder mensajes. Los tests AppTest deben cubrir estas transiciones.

## Trazabilidad

| RF | Parte del plan | Test |
|---|---|---|
| RF-1 | `front.py`, `src/clientes/api_http.py` | `tests/test_front_streamlit_api.py::test_front_no_importa_backend` |
| RF-2 | Carga de entorno y cliente HTTP | `tests/test_api_http.py::test_url_base_por_defecto_y_configurada` |
| RF-3 | Cliente HTTP y `.env.example` | `tests/test_api_http.py::test_api_key_en_query_param` |
| RF-4 | Barra lateral health | `tests/test_front_streamlit_api.py::test_health_publica_y_estado_persistente` |
| RF-5 | Formulario de chat y `/ask` | `tests/test_front_streamlit_api.py::test_ask_envia_opciones_y_hilo_activo` |
| RF-6 | Presentación de planes pendientes | `tests/test_front_streamlit_api.py::test_pendientes_muestran_decisiones` |
| RF-7 | Aprobar/rechazar y recargar historial | `tests/test_front_streamlit_api.py::test_decision_recarga_historial_o_conserva_chat` |
| RF-8 | Carga y presentación del historial | `tests/test_front_streamlit_api.py::test_historial_ordenado_y_hilo_activo` |
| RF-9 | Errores de historial | `tests/test_front_streamlit_api.py::test_historial_501_conserva_chat` |
| RF-10 | Nueva conversación | `tests/test_front_streamlit_api.py::test_nueva_conversacion_omite_thread_id` |
| RF-11 | Estado de hilo y aislamiento de mensajes | `tests/test_front_streamlit_api.py::test_cambio_de_hilo_no_mezcla_mensajes` |
| RF-12 | Errores HTTP y configuración | `tests/test_front_streamlit_api.py::test_error_api_key_401_y_red_conservan_chat` |
| RF-13 | Render de resultados API | `tests/test_front_streamlit_api.py::test_renderiza_resultados_del_contrato_api` |

## Aprobación

Solicito aprobación de este plan antes de pasar a `/sdd-tareas`.
