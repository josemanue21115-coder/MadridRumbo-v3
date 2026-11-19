# Plan técnico — Spec 017

> Basado en `spec.md` (estado: Aprobada). No añade comportamiento fuera de la spec.

## Archivos afectados

| Archivo | Crear / Modificar | Qué cambia | RF |
|---|---|---|---|
| `config.py` | Modificar | Leer `API_KEY`, `RATE_LIMIT_PER_MINUTE` y `ASK_TIMEOUT_SECONDS` del entorno; usar 30 y 300 cuando los límites no sean enteros positivos. Mantener `API_KEY` vacía si no se configuró, para que la API responda 503. | RF-4, RF-5, RF-6, RF-8, RF-17 |
| `src/api/seguridad.py` | Crear | Validar la clave de query y mantener el contador compartido por clave para las tres rutas protegidas, incluida la cuota común de peticiones sin clave. Expirar registros fuera de la ventana móvil de 60 segundos. | RF-1, RF-3, RF-4, RF-6, RF-7, RF-18, RF-19 |
| `app.py` | Modificar | Aplicar la dependencia de autenticación a `/ask`, `/approve` e historial; publicar el parámetro `api_key` en OpenAPI; dejar públicas `/health`, `/docs` y la especificación OpenAPI que carga `/docs`; limitar el tiempo de `/ask`, responder 504 y registrar el vencimiento sin secretos. | RF-1 a RF-4, RF-7 a RF-12 |
| `.env.example` | Modificar | Documentar `API_KEY=` sin secreto y los valores predeterminados `RATE_LIMIT_PER_MINUTE=30` y `ASK_TIMEOUT_SECONDS=300`. | RF-5, RF-13 |
| `tests/test_api_seguridad.py` | Crear | Probar autenticación, precedencia de 503, contadores y ventana móvil, acceso público y ausencia de claves en respuestas y logs. | RF-1 a RF-7, RF-11, RF-14, RF-15, RF-18, RF-19 |
| `tests/test_api_timeout.py` | Crear | Probar 504 y su mensaje, logs sin secretos, que otras rutas no heredan el límite y que el turno lento usa un doble sin LLM. | RF-8 a RF-12, RF-16 |
| `tests/test_api_errores.py` | Modificar | Enviar una clave válida para alcanzar los errores de agente ya cubiertos y conservar la comprobación de 500 genérico ante fallos inesperados. | RF-3, RF-4, RF-11 |
| `tests/test_api_rutas.py` | Modificar | Añadir clave en las solicitudes protegidas de pruebas existentes y confirmar que `/health`, `/docs` y OpenAPI siguen accesibles sin clave. | RF-1, RF-2 |

No se cambian los contratos de `src/api/servicio.py`, el agente ni las respuestas correctas de las rutas. No se añaden dependencias: FastAPI ya permite dependencias de ruta y HTTPX ya está disponible para `TestClient`.

## Contrato

Las tres rutas protegidas reciben `api_key` como parámetro de query, según las specs 013 y 015. Las solicitudes correctas conservan sus cuerpos y respuestas actuales. `/health`, `/docs` y `/openapi.json` no requieren clave.

Ejemplos (la clave es un marcador, no un secreto real):

```http
POST /ask?api_key=<CLAVE_CONFIGURADA>
Content-Type: application/json

{"pregunta":"¿Hasta qué hora hay metro?"}
```

```http
GET /threads/abc123/messages?api_key=<CLAVE_CONFIGURADA>
```

Respuestas de error observables:

```json
{"detail":"..."}
```

Los códigos son 401 para clave ausente o incorrecta, 503 si el servicio no tiene `API_KEY`, 429 al exceder la cuota y 504 cuando el turno de `/ask` supera el timeout. El 504 usa exactamente el mensaje fijado en RF-9. Los errores inesperados siguen el 500 genérico de la spec 013. Ninguna respuesta revela claves, excepciones, trazas ni infraestructura.

## Lógica clave

```text
petición protegida(ruta, api_key):
    si API_KEY no está configurada:
        devolver 503
    identidad = api_key si se proporcionó; si no, contador compartido sin clave
    si identidad superó RATE_LIMIT_PER_MINUTE en los últimos 60 segundos:
        devolver 429
    contabilizar intento de identidad
    si api_key falta o no coincide:
        devolver 401
    continuar con la ruta

POST /ask:
    ejecutar servicio.preguntar con un límite de ASK_TIMEOUT_SECONDS
    si vence el límite:
        registrar evento sin query, clave ni excepción
        devolver 504 con el mensaje definido
    si ocurre otro fallo inesperado:
        conservar el 500 genérico existente
```

La cuota se comparte entre rutas. El contador elimina intentos anteriores a la ventana móvil antes de decidir si admite el siguiente. Las peticiones que no superan la autenticación también consumen cuota según RF-18 y RF-19.

## Decisiones técnicas

| Decisión | Alternativa descartada | Por qué |
|---|---|---|
| Aplicar autenticación mediante dependencias FastAPI en cada ruta protegida y declarar `api_key` como parámetro de query opcional | Middleware global que extraiga la clave de la URL | La dependencia hace visible el parámetro en OpenAPI para poder probarlo desde `/docs` y permite contar intentos sin clave; las rutas públicas quedan fuera explícitamente. |
| Mantener una ventana móvil compartida en memoria del proceso | Ventanas fijas por minuto o un contador separado por endpoint | La ventana móvil cumple el máximo en cualquier periodo de 60 segundos y la cuota compartida evita eludirla alternando rutas. El estado de la API y del agente ya es local al proceso y su operación requiere un solo worker. |
| Expirar registros antiguos y separar el contador sin clave | Conservar indefinidamente cada clave observada | Evita que el contador crezca con claves inválidas antiguas; el contador sin clave permite aplicar el límite a intentos que no identifican una clave. |
| Ejecutar el turno síncrono de `/ask` en un worker y limitar cuánto espera la petición HTTP | Bloquear el event loop o añadir un cliente de tareas externo | El agente actual es síncrono, no se cambia el agente ni se añade infraestructura. El vencimiento puede devolver 504 sin hacer llamadas externas durante las pruebas. |
| Tratar valores de límite no positivos o no enteros como configuración inválida y usar 30/300 | Fallar al arrancar la API | Conserva el comportamiento predeterminado documentado por RF-8 y RF-17. `API_KEY` ausente conserva un estado distinto y produce 503. |
| Mantener parámetros de query por compatibilidad y sanear los logs de acceso para que no registren la query | Mover la clave a una cabecera | Las specs 013 y 015 fijan `api_key` en la query; los registros no deben persistir esa URL con la clave. |

## Estrategia de tests

Todos los tests usarán `TestClient`, variables de entorno controladas por `monkeypatch`, el agente falso existente y funciones simuladas. Ninguna prueba llamará a LLM, embeddings, ChromaDB ni servicios HTTP externos.

- Autenticación: probar clave correcta, ausente e incorrecta en las tres rutas protegidas; verificar que la ruta de historial devuelve 501 con clave correcta y no llega a procesar la ruta sin clave válida.
- Precedencia: sin `API_KEY`, probar que las rutas protegidas responden 503 incluso sin `api_key`; con clave configurada, probar 401 cuando falta o no coincide.
- Rate limit: configurar un umbral bajo; repetir una clave a través de rutas protegidas y comprobar 429 al superar el límite. Usar el historial, que responde 501 sin invocar el agente, para probarlo sin coste. Cubrir también intentos inválidos, el contador compartido sin clave, expiración después de 60 segundos y límites inválidos que vuelven a 30.
- Rutas públicas y documentación: solicitar `/health`, `/docs` y `/openapi.json` sin clave; inspeccionar OpenAPI para comprobar que `api_key` aparece como parámetro de query en las rutas protegidas.
- Errores y secretos: probar que respuestas 401/429/503/504 y 500 no contienen claves; capturar logs en las pruebas y confirmar que el evento de timeout no registra la clave ni la query. Revisar el formato del access log local de Uvicorn sin registrar query strings.
- Timeout: comprobar que un valor ausente o inválido usa 300; establecer un timeout corto y sustituir `servicio.preguntar` por un doble bloqueante; comprobar 504 y el texto exacto sin llamar a LLM. Probar que `/approve` y el historial no reciben este límite y que un fallo inesperado conserva el 500 genérico.
- Configuración de ejemplo: comprobar los valores declarados en `.env.example` y que no contienen secretos reales.

La revisión del access log de Uvicorn se confirma manualmente al arrancar la API y enviar una petición con una clave de prueba; los demás RF se comprueban con tests automatizados.

## Riesgos

- El contador en memoria no se comparte entre procesos o instancias. El diseño actual de conversaciones también depende de memoria local, por lo que el servicio debe ejecutarse con un único worker y una instancia mientras mantenga este almacenamiento.
- El agente síncrono puede seguir trabajando en su hilo después de que la petición haya respondido 504; Python no permite cancelar de forma segura un hilo en ejecución. La respuesta queda acotada, pero un trabajo que ya comenzó podría terminar y modificar estado del turno. La prueba usa un doble controlado para no generar llamadas reales.
- Como `api_key` viaja en la query por contrato, los registros HTTP podrían capturarla si conservan la URL completa. La configuración de logging debe excluir la query y los tests deben comprobar los logs de aplicación.
- Las pruebas de ventana móvil deben controlar el reloj para no depender de esperas reales ni generar resultados intermitentes.
- La ruta del historial sigue respondiendo 501 según la spec 013; se usa para verificar autenticación y rate limit sin coste de LLM.

## Trazabilidad

| RF | Parte del plan | Test |
|---|---|---|
| RF-1 | Dependencia de seguridad y parámetro de query | `tests/test_api_seguridad.py::test_api_key_query_protege_las_tres_rutas` |
| RF-2 | Rutas públicas y OpenAPI | `tests/test_api_seguridad.py::test_health_docs_y_openapi_son_publicos` |
| RF-3 | Respuesta de autenticación | `tests/test_api_seguridad.py::test_clave_ausente_o_incorrecta_responde_401` |
| RF-4 | Configuración y precedencia | `tests/test_api_seguridad.py::test_api_key_no_configurada_responde_503` |
| RF-5 | Lectura de configuración de entorno | `tests/test_api_seguridad.py::test_configuracion_api_se_lee_del_entorno` |
| RF-6 | Cuota predeterminada y ventana | `tests/test_api_seguridad.py::test_limite_predeterminado_y_ventana_movil` |
| RF-7 | Cuota global y respuesta 429 | `tests/test_api_seguridad.py::test_limite_compartido_devuelve_429` |
| RF-8 | Timeout predeterminado y configuración inválida | `tests/test_api_timeout.py::test_timeout_invalido_o_ausente_usa_300` |
| RF-9 | Respuesta 504 y mensaje | `tests/test_api_timeout.py::test_ask_superado_responde_504_con_mensaje_acordado` |
| RF-10 | Timeout solo en `/ask` | `tests/test_api_timeout.py::test_rutas_distintas_de_ask_no_heredan_timeout` |
| RF-11 | Errores genéricos sin detalles | `tests/test_api_errores.py::test_fallo_del_agente_en_ask_da_500_generico` |
| RF-12 | Registro del vencimiento sin secretos | `tests/test_api_timeout.py::test_timeout_se_registra_sin_clave` |
| RF-13 | Variables de ejemplo | `tests/test_api_seguridad.py::test_env_example_documenta_valores_no_secretos` |
| RF-14 | Petición sin `api_key` | `tests/test_api_seguridad.py::test_clave_ausente_o_incorrecta_responde_401` |
| RF-15 | Prueba del 429 sin LLM | `tests/test_api_seguridad.py::test_limite_compartido_devuelve_429` |
| RF-16 | Doble lento sin LLM | `tests/test_api_timeout.py::test_ask_superado_responde_504_con_mensaje_acordado` |
| RF-17 | Valor de rate limit inválido | `tests/test_api_seguridad.py::test_limite_invalido_usa_30` |
| RF-18 | Contador de solicitudes sin clave | `tests/test_api_seguridad.py::test_solicitudes_sin_clave_comparten_contador` |
| RF-19 | Contador de clave inválida | `tests/test_api_seguridad.py::test_solicitudes_con_clave_invalida_se_contabilizan` |
