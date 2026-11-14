# Spec 015 — Front Streamlit como cliente de la API

> Estado: Aprobada · Fecha: 2026-11-14

## Contexto y objetivo

`front.py` todavía carga directamente el agente y las utilidades de sesión, planes y depuración. La spec 013 ya expone una API HTTP para conversar y decidir planes. Esta spec adapta Streamlit para consumir esa API: el frontend no importa ni ejecuta el grafo o sus herramientas, y muestra conversaciones y decisiones usando los datos devueltos por el servicio.

## Usuarios / actores

- Persona usuaria que consulta el asistente desde Streamlit.
- Equipo que configura el frontend para una API local o publicada.

## Historias de usuario

- H1: Como persona usuaria quiero enviar preguntas y ver las respuestas en el chat sin que el frontend ejecute el agente.
- H2: Como persona usuaria quiero comprobar la disponibilidad del backend y cargar una conversación anterior.
- H3: Como equipo quiero cambiar la URL de la API por configuración y mantener la clave fuera del repositorio y de la interfaz.

## Requisitos funcionales (criterios de aceptación en EARS)

- RF-1: EL SISTEMA consumirá la API HTTP para preguntar, aprobar o rechazar y cargar mensajes, y `front.py` no importará ni ejecutará el grafo, herramientas del agente ni módulos de sesión del backend.
- RF-2: DONDE `API_BASE_URL` no esté definida o esté vacía, EL SISTEMA usará `http://127.0.0.1:8000`; DONDE esté definida, EL SISTEMA usará su valor sin requerir cambios de código.
- RF-3: EL SISTEMA leerá `API_KEY` de la configuración local del frontend, la enviará como parámetro `api_key` en las rutas protegidas y nunca la mostrará en pantalla ni la guardará en el repositorio; `.env.example` documentará ambas variables con valores de ejemplo no secretos.
- RF-4: CUANDO la persona pulse el botón de estado en la barra lateral, EL SISTEMA consultará `GET /health` sin clave y mostrará junto al botón el resultado de esa última consulta: «🟢 Backend disponible» si el servicio está disponible según la spec 013, y «🔴 Backend no disponible» si la consulta falla o el servicio no está operativo.
- RF-5: CUANDO la persona envíe texto con Intro o con el botón de envío, EL SISTEMA enviará `POST /ask` con `pregunta`, el `thread_id` activo si existe, y `auto_aprobar` según el interruptor «Aprobar automáticamente un único plan»; el interruptor tendrá como valor inicial `false`.
- RF-6: CUANDO la respuesta de `/ask` indique `pendiente_hitl=true`, EL SISTEMA mostrará los planes pendientes y los botones «Aprobar» y «Rechazar», independientemente del valor de `auto_aprobar`; si hay exactamente un plan y `auto_aprobar=true`, la API podrá aprobarlo según la spec 013, y si hay varios la API no aprobará ninguno y los dejará pendientes para decisión manual.
- RF-7: CUANDO se apruebe o rechace un plan, EL SISTEMA enviará `POST /approve` con el hilo activo, la decisión y, cuando haya varios planes, el `plan_id`; mostrará el resultado devuelto y después volverá a solicitar el historial a la API, reemplazando el chat visible por ese historial si la carga funciona.
- RF-8: CUANDO se solicite cargar una conversación mediante un `thread_id`, EL SISTEMA consultará `GET /threads/{thread_id}/messages`, ordenará los mensajes por `orden` ascendente, presentará `user` como persona usuaria y `assistant` como asistente, y convertirá ese hilo en el activo.
- RF-9: SI la carga de historial falla o el identificador no existe, ENTONCES EL SISTEMA mostrará un error comprensible y conservará íntegro el chat visible y su hilo activo; si la API responde 501, indicará que el historial todavía no está implementado.
- RF-10: CUANDO la persona pulse «Nueva conversación», EL SISTEMA limpiará el chat visible y el estado de aprobación, dejará el hilo activo sin identificador y hará que el siguiente `/ask` omita `thread_id` para que la API genere uno nuevo.
- RF-11: MIENTRAS el chat esté asociado a un hilo, EL SISTEMA mostrará su `thread_id` en la barra lateral y no mezclará mensajes de otros hilos.
- RF-12: SI una petición a la API falla o devuelve un error, ENTONCES EL SISTEMA mostrará un mensaje comprensible en español y conservará los mensajes visibles antes de la petición; si falta `API_KEY`, indicará cómo configurarla sin enviar una ruta protegida, y si la API devuelve 401 mostrará un error de autenticación comprensible.
- RF-13: CUANDO `/ask` o `/approve` responda correctamente, EL SISTEMA mostrará la respuesta y los mensajes disponibles del resultado sin inferir por su cuenta si el turno terminó o si un plan fue aplicado.

## Requisitos no funcionales

- Seguridad: la clave API se obtiene de `.env` local y se transmite solo en las peticiones a rutas protegidas; no aparece en textos, errores ni paneles de depuración.
- Modularidad: Streamlit actúa como cliente HTTP de la API; el frontend no ejecuta lógica del agente.
- Configuración: la URL pública de Render se configura mediante `API_BASE_URL`, sin cambios en `front.py`.
- Idioma: controles y errores visibles en español.
- Robustez: los errores de red, HTTP y respuestas inesperadas no borran el chat en pantalla.

## Casos límite

- `API_BASE_URL` no configurada o en blanco: RF-2.
- Falta `API_KEY` local, o la API devuelve 401 aunque haya una clave configurada: RF-3 y RF-12.
- API apagada: RF-4 y RF-12.
- Respuesta sin plan pendiente: no mostrar controles de decisión (RF-6).
- Historial vacío o fallo al cargarlo: RF-8 y RF-9.
- Iniciar conversación nueva después de cargar una existente: RF-10 y RF-11.
- Error de aprobación: conservar conversación, informar del fallo y no presentar como aplicada una decisión no confirmada (RF-7 y RF-12).
- Historial con respuesta HTTP 501: informar de que todavía no está implementado y conservar el chat visible (RF-9 y RF-12).
- Varios planes pendientes con `auto_aprobar=true`: la API no aprueba ninguno y el frontend permite decidir manualmente (RF-6).
- Rol de historial distinto de `user` o `assistant`: conservar y mostrar el contenido con una presentación genérica (RF-8).
- Fallo del primer `/ask` antes de recibir un `thread_id`: conservar el texto y el error sin reintentar automáticamente; un envío posterior sin identificador inicia un hilo nuevo (RF-10, RF-11 y RF-12).
- `/approve` correcto y recarga del historial fallida: mantener en pantalla el resultado devuelto por `/approve` y el chat existente, con el mensaje del fallo de historial (RF-7, RF-9 y RF-12).

## Fuera de alcance

- Desplegar la API en Render o cambiar la lógica interna del agente.
- Cambiar los contratos de `/ask`, `/approve` o del historial, salvo aclarar los datos que el frontend necesita consumir.
- Implementar almacenamiento del historial en el frontend; la fuente del historial es la API.
- Mostrar la clave API o permitir editarla desde la interfaz.

## Criterios de finalización

- Todos los requisitos funcionales quedan cubiertos por pruebas del cliente HTTP con respuestas simuladas, sin llamadas reales al agente ni a servicios externos.
- Revisión de `front.py` confirma que no importa el grafo, herramientas, cargadores del agente ni la capa de sesión del backend.
- Validación manual permite comprobar health, conversación nueva, aprobación/rechazo, carga de historial, cambio de hilo y mensajes de error conservando el chat.

## Decisiones de clarificación — 2026-11-14

- La clave de rutas protegidas se envía como parámetro `api_key`.
- El indicador de salud refleja únicamente el estado del servicio que declara la spec 013; no afirma la disponibilidad de PostgreSQL.
- El historial puede responder 501 durante esta etapa. El frontend debe explicar que el historial aún no está implementado y conservar la conversación visible.
- Si varios planes quedan pendientes aunque `auto_aprobar=true`, el frontend permite su decisión manual; la API no aprueba ninguno automáticamente conforme a RF-9 de la spec 013.
- Tras una decisión correcta, el resultado de `/approve` se muestra de inmediato. El historial reemplaza el chat solo si se carga correctamente; si la recarga falla, se conserva el chat y el resultado de la decisión.
- Los roles canónicos del historial son `user` y `assistant`, ordenados por `orden` ascendente; un rol desconocido se presenta de forma genérica sin descartar el contenido.
- Si falta `API_KEY`, el frontend muestra cómo configurarla y no envía la petición protegida. La API sigue siendo responsable de validar la clave; un 401 se muestra como error de autenticación.
- Si falla la primera pregunta antes de recibir `thread_id`, no hay reintento automático. Se conserva el texto visible y un envío posterior sin identificador inicia un hilo nuevo.
- La carpeta e identificador de esta spec es 015.
- La constitución permite ahora que Streamlit consuma la API HTTP como cliente fino; el frontend no importa ni ejecuta el grafo.
