# Tareas — Spec 018

> Una tarea cada vez: `/sdd-implementar Tn`. Tests primero. Marca `[x]` al terminar.

- [x] T1. Añadir en `tests/test_api_cors.py` pruebas aisladas para leer `CORS_ORIGINS`: lista separada por comas, espacios, comas repetidas, variable ausente y vacía; incluir la comprobación del valor de ejemplo local en `.env.example`. Desactivar `load_dotenv()` en el proceso aislado para no depender de `.env`. (RF-1, RF-2, RF-7, RF-9)
      Hecho cuando: `python -m pytest tests/test_api_cors.py -k 'config or env_example'` falla solo por la configuración y el ejemplo aún no implementados, sin leer `.env` ni abrir conexiones.

- [x] T2. Implementar en `config.py` la lectura de `CORS_ORIGINS` como lista separada por comas, recortar espacios, omitir elementos vacíos y añadir a `.env.example` el comentario y el ejemplo local acordado. (RF-1, RF-2, RF-7, RF-9)
      Hecho cuando: `python -m pytest tests/test_api_cors.py -k 'config or env_example'` queda verde y `.env.example` no contiene secretos reales.

- [x] T3. Añadir pruebas de integración con `TestClient` para origen permitido y no permitido, preflight en las rutas existentes, ausencia de credenciales CORS y rechazo de métodos o cabeceras fuera de la lista; importar `app.py` con el entorno controlado antes de crear la aplicación. (RF-3, RF-4, RF-5, RF-6)
      Hecho cuando: `python -m pytest tests/test_api_cors.py -k 'middleware or preflight or origen'` falla por la falta del middleware CORS, sin iniciar Uvicorn ni llamar al agente o a servicios externos.

- [x] T4. Configurar `CORSMiddleware` en `app.py` con `config.CORS_ORIGINS`, `allow_credentials=False`, métodos `GET` y `POST`, y cabeceras `Accept` y `Content-Type`, manteniendo rutas, autenticación y contratos actuales. (RF-3, RF-4, RF-5, RF-6)
      Hecho cuando: `python -m pytest tests/test_api_cors.py -k 'middleware or preflight or origen'` queda verde; el preflight permitido incluye autorización CORS y los métodos/cabeceras no permitidos no la reciben.

- [x] T5. Añadir una prueba de documentación que compruebe que README explica la variable `CORS_ORIGINS`, la configuración local y la configuración del servicio API en Render, sin presuponer un frontend desplegado allí. (RF-8)
      Hecho cuando: `python -m pytest tests/test_api_cors.py -k readme` falla solo porque la documentación aún no describe CORS.

- [x] T6. Documentar en README el formato local de `CORS_ORIGINS` y dónde introducir la variable en el entorno del servicio API en Render; indicar que los valores dependen del entorno. (RF-8)
      Hecho cuando: `python -m pytest tests/test_api_cors.py -k readme` queda verde y las instrucciones no requieren editar código ni presuponen un frontend desplegado en Render.

- [x] T7. Validación final RF por RF (`/sdd-validar`) y ejecución de la suite completa, comprobando que la política no cambia autenticación ni contratos HTTP. (RF-1 a RF-9)
      Hecho cuando: `python -m pytest` termina con código 0 y `specs/018-cors-configuracion/validacion.md` registra el resultado de cada RF.
