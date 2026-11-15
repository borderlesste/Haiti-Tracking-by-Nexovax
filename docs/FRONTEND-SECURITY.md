# Revisión de seguridad del frontend

Fecha: 2026-11-15. Alcance: `apps/web/src/` y `apps/web/worker/index.js`, sobre `main`. El inventario SHA-256 del código revisado está en `frontend-security-audit.json`. Se revisaron 14 archivos, trazando entradas, destinos de navegación, solicitudes y puntos de renderizado; las traducciones y CSS se inspeccionaron como contenido estático.

No se confirmó una vulnerabilidad explotable crítica, alta, media o baja en este alcance mediante la revisión manual. Esto describe el código y las rutas examinadas; no certifica todo el sistema ni demuestra ausencia absoluta de vulnerabilidades.

## Evidencia de la revisión manual

| Superficie | Evidencia y conclusión |
| --- | --- |
| DOM XSS | No se encontraron usos de `dangerouslySetInnerHTML`, `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval` o `new Function` en el alcance. Datos de API, nombres de archivos, errores y JSON se renderizan como texto React. En `Map.jsx:66`, el código se codifica en una ruta fija; `:67` asigna el nombre a `textContent` y `:68` entrega ese nodo al popup Leaflet. La atribución HTML del mapa es una cadena fija. |
| URLs y redirecciones | `Auth.jsx:94` pasa `next` por `validNext`, definido en `api.js:42`, que limita la navegación a rutas con una sola barra inicial y rechaza barras inversas y controles ASCII. Las búsquedas y códigos públicos usan `URLSearchParams` o `encodeURIComponent`. El enlace externo `Workspace.jsx:884` procede del catálogo territorial; el contrato del servidor lo restringe a HTTPS y el enlace usa `rel=noreferrer`. No se encontró una ruta de entrada pública que pudiera convertirlo en un esquema ejecutable. |
| Sesiones, claves y CSRF | `api.js:16` obtiene CSRF del mismo origen y `:20` lo adjunta a las mutaciones; las solicitudes usan `credentials: same-origin`. El frontend no lee ni escribe `document.cookie`, no guarda contraseñas ni claves en almacenamiento persistente y no contiene credenciales privadas fijas. La clave recién emitida vive en estado React en `Workspace.jsx:336/455`, se muestra una vez y puede ocultarse. `localStorage` solo se usa para el idioma (`App.jsx:26/92`). La validez de la sesión, los atributos de cookie y los permisos de los objetos siguen siendo responsabilidad del backend, cubierto por el informe general separado. |
| Tokens de correo | `App.jsx:40` lee el token del fragmento; `Auth.jsx` lo canjea mediante POST tras acción del usuario. No se incorpora a solicitudes de mapas ni a registros de consola. La verificación cambia de ruta con reemplazo de historial. El enlace de restablecimiento puede permanecer en el historial local después de su uso; el servidor invalida el token al canjearlo. No se atribuye una reutilización que no exista. |
| GPS, fotos y exportaciones | La captura GPS se inicia únicamente con el botón de `Contribute.jsx`; su lectura se envía por POST y no se guarda en almacenamiento web persistente. Los nombres de archivo se muestran como texto y las fotos se envían al backend; el atributo `accept` y el filtro del cliente son ayudas de UX, no validación de seguridad. Las imágenes de evidencia usan rutas internas y autorización del servidor. La exportación crea un Blob `application/json`, lo descarga y revoca su URL (`Workspace.jsx:597`). |
| Roles y operaciones | `Gate` (`ui.jsx:254`) es un control de presentación. No se observó un secreto, rol o saldo utilizado como sustituto de la autorización del servidor. Moderación, revocación y retirada usan POST mediante el helper común; las respuestas se muestran escapadas. Alterar estado React no concede permisos al backend. |
| Worker | `worker/index.js:3` despacha exclusivamente al binding `ASSETS`; el fallback se limita a GET/HEAD con HTML y cambia el destino a `/index.html`, eliminando la consulta (`:10–13`). No hay proxy a una URL arbitraria, `fetch` global, evaluación de código, lectura de secretos ni serialización del entorno. No se identificó un sumidero SSRF o una salida de credenciales. |

## Análisis automatizado

Semgrep CE 1.185.0 se instaló localmente desde el paquete público desde PyPI (ronda final en un venv dedicado), con cachés y temporales propios en `/var/tmp/haiti-semgrep-20261115`. Los dos intentos previos fallaron por descarga incompleta y falta de espacio en el tmpfs `/tmp`; se eliminaron únicamente sus dos directorios temporales dedicados.

La ejecución OSS usa exclusivamente las reglas JavaScript y TypeScript descargadas del repositorio público `semgrep/semgrep-rules`, fijado al commit `a5ad1714f00c9f7fde980cab0ea1d6dc6d414fd2` (200 archivos de configuración). Se configuraron `--metrics=off`, `--disable-version-check`, `SEMGREP_SEND_METRICS=off` y `SEMGREP_ENABLE_VERSION_CHECK=0`; se retiraron los tokens App/Agent del entorno del proceso. No se usó `--config auto`, servicio de análisis remoto ni recurso de pago, y no se subió el código.

**Ejecución terminada:** salida `0`, 193 reglas ejecutadas, 14 archivos objetivo y aproximadamente 100 % de líneas parseadas, según el resumen de Semgrep. Se cargaron 214 reglas; no todas son aplicables a los lenguajes presentes. El JSON emitió `errors: []` y ninguna regla omitida en `skipped_rules`. El proceso mostró una advertencia al cerrar un subproceso RPC que excedió un segundo; después confirmó el análisis terminado y conservó el resultado JSON completo.

Se obtuvieron **473 avisos, no 473 vulnerabilidades**. Se revisaron sus cinco grupos y los contextos de origen:

| Regla | Avisos | Evaluación |
| --- | ---: | --- |
| `i18next-key-format` | 415 | Convención de nombres de i18next que no aplica al traductor propio del proyecto. No constituye una vulnerabilidad. |
| `jsx-not-internationalized` | 31 | Marcas, identificadores de documentación API, formatos y constantes de texto. Son observaciones de portabilidad; no introducen HTML ejecutable. |
| `react-props-spreading` | 6 | Se comprobaron todos los sitios y sus callers: las props proceden del código y estado de la aplicación, sin un objeto API no confiable expandido como atributos HTML. No se confirmó inyección. |
| `missing-template-string-indicator` | 20 | Duplicados en diez ubicaciones: objetos válidos dentro de interpolaciones `queryString` y un ejemplo JSON/curl literal. Falsos positivos en este contexto. |
| `react-props-in-state` | 1 | El editor territorial mantiene una copia editable inicial del nivel. El diálogo está identificado por territorio y se cierra al recargar/guardar; no decide permisos. |

El archivo `frontend-security-audit.json` conserva el resultado completo, las ubicaciones de cada aviso, su evaluación y el SHA-256 del JSON original. Los 14 hashes de código permanecieron iguales al cerrar la revisión. **Cero vulnerabilidades de seguridad confirmadas tras esta evaluación**, con los límites descritos abajo; no se presenta el barrido como cero avisos ni como certificación de producción.

## Límites y pendientes

- El worker de Sites es estático: no conecta `/v1` al backend y no define por sí mismo CSP/cabeceras de seguridad. Antes de usar esa vía como despliegue funcional hay que comprobar el enrutamiento y las cabeceras del hosting. Las plantillas nginx/Vercel tienen controles propios; esta revisión no verificó un sitio remoto.
- Las teselas se solicitan al proveedor externo. Al centrar un mapa en un aporte, dicho proveedor puede conocer el área del viewport y la IP. La elección del proveedor, sus condiciones y la información de privacidad deben validarse para el piloto; no hay analítica de movimientos añadida por este frontend.
- No se realizaron pentest de navegador, fuzzing, pruebas de extensiones, de proveedores cartográficos o de integración remota en esta tarea. La integración repitió 16 pruebas Node, build y ocho pruebas de navegador; no certifican proveedores remotos ni GPS físico.
- Semgrep OSS y las reglas públicas tienen cobertura limitada, especialmente entre archivos y para la lógica de negocio. Las alertas automáticas requieren comprobar la entrada, el sumidero y las condiciones reales; un resultado limpio no sustituye la revisión manual ni la autorización del servidor.

Las correcciones locales de navegación, intención de corrección y ciclo de vida del mapa están verificadas. No se modificaron datos de producción, servicios compartidos o credenciales reales. La revisión y las descargas de herramientas no generaron cargos de servicios de análisis.

## Ronda final y límites del snapshot

Se repitió el análisis completo después de implementar QR, alias, relaciones, retiro, secciones comunales y administración: salida 0, 473 observaciones, cero errores del scanner, 193 reglas y 14 objetivos. Las referencias de línea de la primera revisión son históricas; los sitios y líneas de la ronda nueva constan en el JSON. Se revisaron los cinco grupos, incluidas las diez ubicaciones de interpolación. La ronda actual se ejecutó después de las correcciones de destino/login y zoom; las fuentes de la aplicación permanecieron iguales durante el scanner. Se actualizó el inventario SHA y se revisó el delta manualmente. Los dos cambios de claves de traducción explican la reducción de 475 a 473 observaciones, sin introducir nuevos grupos. Las pruebas de navegador comprueban conservación del destino e intención después de devolución y ausencia de excepciones al salir durante zoom.

Las nuevas URLs usan rutas fijas y códigos codificados. Las decisiones, relaciones, versiones, propiedad del retiro y tipos de acceso se validan en el servidor. Los nombres locales, referencias y campos del resumen se renderizan como texto React. Ninguna de estas comprobaciones certifica la entrega de correo, GPS físico o permisos reales del hosting.
