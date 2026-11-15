# Plan técnico — Spec 016

> Basado en `spec.md` (estado: Aprobada) · Fecha: 2026-11-15
> Estado del plan: Aprobado por el responsable en la conversación el 2026-11-15. No hay implementación.

## Archivos afectados

| Archivo | Crear / Modificar | Qué cambia | RF |
|---|---|---|---|
| `app.py` | Modificar | Lifespan de arranque PostgreSQL; sustituir historial 501 por lectura; integrar sesiones y documentar 404/422/500. | RF-01 a RF-06, RF-16, RF-18, RF-22 |
| `src/api/servicio.py` | Modificar | Coordinar pregunta, decisión y guardado final; conservar pregunta original; evitar escrituras ante rechazos de control; preservar errores HTTP deliberados. | RF-07 a RF-17, RF-20, RF-21, RF-23, RF-24 |
| `src/api/historial.py` | Crear | Adaptador API–persistencia, registro temporal por hilo y conversión a mensajes públicos ordenados. | RF-01 a RF-17, RF-19, RF-23, RF-24 |
| `src/api/esquemas.py` | Modificar | Validar identificadores recibidos en preguntas y decisiones, conservando campos y tipos públicos. | RF-18, RF-20 |
| `config.py` | Modificar | Centralizar límite de 128 caracteres y mensaje «Conversación no encontrada»; reutilizar error 500 genérico. | RF-05, RF-14, RF-16, RF-18 |
| `tests/conftest.py` | Modificar | Fixtures aisladas de sesiones y estado API, sin retirar el bloqueo de HTTP real. | Transversal |
| `tests/test_api_errores.py` | Modificar | Sustituir la expectativa obsoleta de 501 por la del contrato de historial implementado. | RF-05, RF-16, RF-20 |
| `tests/test_api_ask.py`, `tests/test_api_aprobacion.py`, `tests/test_api_autoaprobar.py`, `tests/test_api_rutas.py` | Modificar | Adaptar fixtures a persistencia obligatoria y conservar la regresión de la spec 013. | RF-07 a RF-12, RF-17, RF-20, RF-21, RF-23 |
| `tests/test_api_historial.py` | Crear | Lectura, formato, orden, separación, hilos conocidos y validación de identificadores. | RF-01 a RF-06, RF-18 |
| `tests/test_api_persistencia.py` | Crear | Turnos directos, HITL, autoaprobación, rechazos, fallos y conteo de llamadas al agente. | RF-07 a RF-17, RF-20, RF-21, RF-23, RF-24 |
| `tests/test_api_arranque.py` | Crear | Lifespan, fallo de configuración, fallo de conexión y creación de tablas. | RF-22 |
| `tests/test_api_postgresql.py` | Crear | Integración explícita con PostgreSQL temporal y reinicio mediante proceso independiente. | RF-01 a RF-04, RF-07, RF-09, RF-13, RF-19, RF-21, RF-23 |
| `README.md` | Modificar | Requisitos de arranque, disponibilidad de historial, errores y límites de reintentos. | RF-01, RF-05, RF-06, RF-14, RF-19, RF-22, RF-24 |
| `specs/016-integracion-api-postgresql/validacion.md` | Crear en fase de validación | Registrar evidencias reales y trazabilidad; no anticipar resultados. | RF-01 a RF-24 |

Se reutilizan `src/models.py`, `src/db.py`, `src/history.py` y sus pruebas de la
SPEC-014 sin modificar sus contratos. No se añaden dependencias. Los archivos de
SPEC-015 están en la rama del frontend: aquí solo se verifica su contrato HTTP.
La división final de fixtures se ajustará al crear las tareas para evitar que
tests ajenos a la API necesiten una base de datos.

## Contrato

`POST /ask` y `POST /approve` conservan `AskIn`, `ApproveIn` y los campos públicos
de `AskOut`: `respuesta`, `thread_id`, `done`, `pendiente_hitl`, `plan` y `error`.
La validación de `thread_id` recibido rechazará texto vacío, espacios y más de
128 caracteres con HTTP 422. Omitirlo o enviarlo como `null` en `/ask` mantiene
la generación de identificador de la spec 013. No se recorta ni transforma un
identificador válido; se conserva exactamente para guardar y recuperar el hilo.

Para una conversación con dos turnos guardados:

```http
GET /threads/hilo-1/messages
```

```json
[
  {"role": "user", "content": "Pregunta 1", "orden": 1},
  {"role": "assistant", "content": "Respuesta 1", "orden": 2},
  {"role": "user", "content": "Pregunta 2", "orden": 3},
  {"role": "assistant", "content": "Respuesta 2", "orden": 4}
]
```

- HTTP 200 con lista vacía para hilo conocido sin mensajes finalizados.
- HTTP 404 con `{"detail": "Conversación no encontrada"}` para hilo desconocido.
- HTTP 422 para identificador inválido recibido en una ruta que lo admite.
- HTTP 500 con `{"detail": "<mensaje genérico de config.API_ERROR_INTERNO>"}` ante fallo de PostgreSQL o respuesta final no persistible.

Un segmento de ruta omitido (`/threads//messages`) no corresponde a la ruta con
`thread_id` y conserva el 404 de enrutamiento de FastAPI; los valores recibidos,
incluidos espacios codificados en URL, se validan según RF-18.

En rechazo del último plan se devuelve el `done=false` original del agente y se
guarda el par pregunta–rechazo. No se redefine `done` como confirmación de escritura.
Las funciones existentes `save_closed_turn()` y `get_thread_messages()` conservan
sus argumentos, retornos y orden de mensajes.

## Lógica clave

### Estado temporal y acceso a datos

El adaptador de historial mantendrá por hilo la pregunta del turno pendiente y
el conocimiento temporal de hilos aceptados por la API. Se coordina con los
planes que actualmente registra el servicio; los tests reinician ambos estados.
El proceso guardará solo los datos necesarios para esta integración, sin copiar
checkpoints del agente. Al cerrar el servicio se elimina este estado temporal.

La existencia persistida se comprobará con `session.get(Conversation, thread_id)`;
los mensajes se leerán mediante `get_thread_messages()` y se convertirán a
`MessageOut` con `enumerate(..., start=1)`. Una consulta no crea conversaciones.
No se insertará una fila vacía para reconocer un hilo pendiente: su reconocimiento
temporal permite el 200 vacío sin alterar la atomicidad de la SPEC-014.

La sesión será propia de cada petición y se cerrará siempre. Las rutas validarán
la entrada antes de ejecutar consultas; las dependencias y los dobles de tests
permitirán comprobar ese orden. El adaptador usará la sesión recibida, sin crear
una segunda sesión durante el guardado del par.

```text
arrancar API:
    obtener motor con DATABASE_URL normalizada por la capa existente
    preparar tablas; si falla, abortar lifespan y no servir peticiones
    preparar registro temporal vacío

consultar historial(thread_id):
    validar identificador recibido
    consultar existencia persistida y mensajes del hilo
    si existe conversación: devolver sus mensajes enumerados desde 1
    si registro temporal reconoce hilo: devolver lista vacía
    en otro caso: responder 404
    ante fallo de base de datos: responder 500 genérico

preguntar(entrada):
    validar entrada y obtener thread_id recibido o generado
    ejecutar el agente una vez para la pregunta
    si hay rechazo de control: devolver contrato actual sin escribir
    registrar hilo aceptado sin sobrescribir otra pregunta ante rechazo de control
    si quedan planes: conservar pregunta original del turno
    aplicar autoaprobación solo conforme a la lógica existente de la spec 013
    si el resultado final cierra el turno: guardar pregunta y respuesta final
    devolver 200 solo después del guardado cuando corresponda

decidir(entrada):
    validar entrada y recuperar contexto original del turno
    invocar decisión del agente conforme al contrato existente
    si hay rechazo de control: no guardar ni perder el contexto pendiente
    si quedan planes: conservar pregunta original y planes restantes
    si done=true sin planes, o rechazo válido sin planes:
        guardar pregunta original y respuesta final una sola vez
        liberar contexto finalizado
    devolver sin alterar done, pendiente_hitl ni la decisión del agente
```

No se detectará un rechazo por comparar el texto de la respuesta. Se combinarán
la decisión recibida, la ausencia de rechazo de control y el estado devuelto por
el agente. El cierre exige ausencia de planes pendientes, además de las
condiciones aprobadas en la spec. La pregunta original permanece igual durante
rechazos parciales y selección posterior de otro plan.

Una respuesta final vacía se tratará como fallo interno antes de confirmar el
turno; no se crea un mensaje vacío. Si falta el contexto original cuando el agente
ha cerrado el turno, no se inventará una pregunta: se responderá 500 sin guardar
un par incompleto.

`save_closed_turn()` seguirá siendo el único punto de commit del par. Su rollback
protege los datos de PostgreSQL; no se intentará deshacer ni repetir acciones del
agente. Si el agente ya cerró el turno y el guardado falla, el servicio sincroniza
su registro de planes con el resultado terminal y libera el contexto del turno:
no queda una aprobación ficticia disponible para reejecutarla como recuperación.
Esto puede dejar un turno sin historial, circunstancia comunicada mediante HTTP
500 y aceptada por D3. Un reenvío de `/ask` puede crear otro turno.

El manejador actual de excepciones captura todo, incluidas `HTTPException`:
se ajustará para preservar 404/422 deliberados y convertir únicamente errores
inesperados en 500 genérico. Las consultas diferenciarán ausencia de datos de
fallos de conexión; un fallo de base de datos no se devolverá como lista vacía.

## Decisiones técnicas

| Decisión | Alternativa descartada | Por qué |
|---|---|---|
| Reutilizar transacción y modelos SPEC-014 | Otra capa de modelos o commit por mensaje | Conserva integridad y evita duplicar una capa ya validada. |
| Adaptador de persistencia propio de la API | Acoplar el grafo a PostgreSQL | Respeta la modularidad y el alcance de la integración. |
| Contexto de pregunta pendiente en el proceso | Nuevas tablas para planes/checkpoints | Solo los turnos finalizados deben persistirse en esta entrega. |
| Hilo conocido = existencia en PostgreSQL o registro temporal | Crear una conversación en cada lectura | Permite D2 sin que una consulta cambie datos. |
| Orden público por posición dentro del hilo | Exponer Message.id como orden consecutivo | Los identificadores globales pueden contener huecos y otros hilos. |
| Detectar rechazo con la decisión y el estado | Comparar frases del asistente | Evita depender de textos del agente. |
| Lifespan obligatorio con preparación de tablas | Declarar health correcto sin validar arranque de persistencia | Cumple RF-22; `/health` sigue sin prometer monitorización continua de PostgreSQL. |
| Inyección de sesión y dobles en pruebas | Exigir PostgreSQL en todos los tests | Mantiene la regresión rápida sin servicios de pago. |
| Sin reintento automático del agente | Reejecutar todo tras un fallo SQL | Respeta D3 y evita repetir acciones por iniciativa del backend. |
| Sin claves de idempotencia nuevas | Ampliar el contrato HTTP en esta integración | Los reintentos seguros quedaron fuera del alcance aprobado. |

## Estrategia de tests

Los nombres de pruebas de la trazabilidad son propuestos y todavía no existen.
En implementación se escribirán primero los tests de cada tarea. No se marcarán
como superados antes de ejecutarlos.

### Pruebas de API sin servicios externos de pago

- Fixtures de SQLite en memoria con sesiones independientes por petición sobre el mismo motor de prueba; sustituir motor y preparación de tablas únicamente dentro del test.
- `TestClient` usado como contexto para probar realmente el lifespan, con override del acceso a datos de cada caso.
- `GrafoFalso` existente para los recorridos simulados y dobles contadores para errores, rechazos de control y respuestas vacías.
- Dobles del contrato del agente real para comprobar que el servicio no tiene una rama especial de persistencia para el modo simulado.
- Fixtures de aislamiento para agente, planes y registro de historial en todos los tests API que compartan esos módulos.
- Fallo de escritura con una restricción o trigger que rechace el segundo mensaje; verificar ausencia del turno y conservación de datos previos.
- Contador de llamadas al agente para comprobar que un fallo de commit no provoca una segunda ejecución.
- Verificar que ninguna petición inválida llega al agente ni ejecuta una consulta SQL.
- Mantener la protección de red de `tests/conftest.py`; no usar Gemini, embeddings, APIs de transporte ni ChromaDB real.

El arranque no quedará desactivado globalmente para que pase la suite. Los tests
de API usarán una base sustituida explícita y los de arranque comprobarán tanto
el camino correcto como los fallos de configuración y conexión.

### Integración real y reinicio

`tests/test_api_postgresql.py` será optativo mediante una URL de pruebas explícita.
Solo admitirá una base dedicada, local y desechable; documentará que crea y borra
sus tablas. Se usará un contenedor temporal de pruebas sin añadir archivos Docker
de despliegue al repositorio. La ausencia de entorno omitirá esos casos con motivo
visible, sin contarlos como pruebas de integración superadas.

Se verificarán varios turnos, hilos intercalados, aprobación manual y automática,
rechazo del último plan y rollback con y sin historial previo. Para RF-19, un
proceso con `TestClient` guardará el turno usando el agente simulado y terminará;
otro proceso independiente consultará la misma base sin compartir estado global.
Esto comprueba reinicio real del contexto API sin llamar a un LLM ni abrir un
servidor HTTP externo durante la prueba.

### Regresión y comprobación manual

- Conservar las pruebas de SPEC-014 y adaptar la expectativa 501 de SPEC-013 al nuevo contrato de historial.
- Ejecutar la suite completa con `.env` deshabilitado y las credenciales ficticias que requieran los dobles existentes de EMT.
- Revisar compatibilidad con el cliente de SPEC-015: roles canónicos, `orden`, 404 de desconocido y lista vacía de conocido.
- Cuando la rama del frontend esté disponible para la prueba conjunta, verificar manualmente en modo simulado pregunta, decisión, recarga de historial y rechazo con `done=false`; no modificar esa rama desde este bloque.
- Registrar omisiones, versiones, comandos y resultados en `validacion.md` durante la fase de validación.

## Riesgos

- La API y PostgreSQL no comparten una transacción con el agente: un fallo de guardado no revierte decisiones ni acciones ya realizadas.
- La pérdida de respuesta después de commit es ambigua; sin identificador conocido de hilo ni clave de idempotencia no existe recuperación garantizada. Se documentará consultar primero el historial cuando se conozca el hilo.
- El registro temporal se pierde al reiniciar y no se comparte entre procesos trabajadores; no se anunciará soporte de continuidad de planes entre varios workers. Los turnos ya guardados sí siguen disponibles en PostgreSQL.
- Un hilo que solo era conocido en memoria puede pasar de 200 vacío a 404 después de reiniciar, conforme al alcance aprobado.
- Las llamadas concurrentes al mismo hilo no reciben una garantía nueva de serialización en esta entrega.
- `create_all` permite preparar tablas pero no sustituye migraciones; no se cambiará el esquema de SPEC-014.
- El frontend debe verificar cómo presenta un 200 vacío durante un plan pendiente; este plan conserva el contrato aprobado y no modifica su interfaz.
- La constitución local y las PR #3/#4 contienen cambios pendientes de coordinación del equipo sobre HITL y clientes HTTP. No se alterarán sus decisiones ni se fusionarán sus ramas desde esta tarea.
- La revisión humana de PR #1 sigue siendo requisito para fusionar la integración; su validación técnica no sustituye esa revisión.

## Trazabilidad

| RF | Parte del plan | Test propuesto |
|---|---|---|
| RF-01 | Ruta de historial y adaptador de lectura | `tests/test_api_historial.py::test_historial_guardado_200` |
| RF-02 | Conversión a MessageOut | `tests/test_api_historial.py::test_campos_publicos_historial` |
| RF-03 | Enumeración por hilo tras ordenar por id | `tests/test_api_historial.py::test_orden_consecutivo_con_ids_intercalados` |
| RF-04 | Filtrado por thread_id | `tests/test_api_historial.py::test_hilos_separados` |
| RF-05 | Existencia persistida y temporal | `tests/test_api_historial.py::test_desconocido_404` |
| RF-06 | Registro de hilo pendiente y conversación vacía | `tests/test_api_historial.py::test_conocido_sin_mensajes_200_vacio` |
| RF-07 | Guardado al finalizar ask | `tests/test_api_persistencia.py::test_ask_directo_guarda_par` |
| RF-08 | Pregunta pendiente en memoria | `tests/test_api_persistencia.py::test_pendiente_y_rechazo_parcial_no_guardan` |
| RF-09 | Cierre tras decisión manual | `tests/test_api_persistencia.py::test_approve_guarda_pregunta_original` |
| RF-10 | Resultado final de autoaprobación | `tests/test_api_persistencia.py::test_autoaprobar_guarda_un_solo_par` |
| RF-11 | Rechazos de control sin escritura | `tests/test_api_persistencia.py::test_rechazo_control_conserva_historial_y_pregunta` |
| RF-12 | Sin plan pendiente tras cierre | `tests/test_api_persistencia.py::test_approve_repetido_no_duplica` |
| RF-13 | Transacción existente y rollback | `tests/test_api_persistencia.py::test_fallo_segundo_mensaje_revierte_turno`; `tests/test_api_postgresql.py::test_rollback_postgresql` |
| RF-14 | Error de guardado genérico | `tests/test_api_persistencia.py::test_guardado_fallido_500_sin_detalles` |
| RF-15 | Commit antes de confirmar éxito | `tests/test_api_persistencia.py::test_200_solo_despues_del_commit` |
| RF-16 | Error de lectura distinto de hilo ausente | `tests/test_api_historial.py::test_lectura_fallida_500` |
| RF-17 | Identificador generado común a respuesta y guardado | `tests/test_api_persistencia.py::test_uuid_devuelto_es_el_persistido` |
| RF-18 | Validación compartida de identificador recibido | `tests/test_api_historial.py::test_thread_invalido_422_sin_consultas` |
| RF-19 | Lectura persistida desde otro proceso | `tests/test_api_postgresql.py::test_historial_tras_reinicio_api` |
| RF-20 | Esquemas públicos y regresión de API | `tests/test_api_persistencia.py::test_respuestas_conservan_contrato_013` |
| RF-21 | Servicio común a modos real y simulado | `tests/test_api_persistencia.py::test_persistencia_independiente_del_modo` |
| RF-22 | Lifespan prepara tablas o aborta | `tests/test_api_arranque.py::test_arranque_postgresql_obligatorio` |
| RF-23 | Rechazo terminal sin cambiar done | `tests/test_api_persistencia.py::test_ultimo_rechazo_guarda_par_con_done_false` |
| RF-24 | Sin bucle de reejecución por fallo SQL | `tests/test_api_persistencia.py::test_fallo_commit_no_repite_agente` |

El responsable aprobó este plan para redactar `tasks.md`. La implementación se
realizará después, una tarea cada vez y con tests primero. Esta aprobación no
autoriza commit, push ni cambios en las PR.
