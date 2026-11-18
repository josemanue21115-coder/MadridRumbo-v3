# Spec 019 — Logs de peticiones protegidas

> Estado: Aprobada · Fecha: 2026-11-18

## Contexto y objetivo

La API ya autentica y limita sus rutas protegidas, aplica un tiempo máximo a los turnos y devuelve errores definidos para fallos conocidos e inesperados (spec 017). El equipo necesita poder seguir el resultado y la duración de cada petición protegida sin exponer claves, secretos ni el contenido privado de las conversaciones. Esta spec establece los datos mínimos de esos registros y su comportamiento cuando la petición falla o no tiene un identificador de conversación.

## Usuarios / actores

- Equipo que opera y diagnostica la API.
- Clientes que consumen `/ask`, `/approve` y el historial protegido.
- Personas usuarias cuyas preguntas y respuestas no deben quedar expuestas en los logs.

## Historias de usuario

- H1: Como equipo quiero relacionar el resultado y duración de cada petición protegida para diagnosticar fallos y latencia.
- H2: Como persona usuaria quiero que los logs permitan diagnosticar la API sin registrar mis preguntas o respuestas ni secretos.

## Requisitos funcionales (criterios de aceptación en EARS)

- RF-1: CUANDO termine el procesamiento de una petición dirigida a una ruta protegida, EL SISTEMA emitirá exactamente un registro de petición con método HTTP, ruta concreta, `thread_id`, duración en milisegundos y código HTTP final si se envió una respuesta.
- RF-2: CUANDO una petición protegida no tenga un `thread_id` disponible, EL SISTEMA registrará `thread_id` como `null`.
- RF-3: SI una petición protegida falla antes de que el sistema pueda obtener su `thread_id`, ENTONCES EL SISTEMA registrará igualmente la petición y `thread_id` como `null`.
- RF-4: EL SISTEMA registrará la ruta concreta solicitada sin parámetros de query, valores de `api_key` ni otros datos de query.
- RF-5: EL SISTEMA no registrará `API_KEY`, claves de proveedores o del LLM, `DATABASE_URL` ni otros secretos de configuración.
- RF-6: EL SISTEMA no registrará ningún fragmento de texto de las preguntas o respuestas conversacionales.
- RF-7: CUANDO una petición protegida termine con un error HTTP, EL SISTEMA registrará su código HTTP final, incluidos 401, 429, 503, 504 y los errores inesperados 500.
- RF-8: SI una petición protegida falla de forma inesperada, ENTONCES EL SISTEMA mantendrá el mensaje genérico al cliente definido por la spec 013 y registrará el resultado sin incluir detalles sensibles de la excepción.
- RF-9: EL SISTEMA permitirá comprobar mediante pruebas locales que cada petición dirigida a una ruta protegida, incluidas las que fallan durante la validación de entrada, genera un registro con método, ruta, `thread_id`, duración en milisegundos y código HTTP cuando se haya enviado una respuesta.
- RF-10: EL SISTEMA permitirá comprobar mediante pruebas locales que los registros de éxito y error no contienen secretos ni ningún fragmento de texto conversacional.

## Requisitos no funcionales

- Seguridad: los registros no contendrán credenciales, secretos, cuerpos completos ni contenido conversacional completo.
- Observabilidad: la duración se expresará en milisegundos y el código reflejará el estado HTTP final que recibió el cliente.
- Compatibilidad: los registros no alterarán los contratos HTTP, la autenticación, el control de peticiones ni las respuestas definidos por las specs 013 y 017.

## Casos límite

- `POST /ask` sin identificador de conversación: el registro incluye `thread_id: null` si no hay identificador disponible al terminar (RF-2).
- `POST /ask` con creación de identificador nuevo: se registra el `thread_id` resultante cuando esté disponible (RF-1).
- `POST /approve` o lectura del historial con identificador disponible en la ruta: se registra dicho identificador (RF-1).
- Rechazo de autenticación, exceso del límite o timeout: se registra el código HTTP final (RF-7).
- Validación, fallo temprano u otro error antes de obtener el identificador: se emite el registro con `thread_id: null` (RF-3).
- Excepción inesperada: se registra el resultado 500 sin propagar su detalle al cliente ni incluir detalles sensibles en el registro (RF-8).
- Fallo antes de enviar una respuesta HTTP: el registro conserva los campos disponibles y registra `null` en el código HTTP, porque no se envió ningún código al cliente (RF-1).
- Fallo durante la validación de entrada en una ruta protegida: se genera igualmente un registro (RF-9).
- La ruta o petición incluye query parameters: no se registran esos parámetros ni sus valores (RF-4).

## Fuera de alcance

- Incorporar una plataforma externa de observabilidad, almacenamiento centralizado, paneles o alertas.
- Registrar métricas agregadas, trazas distribuidas o el historial de conversación.
- Cambiar los códigos, mensajes o contratos HTTP de las specs 013 y 017.
- Registrar preguntas, respuestas, cuerpos completos, claves o credenciales con el fin de reproducir una petición.

## Criterios de finalización

- Las verificaciones locales comprueban los cinco campos obligatorios para una petición protegida correcta y para errores representativos, y el código HTTP es `null` si no se envió respuesta.
- Se verifica el comportamiento con `thread_id` presente, ausente y no disponible por fallo temprano.
- Se comprueba el registro de 401, 429, 503, 504 y 500 sin alterar el mensaje genérico del error inesperado al cliente.
- Las pruebas inspeccionan todos los logs del servicio que puedan capturar la petición y confirman que no contienen `api_key`, secretos de configuración ni texto de preguntas o respuestas.

## Dudas abiertas

- Ninguna.

## Decisiones de clarificación — 2026-11-18

- Cada intento a una ruta protegida genera un solo registro, incluso cuando acaba en una respuesta de error.
- Cuando el identificador de conversación no existe o no puede recuperarse antes del fallo, se registra explícitamente como `null`; no se omite el campo.
- La ruta registrada es la ruta concreta solicitada y no incluye query parameters, para evitar que `api_key` u otros valores de query aparezcan en logs.
- Ningún log del servicio registrará texto conversacional, ni completo ni parcial.
- Si no se envió respuesta HTTP, el campo del código se registra como `null`; si un error inesperado se convierte en una respuesta HTTP 500, se registra 500.
- Los errores inesperados conservan el mensaje genérico de la spec 013; sus detalles sensibles no se incluyen en el registro de petición.
- La comprobación de seguridad inspecciona todos los logs del servicio que puedan capturar la petición, incluidos los de la aplicación y del servidor HTTP, para impedir que se expongan parámetros, secretos o texto conversacional.
