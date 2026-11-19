# Plan técnico — Spec 018

> Basado en `spec.md` (estado: Aprobada). No añade comportamiento fuera de la spec.

## Archivos afectados

| Archivo | Crear / Modificar | Qué cambia | RF |
|---|---|---|---|
| `config.py` | Modificar | Leer `CORS_ORIGINS` del entorno y exponer una lista separada por comas, recortando espacios e ignorando entradas vacías. | RF-1, RF-2, RF-9 |
| `app.py` | Modificar | Importar `CORSMiddleware` y añadirlo a la aplicación con `config.CORS_ORIGINS`, credenciales deshabilitadas y los métodos/cabeceras permitidos explícitamente. | RF-3 a RF-6 |
| `.env.example` | Modificar | Documentar el formato y añadir el ejemplo local de clase para `CORS_ORIGINS`. | RF-7 |
| `README.md` | Modificar | Explicar la configuración local y dónde introducir `CORS_ORIGINS` en el servicio de API de Render. | RF-8 |
| `tests/test_api_cors.py` | Crear | Probar lectura aislada de la configuración, preflight, orígenes permitidos/no permitidos, middleware global y documentación. | RF-1 a RF-9 |

No se modifican los endpoints, el cliente HTTP de Streamlit ni los contratos de autenticación. No se añaden dependencias: FastAPI ya incluye `CORSMiddleware` y `TestClient` está disponible para las pruebas.

## Contrato

No cambia el contrato de las rutas ni de los comandos. `config.CORS_ORIGINS` será una lista de cadenas y `app.py` instalará el middleware CORS al crear la aplicación. La configuración se lee al importar `config.py`; los cambios en el entorno requieren reiniciar el proceso de la API.

Ejemplo de configuración local:

```env
CORS_ORIGINS=http://127.0.0.1:8000,http://localhost:8000,http://127.0.0.1:8501,http://localhost:3000
```

Ejemplo de preflight del navegador:

```http
OPTIONS /ask
Origin: http://localhost:3000
Access-Control-Request-Method: POST
Access-Control-Request-Headers: content-type
```

Si `http://localhost:3000` está permitido, la respuesta incluye las cabeceras CORS correspondientes, incluido el origen autorizado. No incluye `Access-Control-Allow-Credentials: true`. Un origen no permitido no obtiene autorización CORS. La respuesta HTTP de negocio no cambia.

Ejemplo esquemático de respuesta al preflight permitido:

```http
HTTP/1.1 200 OK
Access-Control-Allow-Origin: http://localhost:3000
Access-Control-Allow-Methods: GET, POST
Access-Control-Allow-Headers: Accept, Content-Type
```

## Lógica clave

```text
leer CORS_ORIGINS:
    valor = variable de entorno o cadena vacía
    orígenes = dividir valor por comas
    devolver cada elemento recortado que no esté vacío

crear aplicación FastAPI:
    añadir CORSMiddleware con:
        allow_origins = config.CORS_ORIGINS
        allow_credentials = false
        allow_methods = ["GET", "POST"]
        allow_headers = ["Accept", "Content-Type"]
    declarar rutas existentes sin cambios
```

## Decisiones técnicas

| Decisión | Alternativa descartada | Por qué |
|---|---|---|
| Centralizar la lectura y separación de `CORS_ORIGINS` en `config.py`. | Leer y procesar la variable directamente en `app.py`. | Sigue la constitución de configuración centralizada y permite probar los casos ausente, vacío y lista separada sin iniciar el servidor. |
| Usar `CORSMiddleware` de FastAPI en `app.py`. | Escribir cabeceras CORS manualmente en cada endpoint. | El middleware comparte una política entre rutas y gestiona los preflight `OPTIONS`. |
| Deshabilitar credenciales CORS y permitir solo `GET`, `POST`, `Accept` y `Content-Type`. | Habilitar cookies/credenciales del navegador o usar comodines para métodos y cabeceras. | El contrato actual usa `api_key` en query, no cookies ni credenciales del navegador; `APIHttpClient` usa únicamente esos métodos y cabeceras. La lista explícita limita la política al uso actual. |
| Ejecutar las pruebas HTTP con `TestClient` y aislar la carga de entorno, desactivando `load_dotenv()` en el proceso de prueba. | Probar contra un servidor local desplegado o depender del `.env` de la máquina. | Hace las pruebas deterministas, no requiere red y evita depender de configuración local o secretos. |

## Estrategia de tests

Las pruebas usarán `TestClient` y no iniciarán un servidor ni llamarán al agente, a un LLM o a servicios externos. Para validar valores de entorno, se cargará `config.py` en un proceso aislado con `dotenv.load_dotenv()` sustituido por una función vacía. Para las pruebas de middleware, la aplicación se importará en un proceso con `CORS_ORIGINS` controlado antes de importar `app.py`.

- Configuración: verificar lista con varios orígenes, espacios, comas repetidas, variable ausente, vacía y solo espacios.
- Origen permitido: solicitar `/health` con `Origin` y comprobar `Access-Control-Allow-Origin` y que no se habiliten credenciales CORS.
- Preflight: enviar `OPTIONS` con `Origin`, método solicitado y cabeceras solicitadas; comprobar que `GET` y `POST` con `Accept` y `Content-Type` se autorizan, y que un método o cabecera fuera de la lista se rechaza.
- Origen no permitido: comprobar que la respuesta de `/health` no incluye autorización CORS para ese origen.
- Aplicación global: comprobar preflight en las rutas de `/ask`, `/approve` e historial, sin ejecutar sus operaciones de negocio.
- Ejemplo y documentación: comprobar que `.env.example` contiene la lista acordada y que README describe la variable local y la del servicio API en Render, sin presuponer un frontend allí.

Los escenarios de CORS quedan cubiertos automáticamente mediante `TestClient`; no requieren una prueba manual con navegador para verificar las cabeceras HTTP.

## Riesgos

- CORS limita qué respuestas puede leer JavaScript en un navegador; no bloquea solicitudes HTTP ni reemplaza autenticación. La API debe seguir protegida por los controles de la spec 017.
- La API toma `CORS_ORIGINS` al iniciar. Un cambio en `.env` o en la configuración de Render requiere reiniciar o redesplegar el servicio.
- Los cambios en la lista de métodos o cabeceras requieren actualizar la spec y las pruebas, para que la política se mantenga alineada con los clientes autorizados.

## Trazabilidad

| RF | Parte del plan | Test |
|---|---|---|
| RF-1 | Lectura y separación en `config.py` | `tests/test_api_cors.py::test_config_cors_separa_origenes` |
| RF-2 | Valor ausente o vacío produce lista vacía | `tests/test_api_cors.py::test_config_cors_ausente_o_vacia` |
| RF-3 | `CORSMiddleware` en `app.py` con parámetros acordados | `tests/test_api_cors.py::test_middleware_cors_configurado` |
| RF-4 | Respuesta al origen permitido y preflight | `tests/test_api_cors.py::test_preflight_permitido_devuelve_cabeceras_cors` |
| RF-5 | Origen no autorizado | `tests/test_api_cors.py::test_origen_no_permitido_no_recibe_cabecera_cors` |
| RF-6 | Middleware aplicado en las rutas existentes | `tests/test_api_cors.py::test_preflight_cors_en_rutas_de_api` |
| RF-7 | Variable y ejemplo local en `.env.example` | `tests/test_api_cors.py::test_env_example_documenta_cors` |
| RF-8 | Instrucciones local y Render en README | `tests/test_api_cors.py::test_readme_documenta_cors_local_y_render` |
| RF-9 | Espacios y elementos vacíos al separar la lista | `tests/test_api_cors.py::test_config_cors_recorta_espacios_e_ignora_vacios` |
