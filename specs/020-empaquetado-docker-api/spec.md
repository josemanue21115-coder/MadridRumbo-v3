# Spec 020 — Empaquetado Docker de la API

> Estado: Aprobada · Fecha: 2026-11-20

## Contexto y objetivo

La API FastAPI y la persistencia PostgreSQL ya están integradas, pero el proyecto
no tiene un artefacto reproducible para arrancar la API fuera del entorno local.
Esta spec define una imagen Docker local, segura y verificable para la API, junto
con una prueba de integración contra PostgreSQL temporal.

## Usuarios / actores

- El equipo que necesita construir y ejecutar la API de forma reproducible.
- La persona que revisa la Pull Request y valida el flujo API–PostgreSQL.

## Historias de usuario

- H1: Como integrante del equipo quiero construir una imagen Docker de MadridRumbo para arrancar la API con el mismo comando en distintos entornos.
- H2: Como responsable de integración quiero comprobar `/health`, `/ask` y el historial contra PostgreSQL antes de fusionar la PR.

## Requisitos funcionales (criterios de aceptación en EARS)

- RF-1: CUANDO se ejecuta `docker build -t madridrumbo-api:local .`, EL SISTEMA construye una imagen sin errores usando el `Dockerfile` de la raíz.
- RF-2: CUANDO se arranca la imagen con `DATABASE_URL` válida, EL SISTEMA ejecuta `uvicorn app:app` escuchando en `0.0.0.0` y usa `PORT` o `8000` por defecto.
- RF-3: CUANDO el contenedor arranca con PostgreSQL accesible, EL SISTEMA crea las tablas necesarias antes de servir peticiones.
- RF-4: CUANDO se consulta `GET /health`, EL SISTEMA responde HTTP 200 con el estado del servicio.
- RF-5: CUANDO se envía una pregunta válida a `POST /ask` en modo simulado con la clave configurada, EL SISTEMA devuelve el contrato público de la API.
- RF-6: CUANDO termina correctamente un turno, EL SISTEMA guarda la pregunta y la respuesta en PostgreSQL y `GET /threads/{thread_id}/messages` las devuelve en orden.
- RF-7: CUANDO se construye la imagen, EL SISTEMA no incorpora `.env`, credenciales, tests, documentación ni artefactos generados excluidos por `.dockerignore`.

## Requisitos no funcionales

- La imagen debe usar Python 3.11 slim y no instalar dependencias no utilizadas que arrastren runtimes CUDA.
- Las credenciales se proporcionan mediante variables de entorno y no se almacenan en la imagen ni en Git.
- La validación de integración debe usar un PostgreSQL temporal y el modo simulado para no consumir APIs externas.

## Casos límite

- Sin `DATABASE_URL`, el arranque debe fallar con el error controlado de configuración de PostgreSQL (RF-2, RF-3).
- Si PostgreSQL todavía no acepta conexiones, el contenedor no debe declararse operativo (RF-3, RF-4).
- Una pregunta protegida sin API key debe rechazarse por la seguridad existente; no forma parte de una prueba de credenciales reales (RF-5).

## Fuera de alcance

- Render, cualquier otro proveedor de hosting y configuración de despliegue público.
- Contenedor independiente para Streamlit.
- Migraciones de esquema, alta disponibilidad y rehidratación de planes pendientes.
- Ejecución de la suite completa dentro de Docker.

## Criterios de finalización

- `tests/test_docker_artifact.py` pasa.
- La imagen se construye correctamente.
- Un PostgreSQL temporal y la API arrancan en una red Docker.
- Pasan las comprobaciones manuales de `/health`, `/ask` e historial.

## Dudas abiertas

- Ninguna para esta iteración. La decisión de hosting queda para una spec posterior.
