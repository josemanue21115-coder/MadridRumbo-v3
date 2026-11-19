# Spec 018 — CORS y configuración de orígenes

> Estado: Aprobada · Fecha: 2026-11-18

## Contexto y objetivo

La API FastAPI necesita declarar los orígenes que pueden realizar solicitudes cross-origin desde un navegador. Esta spec configura el middleware CORS de la API mediante `CORS_ORIGINS`, con valores específicos para cada entorno, y documenta la configuración local y la del servicio API en Render. CORS es una política aplicada por el navegador: no autentica ni impide que una solicitud HTTP llegue a la API.

## Usuarios / actores

- Equipo que configura y ejecuta la API en local y en Render.
- Navegadores que acceden a la API desde una página de otro origen.
- Clientes HTTP, incluido Streamlit, que consumen la API.

## Historias de usuario

- H1: Como equipo quiero declarar los orígenes que pueden usar la API desde un navegador para configurar el acceso cross-origin por entorno.
- H2: Como equipo quiero configurar CORS desde el entorno, sin cambiar código al pasar de local a staging o producción.
- H3: Como cliente quiero que la API aplique una política CORS coherente a todas sus rutas.

## Requisitos funcionales (criterios de aceptación en EARS)

- RF-1: EL SISTEMA obtendrá de `config.CORS_ORIGINS` la lista de orígenes permitidos, leída de la variable de entorno `CORS_ORIGINS` como valores separados por comas.
- RF-2: SI `CORS_ORIGINS` no está definida, está vacía o contiene únicamente elementos vacíos o espacios, ENTONCES EL SISTEMA configurará la lista de orígenes permitidos como vacía.
- RF-3: EL SISTEMA configurará en `app.py` el middleware `CORSMiddleware` con `allow_origins=config.CORS_ORIGINS`, `allow_credentials=False`, `allow_methods=["GET", "POST"]` y `allow_headers=["Accept", "Content-Type"]`.
- RF-4: CUANDO un navegador realice una solicitud cross-origin desde un origen permitido, EL SISTEMA responderá con las cabeceras CORS que correspondan a la configuración del middleware, incluidos los preflight `OPTIONS`.
- RF-5: CUANDO un navegador realice una solicitud cross-origin desde un origen no permitido, EL SISTEMA no autorizará ese origen mediante las cabeceras CORS de la respuesta.
- RF-6: EL SISTEMA aplicará el middleware CORS a las rutas de la API, incluidas `/health`, `/ask`, `/approve` y `/threads/{thread_id}/messages`, sin alterar sus contratos HTTP ni su autenticación.
- RF-7: EL SISTEMA documentará en `.env.example` el formato de `CORS_ORIGINS` y el ejemplo local de clase: `http://127.0.0.1:8000,http://localhost:8000,http://127.0.0.1:8501,http://localhost:3000`.
- RF-8: EL SISTEMA documentará en el README cómo configurar `CORS_ORIGINS` localmente y cómo introducir la variable en el entorno del servicio de la API en Render, permitiendo valores diferentes según el entorno.
- RF-9: CUANDO `CORS_ORIGINS` contenga espacios, comas repetidas o comas al inicio o al final, EL SISTEMA ignorará los elementos vacíos y conservará los elementos no vacíos tras recortar espacios.

## Requisitos no funcionales

- Seguridad: CORS no sustituye la autenticación `api_key` definida por las specs 013, 015 y 017.
- Configuración: los orígenes se obtienen del entorno mediante `config.py`; los valores pueden variar entre local, staging y producción.
- Claridad: la documentación explica que CORS limita el acceso que concede el navegador a una respuesta cross-origin; no es un mecanismo de autenticación ni de rechazo de solicitudes HTTP.

## Casos límite

- Variable ausente, vacía o con espacios: la lista de orígenes configurada queda vacía (RF-2).
- Elementos separados por comas con espacios o elementos vacíos: se recortan y se omiten los elementos vacíos (RF-1 y RF-9).
- Preflight del navegador: el middleware procesa la solicitud `OPTIONS` y autoriza los métodos y cabeceras configurados para la petición real (RF-3 y RF-4).
- Origen no permitido: el navegador no recibe autorización CORS para leer la respuesta; el middleware CORS no equivale a bloquear la llegada de la solicitud al servidor (RF-5).
- Solicitud de un cliente Python, incluido Streamlit: CORS no es aplicado por el navegador a esa llamada; la política del middleware permanece configurada en la API (RF-3 y RF-6).
- Solicitud a una ruta protegida desde un origen permitido: sigue necesitando `api_key` conforme a la spec 017 (RF-6).

## Fuera de alcance

- Cambiar los endpoints, métodos de negocio, autenticación, límites o contratos de las specs 013, 015 y 017.
- Configurar DNS, dominios personalizados, TLS o despliegues en Render.
- Añadir autenticación basada en cookies o sesiones del navegador.
- Cambiar el cliente HTTP de Streamlit o trasladar sus llamadas desde Python al navegador.
- Definir orígenes concretos de despliegues futuros distintos de los ejemplos locales; cada entorno introduce sus valores mediante configuración.

## Criterios de finalización

- Las verificaciones locales cubren la lectura de `CORS_ORIGINS`, la configuración del middleware, el preflight, un origen permitido y uno no permitido.
- Las verificaciones confirman que CORS no altera la autenticación ni los contratos de las rutas.
- `.env.example` y README documentan la configuración local y la variable que se debe introducir en Render, sin secretos reales.

## Dudas abiertas

- Ninguna.

## Decisiones de clarificación — 2026-11-18

- No se incorpora un cliente de navegador adicional al alcance; CORS se configura en `app.py` independientemente de que el cliente actual de Streamlit no lo necesite para sus llamadas HTTP desde Python.
- Se configura `allow_credentials=False` porque el contrato actual no usa cookies ni credenciales del navegador; la clave API se envía como parámetro `api_key`.
- Se permiten explícitamente los métodos `GET` y `POST`, y las cabeceras `Accept` y `Content-Type` que usa el cliente HTTP actual. El middleware procesa `OPTIONS` para los preflight.
- CORS permite al navegador acceder a respuestas cross-origin autorizadas; no rechaza por sí mismo una solicitud HTTP ni reemplaza `api_key`.
- `CORS_ORIGINS` es una lista separada por comas, leída mediante `config.py`; el valor puede cambiar en local, staging y producción. Si no hay elementos configurados, la lista queda vacía.
- `.env.example` conserva el ejemplo local de clase: `http://127.0.0.1:8000,http://localhost:8000,http://127.0.0.1:8501,http://localhost:3000`.
- El README documentará la variable `CORS_ORIGINS` en la configuración del servicio de API en Render. No se define ni presupone en esta spec un frontend desplegado allí.
- La carpeta e identificador de esta spec es 018.
