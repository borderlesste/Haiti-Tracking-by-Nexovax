# Verificación del navegador

Fecha: 2026-11-14. Herramienta: navegador integrado, mediante Computer Use. Son recorridos supervisados de la aplicación local; no constituyen una suite Playwright ejecutada en CI ni una prueba de hardware haitiano.

## Entornos y aislamiento

- Aplicación normal: `http://127.0.0.1:3000`, API local `8000`, sin lugares ni cuentas de QA insertados.
- QA: frontend `3001`, API `8001`, `APP_ENV=test`, base explícita `apps/api/.runtime/browser-qa.db`. Cuentas y ubicación ficticias, sin envío de correo externo. Fixture: `apps/api/tests/browser_fixture.py`. Ninguna credencial real se utilizó en los formularios.
- Stack de build: Compose `haiti-tracking-verify`, web `4174`, API `8002`, DB `55433`; recompilado tras los cambios de API y web. Proxy `/v1` y `/openapi.json`, CSP y `nosniff` comprobados.
- Capturas en `docs/evidence/`, excluidas de Git. No contienen claves API, enlaces con tokens ni contraseñas. Los enlaces privados de verificación solo se usaron en memoria/bandeja local.

## Recorridos y resultado observado

| Recorrido | Resultado y evidencia |
| --- | --- |
| Portada y mapa anónimos | Mapa Leaflet/OSM, atribución visible; no se solicita GPS al cargar. Cero lugares reales en base limpia, sin pines ni contadores inventados. Búsqueda vacía con alternativa de sugerencia. `home-750.jpg` |
| Catálogo | Departamentos y las 140 comunas del lote fijado cargan en filtros; paginación de la API, no lista de municipios ficticia. |
| Validación de acceso | Envío vacío muestra error junto al campo y enfoca el primer inválido. Login distingue errores de validación/credenciales/límite sin volcar respuestas técnicas. |
| Verificación de email | Cuenta sintética registrada mediante API local, correo generado en outbox. Apertura de `/verificar#token=…`, confirmación y redirección a `/acceso?verified=1` con éxito visible. El token desaparece de la URL. No demuestra entrega Resend real. |
| Autorización administrativa | Cuenta de colaborador autenticada recibe pantalla de acceso denegado en `/admin`. `admin-forbidden.jpg`. Controles del servidor comprobados adicionalmente por tests negativos. |
| GPS denegado | Captura activada por botón. El entorno del navegador no concedió posición positiva; se mostró alternativa manual/error. Enviar como presencial sin GPS fue bloqueado. La prueba positiva GPS se ejecutó por API con coordenadas sintéticas, no por hardware/navegador. |
| Borrador sin calle/número/GPS | Guardado visible en contribuciones como borrador, sin código publicado. Edición carga el mismo registro/versionado y guarda sin crear otra propuesta. `draft-saved.jpg`. No se certificó una sesión larga offline. |
| Claves de desarrollador | Aplicación de prueba creada; reautenticación para emitir clave; secreto mostrado una vez, comprobado sin imprimirlo. Escape cancela revocación y restaura foco. Confirmación revoca y desactiva acción. `key-revoked.jpg`. |
| Moderación con MFA | Operador sintético inicia sesión con OTP válido. Propuesta enviada mediante API aparece; borradores ajenos no aparecen. Evidencia privada visible solo al abrir fotos. Aprobación con motivo muestra Aprobado, código público y foco devuelto al contenido. |
| Publicación | La ficha aprobada aparece en mapa y detalle con código `HT-NXV-000001`. Aviso explícito de demostración y referencia que impide usarla para navegar. `public-demo-detail.jpg`. |
| Reporte y privacidad | Reporte de categoría privacidad recibido; aparece en bandeja. Retirada con motivo cierra reporte. Código antes público muestra «No encontramos este lugar público». `privacy-hidden.jpg`. No se eliminó información de producción. |
| Auditoría | Tabla del administrador contiene `moderation.approve` y `location.hidden`; paginación/estados vacíos visibles. `admin-audit.jpg`. |
| Idiomas | Cambio a francés en portada y a kreyòl en acceso/registro observado. Test web comprueba todas las claves literales en los tres idiomas. Revisión de calidad lingüística por hablantes nativos pendiente. |

## Correcciones surgidas de QA

- Se extrajeron contextos React estables para evitar el fallo de encabezado durante HMR.
- Filtros vacíos ya no envían un tipo inválido a la API.
- Dialog nativo lleva título accesible, Cerrar localizado y restauración de foco al disparador o al contenido cuando el disparador desaparece.
- Botón ocupado conserva tamaño/nombre; errores del formulario aparecen asociados a campos.
- La edición de borrador restaura la declaración de fuente. Una carga de fotos parcialmente fallida permite reintentar sin duplicar la propuesta.
- Verificación usa fragmento y limpia el token al terminar; el OTP precede al botón de acceso.

## Diseño y límites

La referencia es un collage de tres pantallas, no una sola página. Se comparan por separado la portada, registro y contribución en `design-qa.md`. Los tamaños CSS se comprueban en DOM antes de llamar móvil a una captura. La captura del proveedor no siempre sigue una emulación CDP, por lo que para tamaños estrechos se usa `Page.captureScreenshot` y se guarda la dimensión real.

No se han probado lectores de pantalla, teclado físico en todos los flujos, cámara/teléfono real, GPS en Haití, entrega externa de correo, facturación, carga sostenida ni recuperación de objetos S3 reales. Los pagos y domicilios privados están fuera del MVP por el documento maestro. Los resultados de API y build son evidencia complementaria; no sustituyen estas comprobaciones operativas.

## Red limitada y teclado

En el build Docker a 390×844 CSS px, caché desactivada, 150 ms de latencia, 187.500 B/s de bajada y 75.000 B/s de subida, el mapa llegó al estado vacío listo en 4.894 ms. Tras activar gzip para JavaScript/CSS en Nginx se observó 2.589 ms en otra navegación con la misma configuración. Son dos observaciones locales, no p95 ni SLA. Tamaños de transferencia en `transfer-check.json`. No se habilitó gzip para las respuestas JSON privadas.

El campo de archivo continúa siendo un input nativo: al enfocar mediante teclado su área muestra contorno visible (`focusedType=file`, `outlineStyle=solid`). El formulario a 390 px tuvo `scrollWidth=380` frente a `innerWidth=390`, sin desbordamiento horizontal. Registro a 330 px: documento de 320 px. Los overrides de GPS/red/viewport se retiran al finalizar.

## Recuperación de subida interrumpida

En la base QA se seleccionó `flag.png` público mediante el input/selector nativo del navegador. Se bloquearon únicamente las solicitudes de fotos con CDP y se guardó un borrador sintético. La UI confirmó que la propuesta estaba guardada y ofreció reintento; luego se retiró el bloqueo y el reintento volvió a Mis contribuciones. Consulta SQLite de solo lectura: exactamente un borrador para ese nombre y una evidencia privada. No se creó otra propuesta al reintentar. El bloqueo de red se retiró y no se usaron archivos personales. Captura local `photo-recovery.jpg` (no versionada).


## Ampliación final — 2026-11-15

Sobre QA separado (`3001`/`8001`, cuentas sintéticas):

- Recibo con ID, fecha y estado visible. Se retiró el borrador sintético anterior, se conservó en el listado como Retirado y desaparecieron sus controles de edición/retiro; el API rechaza aprobación posterior.
- A 390 px no hubo desbordamiento horizontal (`innerWidth=390`, documento=380). Se guardó un nuevo borrador sin GPS/calle/número con dos alias y fuente comunitaria. Al reabrir conservó los alias, la fuente y `1re Section St Martin` después de cargar el catálogo.
- Se agregaron tres fichas mediante el comando explícito seed-demo solo a QA. El detalle de Pharmacie Démo muestra claramente que es ficticia y no verificada. Su diálogo QR cargó, copiar enlace cambió a Copiado y Escape cerró/restauró foco en Compartir ficha y QR. El QR también se decodifica independientemente en la suite API.
- Login administrativo con MFA del fixture. Resumen: tres lugares demo y recuentos reales por territorio, sin porcentaje nacional. Editor territorial rechazó repetir versión y guardó una versión marcada QA-only conservando nombre y geografía; el filtro `subject_id=HT05&action=territory.updated` mostró un único evento. No se cambió el catálogo del entorno normal.
- El filtro de auditoría y controles nuevos se revisaron en francés y kreyòl. No hubo errores de consola en este recorrido. Se cerró sesión y se retiró el override de viewport de QA.

Evidencias adicionales locales (ignoradas por Git): `docs/evidence/withdraw-390.png`, `docs/evidence/qr-share-390.png`. El resumen final con envío GPS positivo continúa pendiente de un navegador con permiso/medición física: no se simula como comprobación de campo. Las pruebas backend de señal válida, señal de 150 m, separación pin/observación y corroboración sí pasan.

## Suite Playwright autorizada

Tras la autorización expresa del propietario se ejecutó Chromium con perfil de prueba separado. Los cinco casos de `tests/e2e/critical.spec.mjs` pasaron (66,02 s). El resumen ahora cuenta con evidencia automática positiva mediante GPS ficticio, además de denegación, borrador/retiro y búsqueda/QR. Se consultó la base de ese run de forma independiente. La configuración de CUA fue retirada y su pestaña QA cerrada. No se obtuvieron coordenadas físicas ni se declaró una presencia verificada. WEB-E2E.md y web-e2e-results.json contienen alcance y pendientes.
