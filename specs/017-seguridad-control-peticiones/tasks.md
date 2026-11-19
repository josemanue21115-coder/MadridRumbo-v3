# Tareas — Spec 017

> Una tarea cada vez: `/sdd-implementar Tn`. Tests primero. Marca `[x]` al terminar.

- [x] T1. Añadir pruebas de configuración para `API_KEY`, `RATE_LIMIT_PER_MINUTE` y `ASK_TIMEOUT_SECONDS`, incluidos límites ausentes o inválidos y valores de `.env.example`; aislar el entorno de prueba sin leer `.env`. (RF-5, RF-8, RF-13, RF-17)
      Hecho cuando: `python -m pytest tests/test_api_seguridad.py -k configuracion` falla por las ausencias previstas y los casos fijan 30/300 como valores predeterminados.

- [x] T2. Implementar la lectura y validación de configuración en `config.py` y documentar en `.env.example` `API_KEY=` sin secreto, `RATE_LIMIT_PER_MINUTE=30` y `ASK_TIMEOUT_SECONDS=300`. (RF-5, RF-6, RF-8, RF-13, RF-17)
      Hecho cuando: `python -m pytest tests/test_api_seguridad.py -k configuracion` queda verde y `.env.example` no contiene credenciales reales.

- [x] T3. Añadir pruebas de integración de autenticación con `TestClient`: clave válida, ausente e incorrecta en las tres rutas protegidas, `503` si el servicio carece de `API_KEY`, `401` si está configurada, rutas públicas y exposición de `api_key` en OpenAPI. (RF-1, RF-2, RF-3, RF-4)
      Hecho cuando: `python -m pytest tests/test_api_seguridad.py -k 'clave or publico or openapi'` falla solo por la autenticación aún no implementada.

- [x] T4. Adaptar los tests existentes de `/ask`, `/approve` e historial para configurar una clave de prueba y enviarla en la query, conservando sus aserciones originales de contratos, validaciones, respuestas y error 500. (RF-1, RF-3, RF-11)
      Hecho cuando: `python -m pytest tests/test_api_ask.py tests/test_api_autoaprobar.py tests/test_api_aprobacion.py tests/test_api_errores.py tests/test_api_rutas.py` queda verde con el comportamiento actual y listo para ejecutarse tras activar la autenticación.

- [x] T5. Crear `src/api/seguridad.py` y conectar la dependencia de autenticación a las tres rutas protegidas; dejar `/health`, `/docs` y `/openapi.json` públicos. (RF-1, RF-2, RF-3, RF-4)
      Hecho cuando: `python -m pytest tests/test_api_seguridad.py -k 'clave or publico or openapi' tests/test_api_ask.py tests/test_api_autoaprobar.py tests/test_api_aprobacion.py tests/test_api_errores.py tests/test_api_rutas.py` queda verde.

- [x] T6. Añadir pruebas del límite de peticiones: cuota compartida entre rutas, ventana móvil de 60 segundos, `429`, contador común sin clave y contador por valor de clave inválida; controlar el reloj en los tests. (RF-6, RF-7, RF-18, RF-19)
      Hecho cuando: `python -m pytest tests/test_api_seguridad.py -k limite` falla por el limitador aún no implementado sin depender de esperas reales.

- [x] T7. Implementar el limitador compartido en memoria por clave y para intentos sin clave, con expiración de registros fuera de la ventana móvil, y aplicarlo antes de continuar con las rutas protegidas. (RF-6, RF-7, RF-18, RF-19)
      Hecho cuando: `python -m pytest tests/test_api_seguridad.py -k limite` queda verde y la ruta de historial permite probar `429` sin invocar el agente.

- [x] T8. Añadir pruebas del timeout de `/ask`: valor predeterminado o inválido, respuesta `504` con el mensaje exacto, registro del vencimiento sin clave y ausencia de timeout en `/approve` e historial; usar un turno lento simulado. (RF-8, RF-9, RF-10, RF-12, RF-16)
      Hecho cuando: `python -m pytest tests/test_api_timeout.py` falla solo por la gestión del timeout aún no implementada y no realiza llamadas externas.

- [x] T9. Aplicar el límite temporal únicamente a `/ask`, devolver el `504` acordado al vencer y registrar el evento sin claves, query ni secretos. (RF-8, RF-9, RF-10, RF-12)
      Hecho cuando: `python -m pytest tests/test_api_timeout.py` queda verde con el doble simulado y `/approve` e historial no responden `504` por este límite.

- [x] T10. Añadir pruebas de seguridad de errores y registros: comprobar que errores `401`, `429`, `503`, `504` y `500` no revelan claves ni detalles; cubrir el saneamiento del registro de acceso que podría incluir la query. (RF-11, RF-12)
      Hecho cuando: `python -m pytest tests/test_api_seguridad.py tests/test_api_timeout.py tests/test_api_errores.py` detecta cualquier clave de prueba en cuerpos o registros capturados.

- [x] T11. Ajustar el logging de la API para excluir parámetros de query y secretos, conservando el mensaje genérico de 500 ante fallos inesperados; revisar que la ruta de timeout solo registra el evento sin datos sensibles. (RF-11, RF-12)
      Hecho cuando: `python -m pytest tests/test_api_seguridad.py tests/test_api_timeout.py tests/test_api_errores.py` queda verde y una petición local con `api_key` de prueba no muestra esa clave en el access log de Uvicorn.

- [x] T12. Validación final RF por RF (`/sdd-validar`), ejecutar la suite y comprobar manualmente documentación, autenticación y logs con valores de prueba locales. (RF-1 a RF-19)
      Hecho cuando: `python -m pytest` queda verde; `validacion.md` registra el resultado para RF-1 a RF-19 y la prueba manual confirma `/health`, `/docs`, 401 sin clave, 429 en una ruta sin LLM y 504 con timeout reducido.
