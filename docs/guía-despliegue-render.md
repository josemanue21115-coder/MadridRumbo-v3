# Guía: API en Render y Streamlit local

## Desplegar la API

1. En Render, crea3 un **Web Service** desde el repositorio de MadridRumbo y selecciona3 **Docker**. Usa el `Dockerfile` de la raíz y deja3 el comando de inicio sin sobrescribir.
2. Crear una base de datos Postgre en la misma región que el Web Service.
3. En el entorno del Web Service configurar:

   | Variable | Valor |
   |---|---|
   | `DATABASE_URL` | Internal Database URL de Render Postgres |
   | `API_KEY` | Una clave larga y aleatoria |
   | `MADRIDRUMBO_GRAFO` | `falso` para usar el modo simulado |

   Pegar la URL completa, sin comillas. La aplicación admite los esquemas `postgres://` y `postgresql://`.

4. Configurar el health check del servicio como `/health` y desplegar.
5. Comprobar `https://<servicio>.onrender.com/health`. Debe responder con `"estado":"ok"`.

## Usar la API desde Streamlit local

En el `.env` que usa Streamlit, configurar la URL pública de la API y la misma clave:

```env
API_BASE_URL=https://<servicio>.onrender.com
API_KEY=<la misma clave configurada en Render>
```

Iniciar Streamlit con `streamlit run front.py` y envíar una pregunta. No publicar ni añadir la clave al repositorio. No hace falta configurar CORS para este cliente: sus llamadas a la API se realizan desde Python.

## Si la API no arranca

- Confirmar que `DATABASE_URL` es la Internal Database URL completa y que base y servicio están en la misma región.
- Si aparece `Se requiere PostgreSQL en desarrollo y producción`, revisar que la URL empiece por `postgres://` o `postgresql://` y no tenga comillas.