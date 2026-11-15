# Revisión técnica de seguridad

Actualización: 2026-11-15. Alcance: implementación local de Haiti Tracking, API, flujos web de identidad, dependencias y configuración de infraestructura. Evidencia: revisión de código, regresiones automatizadas, navegador y contenedores aislados. No se explotó ni modificó producción; este informe no equivale a certificación OWASP ASVS.

## 1. Vulnerabilidades encontradas

| ID | Riesgo | Ubicación | Descripción y alcance |
| --- | --- | --- | --- |
| SEC-01 | Bajo · CWE-204 | `apps/api/app/main.py`: register/resend-verification/forgot-password; `apps/api/app/core.py:230` | El proveedor de correo se invocaba solo en la rama elegible de cada cuenta. Su fallo producía `503` frente a `202` en la otra rama, permitiendo enumerar existencia/elegibilidad. La llamada síncrona también añadía latencia de proveedor dependiente de esa rama. No daba control de la cuenta. Corregido y probado. |
| SEC-02 | Bajo en el entorno revisado | `apps/api/app/core.py:234`; `apps/web/src/App.jsx:40`; `apps/web/src/Auth.jsx:69` | Los enlaces de verificación/recuperación llevaban el token en la consulta de una ruta que no completaba el flujo previsto. La consulta se transmite al servidor/proxy y puede quedar en registros o referencias; no se observó extracción de tokens. Se cambió a rutas dedicadas con fragmento y se comprobó verificación en navegador. |
| SEC-03 | Bajo en el alcance local de desarrollo/build | `apps/web/package.json`: dependencia Vite y lockfile | El template incluía Vite `6.4.2`, identificado como vulnerable durante la auditoría de dependencias. Se actualizó a `8.3.8`; la auditoría posterior dio cero vulnerabilidades y el build pasó. No se atribuye un CVE ni un exploit que no conste en la evidencia. |
| SEC-04 | Medio · integridad/concurrencia | `apps/api/app/main.py:642`: merge_locations | Dos fusiones recíprocas concurrentes podían crear un ciclo o romper la resolución canónica. Requiere operaciones de moderación autorizadas; no es una escalada de rol. Se serializaron los cambios canónicos mediante advisory lock transaccional y se probó la carrera con PostgreSQL. |

No se confirmó una vulnerabilidad explotable crítica o alta en el código revisado. La imagen API conserva avisos OS HIGH cuya alcanzabilidad no está demostrada; se detallan abajo y no se declaran resueltos. Los riesgos anteriores se calibran para el entorno local y sus prerrequisitos; no se presume exposición o explotación de un servicio remoto.

## 2. Correcciones implementadas

| Archivos | Cambio | Verificación |
| --- | --- | --- |
| `apps/api/app/core.py`, `models.py`, `main.py`, `cli.py` | Token y `MailJob` cifrado se guardan en una transacción; proveedor después de la respuesta genérica, lease/reintento e idempotencia estable. Registro, reenvío y recuperación mantienen `202` ante fallo del proveedor | Tres regresiones del oráculo y prueba de trabajo durable cifrado con fallo de conexión |
| `apps/api/app/core.py`, `apps/web/src/App.jsx`, `Auth.jsx` | Enlaces `/verificar#token=…` y `/restablecer#token=…`; lectura del fragmento y canje por POST. El fragmento evita enviar el token como parte de la URL HTTP | Pruebas de registro/verificación/reset, un solo uso, expiración y sesión revocada; verificación web completada en navegador |
| `apps/web/package.json`, `pnpm-lock.yaml` | Vite `6.4.2` → `8.3.8` y plugin compatible fijado | Auditoría frontend cero vulnerabilidades y build satisfactorio en la ronda registrada |
| `apps/api/app/main.py`, `tests/test_postgis.py` | Fusiones y publicación comparten `pg_advisory_xact_lock(684172031)` antes de releer/bloquear registros | Fusiones recíprocas concurrentes: respuestas `200`/`422`; ambos códigos resuelven a la misma entidad canónica |
| `apps/api/app/core.py`, `schemas.py` | DTO público con `PublicAddress` explícito; se descartan claves adicionales como `owner_email` o GPS. Coordenadas/tipos y campos mutables se validan con Pydantic | Regresión inyecta campos privados en address y verifica su ausencia en la respuesta; residencias/ocultos excluidos de todas las lecturas públicas |
| `apps/api/app/main.py` | HTTPS obligatorio en producción salvo health, CSP y cabeceras también en errores tempranos; cuerpos limitados a 64 KB salvo fotos con límite específico | Suite final con guard HTTPS, límites de cuerpo y rechazo observable sin registrar entrada sensible |

Además se verificaron autorización del servidor por objeto/rol, MFA de staff, Argon2id, sesiones revocables y cookies HttpOnly/Secure/SameSite=Lax; claves API con hash, propiedad, cuotas, revocación y propietario activo; CSRF y orígenes exactos; consultas parametrizadas; archivos re-encoded sin EXIF y evidencias privadas; rechazo de autoaprobación y de campos financieros/canónicos enviados por el cliente.

El runtime PostgreSQL se separa del propietario, sin superusuario ni `BYPASSRLS`, con políticas RLS explícitas y auditoría de solo inserción/lectura. La API rechaza roles privilegiados y secretos/configuraciones de ejemplo en producción. El catálogo HDX/CNIGS/OCHA conserva fuente, licencia, checksum y polígonos de sus 721 territorios; no equivale a cobertura de establecimientos verificados. No se exige GPS al consultar; la observación del colaborador queda fuera del DTO público.

## 3. Resultados de las pruebas

**Ronda final local del 2026-11-15:**

```text
pytest: 56 passed, 2 warnings in 67.61s (Windows); 72.40s (Linux)
Node (web + Sites + GPS fixtures): 12 passed, 0 failed
Bandit: 0 resultados, 0 errores
pip-audit (51 dependencias auditadas): 0 vulnerabilidades conocidas
```

Incluye seis pruebas PostgreSQL/PostGIS sobre una base desechable: distancias/índice espacial, RLS y auditoría append-only, carreras de publicación/fusión, límites territoriales y ciclos de edificios/índice de alias. Las regresiones nuevas comprueban QR decodificado por un lector independiente, enlaces públicos confiables, relaciones privadas ocultas, alias, FK/ciclos, fusiones con historial, retiro con propietario/versión, corroboración ante 150 m y purga GPS en simulación/aplicación. Se valida búsqueda de secciones desde comuna/departamento/país, contrato OpenAPI y edición territorial con conflicto de versión. Las dos advertencias son deprecación de TestClient/httpx y reflexión SQLAlchemy del tipo geography; no son fallos de los controles ensayados.

La suite independiente de seguridad cubre CSRF/origen, mass assignment de rol/estado/recompensa, sesión caducada, MFA real cifrado, expiración/propósito/replay de tokens, revocación de sesiones, uniformidad del correo ante fallos, IDOR de propuestas/apps/claves/evidencias, idempotencia por usuario, cuota `429`/Retry-After, NaN/límites, inyección SQL en búsquedas, no-store, privacidad en search/code/nearby/geocode/reverse, archivo falso, eliminación EXIF y autoaprobación.

**Evidencia del hallazgo SEC-01:** antes de la corrección, los tres casos fallaron con diferencias `202`/`503`. Después pasan; una caída simulada de conexión devuelve `202` y conserva un trabajo cifrado `pending` con intento contabilizado. No se midió igualdad estadística de latencia real, pero el proveedor dejó de ejecutarse dentro del camino de respuesta HTTP.

**Navegador:** el responsable de integración comprobó el enlace de verificación por fragmento hasta completar la verificación de cuenta. El alcance visual y los demás flujos de navegador se registran por separado; una suite backend no certifica toda la interfaz.

**Prevención de secretos:** `scripts/check-secrets.py` compara fichero/tipo/hash contra candidatos revisados y conserva equivalencia Windows/Linux, comprobada en una regresión. La salida CI solo contiene fichero y línea. Baseline en `docs/secrets-scan.json`; no se aceptan automáticamente valores nuevos. No había historial Git anterior que inspeccionar.

**Dependencias y análisis:** `pip check` no encontró requisitos rotos. `docs/python-dependency-audit.json` registra cero vulnerabilidades conocidas; el auditor se ejecutó en un entorno temporal sin cambiar requisitos. `docs/python-sast.json` registra cero resultados y cero errores en su ronda. La auditoría frontend tras actualizar Vite dio cero vulnerabilidades y el build pasó. Los análisis de dependencias/SAST corresponden a sus rondas registradas y no reemplazan la revisión de cada modificación posterior. Se recomienda fijar hashes de distribución además de versiones.

**Infraestructura y recuperación:** se ejecutó Compose aislado `haiti-tracking-verify` (DB `55433`, API `8002`, web `4174`), con API sin root. `docs/backup-roundtrip.json` registra un backup sintético cifrado/restaurado con 721 territorios, código conservado, auditoría y columna espacial; la clave de prueba no se retuvo. Las plantillas Render/Compose/Vercel pasaron validación de esquema en la ronda correspondiente. Ninguna de estas verificaciones locales prueba un despliegue remoto.

Los avisos de pytest están identificados arriba. Bandit marcó como candidato un DDL interpolado: los identificadores/eventos provienen únicamente de dos tuplas literales de migración, nunca de entradas; se documentó la supresión puntual B608 y se repitió el análisis.

## 4. Problemas pendientes

| Pendiente | Riesgo residual / motivo |
| --- | --- |
| Alcance del barrido de secretos | detect-secrets 1.5.0 revisó los archivos de Git sin validaciones de credenciales por red: Candidatos revisados en `secret-review.json`; hashes públicos y fixtures/credenciales de CI sintéticos. Cero credenciales reales confirmadas. No existían commits anteriores. Ver `secret-review.json`; no demuestra ausencia absoluta ni audita otros repositorios |
| Servicios y destino remoto | Render devolvió `UNAUTHORIZED`; no hubo despliegue remoto. Faltan comprobar TLS/proxy, roles reales, Resend entregable, dominio remitente y S3 privado del entorno elegido |
| Recuperación operativa | El ensayo usó datos y clave sintéticos; no verifica custodia de claves, objetos externos, copias off-site programadas, retención ni RPO/RTO de producción |
| Reintentos y alertas | Programar `deliver-mail` y monitorizar pendientes/intentos agotados; no existe cron ni alertas remotas creadas por esta entrega |
| Carga/abuso | Las carreras concretas pasan; faltan estrés, múltiples procesos, abuso distribuido, fuzzing exhaustivo y agotamiento de recursos de imágenes |
| Datos y privacidad operativa | Validar actualidad territorial en la zona piloto, moderación de referencias sensibles, plazos definitivos de retención GPS/evidencias y ejecución programada de la purga, traducción nativa y GPS físico |
| Auditoría completa de producción | Las pruebas locales y SAST no certifican todos los controles ASVS, hosting, accesibilidad, incidentes o ausencia absoluta de fallos |

## 5. Recomendaciones adicionales

1. Mantener el barrido CI de candidatos nuevos y revisar cada cambio de secreto; evaluar cualquier rotación con impacto y autorización antes de actuar sobre producción. No se revocó ninguna credencial.
2. Preparar staging aislado con rol de migraciones separado del runtime, TLS y orígenes exactos; ejecutar ahí el flujo completo con correo y almacenamiento reales antes de promover el mismo commit probado.
3. Configurar reintentos de correo cada cinco minutos, alertas restringidas y custodia/recuperación de claves de cifrado; probar restauración integral y registrar RPO/RTO medidos.
4. Aplicar retención aprobada a GPS/evidencias, formar moderadores, validar un piloto territorial y calibrar cuotas/capacidad con pruebas de carga.
5. Repetir auditorías de dependencias e imágenes en CI, fijar hashes cuando proceda y revisar la migración del TestClient al actualizar el stack.

No se deben habilitar dinero real ni compartición de residencias sin los requisitos comerciales, financieros y de titularidad del documento maestro.

## 6. Estado de seguridad

El último full pytest pasa con **56 pruebas, incluidos seis casos PostGIS**, y cubre los cambios finales enumerados en este informe. Los hallazgos de correo, enlaces/tokens, dependencia del template y concurrencia canónica tienen correcciones y evidencia de verificación con los límites señalados. Las autorizaciones, privacidad y credenciales disponen de regresiones locales comprobadas.

No se explotó producción, cobraron pagos, revocaron credenciales ni alteraron datos de RD Marketplace. El sistema sigue pendiente de los controles operativos y de despliegue descritos; **no se declara certificación de producción ni ausencia absoluta de vulnerabilidades**. El barrido de archivos iniciales está documentado con sus límites; CI rechaza candidatos nuevos sin imprimir sus valores.

## Ampliación de controles y riesgos residuales

- `models.py`, `core.py`, `main.py`, `schemas.py`, migración 0003: FK, comprobaciones de autorreferencia/ciclo, validación al enviar y aprobar, serialización de mutaciones API y referencias públicas redactadas. Las fusiones preservan alias, redirecciones y versiones; el catálogo usa versiones esperadas y solo un administrador puede editarlo.
- `main.py`, `cli.py`: retiro atómico por el autor antes de decisión, sin borrar historial. La purga GPS es dry-run por defecto, solo elimina observaciones vencidas al aplicar, registra IDs sin coordenadas y exige corroboración adicional después. No se ejecutó sobre producción ni se aprobó una política legal definitiva.
- `Contribute.jsx`, `Workspace.jsx`, `Places.jsx`, `ui.jsx`: resumen previo al envío, recibo con fecha/ID/estado, recuperación de fotos, editor de alias/relaciones y QR limitado a enlace público. El cierre de diálogos respeta la operación pendiente y conserva foco. Backend, no UI, decide propiedad y rol.
- `deploy/api.Dockerfile`, `deploy/web.Dockerfile`: bases fijadas por digest, actualizaciones OS y usuario API sin root. Se verificó la desaparición de los avisos corregibles de zlib/libxslt. **Quedan 206 pares paquete/CVE en API: 47 HIGH en 11 CVE, 89 MEDIUM, 65 LOW, 5 UNKNOWN; 0 CRITICAL y sin FixedVersion residual publicado en la base consultada.** Web: cero coincidencias OS en esta ronda. Son candidatos de paquete, no 47 ataques remotos demostrados. Riesgo pendiente de seguimiento del proveedor y evaluación de alcanzabilidad; no se presenta como imagen libre de vulnerabilidades. Evidencia y versiones: `CONTAINER-AUDIT.md`, `container-audit.json`.
- Frontend: Semgrep CE, reglas públicas fijadas, sin subir código: 475 observaciones en cinco grupos, cero errores del scanner. Triage y límite del snapshot/delta final en `FRONTEND-SECURITY.md` y JSON. No equivalen a 475 vulnerabilidades.
- Navegador: retiro y recibos; persistencia de alias/sección/fuente; QR, copia, Escape y retorno de foco; MFA administrativo, resumen real, edición territorial con versión distinta, auditoría filtrada, FR/HT. El resumen y envío con GPS ficticio ya pasan en Chromium aislado; no se interpreta como comprobación con hardware físico.
- Backups: además del ensayo sintético, se verificó antes de 0003 la restauración cifrada de ambos SQLite locales y del PostgreSQL local, conservando catálogo e integridad. `schema-backup-check.json`. La custodia off-site y la recuperación de objetos en un proveedor real siguen pendientes.
- CI remoto, escenarios web restantes del maestro y staging gratuito pendientes; el primer push usa `[skip ci]` porque no se pudo verificar cuota/cap de gasto. Render sin autenticar y Supabase sin cupo gratuito aislado. No se usaron recursos pagados ni se modificó RD Marketplace.

La suite final también pasó íntegra en Linux, dentro de la imagen API, con checkout de solo lectura y base de pruebas aislada: 56 passed, 2 warnings, 72.40 s. El primer arnés de contenedor falló porque `/app` no incluía la estructura raíz requerida por el test del scanner; se corrigió el montaje y el directorio de caché de pruebas, sin relajar ninguna aserción. La prueba nueva de reverse/geocode comprueba zona administrativa PostGIS, filtro por comuna y punto exterior.

Actualización E2E: 5 pruebas Playwright pasaron en Chromium local aislado, con autorización del propietario. Cubren búsqueda/QR, borrador/alias/retiro, rechazo sin GPS/admin, denegación simulada y revisión antes de envío presencial simulado. Se verificó estado resultante en SQLite por separado. Se agregaron dos regresiones que impiden rutas arbitrarias y reutilizar una base existente en el fixture; correo/S3 quedan deshabilitados y los secretos de sesión son efímeros. WEB-E2E.md distingue estos resultados del GPS físico, escenarios web restantes y CI remoto.
