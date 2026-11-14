# Spec 013 — API REST del agente MadridRumbo

> Estado: Aprovada · Fecha: 2026-11-13 · Responsable: Guzmán (Persona 1)

## Contexto y objetivo
Hoy el agente multiagente solo se usa desde la terminal y desde Streamlit, en local. El Prosject Break 3 exige publicarlo como servicio. Esta spec define la API HTTP que expone el mismo agente: qué rutas hay, qué datos entran y salen y qué códigos de estado devuelve. La API es un cliente más, igual de fino que la CLI y Streamlit: no decide nada por su cuenta, solo traslada la pregunta o la decisión al agente y devuelve lo que este responde.

## Usuarios / actores
- Front web (Persona 3) que consume la API por HTTP.
- Equipo y profesorado, que prueban la API desde su documentación interactiva.
- Servicio de historial (spec de Persona 2), que guarda los turnos cerrados.

## Historias de usuario
- H1: Como front web quiero enviar una pregunta y recibir la respuesta del agente para mostrarla en el chat.
- H2: Como front web quiero saber si hay un plan pendiente y poder aprobarlo o rechazarlo para cerrar el turno.
- H3: Como profesorado quiero probar la API desde su documentación interactiva sin escribir código.
- H4: Como equipo quiero un modo simulado para desarrollar y probar sin gastar API.

## Requisitos funcionales (criterios de aceptación en EARS)
- RF-1: EL SISTEMA expondrá las rutas GET /health, POST /ask, POST /approve y GET /threads/{thread_id}/messages.
- RF-2: EL SISTEMA publicará en /docs una documentación interactiva con las rutas y los formatos de datos, accesible sin clave.
- RF-3: CUANDO se consulte GET /health, EL SISTEMA responderá con estado correcto e indicará que el servicio está vivo.
- RF-4: CUANDO llegue un POST /ask con una pregunta válida, EL SISTEMA enviará la pregunta al agente con el identificador de conversación recibido y devolverá respuesta, identificador de conversación, indicador de terminada, indicador de plan pendiente, planes pendientes y campo de error.
- RF-5: SI la pregunta falta, está vacía, solo tiene espacios o algún campo tiene un tipo incorrecto, ENTONCES EL SISTEMA responderá 422 sin llamar al agente.
- RF-6: DONDE el POST /ask no incluya identificador de conversación, EL SISTEMA creará uno nuevo y lo devolverá en la respuesta.
- RF-7: CUANDO auto_aprobar sea verdadero (valor por defecto) y el agente deje exactamente un plan pendiente, EL SISTEMA aprobará ese plan y devolverá el resultado final del turno.
- RF-8: CUANDO auto_aprobar sea falso y el agente deje un plan pendiente, EL SISTEMA devolverá el plan sin aprobarlo y con el indicador de plan pendiente activo.
- RF-9: CUANDO auto_aprobar sea verdadero y el agente deje más de un plan pendiente, EL SISTEMA no aprobará ninguno y devolverá los planes con el indicador de plan pendiente activo.
- RF-10: CUANDO llegue un POST /approve con identificador de conversación y decisión, EL SISTEMA trasladará la decisión al agente y devolverá el resultado con el mismo formato que POST /ask.
- RF-11: DONDE haya varios planes pendientes, EL SISTEMA exigirá en POST /approve el identificador del plan elegido y lo trasladará al agente.
- RF-12: CUANDO la decisión sea rechazar, EL SISTEMA trasladará el rechazo al agente y la conversación podrá continuar con otra pregunta.
- RF-13: SI no hay plan pendiente en esa conversación, ENTONCES EL SISTEMA devolverá un aviso en español en el campo de error y no cerrará nada.
- RF-14: SI el agente falla de forma inesperada, ENTONCES EL SISTEMA responderá 500 con un mensaje genérico en español, sin detalles internos.
- RF-15: EL SISTEMA devolverá el indicador de terminada exactamente como lo decide el agente, sin modificarlo.
- RF-16: DONDE esté activado el modo simulado mediante una variable de entorno, EL SISTEMA usará un agente simulado en lugar del real e indicará el modo en GET /health.

## Requisitos no funcionales
- Coste: ningún test de esta spec llama a un LLM, a embeddings ni a ChromaDB; usan el agente simulado.
- Idioma: mensajes de error y descripciones de la documentación en español.
- Modularidad: la API no contiene lógica del agente; usa las mismas funciones que la CLI y Streamlit.
- Seguridad: las respuestas no incluyen claves ni el contenido de `.env`.

## Casos límite
- Pregunta vacía o con tipo incorrecto: RF-5.
- Pregunta nueva con un plan pendiente en la conversación: el agente responde con un aviso (RF-4).
- Aprobar sin plan pendiente: RF-13.
- Varios planes pendientes y aprobación automática: RF-9.
- Varios planes pendientes y decisión sin indicar plan: RF-11.
- Fallo del agente a mitad de turno: RF-14.
- Primera pregunta sin identificador de conversación: RF-6.

## Fuera de alcance
- Guardar y leer el historial en base de datos, y el contenido de GET /threads/{thread_id}/messages (spec de Persona 2).
- Docker y despliegue en Render (spec de Persona 2).
- Clave de acceso, límite de peticiones, tiempo máximo, CORS y registros (spec de Persona 3).
- El front web (spec de Persona 3).
- Cambiar el grafo, el supervisor, los especialistas o el RAG.
- Respuestas en streaming.

## Criterios de finalización
Todos los RF con test en verde (`pytest`, sin API) y demo manual desde /docs en modo simulado: pregunta con auto_aprobar verdadero, pregunta con auto_aprobar falso seguida de aprobar, y rechazo.

## Dudas abiertas
- [NECESITA ACLARACIÓN: la constitución (art. 12) cierra el stack; ¿se amplía para añadir FastAPI y su servidor? Afecta a los tres.]
- [NECESITA ACLARACIÓN: coordinar con la spec de Persona 2 qué devuelve GET /threads/{thread_id}/messages.]