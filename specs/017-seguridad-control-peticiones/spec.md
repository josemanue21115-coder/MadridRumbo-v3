# Spec 017 — Seguridad y control de peticiones de la API

> Estado: Borrador · Fecha: 2026-11-17

## Contexto y objetivo

La API de MadridRumbo expone operaciones que inician turnos del agente y consultan conversaciones, pero todavía no aplica autenticación ni límites de uso. Esta spec define cómo proteger sus rutas, limitar las peticiones y acotar la duración de un turno de `/ask`, con errores comprensibles y sin revelar información interna.

## Usuarios / actores

- Frontend Streamlit que consume la API según la spec 015.
- Equipo que configura y verifica la API en local.
- Persona que prueba la documentación interactiva de la API.

## Historias de usuario

- H1: Como equipo quiero exigir una clave en las operaciones protegidas para controlar el acceso a la API.
- H2: Como persona usuaria quiero recibir errores con códigos y mensajes definidos cuando una petición no está autorizada, excede el límite o tarda demasiado.
- H3: Como equipo quiero configurar los límites del servicio desde el entorno y comprobarlos en local sin consumir llamadas a un LLM.

## Requisitos funcionales (criterios de aceptación en EARS)

- RF-1: EL SISTEMA exigirá una clave válida, recibida en el parámetro `api_key`, para atender `POST /ask`, `POST /approve` y `GET /threads/{thread_id}/messages`.
- RF-2: EL SISTEMA permitirá consultar `GET /health` y `/docs` sin proporcionar una clave.
- RF-3: SI una petición a una ruta protegida no incluye una clave o incluye una clave no válida, ENTONCES EL SISTEMA responderá con código HTTP 401.
- RF-4: SI `API_KEY` no está configurada en el servicio, ENTONCES EL SISTEMA responderá con código HTTP 503 a las peticiones de rutas protegidas.
- RF-5: EL SISTEMA obtendrá `API_KEY`, `RATE_LIMIT_PER_MINUTE` y `ASK_TIMEOUT_SECONDS` de la configuración del entorno.
- RF-6: DONDE no se configure `RATE_LIMIT_PER_MINUTE`, EL SISTEMA permitirá como máximo 30 peticiones por clave de API durante cualquier periodo de 60 segundos.
- RF-7: CUANDO una clave supere `RATE_LIMIT_PER_MINUTE` peticiones a rutas protegidas durante cualquier periodo de 60 segundos, EL SISTEMA responderá con código HTTP 429 a las peticiones adicionales de esa clave.
- RF-8: DONDE no se configure `ASK_TIMEOUT_SECONDS`, EL SISTEMA limitará a 300 segundos la duración del turno iniciado por `POST /ask`.
- RF-9: CUANDO el turno iniciado por `POST /ask` supere `ASK_TIMEOUT_SECONDS`, EL SISTEMA responderá con código HTTP 504 y el mensaje «El turno ha superado el tiempo máximo permitido. Inténtalo de nuevo.».
- RF-10: MIENTRAS se procesa una petición distinta de `POST /ask`, EL SISTEMA no aplicará el límite de tiempo definido por `ASK_TIMEOUT_SECONDS`.
- RF-11: SI una petición protegida supera el límite de tiempo o falla, ENTONCES EL SISTEMA no incluirá en su respuesta la excepción, trazas, claves ni detalles de infraestructura.
- RF-12: CUANDO venza el límite de tiempo de un turno, EL SISTEMA registrará el evento en los logs sin incluir claves ni secretos.
- RF-13: EL SISTEMA documentará en `.env.example` las variables `API_KEY`, `RATE_LIMIT_PER_MINUTE` y `ASK_TIMEOUT_SECONDS` con valores de ejemplo que no sean secretos reales.
- RF-14: EL SISTEMA permitirá verificar localmente el código 401 enviando una petición a una ruta protegida sin `api_key`.
- RF-15: EL SISTEMA permitirá verificar localmente el código 429 realizando peticiones con una misma clave a una ruta protegida que no inicie llamadas a un LLM hasta superar el límite configurado.
- RF-16: EL SISTEMA permitirá verificar localmente el código 504 reduciendo `ASK_TIMEOUT_SECONDS` para que venza durante un turno de `/ask`.

## Requisitos no funcionales

- Seguridad: las claves y secretos no aparecerán en respuestas ni logs.
- Coste: las verificaciones de autenticación y límite de peticiones no requerirán llamadas a un LLM.
- Idioma: el mensaje de timeout será el definido en RF-9; los mensajes de error estarán en español.
- Compatibilidad: el nombre y la ubicación de la clave seguirán el contrato `api_key` de las specs 013 y 015.

## Casos límite

- Servicio sin `API_KEY`: responder 503 en rutas protegidas (RF-4).
- Clave ausente o incorrecta con `API_KEY` configurada: responder 401 (RF-3).
- Rutas públicas `/health` y `/docs`: accesibles sin clave (RF-2).
- Clave dentro del límite: petición admitida; clave que excede el límite en la ventana de 60 segundos: 429 (RF-6 y RF-7).
- Vencimiento durante `/ask`: responder 504 con el mensaje acordado y registrar el evento sin secretos (RF-9 y RF-12).
- Peticiones a `/approve` o al historial que tarden más que `ASK_TIMEOUT_SECONDS`: el timeout de turno de `/ask` no se aplica (RF-10).

## Fuera de alcance

- Cambiar los formatos de petición y respuesta de las rutas definidos en las specs 013 y 015, salvo el parámetro de autenticación `api_key`.
- Limitar el tiempo de `/approve`, `/health`, `/docs` o la consulta del historial.
- Autenticación de usuarios individuales, roles o permisos por recurso.
- Cambiar el comportamiento del agente o el contenido del historial.

## Criterios de finalización

- Todos los requisitos funcionales tienen criterios verificables en local.
- Se comprueban los códigos 401, 429 y 504 mediante los procedimientos definidos en RF-14, RF-15 y RF-16.
- La configuración documentada no contiene secretos reales y las respuestas y logs no revelan secretos ni detalles internos.

## Dudas abiertas

- Ninguna.
