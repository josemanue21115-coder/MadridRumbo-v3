# Validación — SPEC-016: integración API–PostgreSQL

Fecha: 15/11/2026. Rama local: `feature/api-postgres-historial`.

> **Actualización del 19/11/2026: veredicto «Sí»; ver «Cierre de T19 y T20» al final.**

**Veredicto a fecha 15/11/2026: Parcial.** La implementación y la validación técnica de los
24 RF están verificadas. El responsable confirmó expresamente que queda pendiente
la revisión conjunta con los compañeros de API y frontend. Por ello T19 y T20
permanecen sin marcar y la especificación no se declara cerrada ni lista para
fusionar. La PR #1 continuaba abierta al consultar GitHub.

## Alcance y entorno

- Base local al iniciar: `578cec567adfe76d401e573bb3ad6b94a63a01ee` (T3).
- Implementación incremental de T4–T18, pruebas y documentación técnica de T19–T20, antes de preparar los commits de entrega por bloques.
- Windows, Python 3.14.4, pytest 9.2.0, SQLModel 0.0.50, SQLAlchemy 2.0.57, psycopg2-binary 2.9.13 y PostgreSQL 16.16.
- Se trabajó primero en una copia aislada sin `.env`; la ejecución final se repitió desde la carpeta real del proyecto.
- `PYTHON_DOTENV_DISABLED=1`; EMT con valores ficticios para sus dobles existentes; ningún LLM, embedding, API de transporte ni ChromaDB real.
- PostgreSQL temporal: contenedor `madridrumbo-spec016-validacion`, base y usuario exclusivos `spec016`, puerto asignado a `127.0.0.1`. Sus credenciales temporales no se guardan en Git.
- Cada caso PostgreSQL crea un esquema aleatorio propio y lo elimina al terminar. El fixture rechaza hosts remotos, otra base, otro usuario, otro backend o parámetros adicionales que puedan redirigir la conexión.

## Resultados verificables

| Ejecución | Resultado |
|---|---|
| T4, tests antes de implementar lectura | 3 fallos por el antiguo 501. |
| Regresión T4 | 1369 passed, 18 skipped in 22.12s. |
| T5, tests antes de corregir errores | 4 fallos: excepciones sin controlar y códigos HTTP deliberados convertidos en 500. |
| Regresión T5 | 1373 passed, 18 skipped in 17.67s. |
| Regresión T6 | 1376 passed, 18 skipped in 17.85s. |
| Regresión T7 | 1378 passed, 18 skipped in 26.75s. |
| Regresión T8 | 1380 passed, 18 skipped in 18.30s. |
| Regresión T9 | 1382 passed, 18 skipped in 18.86s. |
| Regresión T10 | 1384 passed, 18 skipped in 17.48s. |
| Regresión T11 | 1389 passed, 18 skipped in 18.25s. |
| Regresión T12 | 1392 passed, 18 skipped in 18.27s. |
| Regresión T13 | 1399 passed, 18 skipped in 18.41s. |
| Regresión T14 | 1403 passed, 18 skipped in 18.55s. |
| Regresión T15 | 1407 passed, 18 skipped in 18.32s. |
| PostgreSQL optativo sin URL, al preparar T16 | 5 passed, 2 skipped; se explicita que esos dos casos no se ejecutaron. |
| Regresión T16, con PostgreSQL real | 1414 passed, 18 skipped in 19.17s. |
| Regresión T17, con PostgreSQL real | 1420 passed, 18 skipped in 20.32s. |
| Regresión T18, incluyendo dos procesos independientes | 1421 passed, 18 skipped in 22.53s. |
| AppTest con frontend real de SPEC-015, sustituyendo solo transporte HTTP | 3 passed in 7.39s. |
| Revisión adicional RF-11, antes de corregirla | 1 failed, 1 passed: un rechazo de control con plan podía continuar a la autoaprobación. |
| Suite final desde la carpeta real, con PostgreSQL y frontend | **1427 passed, 18 skipped in 31.12s**. |
| JUnit final | 1445 casos, cero fallos; 14 de PostgreSQL y 3 del frontend. |
| Revisión de credenciales y diff | Sin hallazgos de secretos reales; `git diff --check` sin errores. |
| Limpieza PostgreSQL | Cero esquemas `spec016_%` restantes; contenedor y sus volúmenes temporales eliminados. |

El JUnit está en `output/spec016-20261115/pytest.xml`, como evidencia **local**
ignorada por Git. Se puede volver a generar con el comando inferior. Las 18
omisiones finales pertenecen a los tests optativos de SPEC-014: 17 casos requieren
su propia URL PostgreSQL y uno no aplica a SQLite en memoria entre procesos. Los
casos PostgreSQL y frontend de SPEC-016 sí se ejecutaron en la validación final.

## Trazabilidad RF por RF

Todos los archivos de la tabla están dentro de `tests/`. «Superado» significa
verificado técnicamente, no aprobación de la revisión humana pendiente.

| RF | Evidencia ejecutada | Resultado |
|---|---|---|
| RF-01 | `test_api_historial.py::test_historial_guardado_200`; `test_api_postgresql.py::test_postgresql_varios_turnos_y_hilos` | Superado |
| RF-02 | `test_api_historial.py::test_campos_publicos_historial` y respuesta HTTP de historial | Superado |
| RF-03 | `test_orden_consecutivo_con_ids_intercalados`; órdenes 1–4 pese a ids globales 1, 2, 5, 6 | Superado |
| RF-04 | `test_hilos_separados`; hilos intercalados en PostgreSQL real | Superado |
| RF-05 | `test_desconocido_404`; ausencia de filas creadas por lectura | Superado |
| RF-06 | `test_conocido_sin_mensajes_200_vacio`; `test_pendiente_no_guarda_y_conserva_historial_previo` | Superado |
| RF-07 | `test_api_persistencia.py::test_ask_directo_guarda_par` y recorrido PostgreSQL | Superado |
| RF-08 | `test_pendiente_no_guarda_y_conserva_historial_previo`; rechazo parcial en PostgreSQL | Superado |
| RF-09 | `test_approve_guarda_pregunta_original`, con uno o varios planes; caso PostgreSQL manual | Superado |
| RF-10 | `test_autoaprobar_guarda_un_solo_par`; `test_autoaprobar_varios_planes_no_guarda`; caso PostgreSQL automático | Superado |
| RF-11 | `test_rechazo_control_conserva_historial_y_pregunta`, con y sin plan devuelto; selección inválida | Superado |
| RF-12 | `test_approve_repetido_no_duplica`, después de aprobación y rechazo; repetición en PostgreSQL | Superado |
| RF-13 | `test_fallo_segundo_mensaje_revierte_turno`; `test_api_postgresql.py::test_rollback_postgresql`, ambos con y sin historial previo | Superado |
| RF-14 | `test_guardado_fallido_500_sin_detalles`; errores de escritura devuelven 500 genérico | Superado |
| RF-15 | `test_200_solo_despues_del_commit`, junto con errores de commit que nunca devuelven 200 | Superado |
| RF-16 | `test_api_historial.py::test_lectura_fallida_500`, en existencia y lectura de mensajes | Superado |
| RF-17 | `test_uuid_devuelto_es_el_persistido`; `test_postgresql_uuid_crea_y_recupera` | Superado |
| RF-18 | `test_thread_invalido_422_sin_consultas`, contadores de agente/SQL a cero; límites ASCII y Unicode | Superado |
| RF-19 | `test_api_postgresql.py::test_historial_tras_reinicio_api`, con dos procesos nuevos sobre la misma base | Superado |
| RF-20 | `test_respuestas_conservan_contrato_013`; regresión API y frontend | Superado |
| RF-21 | `test_persistencia_independiente_del_modo`, con GrafoFalso y doble del contrato real | Superado |
| RF-22 | `test_api_arranque.py`, incluidos procesos reales con DATABASE_URL ausente o no PostgreSQL; arranque correcto con PostgreSQL | Superado |
| RF-23 | `test_ultimo_rechazo_guarda_par_con_done_false`; rechazo final y parcial en PostgreSQL y frontend | Superado |
| RF-24 | `test_fallo_commit_no_repite_agente`, directo/manual/automático; conteo de llamadas en rollback PostgreSQL | Superado |

No se invocó un modelo real para RF-21: se verificó el contrato sustituido y el
flujo común, conforme a la estrategia sin APIs de pago del plan aprobado.

## Incidencias y cambios finales

1. Se sustituyó el historial reservado 501 por lectura de PostgreSQL con sesiones por petición, 404 de hilo desconocido y 200 vacío de hilo conocido.
2. El manejador genérico ahora conserva `HTTPException` deliberadas; los errores SQL siguen devolviendo un mensaje 500 genérico.
3. El guardado se hace tras el resultado final, conservando la pregunta original durante HITL y liberando el contexto terminal incluso si falla la escritura. No hay reintento automático del agente.
4. La revisión final detectó que la fachada real puede devolver un rechazo de control conservando `hitl_pendiente=true` y el plan. Se añadió el caso regresivo y una salida inmediata para impedir autoaprobarlo.
5. Se añadieron comprobaciones de configuración de arranque en procesos reales, además de los dobles, sin intentar conectarse a bases externas.
6. La comprobación del frontend empleó copias revisadas de `feature/front-seguridad`, sin modificar esa rama: blob de `front.py` `c4b4b48b1b46e6d64e4aea12779298d2f6202c07` y de `api_http.py` `494a572c4c936223a6b92ee3dd7aa0dc3750f5d2`.

AppTest ejecutó salud, pregunta, aprobación/rechazo/autoaprobación, nueva
conversación y recarga del hilo persistido. El cliente y la UI son los de SPEC-015;
solo se sustituyó el transporte de red por acceso a la API en proceso. Esto es
una verificación automatizada, **no una revisión conjunta o prueba manual por
los compañeros**. El responsable confirmó que esa revisión sigue pendiente.

## Reproducción

La suite utiliza `.venv`. Antes de ejecutarla, deshabilitar dotenv y suministrar
valores ficticios de EMT para los dobles existentes. Para reproducir los casos
optativos se necesita la base desechable de pruebas y las dos copias del frontend
revisadas, fuera del código de producción:

```powershell
$env:PYTHON_DOTENV_DISABLED = '1'
$env:EMT_CLIENT_ID = 'spec016_prueba_sin_red'
$env:EMT_PASS_KEY = 'spec016_prueba_sin_red'
# SPEC016_TEST_DATABASE_URL: PostgreSQL local, usuario/base spec016, sin query.
# SPEC016_FRONTEND_DIR: carpeta con front.py y api_http.py revisados de SPEC-015.
python -m pytest -q -p no:cacheprovider -o addopts='' --tb=short --junitxml=output/spec016-20261115/pytest.xml
```

El contenedor de esta ejecución ya está eliminado: para repetir PostgreSQL debe
prepararse otro entorno temporal. Sin las variables de las pruebas optativas,
estas se omiten con motivo visible y no pueden contarse como ejecutadas.

La revisión de secretos abarca los archivos de texto versionados y los nuevos
archivos de esta entrega. No lee `.env`, no imprime valores sensibles y no
constituye una auditoría de todo el historial Git. Las URLs de las pruebas de
seguridad contienen únicamente contraseñas ficticias explícitas.

## Condiciones de cierre

| Condición | Estado |
|---|---|
| Spec y plan aprobados | Sí |
| T4–T18 implementadas y verificadas incrementalmente | Sí |
| 24 RF cubiertos por pruebas ejecutadas | Sí, técnicamente |
| PostgreSQL real, atomicidad y reinicio | Sí |
| Compatibilidad automatizada con frontend SPEC-015 | Sí |
| Regresión completa y revisión de secretos | Sí |
| Limpieza del entorno temporal | Sí |
| Coordinación y comprobación conjunta API/frontend | **Pendiente, confirmado por el responsable** |
| Cierre global T19/T20 | **Pendiente; veredicto Parcial** |
| Revisión humana de PR #1 antes de fusionar integración | Pendiente de gestionar con el equipo; PR abierta |

Se mantienen fuera de alcance Docker de producción, Render, autenticación y
checkpoints persistentes. El historial no restaura planes pendientes y no se
garantiza deduplicación de reenvíos HTTP ni continuidad HITL entre varios workers.
La validación se ejecutó antes de los commits de entrega. Los commits posteriores se preparan por bloques con autorización del responsable; el push lo realiza él desde Visual Studio Code. No se ejecutaron merges ni se modificó `develop` o el estado de las PR.

## Cierre de T19 y T20 — 19/11/2026

Rama: `feature/historial-t19-t20`, creada desde `feature/api-postgres-historial` sin modificar esta última. Se integró `develop`, que ya incluye SPEC-017, SPEC-018 y SPEC-019 (clave de API, límite de peticiones, timeout, CORS y logs), y se resolvieron los conflictos en `app.py`, `src/api/servicio.py` y cuatro tests de API.

### Cambios de integración

- `app.py`: conserva el lifespan, la sesión por petición y la ruta real de historial; `/ask`, `/approve` y `/threads/{thread_id}/messages` exigen `validar_api_key`; `/ask` aplica el timeout (504) y pasa la sesión al servicio.
- `src/api/servicio.py`: sin cambios de lógica; se conserva el guardado del turno.
- Tests: `tests/conftest.py` hace que `cliente_api` envíe una clave de prueba; los tests de SPEC-017 y SPEC-019 pasan a esperar 404 (no 501) en el historial y aceptan la sesión por petición; `tests/test_api_postgresql.py` envía la clave.
- La autenticación, que el alcance de 15/11 dejaba fuera, la aporta ahora SPEC-017.

### Entorno

Windows, Python 3.11.9, PostgreSQL 18 instalado en local (sin contenedor). Base y usuario `spec016` para las pruebas automáticas. Agente simulado, sin APIs de pago.

### Resultados reales

| Comando | Resultado |
|---|---|
| `python -m pytest -q -p no:cacheprovider -o addopts='' --tb=short`, sin URL de PostgreSQL | 1497 passed, 39 skipped in 33.67s. Los 9 tests de integración PostgreSQL de SPEC-016 quedan omitidos. |
| El mismo comando con `SPEC016_TEST_DATABASE_URL` hacia `spec016` en PostgreSQL local | **1506 passed, 30 skipped in 36.85s.** |
| `python -m pytest tests/test_api_postgresql.py -q -p no:cacheprovider` | 14 passed. |

Omisiones justificadas (30): 18 de SPEC-014 que requieren su propia base temporal (`SPEC014_TEST_DATABASE_URL`) o SQLite entre procesos; 3 de compatibilidad con una copia del front (`SPEC016_FRONTEND_DIR`); 9 de `test_app_streamlit.py`, sustituidos por SPEC-015.

### Comprobación manual con Streamlit (T19)

API con PostgreSQL (`madridrumbo_prueba`), agente simulado y clave de API configurada; front de SPEC-015 sin modificar.

- Aprobación: pregunta de ruta, **Aprobar**, respuesta «[Simulado] Plan aprobado…», **Nueva conversación**, **Cargar conversación** con el ID: reaparecen la pregunta y la respuesta.
- Rechazo: pregunta de ruta, **Rechazar**, respuesta de rechazo, nueva conversación y carga por ID: reaparece la conversación.

### Coordinación y limpieza

- PR #6 aprobado por Rubén el 17/11/2026 tras probar con PostgreSQL real; la compatibilidad con el frontend la comprobó Guzmán el 19/11/2026.
- No se usó contenedor Docker. Cada test PostgreSQL crea y elimina su propio esquema; `spec016` y `madridrumbo_prueba` son bases locales desechables sin datos reales.
- La clave `clave-de-prueba` es ficticia y solo existe en los tests.

### Veredicto

**Sí** (propuesto): los 24 RF siguen cubiertos tras integrar SPEC-017 a SPEC-019 y la comprobación con el frontend está hecha. Pendiente de la confirmación de José al revisar estos cambios. Esta validación no autoriza la fusión.
