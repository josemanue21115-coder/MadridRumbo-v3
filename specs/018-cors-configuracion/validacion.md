# Validación — Spec 018

> Fecha: 2026-11-18 · Resultado de `python -m pytest`: 1391 passed / 0 failed / 27 skipped

| RF | Cómo se comprueba | Test o comprobación manual | Resultado |
|---|---|---|---|
| RF-1 | Automático | `tests/test_api_cors.py::test_config_cors_separa_origenes` | ✅ |
| RF-2 | Automático | `tests/test_api_cors.py::test_config_cors_ausente_o_vacia` | ✅ |
| RF-3 | Automático | `tests/test_api_cors.py::test_middleware_cors_configurado` | ✅ |
| RF-4 | Automático | `tests/test_api_cors.py::test_preflight_permitido_devuelve_cabeceras_cors` | ✅ |
| RF-5 | Automático | `tests/test_api_cors.py::test_origen_no_permitido_no_recibe_cabecera_cors` | ✅ |
| RF-6 | Automático | `tests/test_api_cors.py::test_preflight_cors_en_rutas_de_api`; la suite completa comprueba que no cambian autenticación ni contratos HTTP. | ✅ |
| RF-7 | Automático | `tests/test_api_cors.py::test_env_example_documenta_cors` | ✅ |
| RF-8 | Automático | `tests/test_api_cors.py::test_readme_documenta_cors_local_y_render` | ✅ |
| RF-9 | Automático | `tests/test_api_cors.py::test_config_cors_recorta_espacios_e_ignora_vacios` | ✅ |

Las pruebas usan procesos aislados con `load_dotenv()` sustituido y `TestClient`; no leen `.env`, no inician Uvicorn ni llaman a LLM o servicios externos. Las solicitudes de middleware se limitan a `/health` y preflight, que no ejecutan las operaciones protegidas.

## Criterios de finalización

- [x] La configuración local y el middleware se verifican para valores ausentes/vacíos, listas, orígenes permitidos y no permitidos, y preflight.
- [x] La suite completa confirma que la política no cambia autenticación ni contratos HTTP: 1391 pasadas, 0 fallidas y 27 omitidas.
- [x] `.env.example` y README documentan el formato y la configuración local y en el servicio API de Render; la plantilla contiene valores de ejemplo, sin secretos reales.

## Fuera de spec

Nada.

## Veredicto

**Sí** — los RF-1 a RF-9 tienen comprobación satisfactoria y los criterios de finalización se cumplen.
