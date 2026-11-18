# SPEC-014 — Plan técnico

**Proyecto:** MadridRumbo-v3
**PR:** #1 — Persistencia PostgreSQL
**Rama:** `feature/postgres-historial`

## 1. Arquitectura

Se utilizará SQLModel para gestionar la persistencia de conversaciones en PostgreSQL.

Para RF-05 y CA-07, las URLs `postgres://` y `postgresql://` usarán explícitamente
`psycopg2`, el controlador ya declarado en `requirements.txt`. También se admitirá
`postgresql+psycopg2://`; se conserva el soporte existente de `postgresql+psycopg://`
cuando el entorno tenga instalado ese controlador. Así se evita depender del
controlador por defecto de la versión instalada de SQLAlchemy.

La capa de persistencia será independiente de los endpoints FastAPI y del mecanismo de checkpoints de LangGraph.

## 2. Componentes

| Archivo | Responsabilidad |
|---|---|
| `src/models.py` | Definir los modelos `Conversation` y `Message`. |
| `src/db.py` | Gestionar el motor, las sesiones y la creación de tablas. |
| `src/history.py` | Guardar turnos y recuperar el historial. |
| `config.py` | Leer la variable `DATABASE_URL`. |
| `.env.example` | Documentar la configuración sin credenciales reales. |
| `requirements.txt` | Declarar las dependencias SQLModel y PostgreSQL. |
| `tests/test_history.py` | Probar el comportamiento del historial. |

## 3. Implementación

1. Crear los modelos de conversación y mensaje.
2. Configurar la conexión PostgreSQL.
3. Implementar `save_closed_turn()`.
4. Implementar `get_thread_messages()`.
5. Incorporar validaciones y rollback.
6. Ejecutar pruebas unitarias.
7. Validar la integración con PostgreSQL real.

## 4. Estrategia de pruebas

### Pruebas unitarias

Utilizar SQLite en memoria para comprobar la lógica del historial de manera aislada.

### Pruebas de integración

Utilizar PostgreSQL en un contenedor Docker temporal para comprobar:

- Conexión y creación de tablas.
- Escritura y recuperación de mensajes.
- Separación de conversaciones.
- Persistencia entre sesiones.
- Rollback ante errores.

El contenedor será exclusivamente de pruebas. No se incorporarán archivos de Docker al repositorio en esta SPEC.

## 5. Cierre

Registrar los resultados en `validacion.md` y verificar los doce criterios de aceptación definidos en `spec.md`.
