# Tareas — Spec 020

> Tareas documentadas para el empaquetado Docker y su validación. Marca `[x]` al terminar.

- [x] T1. Definir el contrato SDD del empaquetado local, dejando Render y el hosting fuera de alcance. (RF-1 a RF-7)
      Hecho cuando: `spec.md` y `plan.md` describen el comportamiento verificable y sus límites.
- [x] T2. Añadir primero las pruebas estáticas de los artefactos Docker. (RF-1, RF-2, RF-7)
      Hecho cuando: `python -m pytest tests/test_docker_artifact.py -q` pasa sin daemon Docker.
- [x] T3. Crear `Dockerfile` y `.dockerignore`, y ajustar dependencias para evitar `sentence-transformers` no usado. (RF-1, RF-2, RF-7)
      Hecho cuando: `docker build -t madridrumbo-api:local .` termina correctamente.
- [x] T4. Ejecutar el smoke test de API contra PostgreSQL temporal y modo simulado. (RF-3 a RF-6)
      Hecho cuando: `/health`, `/ask` y `/threads/{thread_id}/messages` responden correctamente.
- [x] T5. Actualizar README y documentar la evidencia de validación. (Todos)
      Hecho cuando: `validacion.md` contiene el resultado de cada RF y el alcance excluye hosting.
