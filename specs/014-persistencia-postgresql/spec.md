# SPEC-014 — Persistencia de conversaciones con PostgreSQL

**Proyecto:** MadridRumbo-v3
**Project Break:** 3 — MLOps
**Responsable:** José Manuel — PostgreSQL
**Rama:** `feature/postgres-historial`
**PR:** #1
**Estado:** Validada — 15/11/2026

## 1. Contexto

MadridRumbo necesita almacenar las conversaciones del usuario en una base de datos persistente, independientemente de la memoria temporal del agente LangGraph.

## 2. Objetivo

Implementar una capa de persistencia PostgreSQL que permita guardar y recuperar conversaciones y mensajes, manteniendo su orden, separación e integridad.

## 3. Requisitos funcionales

- **RF-01:** Definir el modelo `Conversation`, identificado mediante `thread_id`.
- **RF-02:** Definir el modelo `Message`, con identificador, conversación, rol, contenido y fecha de creación.
- **RF-03:** Guardar conjuntamente la pregunta y la respuesta de un turno finalizado.
- **RF-04:** Recuperar los mensajes de una conversación ordenados por `Message.id`.
- **RF-05:** Configurar PostgreSQL mediante `DATABASE_URL`, sin credenciales reales en el repositorio.
- **RF-06:** Validar las entradas y revertir las transacciones fallidas.

## 4. Criterios de aceptación

- **CA-01:** Crear correctamente las tablas `conversations` y `messages` en PostgreSQL.
- **CA-02:** Guardar una pregunta y una respuesta por turno.
- **CA-03:** Permitir varios turnos por conversación.
- **CA-04:** Recuperar mensajes en orden de inserción.
- **CA-05:** Mantener separados los mensajes de distintas conversaciones.
- **CA-06:** Rechazar identificadores, preguntas y respuestas vacíos.
- **CA-07:** Admitir `DATABASE_URL` y normalizar `postgres://` a `postgresql://`.
- **CA-08:** No almacenar credenciales reales en los archivos versionados.
- **CA-09:** Superar las pruebas unitarias.
- **CA-10:** Superar una prueba de integración real con PostgreSQL.
- **CA-11:** Garantizar que una escritura fallida no deja un turno incompleto.
- **CA-12:** Recuperar mensajes después de cerrar una sesión y abrir otra.

## 5. Fuera del alcance

- Integración de endpoints FastAPI.
- Persistencia de checkpoints de LangGraph.
- Despliegue en Render.
- Incorporación de Docker al repositorio.
- Migraciones de base de datos.

Docker se utilizará exclusivamente como entorno temporal de pruebas.

## 6. Condición de finalización

La SPEC-014 se considerará completada cuando los doce criterios de aceptación estén verificados y sus resultados documentados en `validacion.md`.
