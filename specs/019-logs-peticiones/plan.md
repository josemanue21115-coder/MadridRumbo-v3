# Plan técnico — Spec 019

> Basado en `spec.md` (estado: Aprobada). No añade comportamiento fuera de la spec.

## Archivos afectados

| Archivo | Crear / Modificar | Qué cambia | RF |
|---|---|---|---|
| `src/api/logs_peticion.py` | Crear | Añadir middleware ASGI que mida cada petición a rutas protegidas, capture método, ruta concreta, `thread_id`, duración y estado enviado, y emita un único registro JSON sin query ni cuerpo. Si no se envía respuesta, el estado será `null`. | RF-1 a RF-7, RF-9, RF-10 |
| `app.py` | Modificar | Envolver la aplicación FastAPI con el middleware externo para observar también los 500 producidos por el manejador global; hacer disponible el `thread_id` validado de `/ask` y `/approve` para el registro, y mantener el identificador de historial que aparece en la ruta. Ajustar el filtro de `uvicorn.access` para conservar la sanitización de query y evitar un segundo registro de petición protegida. Retirar el log separado del timeout, que quedará registrado como 504 en el único evento de petición. | RF-1 a RF-4, RF-7, RF-9, RF-10 |
| `src/api/servicio.py` | Modificar | Evitar que el registro de errores inesperados incluya el texto de la excepción o su traceback, que podrían exponer datos sensibles; el estado HTTP y resultado del error quedan reflejados en el registro de petición. | RF-5, RF-6, RF-8, RF-10 |
| `tests/test_api_logs.py` | Crear | Comprobar los campos, duración, rutas, `thread_id`, códigos de éxito y error, fallos tempranos, ausencia de respuesta, y ausencia de secretos o texto conversacional en todos los logs pertinentes. | RF-1 a RF-10 |
| `tests/test_api_seguridad.py` | Modificar | Adaptar la prueba del access log para comprobar que la query con `api_key` no se registra y que no duplica el registro dedicado de una ruta protegida. | RF-4, RF-5, RF-9, RF-10 |

No cambian los contratos HTTP ni los cuerpos de las respuestas de las specs 013 y 017. No se leen ni registran los cuerpos de solicitud o respuesta. No se añaden dependencias: el middleware y la serialización JSON usan las bibliotecas disponibles en Python y Starlette.

## Contrato

No cambia lo que reciben las rutas ni lo que devuelven sus respuestas. Para cada solicitud dirigida a `/ask`, `/approve` o `/threads/{thread_id}/messages` se emite un registro JSON con estos campos:

```json
{"event":"protected_request","method":"POST","route":"/ask","thread_id":null,"duration_ms":12.4,"status_code":401}
```

`route` contiene la ruta concreta sin query; por tanto, una lectura del historial podría registrarse como `/threads/hilo-123/messages`. `thread_id` usa `null` si no estaba disponible antes del fallo. `status_code` contiene el estado enviado al cliente o `null` si no se envió una respuesta. Los campos no incluyen `api_key`, otros parámetros de query, cuerpos, texto de preguntas o respuestas, secretos ni detalles de excepción.

## Lógica clave

```text
al recibir una solicitud HTTP:
    si método y ruta identifican una ruta protegida:
        registrar instante inicial
        tomar thread_id de la ruta de historial si está presente
        continuar la solicitud sin leer ni registrar su cuerpo
        guardar el estado HTTP cuando se envíe la respuesta
        al terminar o fallar:
            leer thread_id validado que la ruta haya puesto a disposición
            construir un único registro con ruta concreta, sin query
            calcular duración en milisegundos
            usar null como estado si no se envió respuesta
            emitir el registro JSON sin contenido conversacional ni secretos
    para otras rutas:
        continuar sin emitir registro de petición protegida

al ocurrir un fallo inesperado:
    conservar el 500 genérico existente
    no registrar mensaje de excepción ni traceback
```

El access log de Uvicorn no emitirá una segunda entrada para las rutas protegidas; su filtro seguirá retirando query parameters de las demás entradas. La ruta comunica el `thread_id` del historial. `/ask` y `/approve` pondrán a disposición del middleware el identificador una vez que sus datos de entrada estén validados; si una dependencia de seguridad o la validación impide llegar a ese punto, se registra `null`.

## Decisiones técnicas

| Decisión | Alternativa descartada | Por qué |
|---|---|---|
| Envolver FastAPI con middleware ASGI externo para observar el estado HTTP final incluso cuando lo emite el manejador global de errores. | Registrar por separado dentro de cada endpoint. | El envoltorio exterior observa rechazos de autenticación, rate limit, validación, timeout y respuestas 500 sin duplicar lógica por endpoint. |
| Emitir el evento como JSON con los campos en el propio mensaje de log. | Añadir campos solo como atributos internos de `LogRecord`. | El formato JSON garantiza que los campos requeridos aparezcan en la salida del logger con la configuración existente. |
| No leer el cuerpo en el middleware; obtener `thread_id` de la ruta del historial o de los datos validados que los endpoints expongan al middleware. | Inspeccionar o almacenar el cuerpo para buscar identificadores. | Evita retener texto conversacional y fija `null` en los fallos que ocurren antes de validar y exponer el identificador. |
| Suprimir el access log duplicado para rutas protegidas y conservar su filtro de query para otros accesos. | Dejar dos líneas por petición o apagar todos los access logs. | Un único registro dedicado cubre los campos requeridos; el acceso público conserva su diagnóstico y no expone query parameters. El timeout 504 queda reflejado en ese mismo registro, conforme al requisito de registro de timeout de la spec 017. |
| Reemplazar el registro de excepción con traceback por el registro seguro de petición, manteniendo el mensaje genérico 500 al cliente. | Registrar excepción y traceback completos para diagnóstico. | El contenido de excepción puede incluir texto conversacional, credenciales u otros datos internos prohibidos por la spec. |
| Probar mediante `TestClient`, `caplog` y una aplicación ASGI falsa, con agentes y valores simulados. | Arrancar Uvicorn, usar servicios externos o llamar a un LLM. | Permite cubrir estado HTTP, filtros de logs y fallo sin respuesta de forma local, determinista y sin llamadas externas. |

## Estrategia de tests

Todas las pruebas usarán `TestClient`, `caplog`, una aplicación ASGI mínima para el caso sin respuesta, `monkeypatch` y dobles existentes o funciones sustitutas. No se llamará a LLM, embeddings, ChromaDB ni servicios HTTP externos.

- Petición correcta: comprobar exactamente un evento `protected_request` con método, ruta concreta, `thread_id`, duración numérica no negativa y estado HTTP; cubrir `/ask`, `/approve` e historial.
- `thread_id`: probar un `/ask` nuevo que devuelve un ID, un `/ask` sin ID disponible que registre `null`, `/approve` con ID conocido, historial con ID en su ruta, y 401/422 antes de que el ID de cuerpo se exponga, con `null`.
- Errores: parametrizar respuestas 401, 429, 503, 504 y 500, y comprobar que el estado registrado coincide con el enviado. Para validar 429 se reduce la cuota; para 503 se vacía `API_KEY`; para 504 se sustituye `asyncio.wait_for`; para 500 se inyecta un agente falso que falla.
- Fallo sin respuesta: invocar el middleware con una aplicación ASGI falsa que falla antes de enviar `http.response.start`; comprobar un único evento con `status_code: null` y los otros datos disponibles.
- Validación: enviar cuerpos inválidos a las rutas protegidas y confirmar que cada petición genera un registro, aunque la validación devuelva 422 antes de ejecutar el endpoint.
- Privacidad en logs: enviar marcadores únicos como `api_key`, clave de proveedor, `DATABASE_URL`, pregunta, respuesta y mensaje de excepción; inspeccionar los mensajes de `caplog` de la aplicación, servicio y Uvicorn, y confirmar que ninguno aparece. Confirmar además que la ruta concreta permanece y que su query no.
- Duplicados y access log: pasar un registro simulado de `uvicorn.access` para una ruta protegida y comprobar que se filtra; para una ruta no protegida, verificar que el filtro elimina la query.
- Mensaje de cliente: conservar las pruebas existentes del 500 genérico y comprobar que la excepción simulada no aparece en la respuesta ni en ningún log.

## Riesgos

- La ruta concreta contiene el `thread_id` en la URL de historial porque así lo establece la spec; las pruebas comprobarán que se conserva sin query parameters.
- Si el `thread_id` de `/ask` solo se crea dentro del servicio y el turno falla antes de devolverlo, el middleware no puede recuperarlo sin inspeccionar datos internos; se registrará `null`, conforme al caso de fallo antes de obtenerlo.
- Los logs de infraestructura ajenos al proceso de la API no pueden inspeccionarse desde las pruebas locales; el alcance de verificación cubre los logs del servicio que capturan la petición, incluidos aplicación y Uvicorn.
- El formato JSON se escribe como mensaje de log; cualquier cambio posterior de formatter deberá conservar el mensaje y los campos JSON íntegros.

## Trazabilidad

| RF | Parte del plan | Test |
|---|---|---|
| RF-1 | Evento JSON de middleware con método, ruta, ID, duración y estado | `tests/test_api_logs.py::test_peticion_correcta_registra_campos` |
| RF-2 | Campo `thread_id` nulo cuando no está disponible | `tests/test_api_logs.py::test_thread_id_ausente_se_registra_como_null` |
| RF-3 | Estado nulo del identificador en fallos previos a su disponibilidad | `tests/test_api_logs.py::test_fallos_tempranos_registran_thread_id_null` |
| RF-4 | Ruta concreta sin query | `tests/test_api_logs.py::test_ruta_concreta_no_incluye_query` |
| RF-5 | Sanitización del evento y de todos los logs del servicio | `tests/test_api_logs.py::test_logs_no_contienen_secretos` |
| RF-6 | No lectura ni registro de texto conversacional | `tests/test_api_logs.py::test_logs_no_contienen_texto_conversacional` |
| RF-7 | Estado final para errores HTTP relevantes | `tests/test_api_logs.py::test_errores_protegidos_registran_estado_http` |
| RF-8 | Error genérico al cliente y ausencia de detalle de excepción | `tests/test_api_logs.py::test_fallo_inesperado_no_expone_excepcion_en_logs_ni_respuesta` |
| RF-9 | Registro también ante validación fallida y ausencia de respuesta | `tests/test_api_logs.py::test_validacion_fallida_registra_peticion` y `tests/test_api_logs.py::test_fallo_sin_respuesta_registra_estado_null` |
| RF-10 | Inspección de logs de aplicación, servicio y access log | `tests/test_api_logs.py::test_logs_no_contienen_secretos_ni_texto_conversacional` y `tests/test_api_seguridad.py::test_access_log_sanea_query_y_no_duplica_rutas_protegidas` |
