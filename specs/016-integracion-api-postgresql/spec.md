# Spec 016 — Integración de la API con el historial PostgreSQL

> Estado: Aprobada por el responsable en la conversación · Fecha: 2026-11-15

Responsable: Persona 2, en coordinación con Persona 1 (API) y Persona 3 (frontend).

## Contexto y objetivo

La API de la spec 013 permite preguntar al agente y decidir sobre sus planes,
pero todavía no guarda los turnos en PostgreSQL y la consulta de historial
responde 501. La spec 014 aporta la persistencia validada de conversaciones y
mensajes. El frontend de la spec 015 ya solicita el historial por HTTP y espera
mensajes con `role`, `content` y `orden`.

Esta especificación conecta esos contratos para que una respuesta finalizada
quede guardada junto con su pregunta original y pueda recuperarse por `thread_id`,
incluso después de reiniciar la API. El historial guardado no recupera por sí
solo la memoria ni los planes pendientes del agente.

La numeración 015 está ocupada en la PR #4, aunque esa carpeta todavía no aparece
en la rama de PostgreSQL. La PR #1 continúa su revisión por un compañero; este
borrador no cambia su alcance ni implica su aprobación o fusión.

## Usuarios / actores

- Persona usuaria que quiere volver a consultar una conversación guardada.
- Frontend Streamlit que consulta el historial mediante la API HTTP.
- API del agente que recibe preguntas y decisiones de aprobación.
- Equipo que verifica la integración con PostgreSQL sin consumir APIs de pago.

## Historias de usuario

- H1: Como persona usuaria quiero recuperar las preguntas y respuestas finalizadas de mi conversación para consultarlas después.
- H2: Como persona usuaria quiero que la respuesta de un plan aprobado se guarde con la pregunta que lo originó para conservar un historial comprensible.
- H3: Como frontend quiero recibir mensajes ordenados con el formato ya acordado para mostrar una conversación sin mezclar otros hilos.
- H4: Como equipo quiero detectar los fallos de persistencia para no presentar como guardado un turno que no se ha almacenado.

## Requisitos funcionales (criterios de aceptación en EARS)

Los requisitos incorporan las decisiones D1, D2 y D3 confirmadas por el responsable
el 15/11/2026. El responsable confirmó después la aprobación global para preparar
el plan técnico; esa aprobación no autoriza implementación ni publicación.

- RF-01: CUANDO se consulte `GET /threads/{thread_id}/messages` para una conversación persistida, EL SISTEMA devolverá HTTP 200 con una lista de sus mensajes.
- RF-02: EL SISTEMA devolverá cada mensaje del historial con los campos `role`, `content` y `orden`.
- RF-03: EL SISTEMA asignará al historial de cada conversación valores `orden` consecutivos desde 1 según el orden de inserción de sus mensajes.
- RF-04: CUANDO se consulte el historial de un `thread_id`, EL SISTEMA excluirá los mensajes pertenecientes a otros identificadores.
- RF-05: SI el `thread_id` consultado no corresponde a una conversación persistida ni a un hilo conocido por la API en el proceso actual, ENTONCES EL SISTEMA responderá HTTP 404 con el mensaje «Conversación no encontrada».
- RF-06: DONDE un hilo conocido todavía no contenga turnos finalizados guardados, EL SISTEMA devolverá HTTP 200 con una lista vacía.
- RF-07: CUANDO `POST /ask` finalice correctamente un turno sin aprobación pendiente, EL SISTEMA persistirá un par formado por la pregunta recibida y la respuesta final del agente.
- RF-08: MIENTRAS un turno permanezca pendiente de decisión sobre un plan, EL SISTEMA no incorporará ese turno al historial de turnos finalizados.
- RF-09: CUANDO `POST /approve` cierre correctamente un turno pendiente, EL SISTEMA persistirá un par formado por su pregunta original y la respuesta final devuelta tras la decisión.
- RF-10: CUANDO `POST /ask` complete una aprobación automática permitida por la spec 013, EL SISTEMA persistirá un único par de pregunta original y respuesta final.
- RF-11: CUANDO una petición sea rechazada por las reglas de control del agente, EL SISTEMA conservará sin cambios el historial persistido.
- RF-12: CUANDO se repita una aprobación después del cierre de su turno sin existir otro plan pendiente, EL SISTEMA no añadirá mensajes al historial.
- RF-13: SI falla la escritura de uno de los mensajes de un turno, ENTONCES EL SISTEMA revertirá todas las escrituras de ese turno.
- RF-14: SI falla la persistencia durante una petición que debía guardar un turno, ENTONCES EL SISTEMA responderá HTTP 500 con un mensaje genérico en español.
- RF-15: CUANDO una petición deba guardar un turno, EL SISTEMA confirmará HTTP 200 únicamente después de completar la persistencia de ese turno.
- RF-16: SI falla la lectura del historial por un error de conexión o consulta a PostgreSQL, ENTONCES EL SISTEMA responderá HTTP 500 con un mensaje genérico en español.
- RF-17: DONDE `POST /ask` genere un nuevo `thread_id`, EL SISTEMA persistirá el turno bajo el mismo identificador devuelto al cliente.
- RF-18: SI un identificador de conversación recibido en las rutas de preguntas, decisiones o historial está vacío, contiene solo espacios o supera 128 caracteres, ENTONCES EL SISTEMA responderá HTTP 422 antes de invocar al agente o consultar PostgreSQL.
- RF-19: CUANDO se consulte el historial después de reiniciar la API, EL SISTEMA recuperará los turnos previamente persistidos bajo el mismo `thread_id`.
- RF-20: EL SISTEMA conservará los campos públicos de respuesta de `/ask` y `/approve` definidos en la spec 013.
- RF-21: DONDE se utilice el agente simulado, EL SISTEMA aplicará las mismas reglas de persistencia de turnos que con el agente real.
- RF-22: SI la configuración PostgreSQL es inválida o no permite preparar las tablas necesarias durante el arranque, ENTONCES EL SISTEMA impedirá que la API quede disponible como servicio operativo.
- RF-23: CUANDO una decisión válida de rechazo deje el turno sin planes pendientes, EL SISTEMA persistirá un par formado por la pregunta original y la respuesta final de rechazo sin modificar el valor `done` del agente.
- RF-24: SI falla el guardado de un turno, ENTONCES EL SISTEMA no repetirá automáticamente la ejecución del agente.

Un turno finalizado es una interacción con respuesta no vacía, sin error de
control y sin planes pendientes, cerrada por `done=true` o por una decisión válida
de rechazo que deje `done=false`. El cierre del turno para el historial no implica
el cierre de la conversación y no autoriza a modificar los indicadores del agente.
El rechazo de un plan y el rechazo de control de una petición son casos diferentes:
RF-23 guarda el primero; RF-11 conserva el historial ante el segundo.

Un hilo conocido es una conversación que existe en PostgreSQL o que la API
reconoce en el proceso actual, incluido un hilo con un plan pendiente. Si ya tiene
turnos guardados, la consulta devuelve esos mensajes aunque haya otro turno
pendiente. El reconocimiento temporal de un hilo sin datos persistidos no se
garantiza después de reiniciar el proceso.

## Requisitos no funcionales

- Integridad: cada turno guardado contiene exactamente dos mensajes, primero `user` y después `assistant`.
- Compatibilidad: el historial mantiene los nombres de campos esperados por la spec 015; `orden` representa la posición dentro de la conversación y no exige identificadores globales consecutivos.
- Seguridad: ninguna respuesta de error expone credenciales, URLs con contraseña, detalles SQL ni trazas internas.
- Configuración: PostgreSQL se configura mediante `DATABASE_URL`, conservando la compatibilidad con `postgres://` validada en la spec 014.
- Modularidad: esta integración conserva las decisiones del agente sobre cierre, rechazo y aprobación de planes.
- Coste de pruebas: cero llamadas reales a LLM, embeddings o servicios externos de transporte en la validación automatizada.
- Idioma: mensajes de error y documentación de la integración en español.

## Casos límite

| Caso | Resultado propuesto / referencia |
|---|---|
| Dos o más turnos finalizados en un hilo | Se recuperan todos sus pares en orden: RF-01 a RF-04, RF-07. |
| Dos conversaciones intercaladas | Se conserva la separación por `thread_id`: RF-04. |
| Pregunta pendiente de aprobación | No aparece todavía en el historial finalizado: RF-08. |
| Aprobación manual de un plan | Se conserva la pregunta original, no el texto de la decisión: RF-09. |
| Aprobación automática de un único plan | Un solo par con la respuesta final: RF-10. |
| Varios planes pendientes | Se respetan las reglas existentes de selección; solo se guarda al finalizar el turno: RF-08 y RF-09. |
| Rechazo del último plan que deja continuar la conversación | Se guarda pregunta original y respuesta de rechazo, respetando `done=false`: RF-23. |
| Rechazo de un plan cuando todavía quedan otros pendientes | No se guarda todavía el turno: RF-08. |
| Nueva pregunta mientras existe un plan pendiente | El rechazo de control no cambia el historial: RF-11. |
| Aprobación sin plan o con selección inválida | Sin escrituras nuevas: RF-11 y RF-12. |
| Identificador vacío, de espacios o mayor de 128 caracteres | HTTP 422: RF-18; el identificador omitido en `/ask` sigue generándose según la spec 013. |
| Pregunta vacía o de tipo incorrecto | Se conserva el HTTP 422 ya definido en la spec 013, sin guardar mensajes. |
| Respuesta vacía del agente | No se admite un turno incompleto; concretar su clasificación de error en el plan conforme a RF-13 a RF-15. |
| Hilo desconocido | HTTP 404 con «Conversación no encontrada»: RF-05. |
| Hilo conocido con su primer turno pendiente | HTTP 200 con lista vacía: RF-06. |
| Hilo con historial previo y un nuevo turno pendiente | HTTP 200 con los mensajes ya guardados: RF-01 y RF-08. |
| Fallo al escribir el segundo mensaje | Se revierte el turno; los turnos anteriores permanecen: RF-13. |
| Base de datos no disponible durante una petición | HTTP 500 genérico: RF-14 o RF-16. |
| Base de datos no disponible al arrancar | Servicio no operativo: RF-22. |
| Reinicio después de guardar un turno | El historial sigue disponible: RF-19. |
| Reinicio con un plan pendiente | La recuperación del plan no está cubierta por esta especificación. |
| Fallo de guardado después de ejecutar el agente | HTTP 500, rollback del turno y ninguna repetición automática del agente: RF-13, RF-14 y RF-24. |
| Guardado correcto pero respuesta HTTP perdida | Consultar primero el historial del hilo si se conoce su identificador; no se garantiza deduplicación del reenvío: D3. |

## Fuera de alcance

- Modificar la lógica del grafo, sus especialistas, el supervisor o el RAG.
- Persistir o restaurar checkpoints, planes pendientes o contexto del agente tras un reinicio.
- Rehidratar la memoria del agente a partir del historial de producto.
- Incorporar autenticación, autorización por usuario, CORS o límites de peticiones; deben coordinarse con el bloque de seguridad antes de exponer el servicio públicamente.
- Modificar la interfaz de Streamlit o implementar allí almacenamiento de conversaciones.
- Crear imágenes Docker, configurar contenedores de producción o desplegar en Render.
- Añadir migraciones, eliminación de conversaciones o edición de mensajes.
- Garantizar ejecución exactamente una vez frente a reenvíos HTTP o coordinar atómicamente PostgreSQL con la ejecución del agente; se aplica la política de errores y consulta de historial de D3.
- Incorporar un mecanismo de reintento seguro o recuperación de guardados fallidos después de reiniciar el servicio; corresponde a un bloque posterior.
- Ejecutar peticiones concurrentes de modificación del mismo hilo como nueva garantía de esta entrega; su soporte requeriría un alcance específico.
- Fusionar la PR #1, modificar `develop` o publicar este borrador en GitHub.

## Criterios de finalización

- Obtener aprobación global de esta especificación, con D1, D2 y D3 ya aclaradas, antes de elaborar el plan de implementación.
- Coordinar el contrato final con las personas responsables de la API y el frontend.
- Disponer de la base de persistencia de la spec 014 revisada por un compañero antes de fusionar la integración con `develop`.
- Cubrir RF-01 a RF-24 mediante pruebas automatizadas de API con agente simulado o dobles, sin servicios externos de pago.
- Verificar con PostgreSQL temporal el recorrido `/ask` → guardado → lectura de historial y el recorrido `/ask` → `/approve` → guardado → lectura.
- Verificar varios turnos, separación de hilos, persistencia entre sesiones y reinicio de API, además de rollback sobre un hilo nuevo y otro con historial previo.
- Comprobar la compatibilidad con el contrato del frontend de la spec 015.
- Superar la suite de regresión y documentar comandos, entorno, resultados y omisiones justificadas en la fase de validación.
- Revisar el diff para confirmar que no hay credenciales reales ni cambios funcionales fuera de alcance.

No hay implementación ni pruebas nuevas de esta funcionalidad en esta fase.
La aprobación de este documento no certifica que los requisitos estén implementados.

## Dudas abiertas

No quedan dudas abiertas sobre las tres decisiones consultadas. La aprobación
global fue confirmada el 15/11/2026. La coordinación con API y frontend sigue
siendo un criterio de finalización de la integración.

## Decisiones de clarificación — 2026-11-15

- **D1 — Rechazo explícito de planes, confirmada.** Se guarda la pregunta original y la respuesta de rechazo cuando ya no quedan planes pendientes, aunque el agente mantenga `done=false` para permitir continuar conversando. No se guarda un par por cada rechazo parcial de un turno con varios planes.
- **D2 — Hilos sin turnos guardados, confirmada.** Un hilo desconocido devuelve HTTP 404 con «Conversación no encontrada». Un hilo conocido sin turnos finalizados guardados, incluido uno con un plan pendiente, devuelve HTTP 200 con lista vacía. Si tiene historial previo, se devuelve ese historial sin incorporar el turno pendiente.
- **D3 — Fallos y reintentos, confirmada.** Un fallo de guardado devuelve HTTP 500 sin repetir automáticamente la ejecución del agente. Si se pierde la respuesta HTTP, la pauta para el cliente es consultar primero el historial cuando disponga del `thread_id`; si la primera respuesta se pierde antes de conocer ese identificador, este contrato no permite localizar con garantía el turno. Reenviar una petición puede producir duplicados: esta entrega no promete deduplicación ni reintentos seguros. El rollback de PostgreSQL no deshace acciones del agente ni restaura su estado anterior. Un mecanismo de recuperación o idempotencia se estudiará en un bloque posterior.

Referencias revisadas: spec 013 (API), spec 014 (PostgreSQL), spec 015 (frontend
en PR #4) y propuesta de actualización constitucional en PR #3. Las reglas de
aprobación automática de la spec 013 y su encaje constitucional siguen el acuerdo
del equipo; este borrador no decide ni cambia esa política.
