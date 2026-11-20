# Validación — Spec 020

> Fecha: 2026-11-20 · Resultado de `python -m pytest tests/test_docker_artifact.py -q`: 3 passed / 0 failed

| RF | Cómo se comprueba | Test o comprobación manual | Resultado |
|---|---|---|---|
| RF-1 | Automático y manual | `tests/test_docker_artifact.py::test_dockerfile_instala_y_arranca_api`; `docker build -t madridrumbo-api:local .` | ✅ |
| RF-2 | Automático y manual | `tests/test_docker_artifact.py::test_dockerfile_publica_y_resuelve_port`; contenedor arrancado con `PORT=8000` | ✅ |
| RF-3 | Manual | PostgreSQL 16 temporal en `madridrumbo-test-net`; la API creó las tablas durante el lifespan | ✅ |
| RF-4 | Manual | `GET http://127.0.0.1:18000/health` → `{"estado":"ok","modo":"simulado"}` | ✅ |
| RF-5 | Manual | `POST /ask?api_key=test-api-key` → respuesta simulada con `thread_id`, `done`, `pendiente_hitl`, `plan` y `error` | ✅ |
| RF-6 | Manual | `GET /threads/{thread_id}/messages?api_key=test-api-key` → mensaje `user` y `assistant` en orden 1–2 | ✅ |
| RF-7 | Automático | `tests/test_docker_artifact.py::test_dockerignore_excluye_secretos_y_artifactos` | ✅ |

## Criterios de finalización

- [x] Los tres tests estáticos del artefacto pasan.
- [x] La imagen Docker se construye correctamente.
- [x] La API arranca conectada a PostgreSQL temporal.
- [x] Se valida salud, pregunta protegida e historial persistido.
- [x] No se configura Render ni otro hosting.

## Fuera de spec

Nada observable fuera de los comportamientos especificados. La imagen conserva
también `front.py` porque forma parte del repositorio, pero esta spec solo arranca
la API mediante `app:app`.

## Veredicto

**Sí** — RF-1 a RF-7 están cubiertos por tests estáticos y un smoke test Docker
con PostgreSQL temporal; hosting queda explícitamente fuera de alcance.
