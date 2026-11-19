# Spec 017 — Seguridad y control de peticiones de la API

> Estado: Aprobada · Fecha: 2026-11-18

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
- RF-6: DONDE no se configure `RATE_LIMIT_PER_MINUTE`, EL SISTEMA permitirá como máximo 30 intentos de petición por clave presentada durante cualquier periodo móvil de 60 segundos, compartidos entre las rutas protegidas.
- RF-7: CUANDO una clave presentada supere `RATE_LIMIT_PER_MINUTE` intentos de petición a rutas protegidas durante cualquier periodo móvil de 60 segundos, EL SISTEMA responderá con código HTTP 429 a los intentos adicionales asociados a esa clave.
- RF-8: DONDE no se configure `ASK_TIMEOUT_SECONDS` o su valor no sea un entero positivo, EL SISTEMA limitará a 300 segundos la duración del turno iniciado por `POST /ask`.
- RF-9: CUANDO el turno iniciado por `POST /ask` supere `ASK_TIMEOUT_SECONDS`, EL SISTEMA responderá con código HTTP 504 y el mensaje «El turno ha superado el tiempo máximo permitido. Inténtalo de nuevo.».
- RF-10: MIENTRAS se procesa una petición distinta de `POST /ask`, EL SISTEMA no aplicará el límite de tiempo definido por `ASK_TIMEOUT_SECONDS`.
- RF-11: SI una petición protegida falla de forma inesperada, ENTONCES EL SISTEMA responderá con el error genérico definido en la spec 013 y no incluirá la excepción, trazas, claves ni detalles de infraestructura.
- RF-12: CUANDO venza el límite de tiempo de un turno, EL SISTEMA registrará el evento en los logs sin incluir claves ni secretos.
- RF-13: EL SISTEMA documentará en `.env.example` las variables `API_KEY`, `RATE_LIMIT_PER_MINUTE` y `ASK_TIMEOUT_SECONDS` con valores de ejemplo no secretos, incluidos 30 para `RATE_LIMIT_PER_MINUTE` y 300 para `ASK_TIMEOUT_SECONDS`.
- RF-14: EL SISTEMA permitirá verificar localmente el código 401 enviando una petición a una ruta protegida sin `api_key`.
- RF-15: EL SISTEMA permitirá verificar localmente el código 429 realizando peticiones con una misma clave a una ruta protegida que no inicie llamadas a un LLM hasta superar el límite configurado.
- RF-16: EL SISTEMA permitirá verificar localmente el código 504 reduciendo `ASK_TIMEOUT_SECONDS` y usando un turno simulado o sustituido que supere ese límite sin llamar a un LLM real.
- RF-17: SI `RATE_LIMIT_PER_MINUTE` no es un entero positivo, ENTONCES EL SISTEMA aplicará el valor predeterminado de 30 peticiones por periodo móvil de 60 segundos.
- RF-18: SI una petición protegida no incluye `api_key`, ENTONCES EL SISTEMA contabilizará el intento en un límite compartido para peticiones sin clave.
- RF-19: SI una petición protegida incluye una clave inválida, ENTONCES EL SISTEMA contabilizará el intento en el límite asociado al valor de clave presentado.

## Requisitos no funcionales

- Seguridad: las claves y secretos no aparecerán en respuestas ni logs.
- Coste: las verificaciones de autenticación y límite de peticiones no requerirán llamadas a un LLM; la verificación del timeout usará un turno simulado o sustituido.
- Idioma: el mensaje de timeout será el definido en RF-9; los mensajes de error estarán en español.
- Compatibilidad: el nombre y la ubicación de la clave seguirán el contrato `api_key` de las specs 013 y 015.

## Casos límite

- Clave ausente o incorrecta con `API_KEY` configurada: responder 401 y contabilizar el intento en el límite compartido sin clave o en el asociado a la clave presentada, respectivamente (RF-3, RF-18 y RF-19).
- Servicio sin `API_KEY` configurada: responder 503 aunque la petición también carezca de clave (RF-4).
- Rutas públicas `/health` y `/docs`: accesibles sin clave (RF-2).
- El límite se comparte entre las tres rutas protegidas y usa una ventana móvil de 60 segundos; al excederlo, responder 429 (RF-6 y RF-7).
- Valor de `RATE_LIMIT_PER_MINUTE` inválido o ausente: usar 30; valor de `ASK_TIMEOUT_SECONDS` inválido o ausente: usar 300 (RF-8 y RF-17).
- Vencimiento durante `/ask`: responder 504 con el mensaje acordado y registrar el evento sin secretos (RF-9 y RF-12).
- Peticiones a `/approve` o al historial que tarden más que `ASK_TIMEOUT_SECONDS`: el timeout de turno de `/ask` no se aplica (RF-10).

## Fuera de alcance

- Cambiar los formatos de petición y respuesta de las rutas definidos en las specs 013 y 015, salvo el parámetro de autenticación `api_key`.
- Limitar el tiempo de `/approve`, `/health`, `/docs` o la consulta del historial.
- Autenticación de usuarios individuales, roles o permisos por recurso.
- Cambiar el comportamiento del agente o el contenido del historial.
- Aplicar el límite de tiempo de `/ask` a otras rutas.

## Criterios de finalización

- Todos los requisitos funcionales tienen criterios verificables en local, incluidos los valores inválidos de configuración, la cuota compartida y la ventana móvil.
- Se comprueban los códigos 401, 429 y 504 mediante los procedimientos definidos en RF-14, RF-15 y RF-16.
- La configuración documentada no contiene secretos reales y las respuestas y logs no revelan secretos ni detalles internos.

## Dudas abiertas

- Ninguna.

## Decisiones de clarificación — 2026-11-18

- `api_key` se envía como parámetro de query, según las specs 013 y 015.
- El límite es compartido por clave entre `/ask`, `/approve` y el historial, y se mide en una ventana móvil de 60 segundos.
- Los intentos sin clave comparten un contador; los intentos con clave inválida se contabilizan por el valor de clave presentado.
- Si `RATE_LIMIT_PER_MINUTE` no es un entero positivo se usa 30; si `ASK_TIMEOUT_SECONDS` no es un entero positivo se usa 300.
- Si el servicio no tiene `API_KEY`, responde 503 aunque falte también la clave en la petición.
- Los fallos inesperados mantienen el error genérico 500 de la spec 013; los fallos definidos en esta spec usan sus códigos específicos.
- La comprobación local de 504 puede usar un turno simulado o sustituido, sin llamadas a un LLM real.
- Los límites se configuran por entorno y `.env.example` documenta sus valores predeterminados sin secretos reales.
