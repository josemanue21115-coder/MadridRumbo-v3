# SPEC-014 — Validación de persistencia PostgreSQL

**Proyecto:** MadridRumbo-v3
**Rama:** `feature/postgres-historial`
**PR:** [#1](https://github.com/josemanue21115-coder/MadridRumbo-v3/pull/1)
**Fecha:** 15/11/2026
**Veredicto:** Sí, se cumplen RF-01 a RF-06 y CA-01 a CA-12.

## 1. Entorno y alcance

Windows, Python 3.14.4, pytest 9.2.0, SQLModel 0.0.50, SQLAlchemy 2.0.57,
psycopg2-binary 2.9.13 y PostgreSQL 16.16. Se utilizó `.venv` del proyecto.
La base de referencia revisada es `e7f98db2b3adfa93bb83bbad2f3da0796f698866`.

Se creó el contenedor temporal `madridrumbo-spec014-codex`, con imagen `postgres:16`,
base exclusiva `spec014` y puerto aleatorio publicado únicamente en `127.0.0.1`.
Las credenciales de prueba se suministraron durante la ejecución y no se incorporan
al repositorio. No se leyó `.env`; se usó `PYTHON_DOTENV_DISABLED=1`.

No se invocaron LLM, embeddings ni servicios de transporte reales. Los tests usan
dobles y `tests/conftest.py` bloquea las peticiones HTTP de `urllib.request`.

## 2. Ejecuciones y resultados

| Ejecución | Resultado |
|---|---|
| `python -m pytest tests/test_history.py tests/test_config_grafo.py -v -p no:cacheprovider` | 5 passed |
| Nuevos tests antes de corregir `get_engine()` | 3 fallos: driver implícito y rechazo de `postgresql+psycopg2://` |
| `python -m pytest tests/test_history.py tests/test_config_grafo.py tests/test_history_validacion.py -q -p no:cacheprovider -o addopts='' --tb=short`, con PostgreSQL temporal | **47 passed, 1 skipped in 4.75s** |
| `python -m pytest -q -p no:cacheprovider -o addopts='' --tb=short`, sin PostgreSQL y con valores ficticios de EMT | **1322 passed, 18 skipped in 18.53s** |
| Revisión heurística de credenciales en 216 archivos de texto versionados | Sin hallazgos; solo `.env.example` como archivo de entorno versionado |
| `git diff --check` | Sin errores |

La ejecución específica incluye 17 casos con PostgreSQL real. La única omisión
es compartir SQLite en memoria entre procesos, que no es aplicable. En la suite
sin PostgreSQL se omiten esos 17 casos y ese mismo caso de SQLite.

### Incidencias resueltas

- La primera ejecución global no pudo recopilar 40 módulos por dependencias
  ausentes. Se instalaron en `.venv` los paquetes necesarios ya declarados en
  `requirements.txt`, sin añadir dependencias al proyecto.
- Después hubo 13 fallos de tests de BiciMAD porque faltaban valores de EMT en el
  entorno. La ejecución final suministró valores ficticios a `EMT_CLIENT_ID` y
  `EMT_PASS_KEY`; los servicios siguieron sustituidos por dobles. No se cambió código
  de BiciMAD ni se utilizaron credenciales reales.
- La validación anterior documentaba un cambio de controlador predeterminado en
  SQLAlchemy 2.1 y el rechazo de `postgresql+psycopg2://`. Se corrigió `get_engine()`:
  las URLs sin driver seleccionan explícitamente `psycopg2`, que ya está declarado;
  se acepta su URL explícita. Se conserva el soporte existente de `psycopg` si está
  instalado. Cuatro casos unitarios comprueban la selección. La integración real
  de esta ejecución se realizó con SQLAlchemy 2.0.57, no con 2.1.

## 3. Trazabilidad de requisitos

Los nombres siguientes pertenecen a `tests/test_history_validacion.py`, salvo que
se indique otro archivo. Los casos de persistencia se ejecutaron con SQLite y
PostgreSQL cuando resulta aplicable.

| RF | Evidencia | Resultado |
|---|---|---|
| RF-01 — Conversation por thread_id | `test_tablas_modelos_y_persistencia_entre_sesiones`: conversación y fecha recuperadas | Superado |
| RF-02 — Message completo | Mismo test: identificadores, roles, contenido, thread_id y fechas | Superado |
| RF-03 — Guardar turno conjuntamente | Mismo test y `test_rollback_del_segundo_mensaje_y_reutilizacion_sesion` | Superado |
| RF-04 — Recuperar ordenado por id | Mismo test de tablas: orden de roles y contenidos y orden creciente de id; revisión de `order_by(Message.id)` | Superado |
| RF-05 — DATABASE_URL sin secretos | `test_engine_selecciona_driver_declarado`, `test_url_vacia_o_no_textual`, `tests/test_history.py::test_normalize_render_url`; revisión de configuración y credenciales | Superado |
| RF-06 — Validar y revertir | `test_rechaza_entradas_invalidas_sin_escrituras`, `test_limite_identificador`, `test_rollback_del_segundo_mensaje_y_reutilizacion_sesion` | Superado |

## 4. Criterios de aceptación

| Criterio | Evidencia | Estado |
|---|---|---|
| CA-01 — Creación de tablas PostgreSQL | Fixture usa `get_engine()` y `create_db_and_tables()`; inspección de `conversations` y `messages` | Superado |
| CA-02 — Pregunta y respuesta por turno | Comprobación de pares user/assistant y contenidos exactos | Superado |
| CA-03 — Varios turnos por conversación | Dos turnos de `uno`, cuatro mensajes | Superado |
| CA-04 — Orden de inserción | Orden de contenidos y de Message.id | Superado |
| CA-05 — Separación entre conversaciones | `uno` tiene cuatro mensajes; `dos`, dos; hilo inexistente vacío | Superado |
| CA-06 — Rechazo de entradas vacías | Parámetros vacíos, espacios, None y números para cada entrada, sin escrituras | Superado |
| CA-07 — DATABASE_URL y postgres:// | Normalización, selección explícita del driver e integración mediante `postgresql://` | Superado |
| CA-08 — Ausencia de credenciales reales | Revisión del diff y de `.env.example`, reglas de `.gitignore` y escaneo heurístico de archivos versionados sin hallazgos | Superado |
| CA-09 — Unitarias | Suite completa: 1322 passed, 18 skipped; tests específicos sin errores | Superado |
| CA-10 — PostgreSQL real | 17 casos PostgreSQL superados, versión verificada con `SELECT version()` | Superado |
| CA-11 — Atomicidad y rollback | Restricción CHECK rechaza el segundo mensaje: ningún dato del turno fallido; conserva el turno anterior si existe; sesión reutilizable | Superado |
| CA-12 — Persistencia entre sesiones | Nueva sesión y `test_persistencia_desde_otro_proceso`, usando `get_session()` en otro Python | Superado |

El escaneo de credenciales es heurístico y se refiere a los archivos actuales
versionados y al diff revisado; no constituye una auditoría de todo el historial Git.

## 5. Reproducción

Para la suite sin PostgreSQL, desde PowerShell en la raíz del repositorio:

```powershell
$env:PYTHON_DOTENV_DISABLED = '1'
$env:EMT_CLIENT_ID = 'spec014_prueba_sin_red'
$env:EMT_PASS_KEY = 'spec014_prueba_sin_red'
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider -o addopts='' --tb=short
```

Para integración se necesita una base PostgreSQL temporal exclusiva, llamada
`spec014`, en localhost. Suministrar su URL mediante `SPEC014_TEST_DATABASE_URL`
y ejecutar los tres archivos de la tabla de resultados. El fixture rechaza hosts
remotos y otros nombres de base; crea y elimina las tablas en esa base de pruebas
después de cada caso. Nunca apuntar esta variable a datos que se deban conservar.

El contenedor de esta ejecución fue eliminado con
`docker rm --force --volumes madridrumbo-spec014-codex`. Una consulta posterior
con `docker ps -a` filtrada por ese nombre confirmó su ausencia.

## 6. Revisión de la PR y cierre

Se revisó el diff completo de la PR #1 respecto de `develop`, incluidos modelos,
configuración, transacciones, consultas, dependencias y pruebas, además de los
cambios finales de validación. No quedan hallazgos bloqueantes en este alcance.
La incidencia de selección de driver está corregida y cubierta por tests.
Al consultar GitHub, la PR estaba abierta y fusionable, sin revisiones ni hilos de
revisión pendientes y sin estados de CI publicados para la base examinada.
Los resultados aquí documentados proceden de la ejecución local.

La restricción temporal usada para el rollback desaparece al eliminar las tablas
de cada caso. No se incorporan archivos Docker, migraciones, endpoints, despliegue
ni persistencia de checkpoints. Se conserva el límite preexistente de 128 caracteres
de `thread_id`, cubierto por una prueba de frontera.

Los doce criterios quedan verificados. La PR permanece abierta; la fusión con
`develop` corresponde a una decisión posterior del responsable.
