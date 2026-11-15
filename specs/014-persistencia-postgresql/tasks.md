# SPEC-014 — Tareas de implementación

**Proyecto:** MadridRumbo-v3
**Rama:** `feature/postgres-historial`
**PR:** #1 — Persistencia PostgreSQL

## T01 — Modelos de datos

- [x] Crear modelo `Conversation`.
- [x] Crear modelo `Message`.
- [x] Asociar mensajes a conversaciones mediante `thread_id`.

## T02 — Configuración de PostgreSQL

- [x] Incorporar la variable `DATABASE_URL`.
- [x] Normalizar URLs con prefijo `postgres://`.
- [x] Implementar el motor de base de datos.
- [x] Implementar la gestión de sesiones.
- [x] Añadir las dependencias SQLModel y PostgreSQL.

## T03 — Historial de conversaciones

- [x] Implementar `save_closed_turn()`.
- [x] Implementar `get_thread_messages()`.
- [x] Validar entradas vacías.
- [x] Incorporar rollback ante errores.

## T04 — Pruebas unitarias

- [x] Crear pruebas aisladas con SQLite.
- [x] Repetir las pruebas y registrar sus resultados.

## T05 — Integración real con PostgreSQL

- [x] Comprobar Docker.
- [x] Levantar un contenedor temporal PostgreSQL.
- [x] Verificar conexión y creación de tablas.
- [x] Guardar y recuperar mensajes.
- [x] Comprobar separación de conversaciones.
- [x] Comprobar persistencia entre sesiones y procesos.
- [x] Verificar rollback y atomicidad en conversaciones nuevas y existentes.
- [x] Eliminar el entorno temporal de pruebas.

## T06 — Documentación y cierre

- [x] Redactar `spec.md`.
- [x] Redactar `plan.md`.
- [x] Preparar `tasks.md`.
- [x] Completar `validacion.md` con evidencias.
- [x] Revisar los doce criterios de aceptación.
- [ ] Incorporar la documentación a la PR #1.
- [x] Revisar la PR antes de fusionarla con `develop`.

La revisión no incluye la fusión. La PR permanece abierta para la decisión del responsable.
