# Plan técnico — Spec 020

> Basado en `spec.md` (estado: Aprobada). No añade comportamiento que no esté en la spec.

## Archivos afectados

| Archivo | Crear / Modificar | Qué cambia | RF |
|---|---|---|---|
| `Dockerfile` | Crear | Imagen Python 3.11 slim e inicio de `app:app` con `PORT`. | RF-1, RF-2 |
| `.dockerignore` | Crear | Excluye secretos, tests, documentación y artefactos locales. | RF-7 |
| `requirements.txt` | Modificar | Mantiene dependencias necesarias para API, RAG y PostgreSQL; elimina `sentence-transformers`, no usado por el código. | RF-1, RNF |
| `README.md` | Modificar | Documenta la validación local y deja hosting fuera de alcance. | RF-1 a RF-6 |
| `tests/test_docker_artifact.py` | Crear | Comprueba estáticamente los artefactos Docker sin daemon ni red. | RF-1, RF-2, RF-7 |
| `specs/020-empaquetado-docker-api/` | Crear | Spec, plan, tareas y validación SDD. | Todos |

## Contrato

La imagen recibe por entorno `DATABASE_URL`, `API_KEY`, `MADRIDRUMBO_GRAFO` y las
claves de proveedores que necesite el agente. Publica el puerto interno 8000 y
permite sustituirlo mediante `PORT`. El contrato HTTP de `/health`, `/ask` y
`/threads/{thread_id}/messages` no cambia.

## Lógica clave

```text
docker build → instala requirements.txt → copia código
docker run + DATABASE_URL → uvicorn app:app
                         → lifespan crea tablas
                         → /health, /ask, /messages
```

## Decisiones técnicas

| Decisión | Alternativa descartada | Por qué |
|---|---|---|
| `python:3.11-slim` | Imagen completa de Python | Reduce tamaño sin cambiar el runtime soportado. |
| Un `Dockerfile` para la API | Configurar Render o varios servicios | Hosting queda fuera de esta spec; la API es el entregable actual. |
| Eliminar `sentence-transformers` | Instalar PyTorch/CUDA en la imagen | El código usa embeddings Gemini/OpenAI y no importa esa librería; la dependencia hacía crecer innecesariamente la imagen. |
| PostgreSQL temporal para smoke test | Usar la base de datos del equipo | Aísla la validación y evita tocar datos persistentes. |

## Estrategia de tests

- Tests estáticos para el contenido y exclusiones del Dockerfile.
- `docker build` para validar el empaquetado real.
- Smoke test manual con PostgreSQL temporal, modo simulado, `/health`, `/ask` y recuperación del historial.

## Riesgos

- El primer arranque requiere descargar dependencias y puede ser lento.
- La API no arranca sin PostgreSQL, por diseño del contrato de persistencia.
- El contenedor no incluye una base de datos persistente propia.

## Trazabilidad

| RF | Parte del plan | Test |
|---|---|---|
| RF-1 | Dockerfile y requirements | `tests/test_docker_artifact.py::test_dockerfile_instala_y_arranca_api` + `docker build` |
| RF-2 | CMD y `PORT` | `tests/test_docker_artifact.py::test_dockerfile_publica_y_resuelve_port` |
| RF-3 | Smoke test con PostgreSQL | Comprobación manual de arranque |
| RF-4 | Endpoint de salud | `GET /health` |
| RF-5 | API simulada protegida | `POST /ask?api_key=...` |
| RF-6 | Persistencia | `GET /threads/{thread_id}/messages` |
| RF-7 | `.dockerignore` | `tests/test_docker_artifact.py::test_dockerignore_excluye_secretos_y_artifactos` |
