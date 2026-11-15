# Tareas — Spec 016

> Basadas en la especificación y el plan aprobados el 2026-11-15.
> Estado: T1–T18 completadas. T19 preparada técnicamente; T19/T20 pendientes de revisión conjunta API/frontend.
> Una tarea cada vez. Tests primero. Marcar `[x]` solo después de verificarla.

## Reglas de ejecución

- Cada tarea está planteada como un incremento de aproximadamente 20–30 minutos; si no cabe, dividirla antes de ampliar su alcance.
- Seguir el orden indicado y detenerse al terminar una tarea, conforme a `AGENTS.md`.
- En tareas con lógica: ejecutar primero el test nuevo para observar el fallo esperado, implementar solo el incremento y verificar la regresión correspondiente.
- Terminar cada tarea con `pytest` sin servicios externos de pago y registrar su resumen real. Si falla la regresión, resolverlo antes de avanzar.
- Los nombres de tests de las tareas pendientes son propuestos: todavía no se han dado por superados.
- Mantener separados estos cambios de integración del alcance de PR #1; no hacer commit, push, cambios en PR ni modificaciones de `develop` sin autorización expresa.
- No leer `.env`, añadir dependencias ni modificar grafo, RAG, frontend, Docker de despliegue o Render.

## Secuencia de trabajo

- [x] **T1. Preparar las fixtures aisladas de API.** Crear primero una prueba que detecte contaminación de sesiones, agente o planes entre casos; después preparar SQLite compartida por petición, dobles de arranque y limpieza del estado API en fixtures específicas, sin afectar tests ajenos a la API. (RF-20, RF-21)
  **Depende de:** especificación y plan aprobados.
  **Hecho cuando:** `python -m pytest tests/test_api_ask.py tests/test_api_aprobacion.py tests/test_api_autoaprobar.py tests/test_api_rutas.py tests/test_api_errores.py -q` pasa sin PostgreSQL ni HTTP real y la prueba nueva confirma que dos casos no comparten datos o estado residual.

- [x] **T2. Validar los identificadores de conversación.** Escribir primero casos parametrizados para pregunta, decisión e historial; después centralizar el límite y aplicar la validación antes de consultas o llamadas al agente. Mantener generación de identificador para `/ask` sin identificador o con `null`. (RF-18, RF-20)
  **Depende de:** T1.
  **Hecho cuando:** `tests/test_api_historial.py::test_thread_invalido_422_sin_consultas` pasa con espacios, vacío cuando la ruta admita recibirlo, 128 y 129 caracteres; los contadores de consultas y agente permanecen en cero ante entradas inválidas. La ruta sin segmento conserva su 404 de enrutamiento.

- [x] **T3. Crear el registro temporal y la conversión del historial.** Probar primero reconocimiento de hilo, conservación de pregunta original, limpieza y orden público; después crear el adaptador de API reutilizando modelos y funciones SPEC-014. (RF-02, RF-03, RF-04, RF-06)
  **Depende de:** T1, T2.
  **Hecho cuando:** `tests/test_api_historial.py::test_campos_publicos_historial`, `test_orden_consecutivo_con_ids_intercalados` y `test_hilos_separados` pasan, junto con una prueba de limpieza del registro temporal, sin cambiar los contratos de SPEC-014.

- [x] **T4. Conectar la ruta de historial y sustituir el 501.** Escribir primero pruebas HTTP de conversación guardada, desconocida y conocida sin mensajes; después conectar lectura y sesión por petición y actualizar la expectativa 501 obsoleta de SPEC-013. (RF-01, RF-02, RF-03, RF-04, RF-05, RF-06)
  **Depende de:** T2, T3.
  **Hecho cuando:** `tests/test_api_historial.py::test_historial_guardado_200`, `test_desconocido_404` y `test_conocido_sin_mensajes_200_vacio` pasan; el 404 contiene «Conversación no encontrada», no se crean filas al consultar y `tests/test_api_errores.py` queda verde.

- [x] **T5. Distinguir fallos de lectura de ausencia de hilo.** Escribir primero un test que fuerce error SQL y otro que preserve errores HTTP deliberados; después ajustar la conversión de excepciones sin exponer datos internos. (RF-05, RF-16)
  **Depende de:** T4.
  **Hecho cuando:** `tests/test_api_historial.py::test_lectura_fallida_500` pasa con detalle genérico, el error no aparece como lista vacía ni 404 y el test de hilo desconocido sigue devolviendo 404.

- [x] **T6. Guardar respuestas directas de `/ask`.** Escribir primero la prueba de un turno finalizado y la del identificador generado; después conectar el guardado atómico antes de devolver éxito. (RF-07, RF-15, RF-17, RF-20)
  **Depende de:** T3, T5.
  **Hecho cuando:** `tests/test_api_persistencia.py::test_ask_directo_guarda_par`, `test_uuid_devuelto_es_el_persistido` y `test_200_solo_despues_del_commit` pasan; el historial devuelve exactamente pregunta y respuesta bajo el identificador público.

- [x] **T7. Conservar la pregunta mientras haya planes pendientes.** Escribir primero pruebas de espera, varios planes y rechazo de control sobre un hilo pendiente; después enlazar el registro temporal con el estado que ya conserva la API. (RF-06, RF-08, RF-11)
  **Depende de:** T6.
  **Hecho cuando:** el caso de espera de `tests/test_api_persistencia.py::test_pendiente_y_rechazo_parcial_no_guardan` pasa y `test_rechazo_control_conserva_historial_y_pregunta` confirma que la pregunta original no se sobrescribe; un hilo nuevo pendiente devuelve 200 vacío y uno con historial previo conserva sus mensajes.

- [x] **T8. Guardar el cierre por aprobación manual.** Escribir primero la prueba de aprobación con pregunta original, incluida selección tras varios planes; después guardar el par final y liberar el contexto del turno cerrado. (RF-09, RF-15, RF-20)
  **Depende de:** T7.
  **Hecho cuando:** `tests/test_api_persistencia.py::test_approve_guarda_pregunta_original` pasa sin guardar el texto de la decisión como pregunta y conserva los indicadores devueltos por el agente.

- [x] **T9. Cubrir la aprobación automática.** Escribir primero el caso automático y el caso de varios planes sin elección automática; después conectar el mismo cierre de persistencia al resultado final de `/ask`. (RF-08, RF-10, RF-20)
  **Depende de:** T8.
  **Hecho cuando:** `tests/test_api_persistencia.py::test_autoaprobar_guarda_un_solo_par` y la regresión `tests/test_api_autoaprobar.py` pasan; se guardan dos mensajes en el cierre automático y ninguno mientras haya varios planes pendientes.

- [x] **T10. Guardar el rechazo del último plan.** Escribir primero pruebas de rechazo parcial y terminal; después cerrar el turno de historial cuando no queden planes, respetando `done=false`. (RF-08, RF-23)
  **Depende de:** T8, T9.
  **Hecho cuando:** `tests/test_api_persistencia.py::test_pendiente_y_rechazo_parcial_no_guardan` y `test_ultimo_rechazo_guarda_par_con_done_false` pasan; el rechazo parcial no escribe y el último rechazo guarda un único par con la pregunta original.

- [x] **T11. Evitar escrituras ante decisiones inválidas o repetidas.** Escribir primero pruebas de ausencia de plan, selección incorrecta y aprobación repetida después del cierre; después completar las guardas sin alterar el historial ni el contexto pendiente válido. (RF-11, RF-12)
  **Depende de:** T10.
  **Hecho cuando:** `tests/test_api_persistencia.py::test_rechazo_control_conserva_historial_y_pregunta` y `test_approve_repetido_no_duplica` pasan tanto después de aprobación como de rechazo terminal. Esta tarea no añade deduplicación general de reenvíos de `/ask`.

- [x] **T12. Verificar atomicidad y errores de escritura.** Escribir primero pruebas que rechacen el segundo mensaje con y sin turnos previos; después ajustar únicamente el manejo API necesario para reutilizar el rollback de SPEC-014 y devolver 500 genérico. (RF-13, RF-14, RF-15)
  **Depende de:** T11.
  **Hecho cuando:** `tests/test_api_persistencia.py::test_fallo_segundo_mensaje_revierte_turno`, `test_guardado_fallido_500_sin_detalles` y `test_200_solo_despues_del_commit` pasan, sin filas del turno fallido ni pérdida del historial anterior.

- [x] **T13. Aplicar la política de fallo sin repetir el agente.** Escribir primero pruebas con contador de llamadas, respuesta final vacía y contexto original ausente; después completar el tratamiento de error y limpieza del contexto terminal previsto en el plan. (RF-14, RF-15, RF-24)
  **Depende de:** T12.
  **Hecho cuando:** `tests/test_api_persistencia.py::test_fallo_commit_no_repite_agente` pasa y los nuevos casos de respuesta vacía y contexto ausente devuelven 500 sin pares incompletos, sin segunda invocación del agente ni aprobación ficticia pendiente después del cierre.

- [x] **T14. Hacer obligatoria la preparación de PostgreSQL al arrancar.** Escribir primero tests del lifespan correcto y de configuración, conexión o creación de tablas fallidas; después integrar el arranque y cierre de recursos en la API. (RF-22)
  **Depende de:** T1, T13.
  **Hecho cuando:** `tests/test_api_arranque.py::test_arranque_postgresql_obligatorio` pasa con todos esos casos usando `TestClient` como contexto; el arranque fallido no sirve peticiones y la regresión API usa su base sustituida explícita.

- [x] **T15. Verificar contratos y modos del agente.** Escribir primero pruebas parametrizadas para agente simulado y doble del contrato real; después corregir solo incompatibilidades de integración detectadas, si aparecen. (RF-20, RF-21)
  **Depende de:** T14.
  **Hecho cuando:** `tests/test_api_persistencia.py::test_respuestas_conservan_contrato_013` y `test_persistencia_independiente_del_modo` pasan con los mismos campos y reglas de guardado, sin ejecutar un LLM, tools de transporte ni embeddings reales.

- [x] **T16. Preparar las pruebas PostgreSQL explícitas y comprobar lectura de varios turnos.** Escribir primero el fixture optativo con validación del destino y casos de dos turnos e hilos intercalados; después ajustar únicamente su infraestructura de pruebas para ejecutar esos casos en una base local desechable. (RF-01, RF-02, RF-03, RF-04, RF-07, RF-17, RF-21)
  **Depende de:** T15.
  **Hecho cuando:** `python -m pytest tests/test_api_postgresql.py -q` omite con motivo visible los casos sin URL explícita, rechaza destinos no permitidos antes de escribir y, con la base temporal configurada, recupera cuatro mensajes del primer hilo y solo los correspondientes del segundo. No se añaden archivos Docker de despliegue.

- [x] **T17. Verificar HITL y rollback con PostgreSQL real.** Escribir primero los casos de aprobación manual, automática, último rechazo y error de segundo mensaje; después completar los dobles o fixtures necesarios sin cambiar la lógica del agente. (RF-08, RF-09, RF-10, RF-11, RF-12, RF-13, RF-14, RF-15, RF-23, RF-24)
  **Depende de:** T16.
  **Hecho cuando:** los casos PostgreSQL de HITL y `tests/test_api_postgresql.py::test_rollback_postgresql` pasan; se comprueban rollback en hilo nuevo y existente, conservación de datos anteriores y una sola ejecución del agente por petición.

- [x] **T18. Verificar recuperación después de reiniciar la API.** Escribir primero una prueba con dos procesos Python independientes sobre la misma base; después completar el soporte de ejecución del test sin compartir estado del servicio. (RF-06, RF-19, RF-21)
  **Depende de:** T17.
  **Hecho cuando:** `tests/test_api_postgresql.py::test_historial_tras_reinicio_api` guarda desde un proceso, termina y recupera el mismo historial desde otro; el test diferencia ese historial persistido de un hilo solo conocido temporalmente y no afirma restaurar planes pendientes.

- [ ] **T19. Documentar y comprobar la compatibilidad con el frontend.** Actualizar instrucciones de arranque y lectura, ejemplos HTTP, errores y límites de reintentos; contrastar el contrato con SPEC-015 y coordinar la comprobación manual con sus responsables sin modificar su rama. (RF-01, RF-02, RF-03, RF-05, RF-06, RF-14, RF-19, RF-20, RF-22, RF-23, RF-24)
  **Depende de:** T18.
  **Hecho cuando:** `README.md` describe los códigos 200/404/422/500, la necesidad de PostgreSQL al arrancar y la consulta de historial tras pérdida de respuesta; se registra evidencia del recorrido simulado pregunta → decisión → recarga, incluido rechazo con `done=false`, o se identifica explícitamente la coordinación pendiente sin darla por superada.

- [ ] **T20. Validación final RF por RF.** Ejecutar la regresión completa, las pruebas de PostgreSQL y la revisión de credenciales; eliminar el entorno temporal de esta validación y redactar `validacion.md` con evidencias verificables. (RF-01, RF-02, RF-03, RF-04, RF-05, RF-06, RF-07, RF-08, RF-09, RF-10, RF-11, RF-12, RF-13, RF-14, RF-15, RF-16, RF-17, RF-18, RF-19, RF-20, RF-21, RF-22, RF-23, RF-24)
  **Depende de:** T19 y coordinación de API/frontend exigida por la especificación.
  **Hecho cuando:** `validacion.md` contiene trazabilidad de los 24 requisitos, comandos, versiones, resultados reales, omisiones justificadas y veredicto «Sí» con todos los criterios cumplidos; se acredita la limpieza del contenedor y sus volúmenes de pruebas. Si falta alguna evidencia, el veredicto será «Parcial» y T20 permanecerá pendiente. La revisión humana de SPEC-014 debe constar antes de fusionar la integración; esta tarea no autoriza la fusión.

## Cobertura comprobada al preparar las tareas

| Requisitos | Tareas principales |
|---|---|
| RF-01 a RF-06 | T3, T4, T5, T16, T18, T19 |
| RF-07 a RF-10 | T6, T7, T8, T9, T16, T17 |
| RF-11 y RF-12 | T7, T11, T17 |
| RF-13 a RF-16 | T5, T6, T12, T13, T17 |
| RF-17 y RF-18 | T2, T6, T16 |
| RF-19 | T18, T19 |
| RF-20 y RF-21 | T1, T2, T6, T8, T9, T15, T16, T18, T19 |
| RF-22 | T14, T19 |
| RF-23 y RF-24 | T10, T13, T17, T19 |
| RF-01 a RF-24 | T20: validación final individual |

Los 24 requisitos aparecen en tareas anteriores al cierre; no falta ninguno.
Las dependencias permiten una suite verde tras cada incremento, aunque los
requisitos de la funcionalidad solo queden completos al terminar sus tareas.
El estado de las tareas y las evidencias se actualiza por incremento.

## Evidencias de T1 — 2026-11-15

Se añadieron fixtures optativas `motor_api`, `sesiones_api`, `entorno_api` y
`cliente_api` en `tests/conftest.py`. Cada caso de API obtiene SQLite en memoria,
sesiones independientes sobre su mismo motor y un cliente con contexto de ciclo
de vida. Se sustituyen el acceso a motor, la preparación de tablas y la dependencia
de sesión; se restauran los overrides anteriores al terminar. El agente y los
planes se reinician por caso, manteniendo el bloqueo de HTTP real existente.
No se ha implementado todavía el lifespan de producción de T14.

Se adaptaron los cinco módulos API del criterio de T1 para usar el cliente común.
`tests/test_api_aislamiento.py` incorpora seis casos que comprueban aislamiento
de agente y planes, aislamiento de datos entre casos, lectura entre sesiones del
mismo caso, rollback al cerrar sin commit y coherencia del motor de arranque.

| Comando / comprobación | Resultado real |
|---|---|
| `python -m pytest tests/test_api_aislamiento.py::test_estado_api_no_se_comparte_entre_casos -v -p no:cacheprovider -o addopts='' --tb=short`, con el cliente previo a las fixtures | 1 passed, 1 failed: el segundo caso heredó el plan `hilo-aislamiento` del primero. |
| `python -m pytest tests/test_api_aislamiento.py tests/test_api_ask.py tests/test_api_aprobacion.py tests/test_api_autoaprobar.py tests/test_api_rutas.py tests/test_api_errores.py -q -p no:cacheprovider -o addopts='' --tb=short` | 37 passed in 1.21s. |
| `python -m pytest -q -p no:cacheprovider -o addopts='' --tb=short` | 1328 passed, 18 skipped in 21.40s. |
| `git diff --check` | Sin errores. |

Durante la adaptación hubo cuatro fallos por retirar un import de `config` que
seguía siendo necesario en los tests de errores; se restauró antes de las dos
ejecuciones finales en verde.

Las ejecuciones usaron `PYTHON_DOTENV_DISABLED=1`, sin leer `.env`, con valores
ficticios de EMT para los dobles existentes de la suite global. No se configuró
`SPEC014_TEST_DATABASE_URL`: los 18 casos omitidos corresponden a integración
PostgreSQL optativa y al caso de SQLite en memoria entre procesos de SPEC-014.
Esta ejecución no certifica nuevas pruebas con PostgreSQL real.

T1 proporciona infraestructura y regresión de apoyo a RF-20 y RF-21; no certifica
que la nueva persistencia de la API esté implementada. No se modificó código de
producción, `develop` ni las PR. No se hizo `git add`, commit o push.

## Evidencias de T2 — 2026-11-15

Se centralizó el límite de identificador recibido en `config.API_THREAD_ID_MAX_LENGTH`.
El tipo `ThreadId` de `src/api/esquemas.py` se reutiliza en `AskIn`, `ApproveIn`
y el parámetro de la ruta de historial. Comprueba longitud de 1 a 128 caracteres
y rechaza texto formado solo por espacios, sin recortar identificadores válidos.
La generación automática de identificador en `/ask` sigue admitiendo omisión y `null`.

`tests/test_api_historial.py` contiene 29 casos de T2. Incluyen cuerpos de pregunta
y decisión, parámetros de ruta codificados en URL, entradas vacías o de espacios,
longitud 129, tipos incorrectos, longitud 128 con caracteres ASCII y Unicode,
conservación de espacios en identificadores válidos y generación de UUID distintos.
Los contadores de acceso al agente y ejecución SQL permanecen en cero ante las
entradas inválidas. El segmento de ruta ausente conserva su 404 de enrutamiento.

| Comando / comprobación | Resultado real |
|---|---|
| `python -m pytest tests/test_api_historial.py -q -p no:cacheprovider -o addopts='' --tb=short`, antes de implementar | 10 failed, 19 passed in 1.69s: se admitían identificadores inválidos o la ruta de historial devolvía 501 en lugar de validar. |
| `python -m pytest tests/test_api_historial.py tests/test_api_esquemas.py tests/test_api_ask.py tests/test_api_aprobacion.py tests/test_api_autoaprobar.py tests/test_api_rutas.py tests/test_api_errores.py tests/test_api_aislamiento.py -q -p no:cacheprovider -o addopts='' --tb=short` | 74 passed in 2.06s. |
| `python -m pytest -q -p no:cacheprovider -o addopts='' --tb=short` | 1357 passed, 18 skipped in 21.78s. |
| `git diff --check` | Sin errores. |

Se mantuvo `PYTHON_DOTENV_DISABLED=1`; la suite global usó valores ficticios de EMT
para los dobles existentes. No se configuró PostgreSQL real: las 18 omisiones
mantienen los mismos motivos documentados en T1.

T2 cubre RF-18 y conserva el contrato público de RF-20. Los identificadores válidos
todavía llegan al 501 existente de historial: sustituirlo por lectura corresponde
a T4. No se implementó T3 ni se modificaron las funciones del agente o la capa de
persistencia. No se hizo `git add`, commit, push ni cambios en PR.

## Evidencias de T3 — 2026-11-15

Se creó `src/api/historial.py`. `RegistroTemporal` reconoce los hilos del proceso,
conserva la primera pregunta de cada turno pendiente, permite liberarla al finalizar
el turno y ofrece limpieza explícita del estado. Cada instancia tiene colecciones
propias. Finalizar un turno mantiene el hilo conocido y permite recordar la
pregunta del siguiente; limpiar elimina tanto las preguntas como los hilos temporales.

`es_hilo_conocido()` consulta la existencia persistida o el registro temporal sin
crear conversaciones. `leer_historial()` reutiliza `get_thread_messages()` de
SPEC-014 y genera `MessageOut` con `role`, `content` y un `orden` consecutivo desde
1 por hilo. No cambia los mensajes originales ni los contratos de SPEC-014.

Las fixtures de API sustituyen el registro temporal por una instancia nueva en
cada caso. Se amplió la prueba existente de aislamiento para detectar hilos o
preguntas heredados. Se añadieron nueve casos de T3 en `tests/test_api_historial.py`,
incluido reconocimiento de una conversación persistida vacía y consultas que no
crean filas. Se comprobó la conversión de ids 1, 2, 5 y 6 en órdenes 1, 2, 3 y 4.

| Comando / comprobación | Resultado real |
|---|---|
| `python -m pytest tests/test_api_historial.py -q -p no:cacheprovider -o addopts='' --tb=short`, antes de implementar | 29 passed, 9 errors in 3.79s: los nueve casos nuevos no podían importar el adaptador inexistente. |
| `python -m pytest tests/test_api_historial.py tests/test_api_aislamiento.py tests/test_history.py -q -p no:cacheprovider -o addopts='' --tb=short` | 46 passed in 2.76s. |
| `python -m pytest -q -p no:cacheprovider -o addopts='' --tb=short` | 1366 passed, 18 skipped in 27.77s. |
| `git diff --check` | Sin errores. |

Se usó `.venv`, `PYTHON_DOTENV_DISABLED=1` y SQLite en memoria. La suite global
recibió valores ficticios de EMT para sus dobles. No se ejecutó PostgreSQL real;
las 18 omisiones conservan los motivos documentados en T1.

T3 verifica el adaptador de apoyo a RF-02, RF-03, RF-04 y RF-06. Las rutas y el
servicio todavía no usan este registro para tramitar turnos: esa conexión se
realizará en las tareas posteriores. La ruta de historial válida conserva su
501 hasta T4. No se modificaron el agente, el frontend ni la capa de SPEC-014.
No se hizo `git add`, commit, push ni cambios en PR; T4 no se ha iniciado.


## Evidencias de T4 — 2026-11-15

Pruebas previas: tres fallos por 501. Ruta HTTP conectada, con sesión por petición, mensajes ordenados, 404 de desconocido y 200 vacío del conocido.

Regresión: **1369 passed, 18 skipped in 22.12s**. Sin APIs de pago, con dotenv deshabilitado y EMT ficticia. Cambios locales, sin commit ni push.


## Evidencias de T5 — 2026-11-15

Pruebas previas: cuatro fallos. Se conserva HTTPException y se transforman errores inesperados de lectura en 500 genérico.

Regresión: **1373 passed, 18 skipped in 17.67s**. Sin APIs de pago, con dotenv deshabilitado y EMT ficticia. Cambios locales, sin commit ni push.


## Evidencias de T6 — 2026-11-15

Tres fallos previos: no existían mensajes ni commit. Guardado del par directo con el UUID público y confirmación solo tras commit.

Regresión: **1376 passed, 18 skipped in 17.85s**. Sin APIs de pago, con dotenv deshabilitado y EMT ficticia. Cambios locales, sin commit ni push.


## Evidencias de T7 — 2026-11-15

Dos fallos previos. Un hilo pendiente devuelve 200 vacío; se conserva la pregunta ante un rechazo de control y se mantiene el historial previo.

Regresión: **1378 passed, 18 skipped in 26.75s**. Sin APIs de pago, con dotenv deshabilitado y EMT ficticia. Cambios locales, sin commit ni push.


## Evidencias de T8 — 2026-11-15

Dos fallos previos de aprobación manual. Guardado con pregunta original y liberación del contexto al cerrar.

Regresión: **1380 passed, 18 skipped in 18.30s**. Sin APIs de pago, con dotenv deshabilitado y EMT ficticia. Cambios locales, sin commit ni push.


## Evidencias de T9 — 2026-11-15

Dos tests nuevos; ya pasan con el flujo común implementado en T6-T8. No se añadió código redundante: autoaprobación genera un par y varios planes siguen pendientes.

Regresión: **1382 passed, 18 skipped in 18.86s**. Sin APIs de pago, con dotenv deshabilitado y EMT ficticia. Cambios locales, sin commit ni push.


## Evidencias de T10 — 2026-11-15

Dos fallos previos. El rechazo parcial no escribe; el rechazo final conserva done=false y guarda pregunta original y respuesta.

Regresión: **1384 passed, 18 skipped in 17.48s**. Sin APIs de pago, con dotenv deshabilitado y EMT ficticia. Cambios locales, sin commit ni push.


## Evidencias de T11 — 2026-11-15

Cinco tests nuevos ya cubiertos por las guardas existentes: repetir decisiones o seleccionar mal no duplica ni sobrescribe el turno.

Regresión: **1389 passed, 18 skipped in 18.25s**. Sin APIs de pago, con dotenv deshabilitado y EMT ficticia. Cambios locales, sin commit ni push.


## Evidencias de T12 — 2026-11-15

Tests HTTP nuevos verifican el rollback existente: falla el segundo mensaje y no queda turno parcial ni se pierden turnos previos. También se fuerza error de commit y se verifica 500 genérico.

Regresión: **1392 passed, 18 skipped in 18.27s**. Sin APIs de pago, con dotenv deshabilitado y EMT ficticia. Cambios locales, sin commit ni push.


## Evidencias de T13 — 2026-11-15

Siete tests nuevos verifican la política ya implementada: no repetir agente tras fallo, no inventar pregunta, no guardar respuestas vacías y limpiar contexto terminal.

Regresión: **1399 passed, 18 skipped in 18.41s**. Sin APIs de pago, con dotenv deshabilitado y EMT ficticia. Cambios locales, sin commit ni push.


## Evidencias de T14 — 2026-11-15

Cuatro fallos previos. Lifespan prepara tablas, aborta arranque fallido con error genérico y limpia estado y motor al cerrar.

Regresión: **1403 passed, 18 skipped in 18.55s**. Sin APIs de pago, con dotenv deshabilitado y EMT ficticia. Cambios locales, sin commit ni push.


## Evidencias de T15 — 2026-11-15

Cuatro tests nuevos verifican el mismo guardado con GrafoFalso y un doble del contrato real, sin LLM. Se conservan los seis campos públicos y done del agente.

Regresión: **1407 passed, 18 skipped in 18.32s**. Sin APIs de pago, con dotenv deshabilitado y EMT ficticia. Cambios locales, sin commit ni push.


## Evidencias de T16 — 2026-11-15

Cinco fallos previos por infraestructura de destino inexistente. Sin URL: 5 passed, 2 skipped. Con PostgreSQL temporal: varios turnos, aislamiento y UUID verificados. Un esquema aleatorio por caso, sin tocar tablas públicas.

Regresión: **1414 passed, 18 skipped in 19.17s**. Sin APIs de pago, con dotenv deshabilitado y EMT ficticia. Cambios locales, sin commit ni push.


## Evidencias de T17 — 2026-11-15

PostgreSQL real: aprobación manual y automática, rechazo final y parcial, decisión repetida y dos escenarios de rollback. Todos pasan con un esquema propio por caso.

Regresión: **1420 passed, 18 skipped in 20.32s**. Sin APIs de pago, con dotenv deshabilitado y EMT ficticia. Cambios locales, sin commit ni push.


## Evidencias de T18 — 2026-11-15

Dos procesos independientes guardan y recuperan historial en PostgreSQL. El hilo solo temporal desaparece tras reiniciar; no se promete recuperar planes pendientes.

Regresión: **1421 passed, 18 skipped in 22.53s**. Sin APIs de pago, con dotenv deshabilitado y EMT ficticia. Cambios locales, sin commit ni push.

## Avance técnico T19 y validación parcial T20 — 2026-11-15

La documentación de README está actualizada y se ejecutaron tres recorridos
AppTest con el frontend existente de SPEC-015: aprobación, rechazo y automática,
seguido de nueva conversación y recarga del historial. Se sustituyó solo el
transporte HTTP por la API en proceso; no se modificó la rama del frontend.

En la revisión final se detectó y corrigió un rechazo de control del agente real
que conservaba el plan: ya no puede provocar una autoaprobación. El test nuevo
falló antes de aplicar la salida inmediata. También se comprobaron configuraciones
de arranque inválidas en procesos reales.

Resultado final desde el proyecto real: **1427 passed, 18 skipped in 31.12s**,
con PostgreSQL real y frontend activados. JUnit local en
`output/spec016-20261115/pytest.xml`: 1445 casos, 14 de PostgreSQL (5 protecciones
de destino y 9 casos de integración) y 3 de frontend. No se usaron APIs de pago.
Contenedor y volúmenes temporales eliminados tras comprobar cero esquemas restantes.

El responsable confirmó que falta revisar el contrato con sus compañeros de API
y frontend. T19 y T20 permanecen pendientes y `validacion.md` tiene veredicto
**Parcial**, sin dar por realizada esa revisión. No se hizo commit ni push.